from datetime import datetime
from functools import lru_cache
from contextlib import suppress
from .models import Event, Quality, Impact, Demographic, Node, SystemSettings, Response


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
        use_node=None,
        is_tab=False
    ):
        self.is_tab = is_tab
        self.use_node = use_node
        self.field_mapping = field_mapping
        self.name = name
        self.filter_fields = filter_fields
        self.graph_type = graph_type
        self.model = Event
        self.use_fields = use_fields
        self.field_options_mapping = field_options_mapping
        self.fields = {
            field_id: self.model.objects.order_by().values(field_id).distinct().values_list(field_id, flat=True)
            for field_id in set([*self.use_fields, *self.filter_fields])
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


class LegacyGroup():
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
        use_node=None,
        is_tab=False
    ):
        self.is_tab = is_tab
        self.use_node = use_node
        self.field_mapping = field_mapping
        self.name = name
        self.filter_fields = filter_fields
        self.graph_type = graph_type
        self.model = model
        self.use_fields = use_fields
        self.field_options_mapping = field_options_mapping
        self.fields = {
            **{
                field_id: self.model.objects.order_by().values(field_id).distinct().values_list(field_id, flat=True)
                for field_id in self.use_fields
            },
            **{
                f"event_{field_id}": Event.objects.order_by().values(field_id).distinct().values_list(field_id, flat=True)
                for field_id in [
                    "type",
                    "funding",
                    "target_audience",
                    "additional_platforms",
                    "communities",
                ]
            }
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


class MetricsGroup:
    def __init__(
        self,
        name,
        question_set,
        graph_type="bar",
        field_options_mapping={},
        use_node=None,
        is_tab=False
    ):
        self.question_set = question_set
        self._questions = None
        self._answers = None
        self.event_field_mapping = {
            "event_type": "Type",
            "event_funding": "Event funding",
            "event_target_audience": "Target audience",
            "event_additional_platforms": "Additional platforms",
            "event_communities": "Communities",
        }
        
        event_fields = [
            field_id.replace("event_", "")
            for field_id in self.event_field_mapping.keys()
        ]
        self.is_tab = is_tab
        self.use_node = use_node
        self.name = name
        self.filter_fields = list(self.event_field_mapping.keys())
        self.graph_type = graph_type
        self.field_options_mapping = field_options_mapping
        self.fields = {
            **{
                f"event_{field_id}": Event.objects.order_by().values(field_id).distinct().values_list(field_id, flat=True)
                for field_id in event_fields
            }
        }

    @property
    def questions(self):
        if not self._questions:
            self._questions = {
                q.slug: q
                for q in self.question_set.questions.all()
            }
        return self._questions
    
    @property
    def answers(self):
        if not self._answers:
            self._answers = {
                f"{q.slug}:{a.slug}": a
                for q in self.questions.values()
                for a in q.answers.all()
            }
        return self._answers
    
    def get_graph_type(self):
        return self.graph_type

    def get_fields(self):
        return list(self.questions.keys())
    
    def get_filter_fields(self):
        return self.filter_fields
    
    def get_field_placeholder(self, field_id):
        return f"Select {self.get_field_title(field_id)}"
    
    def get_field_options(self, field_id):
        try:
            return [
                answer.slug
                for answer in self.questions[field_id].answers.all()
            ]
        except KeyError:
            return self.fields.get(field_id, [])
    
    def get_field_option_name(self, field_id, option_id):
        field_option_id = f"{field_id}:{option_id}"
        try:
            return self.answers[field_option_id].text
        except KeyError:
            return field_option_id
    
    def get_field_title(self, lookup_id):
        try:
            return self.questions[lookup_id].text
        except KeyError:
            return self.event_field_mapping.get(lookup_id, lookup_id)
    
    def get_values(self, **params):
        query = Response.objects.filter(answer__question__in=self.questions.values())
        if params.get("event_type"):
            query = query.filter(response_set__event__type=params.get("event_type"))
        if params.get("event_funding"):
            query = query.filter(response_set__event__funding=params.get("event_funding"))
        if params.get("event_target_audience"):
            query = query.filter(response_set__event__target_audience=params.get("event_target_audience"))
        if params.get("event_additional_platforms"):
            query = query.filter(response_set__event__additional_platforms=params.get("event_additional_platforms"))
        if params.get("node_only") and self.use_node:
            query = query.filter(response_set__event__node=self.use_node)

        values = query.prefetch_related("answer", "answer__question", "response_set")
        grouped_values = {}
        for value in values:
            group_id = value.response_set.id
            value_group = grouped_values.get(group_id, [])
            value_group.append(value)
            grouped_values[group_id] = value_group

        result = [
            {
                r.answer.question.slug: r.answer.slug
                for r in value_group
            }
            for value_group in grouped_values.values()
        ]
        return result
    
    def get_name(self):
        return self.name


class Metrics():
    def __init__(self, groups):
        self.groups = groups

    def get_group(self, name):
        return self.groups.get(name, None)


def get_legacy_event_metrics(node):
    shared_field_mapping = {
        "Type": "event_type",
        "Event funding": "event_funding",
        "Target audience": "event_target_audience",
        "Additional platforms": "event_additional_platforms"
    }
    return {
        "impact": LegacyGroup(
            "Impact metrics",
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
            use_node=node,
            is_tab=True,
        ),
        "quality": LegacyGroup(
            "Quality metrics",
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
            use_node=node,
            is_tab=True,
        ),
        "demographic": LegacyGroup(
            "Demographic metrics",
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
            use_node=node,
            is_tab=True,
        ),
    }


def get_event_metrics(node, super_set):
    if not super_set:
        return {}
    question_sets = list(super_set.question_sets.all())
    return {
        question_set.slug: MetricsGroup(
            question_set.name,
            question_set,
            graph_type="pie",
            use_node=node,
            is_tab=True,
        )
        for question_set in question_sets
    }


def get_metrics(request):
    settings = SystemSettings.get_settings()
    node = (
        request.user.get_node()
        if request.user.is_authenticated
        else None
    )
    
    event_metrics = (
        get_event_metrics(node, settings.get_current_super_set())
        if settings.has_flag("use_new_model_stats")
        else get_legacy_event_metrics(node)
    )
    groups = {
        "event": EventGroup(
            "Event metrics",
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
            use_node=node,
            is_tab=True
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
            use_node=node,
        ),
        **event_metrics
    }
    return Metrics(groups)

def metrics_middleware(get_response):
    def middleware(request):
        setattr(request, "metrics", get_metrics(request))
        response = get_response(request)
        return response

    return middleware