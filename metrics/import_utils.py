from datetime import datetime
from metrics.models import Event, Demographic, Quality, Impact, User, Node
from django.utils.text import slugify
from django.core.exceptions import ValidationError


class ImportContext:
    def __init__(self, user=None, node_main=None):
        self._user = user
        self._node_main = node_main

    def event_from_dict(self, data: dict):
        (created, modified) = timestamps_from_dict(data)

        event = Event.objects.create(
            user=self.user_from_data(data),
            created=created,
            modified=modified,
            code=slugify(data.get('code')),
            title=data['title'],
            node_main=self.node_from_data(data),
            date_start=convert_to_date(data['date_start']),
            date_end=convert_to_date(data['date_end']),
            duration=float(data['duration']),
            type=data['type'],
            funding=csv_to_array(data['funding']),
            location_city=data['location_city'],
            location_country=data['location_country'],
            target_audience=csv_to_array(data['target_audience']),
            additional_platforms=csv_to_array(data['additional_platforms']),
            communities=csv_to_array(data['communities']),
            number_participants=data['number_participants'],
            number_trainers=data['number_trainers'],
            url=data['url'],
            status=data['status'],
        )
        # event.organising_institution.set([data['organising_institution']])
        node_names = data['node'].split(",")
        stripped_names = [name.strip() for name in node_names]
        nodes = [
            Node.objects.get(name=node)
            for node in stripped_names
        ]
        event.node.add(*nodes)

        return event

    def demographic_from_dict(self, data: dict):
        (created, modified) = timestamps_from_dict(data)
        demographic = Demographic.objects.create(
            user=self.user_from_data(data),
            created=created,
            modified=modified,
            event=Event.objects.get(code=int(data['event'])),
            heard_from=csv_to_array(data['heard_from']),
            employment_sector=data['employment_sector'],
            employment_country=data['employment_country'],
            gender=data['gender'],
            career_stage=data['career_stage'],
        )
        return demographic

    def quality_from_dict(self, data: dict):
        (created, modified) = timestamps_from_dict(data)
        quality = Quality.objects.create(
            user=self.user_from_data(data),
            created=created,
            modified=modified,
            event=Event.objects.get(code=data['event']),
            used_resources_before=data['used_resources_before'],
            used_resources_future=data['used_resources_future'],
            recommend_course=data['recommend_course'],
            course_rating=data['course_rating'],
            balance=data['balance'],
            email_contact=data['email_contact'],
        )
        return quality

    def impact_from_dict(self, data: dict):
        (created, modified) = timestamps_from_dict(data)
        impact = Impact.objects.create(
            user=self.user_from_data(data),
            created=created,
            modified=modified,
            event=Event.objects.get(code=data['event']),
            when_attend_training=data['when_attend_training'],
            main_attend_reason=data['main_attend_reason'],
            how_often_use_before=data['how_often_use_before'],
            how_often_use_after=data['how_often_use_after'],
            able_to_explain=data['able_to_explain'],
            able_use_now=data['able_use_now'],
            help_work=csv_to_array(data['help_work']),
            attending_led_to=csv_to_array(data['attending_led_to']),
            people_share_knowledge=data['people_share_knowledge'],
            recommend_others=data['recommend_others'],
        )
        return impact

    def user_from_data(self, data: dict):
        return (
            User.objects.get(username=data['user'])
            if self._user is None
            else self._user
        )

    def node_from_data(self, data: dict):
        node_main = data['node_main'] if data['node_main'] else ''
        return (
            Node.objects.get(
                name=node_main
            ) if node_main and self._node_main is None
            else self._node_main
        )

    @staticmethod
    def from_request(request):
        return ImportContext(user=request.user)


def csv_to_array(csv_string):
    return [x for x in csv_string.split(",")] if csv_string else []


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
            **parse_location(data, key="Location (city, country)"),
            "node_main": None,
            "duration": 0,
            "status": "Complete",
        }
    except KeyError as e:
        raise ValidationError(f"Missing source data '{e}'")


def legacy_to_current_quality_or_demographic_dict(data: dict) -> dict:
    try:
        mapping = {
            "event_code": "event",
            "Where did you see the course advertised?": None,
            "What is your career stage?": "career_stage",
            "What is your employment sector?": "employment_country",
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
            target_id: data[source_id]
            for source_id, target_id in mapping.items()
            if target_id is not None
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
            target_id: data[source_id]
            for source_id, target_id in mapping.items()
            if target_id is not None
        }
    except KeyError as e:
        raise ValidationError(f"Missing source data '{e}'")


def parse_location(data: dict, key="location") -> dict:
    location = data[key]
    try:
        [city, country] = [value.strip() for value in location.split(",")]
        return {
            "location_city": city,
            "location_country": country
        }
    except ValueError as e:
        raise ValidationError(f"Failed to parse location: {e}")

