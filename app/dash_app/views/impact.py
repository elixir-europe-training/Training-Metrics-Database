from metrics.views.common import get_layout, use_callback, get_tabs

from django_plotly_dash import DjangoDash
from django.shortcuts import render


def impact_report(request):
    app = DjangoDash("ImpactReport")
    group = request.metrics.get_group('impact')
    dash_config = {}
    if group:
        app.layout = get_layout(app, group)
        use_callback(app, group)
        dash_config = {
            "dash_name": "ImpactReport"
        }

    return render(
        request,
        'dash_app/template.html',
        context={
            **get_tabs(request),
            **dash_config,
            "title": "Impact metrics"
        }
    )


