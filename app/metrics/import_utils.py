from django.conf import settings
from datetime import datetime
from django.db.models import TextField
from metrics.models import (
    Event,
    Demographic,
    Quality,
    Impact,
    User,
    Node,
    OrganisingInstitution,
    ChoiceArrayField,
)
from django.utils.text import slugify
from django.core.exceptions import ValidationError, PermissionDenied
import random
from typing import Callable
import functools
import csv
import logging


logger = logging.getLogger(__name__)


class ImportContext:
    def __init__(self):
        self._institutions = {}

    def event_from_dict(self, data: dict):
        (created, modified) = self.timestamps_from_data(data)
        start_date = convert_to_date(data['date_start'])
        end_date = convert_to_date(data['date_end'])
        event = Event.objects.create(
            user=self.user_from_data(data),
            created=created,
            modified=modified,
            code=(
                slugify(data['code'])
                if 'code' in data
                else None
            ),
            title=data['title'],
            node_main=self.node_from_data(data),
            date_start=start_date,
            date_end=end_date,
            duration=float(data['duration']) if data['duration'] else (end_date - start_date).days + 1,
            type=use_alias(data['type']),
            funding=csv_to_array(data['funding']) or ["ELIXIR Node"],
            location_city=data['location_city'] or "NA",
            location_country=data['location_country'],
            target_audience=csv_to_array(data['target_audience']) or ["Academia/ Research Institution"],
            additional_platforms=csv_to_array(data['additional_platforms']) or ["NA"],
            communities=csv_to_array(data['communities']) or ["NA"],
            number_participants=int(data['number_participants'] or 0),
            number_trainers=int(data['number_trainers'] or 0),
            url=data['url'],
            status=use_alias(data['status']),
        )
        institution_ids = csv_to_array(data['organising_institution'])
        event.organising_institution.set(self.get_institutions(institution_ids))
        node_names = data['node'].split(",")
        stripped_names = [name.strip() for name in node_names]
        nodes = [
            Node.objects.get(name=node)
            for node in stripped_names
        ]
        event.node.add(*nodes)

        event.full_clean()
        return event

    def get_institutions(self, ror_ids):
        result = []
        for ror_id in ror_ids:
            try:
                result.append(self.get_institution(ror_id))
            except ValidationError:
                pass
        return result

    def get_institution(self, ror_id):
        institution = self._institutions.get(ror_id)
        if institution is not None:
            return institution

        existing_inst = OrganisingInstitution.objects.filter(ror_id=ror_id).first()
        if existing_inst is not None:
            self._institutions[ror_id] = existing_inst
            return existing_inst

        new_inst = OrganisingInstitution(ror_id=ror_id)
        new_inst.update_ror_data()
        new_inst.save()
        self._institutions[ror_id] = new_inst
        return new_inst

    def demographic_from_dict(self, data: dict):
        (created, modified) = self.timestamps_from_data(data)
        (user, event) = self.get_user_and_event(data)
        demographic = Demographic.objects.create(
            user=user,
            created=created,
            modified=modified,
            event=event,
            heard_from=csv_to_array(data['heard_from']) or ["Other"],
            employment_sector=use_alias(data['employment_sector']) or "Other",
            employment_country=data['employment_country'],
            gender=use_alias(data['gender']) or "Other",
            career_stage=use_alias(data['career_stage']) or "Other",
        )
        demographic.full_clean()
        return demographic

    def quality_from_dict(self, data: dict):
        (created, modified) = self.timestamps_from_data(data)
        (user, event) = self.get_user_and_event(data)
        quality = Quality.objects.create(
            user=user,
            created=created,
            modified=modified,
            event=event,
            used_resources_before=use_alias(data['used_resources_before']),
            used_resources_future=use_alias(data['used_resources_future']),
            recommend_course=use_alias(data['recommend_course']),
            course_rating=use_alias(data['course_rating']),
            balance=use_alias(data['balance']),
            email_contact=use_alias(data['email_contact']) or "No",
        )
        quality.full_clean()
        return quality

    def impact_from_dict(self, data: dict):
        (created, modified) = self.timestamps_from_data(data)
        (user, event) = self.get_user_and_event(data)
        impact = Impact.objects.create(
            user=user,
            created=created,
            modified=modified,
            event=event,
            when_attend_training=use_alias(data['when_attend_training']),
            main_attend_reason=use_alias(data['main_attend_reason']),
            how_often_use_before=use_alias(data['how_often_use_before']),
            how_often_use_after=use_alias(data['how_often_use_after']),
            able_to_explain=use_alias(data['able_to_explain']) or "Other",
            able_use_now=use_alias(data['able_use_now']) or "Other",
            help_work=csv_to_array(data['help_work']) or ["Other"],
            attending_led_to=csv_to_array(data['attending_led_to']) or ["Other"],
            people_share_knowledge=use_alias(data['people_share_knowledge']),
            recommend_others=use_alias(data['recommend_others']),
        )
        impact.full_clean()
        return impact

    def get_user_and_event(self, data: dict):
        event = self.get_event(data)
        user = self.user_from_data(data)
        self.assert_can_change_data(user, event)
        return (user, event)

    def get_event(self, data):
        identifier = data['event']
        return Event.objects.get(code=identifier)

    def user_from_data(self, data: dict):
        return User.objects.get(username=data['user'])

    def node_from_data(self, data: dict):
        node_main = data['node_main'] if data['node_main'] else ''
        return (
            Node.objects.get(
                name=node_main
            ) if node_main
            else None
        )

    def timestamps_from_data(self, data: dict):
        return timestamps_from_dict(data)

    def assert_can_change_data(self, user, event):
        pass


class LegacyImportContext(ImportContext):
    def __init__(self, user=None, node_main=None, timestamps=None, fixed_event=None):
        super().__init__()
        self._user = user
        self._node_main = node_main
        self._timestamps = timestamps
        self._fixed_event = fixed_event

    def quality_or_demographic_from_dict(self, data: dict):
        return (
            self.quality_from_dict(data),
            self.demographic_from_dict(data)
        )

    def get_institutions(self, ror_ids):
        return [
            self.get_institution(ror_id)
            for ror_id in ror_ids
        ]

    def get_event(self, data):
        if self._fixed_event:
            return self._fixed_event

        identifier = data['event']
        return Event.objects.get(id=int(identifier))

    def user_from_data(self, data: dict):
        return self._user

    def node_from_data(self, data: dict):
        return self._node_main

    def timestamps_from_data(self, data: dict):
        return self._timestamps

    def assert_can_change_data(self, user, event):
        if user.get_node() != event.node_main:
            raise PermissionDenied(
                f"The metrics for the event {event.id}, {event.code} can not"
                f" be updated by the current user: {user.username}"
            )


def read_aliases(path):
    aliases = {}
    ignore_columns = {"field", "value"}
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            value = row["value"]
            for (column, alias) in row.items():
                if column not in ignore_columns and alias:
                    simplified_alias = alias.lower().strip()
                    existing_alias = aliases.get(simplified_alias)
                    if existing_alias is None:
                        aliases[simplified_alias] = value
                    elif existing_alias != value:
                        raise ValueError(
                            f"Confliciting aliases for '{simplified_alias}': '{existing_alias}' <-> '{value}'"
                        )
    return aliases


@functools.cache
def get_aliases():
    aliases = {
        "academia/ research institution": "Academia/ Research Institution",
        "non-profit organisation": "Non-Profit Organisation",
        "complete": "Complete",
        "non-elixir/ non-excelerate funds": "Non-ELIXIR / Non-EXCELERATE Funds",
        "training - elearning": "Training - e-learning",
        "converge": "ELIXIR Converge",
        "eosc-life": "EOSC Life",
        "knowledge exchange workshop": "Knowledge Exchange Workshop",
        "elixir community/ use case": "ELIXIR Community / Use case",
        "to learn something new to aid me in my current research/ work": "To learn something new to aid me in my current research/work",
        "by using training materials/ notes from the training event": "By using training materials/notes from the training event",
        "to build an existing knowledge to aid me in my current research/ work": "To build on existing knowledge to aid me in my current research/work",
        "useful collaboration(s) with other participants/ trainers from the training event": "Useful collaboration(s) with other participants/trainers from the training event",
        "it improved communication with the bioinformatician/ statistician analyzing my data": "It improved communication with the bioinformatician/statistician analyzing my data",
        "it did not help as i do not use the tool(s)/ resource(s) covered in the training event": "It did not help as I do not use the tool(s)/resource(s) covered in the training event",
        "submission of my dissertation/ thesis for degree purposes": "Submission of my dissertation/thesis for degree purposes",
    }

    aliases_path = getattr(settings, "VALUE_ALIASES_PATH", None)
    if aliases_path is not None:
        try:
            aliases = read_aliases(aliases_path)
            logger.info(f"Aliases loaded from: {aliases_path}")
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"Failed to load aliases from: {aliases_path}: {str(e)}")

    return aliases


def use_alias(value):
    aliases = get_aliases()
    return (
        [
            aliases.get(value.lower(), v)
            for v in value
        ]
        if type(value) is list
        else aliases.get(value.lower(), value)
    )


def csv_to_array(csv_string):
    return [
        use_alias(x.strip())
        for x in csv_string.split(",")
    ] if csv_string else []


def convert_to_timestamp(date_string):
    try:
        return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S').timestamp()
    except ValueError as e:
        raise ValidationError(f"Failed to parse timestamp: {e}")


def convert_to_date(date_string):
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except ValueError as e:
        raise ValidationError(f"Failed to parse date: {e}")


def timestamps_from_dict(data: dict):
    created = (
        convert_to_timestamp(data['created'])
        if data.get('created')
        else ''
    )
    modified = (
        convert_to_timestamp(data['modified'])
        if data.get('modified')
        else ''
    )
    return (created, modified)


def legacy_to_current_event_dict(data: dict) -> dict:
    try:
        mapping = {
            "Title": "title",
            "ELIXIR Node": "node",
            "Start Date": "date_start",
            "End Date": "date_end",
            "Event type": "type",
            "Funding": "funding",
            "Organising Institution/s": "organising_institution",
            "Location (city, country)": None,
            "EXCELERATE WP": None,
            "Target audience": "target_audience",
            "Additional ELIXIR Platforms involved": "additional_platforms",
            "ELIXIR Communities involved": "communities",
            "No. of participants": "number_participants",
            "No. of trainers/ facilitators": "number_trainers",
            "Url to event page/ agenda": "url",
        }
        return {
            **{
                target_id: data[source_id]
                for source_id, target_id in mapping.items()
                if target_id is not None
            },
            **parse_location(data["Location (city, country)"]),
            "node_main": None,
            "duration": None,
            "status": "Complete",
        }
    except KeyError as e:
        raise ValidationError(f"Missing source data '{e}'")


def legacy_to_current_quality_or_demographic_dict(data: dict) -> dict:
    try:
        mapping = {
            "event_code": "event",
            "Where did you see the course advertised?": "heard_from",
            "What is your career stage?": "career_stage",
            "What is your employment sector?": "employment_sector",
            "What is your country of employment?": "employment_country",
            "What is your gender?": "gender",
            "Have you used the tool(s)/resource(s) covered in the course before?": "used_resources_before",
            "Will you use the tool(s)/resource(s) covered in the course again?": "used_resources_future",
            "Would you recommend the course?": "recommend_course",
            "Please tell us your overall rating for the entire course": "course_rating",
            "May we contact you by email in the future for more feedback?": "email_contact",
            "What part of the training did you enjoy the most?": None,
            "What part of the training did you enjoy the least?": None,
            "The balance of theoretical and practical content was": "balance",
            "What other topics would you like to see covered in the future?": None,
            "Any other comments?": None,
        }
        return {
            **{
                target_id: data[source_id]
                for source_id, target_id in mapping.items()
                if target_id is not None
            },
            "event": int(data["event_code"])
        }
    except KeyError as e:
        raise ValidationError(f"Missing source data '{e}'")


def legacy_to_current_impact_dict(data: dict) -> dict:
    try:
        mapping = {
            "event_code": "event",
            "Which training event did you take part in?": None,
            "How long ago did you attend the training?": "when_attend_training",
            "What was your main reason for attending the training?": "main_attend_reason",
            "What was your main reason for attending the training? (Other)": None,
            "How often did you use the tool(s)/ resource(s), covered in the training, BEFORE attending the training?": "how_often_use_before",
            "How often do you use the tool(s)/ resource(s), covered in the training, AFTER having attended the training?": "how_often_use_after",
            "Do you feel that you are able to explain to others what you learnt in the training?": "able_to_explain",
            "Do you feel that you are able to explain to others what you learnt in the training? (Other)": None,
            "Are you now able to use the tool(s)/ resource(s) covered in the training:": "able_use_now",
            "Are you now able to use the tool(s)/ resource(s) covered in the training: (Other)": None,
            "How did the training event help with your work? [select all that apply]": "help_work",
            "How did the training event help with your work? (Other)": None,
            "Attending the training event led to/ facilitated: [select all that apply]": "attending_led_to",
            "Attending the training event led to/ facilitated: (Other)": None,
            "Please elaborate on any impact": None,
            "How many people have you shared the skills and/or knowledge that you learned during the training, with?": "people_share_knowledge",
            "Would you recommend the training to others?": "recommend_others",
            "Any other comments?": None,
        }
        return {
            **{
                target_id: data[source_id]
                for source_id, target_id in mapping.items()
                if target_id is not None
            },
            "event": int(data["event_code"])
        }
    except KeyError as e:
        raise ValidationError(f"Missing source data '{e}'")


def parse_location(location: str) -> dict:
    try:
        [city, country] = [value.strip() for value in location.split(",")]
        return {
            "location_city": city,
            "location_country": country
        }
    except ValueError as e:
        raise ValidationError(f"Failed to parse location: {e}")


def get_field_info(model, field_id):
    field = model._meta.get_field(field_id)
    text_choices = (
        [
            c[0]
            for c in field.choices
        ]
        if type(field) is TextField and field.choices is not None
        else None
    )
    array_choices = (
        [
            c[0]
            for c in field.base_field.choices
        ]
        if type(field) is ChoiceArrayField
        else None
    )
    return {
        "id": field_id,
        "type": str(type(field)),
        "multichoice": type(field) is ChoiceArrayField,
        "values": array_choices or text_choices,
    }


def get_test_data_from_model(model, fields: list[tuple[str, str]], number_of_samples: int) -> list[dict]:
    field_info = {
        field_id: {
            "alias": alias,
            **get_field_info(model, field_id)
        }
        for field_id, alias in fields
    }

    samples = [
        {
            info["alias"]: (
                (
                    ", ".join(
                        random.choices(info["values"], k=random.randint(1, len(info["values"])))
                    )
                    if info["multichoice"]
                    else random.choice(info["values"])
                )
                if info["values"] is not None
                else ""
            )
            for info in field_info.values()
        }
        for i in range(number_of_samples)
    ]
    return samples


def update_table_rows(
    table: list[dict],
    columns: dict[str, Callable[[], str] | None]
) -> list[dict]:
    new_data = []
    for row in table:
        new_row = row.copy()
        for (alias, generator) in columns.items():
            generator = (lambda: "") if generator is None else generator
            new_row[alias] = generator()
        new_data.append(new_row)
    return new_data
