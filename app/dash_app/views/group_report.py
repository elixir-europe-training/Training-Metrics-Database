from metrics.views.common import get_layout, use_callback, get_tabs
from django.http import HttpResponseNotFound

from django_plotly_dash import DjangoDash
from django.shortcuts import render


def group_report(request, group_id):
    group = request.metrics.get_group(group_id)
    if not group:
        return HttpResponseNotFound(f"Group with id '{group_id}' not found.")  

    app = DjangoDash(group_id)
    app.layout = get_layout(app, group)
    use_callback(app, group)
    dash_config = {
        "dash_name": group_id
    }

    return render(
        request,
        'dash_app/template.html',
        context={
            **get_tabs(request),
            **dash_config
        }
    )


