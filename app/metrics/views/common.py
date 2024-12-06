from datetime import datetime
from functools import lru_cache
from itertools import groupby

from django.urls import reverse
from metrics.models import SystemSettings


def get_metrics_tabs():
    settings = SystemSettings.get_settings()
    supersets = settings.get_metrics_sets()
    set_tabs = [
        (superset.name, "metrics-set-report", {"question_set_id": superset.slug})
        for superset in supersets
    ]
    return [
        ("Events", "metrics-event-report", {}),
        *set_tabs
    ]


def get_tabs(request, view_name=None):
    view_name = (
        request.resolver_match.view_name
        if view_name is None
        else view_name
    )
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
        {"title": title, "url": reverse(name, kwargs=kwargs)}
        for title, name, kwargs in [
            ("World map", "world-map", {}),
            *get_metrics_tabs(),
            ("Browse events", "event-list", {}),
            *user_input,
        ]
    ]
    return {
        "tabs": [
            {**tab, "active": tab["url"] == request.path_info}
            for tab in tabs
        ]
    }
