from django.shortcuts import render
from .common import get_tabs
from django import forms
from django.forms.widgets import FileInput, Select
import re
import csv
import io
from metrics import import_utils, models
import traceback
from django.core.exceptions import ValidationError


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
        label="File",
        widget=FileInput(attrs={"class": "form-control"}),
    )
    upload_type = forms.ChoiceField(
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


def _parse_legacy_event(context, row):
    updated_data = import_utils.legacy_to_current_event_dict(row)
    return context.event_from_dict(updated_data)


def _parse_legacy_impact_metrics(context, row):
    updated_data = import_utils.demographic_from_dict(row)
    return context.impact_from_dict(updated_data)


def _parse_legacy_quality_or_demographic_metrics(context, row):
    updated_data = import_utils.legacy_to_current_quality_or_demographic_dict(row)
    return context.demographic_from_dict(updated_data)


def upload_data(request):
    forms = [
        DataUploadForm(
            request.POST if request.method == "POST" else None,
            request.FILES if request.method == "POST" else None,
            fixed_type=upload_type["id"],
            title=upload_type["title"],
            description=upload_type["description"],
            prefix=upload_type["id"],
        )
        for upload_type in UPLOAD_TYPES.values()
    ]

    if request.method == "POST":
        for form in forms:
            if form.has_changed() and form.is_valid():
                data = form.cleaned_data
                upload_type = data["upload_type"]
                file = data["file"]
                importer = {
                    "events": _parse_legacy_event,
                    "demographic_quality_metrics": _parse_legacy_quality_or_demographic_metrics,
                    "impact_metrics": _parse_legacy_impact_metrics,
                }[upload_type]
                node_main_id = f"ELIXIR-{request.user.username.upper()}"
                node_main = models.Node.objects.get(name=node_main_id)
                import_context = import_utils.ImportContext(
                    user=request.user,
                    node_main=node_main,
                )

                csv_stream = io.StringIO(file.read().decode())
                reader = csv.DictReader(csv_stream, delimiter=',')
                for (index, row) in enumerate(reader):
                    try:
                        importer(import_context, row)
                    except ValidationError as e:
                        traceback.print_exc()
                        form.add_error(None, f"Failed to parse '{upload_type}' row {index} : {e}")

    return render(
        request,
        'dash_app/upload.html',
        context={
            "title": "Upload data",
            **get_tabs(request),
            "forms": forms,
        }
    )
