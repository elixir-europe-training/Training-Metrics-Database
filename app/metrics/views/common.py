from datetime import datetime
from functools import lru_cache
from itertools import groupby

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
