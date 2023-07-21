from datetime import datetime
from functools import lru_cache
from contextlib import suppress
from .models import Event, Quality, Impact


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
        graph_type="bar"
    ):
        self.field_mapping = field_mapping
        self.name = name
        self.filter_fields = filter_fields
        self.graph_type = graph_type
        self.model = model
        self.use_fields = use_fields
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
    
    def get_field_title(self, lookup_id):
        for name, field_id in self.field_mapping.items():
            if lookup_id == field_id:
                return name
        return lookup_id
        
    
    def get_values(self, **params):
        print(params)
        query = self.model.objects.all()
        if params.get("event_type"):
            query = query.filter(event__type=params.get("event_type"))
        result = list(query.values())
        print(result)
        return result
    
    def get_name(self):
        return self.name


class Metrics():
    def __init__(self, groups):
        self.groups = groups

    def get_group(self, name):
        return self.groups.get(name, None)


@lru_cache
def get_metrics():
    groups = {
        "impact": Group(
            "Impact",
            {},
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
            ]
        ),
        "quality": Group(
            "Quality",
            {},
            Quality,
            use_fields=[
                "used_resources_before",
                "used_resources_future",
                "recommend_course",
                "course_rating",
                "balance",
                "email_contact",
            ]
        ),
    }
    return Metrics(groups)

def metrics_middleware(get_response):
    def middleware(request):
        setattr(request, "metrics", get_metrics())
        response = get_response(request)
        return response

    return middleware