from .models import (
    Event,
    Quality,
    Impact,
    Demographic,
    Node,
    SystemSettings,
    Response,
    ResponseSet,
    QuestionSet,
    QuestionSuperSet
)
from .forms import QuestionSetForm
from django.template.defaultfilters import slugify
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
import functools


def quality_to_responseset(entries: list[Quality], questionset: QuestionSet):
    return migrate_entries(entries, Quality, questionset)


def impact_to_responseset(entries: list[Impact], questionset: QuestionSet):
    return migrate_entries(entries, Impact, questionset)


def demographic_to_responseset(entries: list[Demographic], questionset: QuestionSet):
    return migrate_entries(entries, Demographic, questionset)


def migrate_entries(entries: list, model, questionset: QuestionSet):
    fields = list(model._meta.get_fields())

    QSForm = QuestionSetForm.from_question_set(questionset)

    model_name = slugify(model._meta.verbose_name)

    for entry in entries:
        entry_data = {
            f"{model_name}-{field.name}": (
                [
                    map_response(value)
                    for value in getattr(entry, field.name)
                ]
                if isinstance(getattr(entry, field.name), list)
                else map_response(getattr(entry, field.name))
            )
            for field in fields
        }
        dict_to_responseset(entry_data, entry.user, entry.event, QSForm)


@functools.cache
def get_response_map():
    country_base_map = {
        "Switzerland": "ch",
        "Germany": "de",
        "United Kingdom": "gb",
        "France": "fr",
        "Lithuania": "lt",
        "Hungary": "hu",
        "Uganda": "ug",
        "Republic of Ireland": "ie",
        "Spain": "es",
        "India": "in",
        "United States": "us",
        "Canada": "ca",
        "Japan": "jp",
        "Romania": "ro",
        "Italy": "it",
        "Slovenia": "si",
        "Singapore": "sg",
        "Netherlands": "nl",
        "Belgium": "be",
        "Norway": "no",
        "Portugal": "pt",
        "Czech Republic": "cz",
        "China": "cn",
        "Iran": "iq",
        "Sweden": "se",
        "Luxembourg": "lu",
        "Pakistan": "pk",
        "Estonia": "ee",
        "Poland": "pl",
        "South Africa": "za",
        "Austria": "at",
        "Denmark": "dk",
        "Saudi Arabia": "sa",
        "Oman": "om",
        "Jordan": "jo",
        "Sudan": "sd",
        "Ghana": "gh",
        "Malaysia": "my",
        "Nigeria": "ng",
        "Qatar": "qa",
        "Australia": "au",
        "Bangladesh": "bd",
        "Morocco": "ma",
        "Ecuador": "ec",
        "Greece": "gr",
        "Finland": "fi",
        "Bosnia Herzegovina": "ba",
        "Montenegro": "me",
        "Albania": "al",
        "United Arab Emirates": "ae",
        "Uruguay": "uy",
        "Mexico": "mx",
        "Serbia": "rs",
        "Israel": "il",
        "Kenya": "ke",
        "Argentina": "ar",
        "Kuwait": "kw",
        "Turkey": "tr",
        "Colombia": "co",
        "Philippines": "ph",
        "Brazil": "br",
        "Algeria": "dz",
        "Indonesia": "id",
        "South Korea": "kr",
        "Egypt": "eg",
        "Nepal": "np",
        "Vietnam": "vn",
        "Cameroon": "cm",
        "Afghanistan": "af",
        "Kazakhstan": "kz",
        "Ukraine": "ua",
        "Myanmar, {Burma}": "mm",
        "Zimbabwe": "zw",
        "Bulgaria": "bg",
        "Tunisia": "tn",
        "Latvia": "lv",
        "Russia": "ru",
        "Belarus": "by",
        "Tanzania": "tz",
        "Malta": "mt",
        "Slovakia": "sk",
        "Chile": "cl",
        "Ethiopia": "et",
        "Taiwan": "th",
        "Saint Vincent & the Grenadines": "vc",
        "Peru": "pe",
        "Cyprus": "cy",
        "Bahrain": "bh",
        "Mali": "ml",
        "Mozambique": "mz",
        "Croatia": "hr",
        "Iceland": "is",
        "St Kitts & Nevis": "kn",
        "Panama": "pa",
        "Thailand": "th",
        "Gambia": "zm",
        "Andorra": "ad",
        "New Zealand": "nz"
    }
    country_map = {
        slugify(key): value
        for key, value in country_base_map.items()
    }
    response_map = {
        "to-learn-something-new-to-aid-me-in-my-current-researchwork": "to-learn-something-new-to-aid-me-in-my-current-research-work",
        "to-build-on-existing-knowledge-to-aid-me-in-my-current-researchwork": "to-build-on-existing-knowledge-to-aid-me-in-my-current-research-work",
        "by-using-training-materialsnotes-from-the-training-event": "by-using-training-materials-notes-from-the-training-event",
        "it-did-not-help-as-i-do-not-use-the-toolsresources-covered-in-the-training-event": "it-did-not-help-as-i-do-not-use-the-tools-resources-covered-in-the-training-event",
        "it-improved-communication-with-the-bioinformaticianstatistician-analyzing-my-data": "it-improved-communication-with-the-bioinformatician-statistician-analyzing-my-data",
        "submission-of-my-dissertationthesis-for-degree-purposes": "submission-of-my-dissertation-thesis-for-degree-purposes",
        "useful-collaborations-with-other-participantstrainers-from-the-training-event": "useful-collaborations-with-other-participants-trainers-from-the-training-event"
    }

    return {
        **country_map,
        **response_map
    }



def map_response(response: str):
    slug_response = slugify(response)
    response_map = get_response_map()

    return response_map.get(slug_response, slug_response)


def dict_to_responseset(entry: dict, user: User, event: Event, QSForm: QuestionSetForm):
    form = QSForm(entry)

    if not form.is_valid():
        raise ValidationError(f"Failed to validate form: {form.errors}")

    data = form.cleaned_data
    rs = ResponseSet.objects.create(user=user, event=event, question_set=form.question_set)
    for answer in data.values():
        all_answers = answer if isinstance(answer, list) else [answer]
        for a in all_answers:
            r = Response.objects.create(response_set=rs, answer=a)

