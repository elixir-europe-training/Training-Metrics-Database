from metrics.views.common import get_layout, use_table_callback, get_table_layout, get_tabs

from django_plotly_dash import DjangoDash
from django.shortcuts import render


def all_events(request):
    app = DjangoDash("AllEvents")
    group = request.metrics.get_group('event_full')
    dash_config = {}
    if group:
        app.layout = get_table_layout(app, group)
        use_table_callback(app, group)
        dash_config = {
            "dash_name": "AllEvents"
        }

    return render(
        request,
        'dash_app/template.html',
        context={
            **get_tabs(request),
            **dash_config
        }
    )


