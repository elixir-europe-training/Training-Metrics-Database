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
from metrics.models.questions import QuestionSuperSet, ResponseSet, Response
from django.http import HttpResponseNotFound
from metrics.forms import QuestionSetForm


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
            "template_url": reverse_lazy("download_template", kwargs={"data_type": "metrics", "slug": "demographic-quality"})
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


def get_event_context(user, node_main, event):
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
    return (
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


def get_question_import_context(super_set, user, node_main, event, is_legacy_data=False):
    forms = [
        QuestionSetForm.from_question_set(qs)
        for qs in super_set.question_sets.all()
    ]
    legacy_extractors = (
        {
            "quality": [
                import_utils.legacy_extract_quality,
                import_utils.legacy_extract_event_id
            ],
            "demographic": [
                import_utils.legacy_extract_demographic,
                import_utils.legacy_extract_event_id
            ],
            "quality-and-demographic": [
                import_utils.legacy_extract_quality,
                import_utils.legacy_extract_demographic,
                import_utils.legacy_extract_event_id
            ],
            "impact": [
                import_utils.legacy_extract_impact,
                import_utils.legacy_extract_event_id
            ],
        }.get(super_set.slug, None)
        if is_legacy_data
        else None
    )
    def _form_parser(entry):
        entry = (
            import_utils.use_extractors(entry, legacy_extractors)
            if legacy_extractors
            else entry
        )
        errors = []
        entry_forms = [
            form(entry)
            for form in forms
        ]
        for form in entry_forms:
            if not form.is_valid():
                errors.extend(form.errors)
        if len(errors) > 0:
            raise ValidationError(errors)
        
        current_event = event
        event_id = entry["event_id"]
        if not current_event:
            try:
                event_id = entry["event_id"]
                current_event = models.Event.objects.filter(id=event_id).first()
            except (KeyError, ValueError) as e:
                raise ValidationError(f"Failed to parse 'event_id': {e}")
        
        if not current_event:
            raise ValidationError(
                f"Event with id '{event_id}', does not exist"
            )

        if current_event.is_locked or user.get_node() != current_event.node_main:
            raise ValidationError(
                f"The metrics for the event {current_event.id} can not"
                f" be updated by the current user: {user.username}"
            )
        return (
            current_event,
            [
                (form.question_set, form.cleaned_data)
                for form in entry_forms
            ]
        )
    
    def _importer(entry):
        (event, response_sets) = entry

        for qs, data in response_sets:
            rs = ResponseSet(user=user, event=event, question_set=qs)
            rs.save()
            for answer in data.values():
                all_answers = answer if isinstance(answer, list) else [answer]
                for a in all_answers:
                    r = Response(response_set=rs, answer=a)
                    r.save()

    return (
        _form_parser,
        _importer,
        {"summary": summary_output}
    )


def response_upload(request, event):
    settings = models.SystemSettings.get_settings()
    node = request.user.get_node()
    question_supersets = settings.get_upload_sets()
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
                data_type=super_set,
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

                    (parser, importer, view_transforms) = (
                        get_event_context(
                            request.user,
                            node_main,
                            event
                        )
                        if upload_type == "events"
                        else get_question_import_context(
                            upload_type,
                            request.user,
                            node_main,
                            event,
                            True
                        )
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
    node = request.user.get_node()
    event = get_object_or_404(models.Event, id=event_id) if event_id else None

    if not node:
        raise PermissionDenied(f"You have to be associated with a node to upload data.")

    if event and (event.is_locked or node != event.node_main):
        raise PermissionDenied(f"You do not have permissions the upload data to event {event.id}")
    
    return response_upload(request, event)


def download_csv(lines, filename="template"):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
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
        return download_csv([event_metrics], "event-template")
    
    elif data_type == "metrics":
        questionsuperset = get_object_or_404(QuestionSuperSet, slug=slug)

        # Write each question in the QuestionSuperSet to the CSV
        question_texts = ["event_id"]
        question_slugs = ["event_id"]
        question_sample = [1]

        filtered_sets = questionsuperset.question_sets.all()

        for question_set in filtered_sets:
            for question in question_set.questions.all():
                question_texts.append(question.text)
                question_slugs.append(question.slug)
                first_answer = question.answers.first()
                question_sample.append(first_answer.slug if first_answer else None)
        

        return download_csv([question_slugs, question_sample], f"metrics-{slug}-template")

    return HttpResponseNotFound("Template not found")
