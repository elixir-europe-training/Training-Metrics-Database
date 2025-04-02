from django.shortcuts import render, get_object_or_404
from metrics.views.common import get_tabs
from django import forms
from django.forms.widgets import FileInput
import re
import csv
import io
from metrics import import_utils, models
import traceback
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
import datetime
from django.utils.text import slugify
from django.contrib.auth.decorators import login_required
from django.urls import reverse, reverse_lazy
from django.utils.http import urlencode
from django.http import HttpResponse
from metrics.models.questions import QuestionSuperSet, ResponseSet, Response
from django.http import HttpResponseNotFound
from metrics.forms import QuestionSetForm
from metrics.models import UserProfile, SystemSettings


UPLOAD_TYPES = {
    upload_type["id"]: upload_type
    for upload_type in [
        {
            "id": "events",
            "title": "Events",
            "description": "",
            "template_url": reverse_lazy(
                "download_template",
                kwargs={"data_type": "event", "slug": "base"}
            )
        },
        {
            "id": "demographic_quality_metrics",
            "title": "Demographic and quality metrics",
            "description": "",
            "template_url": reverse_lazy(
                "download_template",
                kwargs={"data_type": "metrics", "slug": "demographic-quality"}
            )
        },
        {
            "id": "impact_metrics",
            "title": "Impact metrics",
            "description": "",
            "template_url": reverse_lazy(
                "download_template",
                kwargs={"data_type": "metrics", "slug": "impact"}
            )
        },
    ]
}


class DataUploadForm(forms.Form):
    file = forms.FileField(
        label="CSV batch file",
        widget=FileInput(attrs={"class": "form-control"}),
    )

    def __init__(
        self,
        *args,
        title=None,
        description=None,
        associated_templates=None,
        data_type=None,
        badge=None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.badge = badge
        self.data_type = data_type
        self.associated_templates = associated_templates

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
        return (
            import_utils.legacy_to_current_quality_or_demographic_dict,
            import_context.quality_or_demographic_from_dict,
            {"summary": summary_output}
        )
    elif data_type == "impact_metrics":
        return (
            import_utils.legacy_to_current_impact_dict,
            import_context.impact_from_dict,
            {"summary": summary_output}
        )


def get_matching_legacy_model(headers, model_ids=None):
    legacy_models = [
        models.legacy.Demographic,
        models.legacy.Impact,
        models.legacy.Quality,
    ]
    legacy_models = (
        legacy_models
        if model_ids is None
        else [
            model
            for model in legacy_models
            if slugify(model._meta.verbose_name) in model_ids
        ]
    )
    headers = set(header.lower() for header in headers)
    for model in legacy_models:
        fields = set(
            field.verbose_name.lower()
            for field in import_utils.get_metrics_fields(model)
        )
        if fields.issubset(headers):
            return model

    return None


def get_model_transform(model):
    metrics_fields = import_utils.get_metrics_fields(model)
    field_name_map = {
        field.verbose_name.lower(): field.name
        for field in metrics_fields
    }
    field_multichoice_map = {
        field.name: isinstance(field, models.ChoiceArrayField)
        for field in metrics_fields

    }

    def _model_transform(entry):
        metrics_data = {
            field_name_map[field_name.lower()]: value
            for field_name, value in entry.items()
            if field_name.lower() in field_name_map
        }
        base_data = {
            field_name: value
            for field_name, value in entry.items()
            if field_name not in field_name_map
        }

        for field_name, value in metrics_data.items():
            if field_multichoice_map.get(field_name, False):
                metrics_data[field_name] = import_utils.csv_to_array(value)
            else:
                metrics_data[field_name] = import_utils.use_alias(value)

        metrics_data = import_utils.parse_legacy_entry_data(
            metrics_data,
            model
        )
        return {
            **metrics_data,
            **base_data
        }

    return _model_transform


def get_question_import_context(super_set, user, node_main, event):
    forms = [
        QuestionSetForm.from_question_set(qs)
        for qs in super_set.question_sets.all()
    ]

    def _form_parser(entry):
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
        event_id = None
        if not current_event:
            try:
                event_id = entry["event_id"]
                current_event = models.Event.objects.filter(
                    id=event_id
                ).first()
            except (KeyError, ValueError) as e:
                raise ValidationError(f"Failed to parse 'event_id': {e}")

        if not current_event:
            raise ValidationError(
                f"Event with id '{event_id}', does not exist"
            )

        if (
            current_event.is_locked or
            UserProfile.get_node(user) != current_event.node_main
        ):
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


def parse_csv_to_dict(file, event):
    file_match = rf"^.+-{event.id}\.csv$" if event else r"^.+\.csv$"
    if not re.match(file_match, file.name):
        raise ValidationError(
            None,
            "Incorrect file name. The file name needs "
            f"to match the following regex: '{file_match}'"
        )
    csv_stream = io.StringIO(file.read().decode("utf-8-sig"))
    dialect = csv.Sniffer().sniff(csv_stream.readline(), delimiters=[",", ";"])
    csv_stream.seek(0)
    return csv.DictReader(csv_stream, dialect=dialect)


def legacy_upload(request, event):
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
            associated_templates=[(
                upload_type["title"],
                str(upload_type["template_url"])
            )]
        )
        for upload_type in upload_types.values()
    ]

    if request.method == "POST":
        for form in forms:
            if form.has_changed() and form.is_valid():
                data = form.cleaned_data
                upload_type = form.data_type

                try:
                    node_main = UserProfile.get_node(request.user)
                    reader = parse_csv_to_dict(data["file"], event)
                    (parser, importer, view_transforms) = get_import_context(
                        upload_type,
                        request.user,
                        node_main,
                        event
                    )

                    entries = []
                    for (index, row) in enumerate(reader):
                        try:
                            entries.append(parser(row))
                        except ValidationError as e:
                            traceback.print_exc()
                            form.add_error(
                                None,
                                f"Failed to parse '{upload_type}' "
                                f"row {index} : {e}"
                            )

                    if len(form.errors) == 0:
                        items = []
                        with transaction.atomic():
                            items = [importer(entry) for entry in entries]

                        form.outputs = {
                            key: view_transform(items)
                            for key, view_transform
                            in view_transforms.items()
                        }
                    else:
                        dialect = reader.dialect
                        form.add_error(
                            None,
                            "Using dialect: "
                            f"delimiter [{dialect.delimiter}], "
                            f"quotechar [{dialect.quotechar}], "
                            f"doublequote [{dialect.doublequote}]"
                        )
                except (ValidationError, UnicodeDecodeError, csv.Error, Exception) as e:
                    traceback.print_exc()
                    form.add_error(None, f"Failed to import '{upload_type}': {e}")
                    if isinstance(e, UnicodeDecodeError):
                        form.add_error(
                            None,
                            "Make sure that the file is of the right format. "
                            "The file needs to be a CSV (comma separated values) "
                            "and use the character encoding UTF-8."
                        )

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
    settings = SystemSettings.get_settings(request.user)
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
            associated_templates=[(
                upload_type["title"],
                str(upload_type["template_url"])
            )]
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
                badge=None if super_set.node is None else super_set.node.name,
                associated_templates=[(
                    super_set.name,
                    reverse(
                        "download_template",
                        kwargs={"data_type": "metrics", "slug": super_set.slug}
                    )
                )]
            )
            for super_set in question_supersets
        ]
    ]

    if request.method == "POST":
        for form in forms:
            if form.has_changed() and form.is_valid():
                data = form.cleaned_data
                upload_type = form.data_type

                try:
                    node_main = UserProfile.get_node(request.user)
                    reader = parse_csv_to_dict(data["file"], event)
                    (parser, importer, view_transforms) = (
                        get_import_context(
                            upload_type,
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
                        )
                    )

                    compatiblity_model = (
                        get_matching_legacy_model(
                            reader.fieldnames,
                            {upload_type.slug}
                        )
                        if isinstance(upload_type, QuestionSuperSet)
                        else None
                    )
                    compatibility_transform = (
                        None
                        if compatiblity_model is None
                        else get_model_transform(compatiblity_model)
                    )

                    entries = []
                    for (index, row) in enumerate(reader):
                        try:
                            entry = (
                                row
                                if compatibility_transform is None
                                else compatibility_transform(row)
                            )
                            entries.append(parser(entry))
                        except (ValidationError, ) as e:
                            traceback.print_exc()
                            form.add_error(
                                None,
                                f"Failed to parse '{upload_type}' "
                                f"row {index} : {e}"
                            )

                    if len(form.errors) == 0:
                        items = []
                        with transaction.atomic():
                            items = [
                                importer(entry)
                                for entry in entries
                            ]

                        form.outputs = {
                            key: view_transform(items)
                            for key, view_transform
                            in view_transforms.items()
                        }
                        if compatiblity_model is not None:
                            form.outputs["summary"] = (
                                f"Using compatiblity model {compatiblity_model._meta.verbose_name}: "
                                f"{form.outputs.get('summary', '')}"
                            )
                    else:
                        dialect = reader.dialect
                        form.add_error(
                            None,
                            "Using dialect: "
                            f"delimiter [{dialect.delimiter}], "
                            f"quotechar [{dialect.quotechar}], "
                            f"doublequote [{dialect.doublequote}]"
                        )
                        if compatiblity_model:
                            form.add_error(None, f"Using compatiblity model {compatiblity_model._meta.verbose_name}")

                except (ValidationError, UnicodeDecodeError, csv.Error, Exception) as e:
                    form.add_error(None, f"Failed to import '{upload_type}': {e}")
                    if isinstance(e, UnicodeDecodeError):
                        form.add_error(
                            None,
                            "Make sure that the file is of the right format. "
                            "The file needs to be a CSV (comma separated values) "
                            "and use the character encoding UTF-8."
                        )

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
    settings = SystemSettings.get_settings(request.user)
    node = UserProfile.get_node(request.user)
    event = get_object_or_404(models.Event, id=event_id) if event_id else None

    if not node:
        raise PermissionDenied("You have to be associated with a node to upload data.")

    if event and (event.is_locked or node != event.node_main):
        raise PermissionDenied(f"You do not have permissions the upload data to event {event.id}")

    if settings.has_flag("use_new_model_upload"):
        return response_upload(request, event)
    else:
        return legacy_upload(request, event)


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
        settings = SystemSettings.get_settings(request.user)
        if settings.has_flag("use_new_model_upload"):
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

            elif slug == "demographic-quality":
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
            return download_csv([["event_code", *fields]], f"metrics-{slug}-template")

    return HttpResponseNotFound("Template not found")
