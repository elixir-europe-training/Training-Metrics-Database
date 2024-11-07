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
from django.http import HttpResponse
from metrics.models.questions import QuestionSuperSet
from metrics.models.common import Event
from django.urls import reverse
from django.utils.http import urlencode


UPLOAD_TYPES = {
    upload_type["id"]: upload_type
    for upload_type in [
        {
            "id": "events",
            "title": "Events",
            "description": ""
        },
        {
            "id": "demographic_quality_metrics",
            "title": "Demographic and quality metrics",
            "description": ""
        },
        {
            "id": "impact_metrics",
            "title": "Impact metrics",
            "description": ""
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

    def __init__(self, *args, title=None, description=None, fixed_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fixed_type = fixed_type
        if self.fixed_type is not None:
            upload_type = self.fields["upload_type"]
            upload_type.initial = self.fixed_type
            upload_type.disabled = True

        self.description = (
            None
            if description is None
            else re.split("\n\n+", description)
        )
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


@login_required
def upload_data(request, event_id=None):
    node = request.user.get_node()
    question_supersets = QuestionSuperSet.objects.filter(node = node)

    event = get_object_or_404(models.Event, id=event_id) if event_id else None
    file_match = f"^.+-{event.id}\.csv$" if event else "^.+\.csv$"

    if event and (event.is_locked or request.user.get_node() != event.node_main):
        raise PermissionDenied(f"You do not have permissions the upload data to event {event.id}")

    upload_types = {
        key: value
        for key, value in UPLOAD_TYPES.items()
        if event is None or key != "events"
    }
    forms = [
        DataUploadForm(
            request.POST if request.method == "POST" else None,
            request.FILES if request.method == "POST" else None,
            fixed_type=upload_type["id"],
            title=upload_type["title"],
            description=upload_type["description"],
            prefix=upload_type["id"],
        )
        for upload_type in upload_types.values()
    ]

    if request.method == "POST":
        for form in forms:
            if form.has_changed() and form.is_valid():
                data = form.cleaned_data
                upload_type = data["upload_type"]
                file = data["file"]

                if not re.match(file_match, file.name):
                    form.add_error(None, f"Incorrect file name. The file name needs to match the following regex: '{file_match}'")
                else:
                    node_main = request.user.get_node()
                    current_time = datetime.datetime.now()
                    import_context = import_utils.LegacyImportContext(
                        user=request.user,
                        node_main=node_main,
                        timestamps=(
                            current_time,
                            current_time
                        ),
                        fixed_event=event
                    )

                    (parser, importer, view_transforms) = {
                        "events": (
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
                        ),
                        "demographic_quality_metrics": (
                            import_utils.legacy_to_current_quality_or_demographic_dict,
                            import_context.quality_or_demographic_from_dict,
                            {"summary": summary_output}
                        ),
                        "impact_metrics": (
                            import_utils.legacy_to_current_impact_dict,
                            import_context.impact_from_dict,
                            {"summary": summary_output}
                        ),
                    }[upload_type]

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
            "question_supersets": question_supersets,
            **get_tabs(request, view_name="event-list" if event else None),
            "forms": forms,
        }
    )


@login_required
def download_event_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="event_template.csv"'

    event_metrics = ['Title',
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

    writer = csv.writer(response)
    writer.writerow(event_metrics)
    return response

def download_questionsuperset_template(request, questionsuperset_id, type):
    # Here we also need to filter out on what type/category....
    questionsuperset = get_object_or_404(QuestionSuperSet, id = questionsuperset_id)
    print(questionsuperset)
    print(type)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{questionsuperset.name}_{type}_template.csv"'
    writer = csv.writer(response)

    # Write each question in the QuestionSuperSet to the CSV
    question_texts = []
    question_slugs = []
    question_answers = []

    # Filter based on the type parameter
    if type == 'Demographic and quality metrics':
        filtered_sets = questionsuperset.question_sets.all()
       # filtered_sets = questionsuperset.question_sets.filter(type__in=['demo', 'qual']) update this!!
    elif type == 'Impact metrics':
        filtered_sets = questionsuperset.question_sets.all()
       # filtered_sets = questionsuperset.question_sets.filter(type='impact')
    else:
        # Node has to be here too
        filtered_sets = questionsuperset.question_sets.all()


    for set in filtered_sets:
        for question in set.questions.all():
            question_texts.append(question.text)
            question_slugs.append(question.slug)

      #      answers_list = [answer.text for answer in question.answers.all()]
      #      answers_dict = {f"{i+1}": answer.text for i, answer in enumerate(question.answers.all())}

    writer.writerow(question_texts)
    writer.writerow(question_slugs)
    
    return response