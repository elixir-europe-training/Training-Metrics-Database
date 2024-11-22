from datetime import datetime
from functools import lru_cache
from contextlib import suppress
from .models import Event, Quality, Impact, Demographic, Node


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


def get_model_field_options(model):
    return (
        (field.name, get_field_options(field))
        for field in model._meta.get_fields()
    )


class EventGroup():
    def __init__(
        self,
        name,
        field_mapping,
        use_fields=None,
        filter_fields=[
            "type",
            "funding",
            "target_audience",
            "additional_platforms"
        ],
        graph_type="bar",
        field_options_mapping={},
        use_node=None
    ):
        self.use_node = use_node
        self.field_mapping = field_mapping
        self.name = name
        self.filter_fields = filter_fields
        self.graph_type = graph_type
        self.model = Event
        self.use_fields = use_fields
        self.field_options_mapping = field_options_mapping
        
        all_fields = set([*self.use_fields, *self.filter_fields])
        self.fields = {
            field_id: options
            for field_id, options in get_model_field_options(self.model)
            if field_id in all_fields
        }
    
    def get_graph_type(self):
        return self.graph_type

    def get_fields(self):
        return self.use_fields
    
    def get_filter_fields(self):
        return self.filter_fields
    
    def get_field_placeholder(self, field_id):
        return f"Select {self.get_field_title(field_id)}"
    
    def get_field_options(self, field_id):
        return self.fields[field_id]
    
    def get_field_option_name(self, field_id, option_id):
        field_option_id = f"{field_id}:{option_id}"
        return self.field_options_mapping.get(field_option_id, option_id)
    
    def get_field_title(self, lookup_id):
        for name, field_id in self.field_mapping.items():
            if lookup_id == field_id:
                return name
        return lookup_id
        
    
    def get_values(self, **params):
        query = self.model.objects.all()
        if params.get("type"):
            query = query.filter(type=params.get("type"))
        if params.get("funding"):
            query = query.filter(funding=params.get("funding"))
        if params.get("target_audience"):
            query = query.filter(target_audience=params.get("target_audience"))
        if params.get("additional_platforms"):
            query = query.filter(additional_platforms=params.get("additional_platforms"))

        date_from = params.get("date_from")
        date_to = params.get("date_to")
        if date_from is not None and date_to is not None:
            query = query.filter(date_start__range=[date_from, date_to]).filter(date_end__range=[date_from, date_to])
        if params.get("node_only") and self.use_node:
            query = query.filter(node=self.use_node)
        
        related_values = list(query.values_list("node__name", "node_main__name", "organising_institution"))
        values = list(query.values())
        result = [
            {
                **value,
                "node": node,
                "organising_institution": organising_institution,
                "node_main": node_main
            }
            for value, (node, node_main, organising_institution) in zip(values, related_values)
        ]
        return result
    
    def get_name(self):
        return self.name


class Group():
    def __init__(
        self,
        name,
        field_mapping,
        model,
        use_fields=None,
        filter_fields=[
            "event_type",
            "event_funding",
            "event_target_audience",
            "event_additional_platforms"
        ],
        graph_type="bar",
        field_options_mapping={},
        use_node=None
    ):
        self.use_node = use_node
        self.field_mapping = field_mapping
        self.name = name
        self.filter_fields = filter_fields
        self.graph_type = graph_type
        self.model = model
        self.use_fields = use_fields
        self.field_options_mapping = field_options_mapping

        event_fields = [
            "type",
            "funding",
            "target_audience",
            "additional_platforms",
            "communities",
        ]
        all_fields = set([*self.use_fields, *self.filter_fields])
        self.fields = {
            **{
                field_id: options
                for field_id, options in get_model_field_options(self.model)
                if field_id in self.use_fields
            },
            **{
                f"event_{field_id}": options
                for field_id, options in get_model_field_options(Event)
                if field_id in event_fields
            },
        }
        
    
    def get_graph_type(self):
        return self.graph_type

    def get_fields(self):
        return self.use_fields
    
    def get_filter_fields(self):
        return self.filter_fields
    
    def get_field_placeholder(self, field_id):
        return f"Select {self.get_field_title(field_id)}"
    
    def get_field_options(self, field_id):
        return self.fields[field_id]
    
    def get_field_option_name(self, field_id, option_id):
        field_option_id = f"{field_id}:{option_id}"
        default = option_id if option_id else "No response"
        return self.field_options_mapping.get(field_option_id, default)
    
    def get_field_title(self, lookup_id):
        for name, field_id in self.field_mapping.items():
            if lookup_id == field_id:
                return name
        return lookup_id
        
    
    def get_values(self, **params):
        query = self.model.objects.all()
        if params.get("event_type"):
            query = query.filter(event__type=params.get("event_type"))
        if params.get("event_funding"):
            query = query.filter(event__funding=params.get("event_funding"))
        if params.get("event_target_audience"):
            query = query.filter(event__target_audience=params.get("event_target_audience"))
        if params.get("event_additional_platforms"):
            query = query.filter(event__additional_platforms=params.get("event_additional_platforms"))

        date_from = params.get("date_from")
        date_to = params.get("date_to")
        if date_from is not None and date_to is not None:
            query = query.filter(event__date_start__range=[date_from, date_to]).filter(event__date_end__range=[date_from, date_to])
        if params.get("node_only") and self.use_node:
            query = query.filter(event__node=self.use_node)

        result = list(query.values())
        return result
    
    def get_name(self):
        return self.name


class Metrics():
    def __init__(self, groups):
        self.groups = groups

    def get_group(self, name):
        return self.groups.get(name, None)


def get_metrics(request):
    node = (
        request.user.get_node()
        if request.user.is_authenticated
        else None
    )
    shared_field_mapping = {
        "Type": "event_type",
        "Event funding": "event_funding",
        "Target audience": "event_target_audience",
        "Additional platforms": "event_additional_platforms",
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
        "The balance of theoretical and practical content was": "balance",
        "How long ago did you attend the training?": "when_attend_training",
        "What was your main reason for attending the training?": "main_attend_reason",
        "How often did you use the tool(s)/ resource(s), covered in the training, BEFORE attending the training?": "how_often_use_before",
        "How often do you use the tool(s)/ resource(s), covered in the training, AFTER having attended the training?": "how_often_use_after",
        "Do you feel that you are able to explain to others what you learnt in the training?": "able_to_explain",
        "Are you now able to use the tool(s)/ resource(s) covered in the training?": "able_use_now",
        "How did the training event help with your work?": "help_work",
        "Attending the training event led to/ facilitated:": "attending_led_to",
        "How many people have you shared the skills and/or knowledge that you learned during the training, with?": "people_share_knowledge",
        "Would you recommend the training to others?": "recommend_others"
    }
    groups = {
        "event": EventGroup(
            "Number of events",
            {
                "Type": "type",
                "Event funding": "funding",
                "Target audience": "target_audience",
                "Additional platforms": "additional_platforms"
            },
            use_fields=[
                "type",
                "funding",
                "target_audience",
                "additional_platforms"
            ],
            use_node=node
        ),
        "event_full": EventGroup(
            "Events",
            {
                "Type": "type",
                "Event funding": "funding",
                "Target audience": "target_audience",
                "Additional platforms": "additional_platforms"
            },
            use_fields=[
                "code",
                "id",
                "title",
                "node",
                "node_main",
                "date_start",
                "date_end",
                "type",
                "organising_institution",
            ],
            use_node=node
        ),
        "impact": Group(
            "Number of answers",
            {
               **shared_field_mapping,
            },
            Impact,
            use_fields=[
                "when_attend_training",
                "main_attend_reason",
                "how_often_use_before",
                "how_often_use_after",
                "able_to_explain",
                "able_use_now",
                "attending_led_to",
                "people_share_knowledge",
                "recommend_others",
            ],
            graph_type="pie",
            use_node=node
        ),
        "quality": Group(
            "Number of answers",
            {
               **shared_field_mapping,
            },
            Quality,
            use_fields=[
                "used_resources_before",
                "used_resources_future",
                "recommend_course",
                "course_rating",
                "balance",
                "email_contact",
            ],
            graph_type="pie",
            use_node=node
        ),
        "demographic": Group(
            "Number of answers",
            {
               **shared_field_mapping,
            },
            Demographic,
            use_fields=[
                "employment_country",
                "heard_from",
                "employment_sector",
                "gender",
                "career_stage",
            ],
            graph_type="pie",
            use_node=node
        ),
    }
    return Metrics(groups)

def metrics_middleware(get_response):
    def middleware(request):
        setattr(request, "metrics", get_metrics(request))
        response = get_response(request)
        return response

    return middleware