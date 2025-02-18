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
    country_base_map = {
        "Afghanistan": "af",
        "Ecuador": "ec",
        "Luxembourg": "lu",
        "Sao Tome & Principe": "st",
        "Albania": "al",
        "Egypt": "eg",
        "Macedonia": "mk",
        "Saudi Arabia": "sa",
        "Algeria": "dz",
        "El Salvador": "sv",
        "Madagascar": "mg",
        "Senegal": "sn",
        "Andorra": "ad",
        "Equatorial Guinea": "gq",
        "Malawi": "mw",
        "Serbia": "rs",
        "Angola": "ao",
        "Eritrea": "er",
        "Malaysia": "my",
        "Seychelles": "sc",
        "Antigua & Deps": "ag",
        "Estonia": "ee",
        "Maldives": "mv",
        "Sierra Leone": "sl",
        "Argentina": "ar",
        "Ethiopia": "et",
        "Mali": "ml",
        "Singapore": "sg",
        "Armenia": "am",
        "Fiji": "fj",
        "Malta": "mt",
        "Slovakia": "sk",
        "Australia": "au",
        "Finland": "fi",
        "Marshall Islands": "mh",
        "Slovenia": "si",
        "Austria": "at",
        "France": "fr",
        "Mauritania": "mr",
        "Solomon Islands": "sb",
        "Azerbaijan": "az",
        "Gabon": "ga",
        "Mauritius": "mu",
        "Somalia": "so",
        "Bahamas": "bs",
        "Gambia": "gm",
        "Mexico": "mx",
        "South Africa": "za",
        "Bahrain": "bh",
        "Georgia": "ge",
        "Micronesia": "fm",
        "South Korea": "kr",
        "Bangladesh": "bd",
        "Germany": "de",
        "Moldova": "md",
        "South Sudan": "ss",
        "Barbados": "bb",
        "Ghana": "gh",
        "Monaco": "mc",
        "Spain": "es",
        "Belarus": "by",
        "Greece": "gr",
        "Mongolia": "mn",
        "Sri Lanka": "lk",
        "Belgium": "be",
        "Grenada": "gd",
        "Montenegro": "me",
        "St Kitts & Nevis": "kn",
        "Belize": "bz",
        "Guatemala": "gt",
        "Morocco": "ma",
        "St Lucia": "lc",
        "Benin": "bj",
        "Guinea": "gn",
        "Mozambique": "mz",
        "Sudan": "sd",
        "Bhutan": "bt",
        "Guinea-Bissau": "gw",
        "Myanmar, {Burma}": "mm",
        "Suriname": "sr",
        "Bolivia": "bo",
        "Guyana": "gy",
        "Namibia": "na",
        "Swaziland": "sz",
        "Bosnia Herzegovina": "ba",
        "Haiti": "ht",
        "Nauru": "nr",
        "Sweden": "se",
        "Botswana": "bw",
        "Honduras": "hn",
        "Nepal": "np",
        "Switzerland": "ch",
        "Brazil": "br",
        "Hungary": "hu",
        "Netherlands": "nl",
        "Syria": "sy",
        "Brunei": "bn",
        "Iceland": "is",
        "New Zealand": "nz",
        "Taiwan": "tw",
        "Bulgaria": "bg",
        "India": "in",
        "Nicaragua": "ni",
        "Tajikistan": "tj",
        "Burkina Faso": "bf",
        "Indonesia": "id",
        "Niger": "ne",
        "Tanzania": "tz",
        "Burundi": "bi",
        "Iran": "ir",
        "Nigeria": "ng",
        "Thailand": "th",
        "Cambodia": "kh",
        "Iraq": "iq",
        "North Korea": "kp",
        "Togo": "tg",
        "Cameroon": "cm",
        "Israel": "il",
        "Norway": "no",
        "Tonga": "to",
        "Canada": "ca",
        "Italy": "it",
        "Oman": "om",
        "Trinidad & Tobago": "tt",
        "Cape Verde": "cv",
        "Ivory Coast": "ci",
        "Online": "other",
        "Tunisia": "tn",
        "Central African Rep": "cf",
        "Jamaica": "jm",
        "Pakistan": "pk",
        "Turkey": "tr",
        "Chad": "td",
        "Japan": "jp",
        "Palau": "pw",
        "Turkmenistan": "tm",
        "Chile": "cl",
        "Jordan": "jo",
        "Panama": "pa",
        "Tuvalu": "tv",
        "China": "cn",
        "Kazakhstan": "kz",
        "Papua New Guinea": "pg",
        "Uganda": "ug",
        "Colombia": "co",
        "Kenya": "ke",
        "Paraguay": "py",
        "Ukraine": "ua",
        "Comoros": "km",
        "Kiribati": "ki",
        "Peru": "pe",
        "United Arab Emirates": "ae",
        "Congo": "cg",
        "Kosovo": "xk",
        "Philippines": "ph",
        "United Kingdom": "gb",
        "Congo {Democratic Rep}": "cd",
        "Kuwait": "kw",
        "Poland": "pl",
        "United States": "us",
        "Costa Rica": "cr",
        "Kyrgyzstan": "kg",
        "Portugal": "pt",
        "Uruguay": "uy",
        "Croatia": "hr",
        "Laos": "la",
        "Qatar": "qa",
        "Uzbekistan": "uz",
        "Cuba": "cu",
        "Latvia": "lv",
        "Republic of Ireland": "ie",
        "Vanuatu": "vu",
        "Cyprus": "cy",
        "Lebanon": "lb",
        "Romania": "ro",
        "Vatican City": "va",
        "Czech Republic": "cz",
        "Lesotho": "ls",
        "Russia": "ru",
        "Venezuela": "ve",
        "Denmark": "dk",
        "Liberia": "lr",
        "Rwanda": "rw",
        "Vietnam": "vn",
        "Djibouti": "dj",
        "Libya": "ly",
        "Saint Vincent & the Grenadines": "vc",
        "Yemen": "ye",
        "Dominica": "dm",
        "Liechtenstein": "li",
        "Samoa": "ws",
        "Zambia": "zm",
        "Dominican Republic": "do",
        "Lithuania": "lt",
        "San Marino": "sm",
        "Zimbabwe": "zw",
        "East Timor": "tl"
    }

    country_map = {
        slugify(key): value
        for key, value in country_base_map.items()
    }
    response_map = {
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
