from django.shortcuts import render, redirect, get_object_or_404
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
from metrics.forms import QuestionSetForm, SubmissionOptions
from metrics.models import UserProfile, SystemSettings
from django.forms import formset_factory, BaseFormSet
import json


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
        widget=FileInput(attrs={"class": "form-control", "accept": ".csv"}),
    )

    def __init__(
        self,
        *args,
        title=None,
        description=None,
        associated_templates=None,
        data_type=None,
        badge=None,
        action=None,
        file_match=None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.badge = badge
        self.data_type = data_type
        self.associated_templates = associated_templates

        self.description = description
        self.title = title
        self.action = action
        self.file_match = file_match

    def clean(self):
        data = super().clean()
        if self.file_match:
            if not re.match(self.file_match, data["file"].name):
                self.add_error(
                    "file",
                    "Incorrect file name. The file name needs "
                    f"to match the following regex: '{self.file_match}'"
                )
        return data


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


def import_data_for_question_set(qs, event, user, data):
    rs = ResponseSet(user=user, event=event, question_set=qs)
    rs.save()
    questions = qs.questions.all()
    for question in questions:
        answer = data[question.slug]
        all_answers = answer if isinstance(answer, list) else [answer]
        for a in all_answers:
            r = Response(response_set=rs, answer=a)
            r.save()


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


def parse_csv_to_dict(file):
    csv_stream = io.StringIO(file.read().decode("utf-8-sig"))
    dialect = csv.Sniffer().sniff(csv_stream.readline(), delimiters=[",", ";"])
    csv_stream.seek(0)
    return csv.DictReader(csv_stream, dialect=dialect)


@login_required
def submit_entries(request, question_set_id: str, event_id=None):
    superset = get_object_or_404(QuestionSuperSet, slug=question_set_id, use_for_metrics=True)
    node = UserProfile.get_node(request.user)
    upload_form = DataUploadForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        data_type=superset,
        title=superset.name,
        prefix=superset.slug,
        description=superset.description,
        badge=None if superset.node is None else superset.node.name,
        action=reverse(
            "submit_entries",
            kwargs={"question_set_id": superset.slug}
        ),
        file_match=rf"^.+-{event_id}\.csv$" if event_id else r"^.+\.csv$",
        associated_templates=[(
            superset.name,
            reverse(
                "download_template",
                kwargs={"data_type": "metrics", "slug": superset.slug}
            )
        )]
    )
    if (superset.node is not None and superset.node != current_node):
        raise PermissionDenied("This set is not publicly available")

    if not node:
        raise PermissionDenied("You have to be associated with a node to upload data.")

    event = get_object_or_404(models.Event, id=event_id) if event_id else None

    question_sets = tuple(superset.question_sets.all())
    _BaseForm = QuestionSetForm.from_question_sets(
        question_sets,
        hidden=True,
        additional_fields=(
            {
                "event_id": forms.ModelChoiceField(queryset=models.Event.objects.filter(node_main=node))
            } if event_id is None
            else {}
        )
    )
    _FormSet = formset_factory(_BaseForm, extra=0)

    entries = []
    initial_data = []
    values = None
    formset = None
    submission_options = None
    if upload_form.has_changed() and upload_form.is_valid():
        data = upload_form.cleaned_data

        reader = parse_csv_to_dict(data["file"])
        for (index, row) in enumerate(reader):
            try:
                entries.append((row, None))
            except (ValidationError, ) as e:
                traceback.print_exc()
                error_message = f"On row {index} : {e}"
                entries.append((
                    None,
                    (index, error_message)
                ))
        initial_data = [entry for (entry, error) in entries if error is None]
        values = {
            "form-TOTAL_FORMS": len(initial_data),
            "form-INITIAL_FORMS": len(initial_data),
            **{
                f"form-{index}-{key}": value
                for index, entry in enumerate(initial_data)
                for key, value in entry.items()
            }
        }
    else:
        values = request.POST if request.method == "POST" else None

    if values:
        formset = _FormSet(values)
        if formset.is_valid():
            submission_options = SubmissionOptions(request.POST if request.method == "POST" else None)
            if submission_options.is_valid() and submission_options.has_changed():
                with transaction.atomic():
                    options = submission_options.cleaned_data
                    if options["submission_method"] == "replace":
                        ResponseSet.objects.filter(user=request.user, event=event, question_set__in=question_sets).delete()
                    for entry_form in formset:
                        for qs in question_sets:
                            import_data_for_question_set(qs, event, request.user, entry_form.cleaned_data)

                return (
                    redirect("upload-data")
                    if event is None
                    else redirect(
                        "upload-data-event",
                        event_id=event.id
                    )
                )

    title = "Upload data: " + superset.name
    return render(
        request,
        'metrics/submit-entries.html',
        context={
            "title": title,
            **get_tabs(request, view_name="upload-data"),
            "formset": formset,
            "submission_options": submission_options,
            "messages": (
                ()
                if formset.is_valid()
                else (("warning", "The data set contains one or more errors. Please adjust your data and try again."),)
            ),
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
            )],
            file_match=r"^.+\.csv$",
        )
    forms = [
        *([event_upload_form] if event_upload_form else []),
        *[
            DataUploadForm(
                request.POST if request.method == "POST" else None,
                request.FILES if request.method == "POST" else None,
                data_type=superset,
                title=superset.name,
                prefix=superset.slug,
                description=superset.description,
                badge=None if superset.node is None else superset.node.name,
                action=(
                    reverse(
                        "submit_entries",
                        kwargs={"question_set_id": superset.slug}
                    )
                    if event is None
                    else reverse(
                        "submit_event_entries",
                        kwargs={"question_set_id": superset.slug, "event_id": event.id}
                    )
                ),
                associated_templates=[(
                    superset.name,
                    reverse(
                        "download_template",
                        kwargs={"data_type": "metrics", "slug": superset.slug}
                    )
                )]
            )
            for superset in question_supersets
        ]
    ]

    if request.method == "POST":
        for form in forms:
            if form.has_changed() and form.is_valid():
                data = form.cleaned_data
                upload_type = form.data_type

                try:
                    node_main = UserProfile.get_node(request.user)
                    reader = parse_csv_to_dict(data["file"])
                    (parser, importer, view_transforms) = (
                        get_event_import_context(
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

                    entries = []
                    for (index, row) in enumerate(reader):
                        try:
                            entries.append(parser(row))
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
                            for index, entry in enumerate(entries):
                                try:
                                    items.append(importer(entry))
                                except ValidationError as e:
                                    traceback.print_exc()
                                    raise ValidationError([
                                        ValidationError(f"Error for entry[{index}]: {e}"),
                                        e
                                    ])

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
                    form.add_error(None, f"Failed to import '{upload_type}': {e}")
                    traceback.print_exc()
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


def get_event_import_context(user, node_main, event):
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


@login_required
def upload_data(request, event_id=None):
    node = UserProfile.get_node(request.user)
    event = get_object_or_404(models.Event, id=event_id) if event_id else None

    if not node:
        raise PermissionDenied("You have to be associated with a node to upload data.")

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
        settings = SystemSettings.get_settings(request.user)
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
