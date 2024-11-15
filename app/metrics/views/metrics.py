from django.http import JsonResponse
from metrics.models import Event
from django.db.models import Count, F
from metrics.views.common import get_tabs
from django.urls import reverse
from django.shortcuts import render


def world_map_api(request):
    events = (
        Event.objects.order_by('location_country').values('location_country').annotate(count=Count('location_country'))
    )
    output = [
        {
            "country": event["location_country"],
            "count": event["count"]
        }
        for event in events
    ]
    return JsonResponse({
        "values": output
    })


def world_map_event_count(request):
    return render(
        request,
        "metrics/world-map.html",
        context={
            **get_tabs(request),
            "data_url": reverse("world-map-api")
        }
    )