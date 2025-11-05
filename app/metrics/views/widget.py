from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import quote

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.templatetags.static import static
from django.views.generic import TemplateView


TMD_METRICS_BASE_URL = "https://tmd.elixir-europe.org/metrics/set/"


class WidgetDemoView(TemplateView):
    template_name = "widgets/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        script_url = getattr(settings, "TMD_WIDGET_SCRIPT_URL", "")
        if script_url:
            context["widget_script_url"] = script_url
        else:
            context["widget_script_url"] = static("widgets/widget.js")
        return context

def _set_cors_headers(response):
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Headers"] = "Content-Type"
    response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response


def proxy_question_set(request, question_set_slug: str):
    """
    Lightweight proxy to work around missing CORS headers on the public TMD endpoint.
    Retrieves the aggregated statistics for the provided question set and pipes the raw JSON back to the widget.
    """

    if request.method == "OPTIONS":
        return _set_cors_headers(HttpResponse(status=204))

    endpoint = f"{TMD_METRICS_BASE_URL}{quote(question_set_slug)}"
    query_string = request.META.get("QUERY_STRING")
    if query_string:
        endpoint = f"{endpoint}?{query_string}"
    try:
        with urlrequest.urlopen(endpoint) as response:
            payload = response.read()
            content_type = response.headers.get("Content-Type", "application/json")
    except urlerror.HTTPError as exc:
        return JsonResponse(
            {"error": "TMD upstream returned an error."},
            status=exc.code,
        )
    except urlerror.URLError:
        return JsonResponse(
            {"error": "Failed to reach the TMD upstream service."},
            status=502,
        )

    return _set_cors_headers(HttpResponse(payload, content_type=content_type))
