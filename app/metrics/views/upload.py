from django.shortcuts import render
from metrics.views.common import get_tabs
from django import forms
from django.forms.widgets import FileInput, Select, CheckboxInput
import re
import csv
import io
from metrics import import_utils, models
import traceback
from django.core.exceptions import ValidationError
from django.db import transaction
import datetime
from django.contrib.auth.decorators import login_required


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

                node_main = request.user.get_node()
                current_time = datetime.datetime.now()
                import_context = import_utils.LegacyImportContext(
                    user=request.user,
                    node_main=node_main,
                    timestamps=(
                        current_time,
                        current_time
                    ),
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
                            })
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
    return render(
        request,
        'metrics/upload.html',
        context={
            "title": "Upload data",
            **get_tabs(request),
            "forms": forms,
        }
    )
