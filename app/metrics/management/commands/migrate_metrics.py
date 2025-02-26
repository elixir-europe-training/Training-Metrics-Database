from django.core.management.base import BaseCommand
from django.db import transaction
from django.template.defaultfilters import slugify
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
    country_mapping,
)
from metrics.forms import QuestionSetForm
from typing import Type
from django.contrib.auth.models import User
import functools


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

    fields = list(model._meta.get_fields())

    QSForm = QuestionSetForm.from_question_set(questionset)

    ignored_fields = get_ignored_fields()
    for entry in entries:
        try:
            entry_data = {
                get_field_id(model, field): (
                    [
                        map_response(value)
                        for value in getattr(entry, field.name)
                    ]
                    if isinstance(getattr(entry, field.name), list)
                    else map_response(getattr(entry, field.name))
                )
                for field in fields
                if field.name not in ignored_fields
            }
            dict_to_responseset(entry_data, entry.user, entry.event, QSForm)
        except ValidationError as e:
            print(entry_data)
            raise e


def validate_compatibility(model, questionset: QuestionSet):
    ignored_fields = get_ignored_fields()
    fields = list(model._meta.get_fields())
    for field in fields:
        if field.name not in ignored_fields:
            field_id = get_field_id(model, field)
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


def get_ignored_fields():
    return {
        "id",
        "event",
        *{
            field.name
            for field in EditTracking._meta.get_fields()
        }
    }


def get_field_id(model, field):
    model_name = slugify(model._meta.verbose_name)
    return f"{model_name}-{field.name}"


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


@functools.cache
def get_response_map():
    country_base_map = country_mapping

    country_map = {
        slugify(key): value
        for key, value in country_base_map.items()
    }
    response_map = {
        "": "no-response",
        "to-learn-something-new-to-aid-me-in-my-current-researchwork": "to-learn-something-new-to-aid-me-in-my-current-research-work",  # noqa: E501
        "to-build-on-existing-knowledge-to-aid-me-in-my-current-researchwork": "to-build-on-existing-knowledge-to-aid-me-in-my-current-research-work",  # noqa: E501
        "by-using-training-materialsnotes-from-the-training-event": "by-using-training-materials-notes-from-the-training-event",  # noqa: E501
        "it-did-not-help-as-i-do-not-use-the-toolsresources-covered-in-the-training-event": "it-did-not-help-as-i-do-not-use-the-tools-resources-covered-in-the-training-event",  # noqa: E501
        "it-improved-communication-with-the-bioinformaticianstatistician-analyzing-my-data": "it-improved-communication-with-the-bioinformatician-statistician-analyzing-my-data",  # noqa: E501
        "submission-of-my-dissertationthesis-for-degree-purposes": "submission-of-my-dissertation-thesis-for-degree-purposes",  # noqa: E501
        "useful-collaborations-with-other-participantstrainers-from-the-training-event": "useful-collaborations-with-other-participants-trainers-from-the-training-event"  # noqa: E501
    }

    return {
        **country_map,
        **response_map
    }


def map_response(response: str):
    slug_response = slugify(response)
    response_map = get_response_map()

    return response_map.get(slug_response, slug_response)


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
