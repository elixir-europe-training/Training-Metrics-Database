from django.db.models import Q
from django.http import QueryDict

from django.urls import reverse
from metrics.models import SystemSettings


def get_metrics_tabs(request):
    settings = SystemSettings.get_settings(request.user)
    set_ids = (
        [
            (superset.name, superset.slug)
            for superset in settings.get_metrics_sets()
        ]
        if settings.has_flag("use_new_model_stats")
        else [
            ("Impact metrics", "impact"),
            ("Demographic metrics", "demographic"),
            ("Quality metrics", "quality")
        ]
    )
    set_tabs = [
        (label, "metrics-set-report", {"question_set_id": set_id})
        for (label, set_id) in set_ids
    ]
    return [
        ("Events", "metrics-event-report", {}),
        *set_tabs
    ]


def get_tabs(request, view_name=None):
    user_input = (
        [
            ("Upload data", "upload-data", {}),
            ("Import from TeSS", "tess-import", {}),
            ("All institutions", "institution-list", {})
        ]
        if request.user.is_authenticated
        else []
    )
    tabs = [
        {"title": title, "url": reverse(name, kwargs=kwargs), "name": name}
        for title, name, kwargs in [
            ("World map", "world-map", {}),
            *get_metrics_tabs(request),
            ("Browse events", "event-list", {}),
            *user_input,
        ]
    ]
    return {
        "tabs": [
            {**tab, "active": tab["url"] == request.path_info or tab["name"] == view_name}
            for tab in tabs
        ]
    }


def get_event_filter_query(
    event_type=None,
    event_funding=None,
    event_target_audience=None,
    event_additional_platforms=None,
    event_node=None,
    date_to=None,
    date_from=None,
    prefix=None
):
    prefix = "" if prefix is None else prefix
    filter_variants = [
        {f"{prefix}type": event_type} if event_type else None,
        {f"{prefix}funding__contains": event_funding} if event_funding else None,
        {f"{prefix}target_audience__contains": event_target_audience} if event_target_audience else None,
        {f"{prefix}additional_platforms__contains": event_additional_platforms} if event_additional_platforms else None,
        {f"{prefix}date_end__gte": date_from} if date_from else None,
        {f"{prefix}date_start__lte": date_to} if date_to else None,
        {f"{prefix}node__in": [event_node]} if event_node else None,
    ]

    query = Q()
    for filter_variant in filter_variants:
        if filter_variant:
            query = query & Q(**filter_variant)

    return query


def dict_to_querydict(d):
    qd = QueryDict("", mutable=True)
    for key, values in d.items():
        for value in (values if isinstance(values, list) else [values]):
            if value:
                qd.update({key: value})
    return qd
