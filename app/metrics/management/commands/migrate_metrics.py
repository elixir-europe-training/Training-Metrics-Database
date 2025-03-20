from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.exceptions import ValidationError

from metrics.models import (
    Event,
    Quality,
    Impact,
    Demographic,
    Response,
    ResponseSet,
    QuestionSet,
    EditTracking,
)
from metrics.forms import QuestionSetForm
from metrics.import_utils import (
    get_field_id,
    parse_legacy_entry_data,
    map_response,
    get_metrics_fields
)
from typing import Type
from django.contrib.auth.models import User


def quality_to_responseset(
    entries: list[Quality],
    questionset: QuestionSet
):
    return migrate_entries(entries, Quality, questionset)


def impact_to_responseset(
    entries: list[Impact],
    questionset: QuestionSet
):
    return migrate_entries(entries, Impact, questionset)


def demographic_to_responseset(
    entries: list[Demographic],
    questionset: QuestionSet
):
    return migrate_entries(entries, Demographic, questionset)


def migrate_entries(entries: list, model, questionset: QuestionSet):
    validate_compatibility(model, questionset)

    fields = get_metrics_fields(model)

    QSForm = QuestionSetForm.from_question_set(questionset)

    for entry in entries:
        try:
            entry_data = parse_legacy_entry_data(
                {
                    field.name: getattr(entry, field.name)
                    for field in fields
                },
                model
            )
            dict_to_responseset(entry_data, entry.user, entry.event, QSForm)
        except ValidationError as e:
            print(entry_data)
            raise e


def validate_compatibility(model, questionset: QuestionSet):
    fields = get_metrics_fields(model)
    for field in fields:
        field_id = get_field_id(model, field.name)
        question = questionset.questions.filter(slug=field_id).first()

        if question is None:
            raise ValidationError(
                f"Field {field_id} has no representation in set {questionset.slug}"  # noqa: E501
            )

        for option in get_field_options(field):
            mapped_option = map_response(option)
            if not question.answers.filter(slug=mapped_option).exists():
                raise ValidationError(
                    f"Choice {field_id}.{option}({mapped_option}) has no representation in set {question.slug}"  # noqa: E501
                )


def get_field_options(field):
    choices = getattr(field, "choices", [])
    choices = getattr(
        getattr(field, "base_field", None),
        "choices",
        []
    ) if not choices else choices
    return (
        []
        if not choices
        else [
            choice[0]
            for choice in choices
        ]
    )


def dict_to_responseset(
    entry: dict,
    user: User,
    event: Event,
    QSForm: Type[QuestionSetForm]
):
    form = QSForm(entry)

    if not form.is_valid():
        raise ValidationError(f"Failed to validate form: {form.errors}")

    data = form.cleaned_data
    rs = ResponseSet.objects.create(
        user=user,
        event=event,
        question_set=form.question_set
    )
    for answer in data.values():
        all_answers = answer if isinstance(answer, list) else [answer]
        for a in all_answers:
            Response.objects.create(response_set=rs, answer=a)
    return rs


def migrate_all():
    (
        quality,
        impact,
        demographic
    ) = (
        QuestionSet.objects.filter(slug=slug).get()
        for slug in ["quality", "impact", "demographic"]
    )

    with transaction.atomic():
        quality_to_responseset(list(Quality.objects.all()), quality)
        impact_to_responseset(list(Impact.objects.all()), impact)
        demographic_to_responseset(
            list(Demographic.objects.all()),
            demographic
        )


class Command(BaseCommand):
    help = "Migrates metrics from old structure to the new"

    def handle(self, *args, **options):
        migrate_all()
