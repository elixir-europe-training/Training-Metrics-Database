from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import quote

from django.http import HttpResponse, JsonResponse


TMD_METRICS_BASE_URL = "https://tmd.elixir-europe.org/metrics/set/"


def proxy_question_set(request, question_set_slug: str):
    """
    Lightweight proxy to work around missing CORS headers on the public TMD endpoint.
    Retrieves the aggregated statistics for the provided question set and pipes the raw JSON back to the widget.
    """
    endpoint = f"{TMD_METRICS_BASE_URL}{quote(question_set_slug)}"
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

    return HttpResponse(payload, content_type=content_type)
