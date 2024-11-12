from django.shortcuts import render, get_object_or_404
from metrics.views.common import get_tabs
from django import forms
from django.forms.widgets import FileInput, Select, CheckboxInput
from django.shortcuts import get_object_or_404
import re
import csv
import io
import json
from metrics import import_utils, models
import traceback
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
import datetime
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.utils.http import urlencode
from django.http import HttpResponse
from metrics.models.questions import QuestionSuperSet
from django.http import HttpResponseNotFound


UPLOAD_TYPES = {
    upload_type["id"]: upload_type
    for upload_type in [
        {
            "id": "events",
            "title": "Events",
            "description": "",
            "template_url": reverse_lazy("download_template", kwargs={"data_type": "event", "slug": "base"})
        },
        {
            "id": "demographic_quality_metrics",
            "title": "Demographic and quality metrics",
            "description": "",
            "template_url": reverse_lazy("download_template", kwargs={"data_type": "metrics", "slug": "demographic_quality"})
        },
        {
            "id": "impact_metrics",
            "title": "Impact metrics",
            "description": "",
            "template_url": reverse_lazy("download_template", kwargs={"data_type": "metrics", "slug": "impact"})
        },
    ]
}


class DataUploadForm(forms.Form):
    file = forms.FileField(
        label="CSV batch file",
        widget=FileInput(attrs={"class": "form-control"}),
    )
    upload_type = forms.ChoiceField(
        label="Data type",
        choices=(
            (upload_id, upload_type["title"])
            for (upload_id, upload_type) in UPLOAD_TYPES.items()
        ),
        widget=Select(attrs={"class": "form-control d-none"}),
    )

    def __init__(self, *args, title=None, description=None, associated_templates=None, data_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_type = data_type
        self.associated_templates=associated_templates

        self.description = description
        self.title = title


def summary_output(items: list):
    return f"Successfully uploaded {len(items)} objects."


def events_actions_output(items: list):
    item_ids = [item.id for item in items]
    base_url = reverse("event-list")
    query_params = {"id": item_ids}
    view_list_url = f"{base_url}?{urlencode(query_params, doseq=True)}"
    return [
        ("View events", view_list_url)
    ]


def table_output(columns: dict):
    def _table_output(items: list):
        return {
            "headers": [value for value in columns.values()],
            "content": [
                [getattr(item, key, None) for key in columns.keys()]
                for item in items
            ]
        }
    return _table_output


def get_import_context(data_type, user, node_main, event):
    current_time = datetime.datetime.now()
    import_context = import_utils.LegacyImportContext(
        user=user,
        node_main=node_main,
        timestamps=(
            current_time,
            current_time
        ),
        fixed_event=event
    )
    if data_type == "events":
        return (
            import_context,
            import_utils.legacy_to_current_event_dict,
            import_context.event_from_dict,
            {
                "summary": summary_output,
                "table": table_output({
                    "id": "Event Code",
                    "title": "Title",
                    "date_start": "Start date",
                    "date_end": "End date"
                }),
                "actions": events_actions_output
            }
        )
    elif data_type == "demographic_quality_metrics":
        (
            import_context,
            import_utils.legacy_to_current_quality_or_demographic_dict,
            import_context.quality_or_demographic_from_dict,
            {"summary": summary_output}
        )
    elif data_type == "impact_metrics":
        return (
            import_context,
            import_utils.legacy_to_current_impact_dict,
            import_context.impact_from_dict,
            {"summary": summary_output}
        )


def legacy_upload(request, event):
    node = request.user.get_node()
    upload_types = {
        key: value
        for key, value in UPLOAD_TYPES.items()
        if event is None or key != "events"
    }
    forms = [
        DataUploadForm(
            request.POST if request.method == "POST" else None,
            request.FILES if request.method == "POST" else None,
            data_type=upload_type["id"],
            title=upload_type["title"],
            description=upload_type["description"],
            prefix=upload_type["id"],
            associated_templates=[(upload_type["title"], str(upload_type["template_url"]))]
        )
        for upload_type in upload_types.values()
    ]
    file_match = f"^.+-{event.id}\.csv$" if event else "^.+\.csv$"

    if request.method == "POST":
        for form in forms:
            if form.has_changed() and form.is_valid():
                data = form.cleaned_data
                upload_type = form.data_type
                file = data["file"]

                if not re.match(file_match, file.name):
                    form.add_error(None, f"Incorrect file name. The file name needs to match the following regex: '{file_match}'")
                else:
                    node_main = request.user.get_node()

                    (import_context, parser, importer, view_transforms) = get_import_context(
                        upload_type,
                        request.user,
                        node_main,
                        event
                    )

                    csv_stream = io.StringIO(file.read().decode())
                    reader = csv.DictReader(csv_stream, delimiter=',')
                    entries = []
                    for (index, row) in enumerate(reader):
                        try:
                            entries.append(parser(row))
                        except ValidationError as e:
                            traceback.print_exc()
                            form.add_error(None, f"Failed to parse '{upload_type}' row {index} : {e}")

                    if len(form.errors) == 0:
                        items = []
                        try:
                            with transaction.atomic():
                                items = [importer(entry) for entry in entries]

                            form.outputs = {
                                key: view_transform(items)
                                for key, view_transform in view_transforms.items()
                            }
                        except Exception as e:
                            traceback.print_exc()
                            form.add_error(None, f"Failed to import '{upload_type}': {e}")
    
    title = (
        f"Upload data for event: {event.title}" 
        if event
        else "Upload data"
    )
    return render(
        request,
        'metrics/upload.html',
        context={
            "title": title,
            **get_tabs(request, view_name="event-list" if event else None),
            "forms": forms,
        }
    )


def response_upload(request, event):
    node = request.user.get_node()
    question_supersets = QuestionSuperSet.objects.filter(
        use_for_upload=True
    )
    event_upload_form = None
    if event is None:
        upload_type = UPLOAD_TYPES["events"]
        event_upload_form = DataUploadForm(
            request.POST if request.method == "POST" else None,
            request.FILES if request.method == "POST" else None,
            data_type=upload_type["id"],
            title=upload_type["title"],
            description=upload_type["description"],
            prefix=upload_type["id"],
            associated_templates=[(upload_type["title"], str(upload_type["template_url"]))]
        )
    forms = [
        *([event_upload_form] if event_upload_form else []),
        *[
            DataUploadForm(
                request.POST if request.method == "POST" else None,
                request.FILES if request.method == "POST" else None,
                data_type=super_set.slug,
                title=super_set.name,
                prefix=super_set.slug,
                description=super_set.description,
                associated_templates=[(
                    super_set.name,
                    reverse("download_template", kwargs={"data_type": "metrics", "slug": super_set.slug})
                )]
            )
            for super_set in question_supersets
        ]
    ]
    file_match = f"^.+-{event.id}\.csv$" if event else "^.+\.csv$"

    if request.method == "POST":
        for form in forms:
            if form.has_changed() and form.is_valid():
                data = form.cleaned_data
                upload_type = form.data_type
                file = data["file"]

                if not re.match(file_match, file.name):
                    form.add_error(None, f"Incorrect file name. The file name needs to match the following regex: '{file_match}'")
                else:
                    node_main = request.user.get_node()

                    (import_context, parser, importer, view_transforms) = (
                        get_import_context(
                            upload_type,
                            request.user,
                            node_main,
                            event
                        )
                        if upload_type == "events"
                        else (None, None, None, None)
                    )

                    csv_stream = io.StringIO(file.read().decode())
                    reader = csv.DictReader(csv_stream, delimiter=',')
                    entries = []
                    for (index, row) in enumerate(reader):
                        try:
                            entries.append(parser(row))
                        except ValidationError as e:
                            traceback.print_exc()
                            form.add_error(None, f"Failed to parse '{upload_type}' row {index} : {e}")

                    if len(form.errors) == 0:
                        items = []
                        try:
                            with transaction.atomic():
                                items = [importer(entry) for entry in entries]

                            form.outputs = {
                                key: view_transform(items)
                                for key, view_transform in view_transforms.items()
                            }
                        except Exception as e:
                            traceback.print_exc()
                            form.add_error(None, f"Failed to import '{upload_type}': {e}")

    title = (
        f"Upload data for event: {event.title}" 
        if event
        else "Upload data"
    )
    return render(
        request,
        'metrics/upload.html',
        context={
            "title": title,
            **get_tabs(request, view_name="event-list" if event else None),
            "forms": forms,
        }
    )


@login_required
def upload_data(request, event_id=None):
    settings = models.SystemSettings.get_settings()
    node = request.user.get_node()
    event = get_object_or_404(models.Event, id=event_id) if event_id else None

    if not node:
        raise PermissionDenied(f"You have to be associated with a node to upload data.")

    if event and (event.is_locked or node != event.node_main):
        raise PermissionDenied(f"You do not have permissions the upload data to event {event.id}")
    
    if settings.has_flag("use_new_model_upload"):
        return response_upload(request, event)
    else:
        return legacy_upload(request, event)


def download_csv(lines):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="event_template.csv"'
    writer = csv.writer(response)

    for line in lines:
        writer.writerow(line)
    return response


@login_required
def download_template(request, data_type, slug):
    if data_type == "event" and slug == "base":
        event_metrics = [
            'Title',
            'ELIXIR Node',
            'Start Date',
            'End Date',
            'Event type',
            'Funding',
            'Organising Institution/s',
            'Location (city, country)',
            'EXCELERATE WP',
            'Target audience',
            'Additional ELIXIR Platforms involved',
            'ELIXIR Communities involved',
            'No. of participants',
            'No. of trainers/ facilitators',
            'Url to event page/ agenda'
        ]
        return download_csv([event_metrics])
    
    elif data_type == "metrics":
        settings = models.SystemSettings.get_settings()
        if settings.has_flag("use_new_model_upload"):
            questionsuperset = get_object_or_404(QuestionSuperSet, slug=slug)

            # Write each question in the QuestionSuperSet to the CSV
            question_texts = []
            question_slugs = []

            filtered_sets = questionsuperset.question_sets.all()

            for question_set in filtered_sets:
                for question in question_set.questions.all():
                    question_texts.append(question.text)
                    question_slugs.append(question.slug)

            return download_csv([question_texts, question_slugs])
        else:
            fields = []
            if slug == "impact":
                fields = [
                    "Where did you see the course advertised?",
                    "What is your career stage?",
                    "What is your employment sector?",
                    "What is your country of employment?",
                    "What is your gender?",
                    "Have you used the tool(s)/resource(s) covered in the course before?",
                    "Will you use the tool(s)/resource(s) covered in the course again?",
                    "Would you recommend the course?",
                    "Please tell us your overall rating for the entire course",
                    "May we contact you by email in the future for more feedback?",
                    "What part of the training did you enjoy the most?",
                    "What part of the training did you enjoy the least?",
                    "The balance of theoretical and practical content was",
                    "What other topics would you like to see covered in the future?",
                    "Any other comments?",
                ]
                
            elif slug == "demographic_quality":
                fields = [
                    "Which training event did you take part in?",
                    "How long ago did you attend the training?",
                    "What was your main reason for attending the training?",
                    "What was your main reason for attending the training? (Other)",
                    "How often did you use the tool(s)/ resource(s), covered in the training, BEFORE attending the training?",
                    "How often do you use the tool(s)/ resource(s), covered in the training, AFTER having attended the training?",
                    "Do you feel that you are able to explain to others what you learnt in the training?",
                    "Do you feel that you are able to explain to others what you learnt in the training? (Other)",
                    "Are you now able to use the tool(s)/ resource(s) covered in the training:",
                    "Are you now able to use the tool(s)/ resource(s) covered in the training: (Other)",
                    "How did the training event help with your work? [select all that apply]",
                    "How did the training event help with your work? (Other)",
                    "Attending the training event led to/ facilitated: [select all that apply]",
                    "Attending the training event led to/ facilitated: (Other),Please elaborate on any impact",
                    "How many people have you shared the skills and/or knowledge that you learned during the training, with?",
                    "Would you recommend the training to others?",
                    "Any other comments?",
                ]
            return download_csv([["event_code", *fields]])

    return HttpResponseNotFound("Template not found")
