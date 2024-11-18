from django.http import JsonResponse
from metrics.models import Event, QuestionSuperSet, Response
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F
from metrics.views.common import get_tabs
from django.urls import reverse
from django.shortcuts import render
from datetime import date
from django.shortcuts import get_object_or_404
from django.db.models import Q


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


def event_api(request):
    (
        event_type,
        funding,
        target_audience,
        additional_platforms,
        date_from,
        date_to,
        node_only,
        current_node
    ) = _get_filter_params(request)

    query = Event.objects.all()
    if event_type:
        query = query.filter(type=event_type)
    if funding:
        query = query.filter(funding=funding)
    if target_audience:
        query = query.filter(target_audience=target_audience)
    if additional_platforms:
        query = query.filter(additional_platforms=additional_platforms)
    if date_from is not None and date_to is not None:
        query = query.filter(
            Q(date_start__range=[date_from, date_to]) |
            Q(date_end__range=[date_from, date_to])
        )
    if node_only and current_node:
        query = query.filter(event__node=current_node)

    entries = list(query.values())
    params = {
        "type": "Type",
        "funding": "Event funding",
        "target_audience": "Target audience",
        "additional_platforms": "Additional platforms",
        "communities": "Communities",
    }

    summary = {
        key: _calculate_metrics(entries, key)
        for key in params.keys()
    }
    result = [
        {
            "label": params.get(key),
            "id": key,
            "count": [
                {
                    "label": param,
                    "id": param,
                    "count": count
                }
                for param, count in summary[key].items()
            ]
        }
        for key in params.keys()
    ]

    return JsonResponse({
        "values": result
    })


def metrics_api(request, question_set_id):
    (
        event_type,
        funding,
        target_audience,
        additional_platforms,
        date_from,
        date_to,
        node_only,
        current_node
    ) = _get_filter_params(request)

    superset = get_object_or_404(QuestionSuperSet, slug=question_set_id, use_for_metrics=True)
    if (superset.node is not None and superset.node != current_node):
        raise PermissionDenied("This set is not publicly available")

    questions = {
        q.slug: q
        for qs in superset.question_sets.all()
        for q in qs.questions.all()
    }

    query = Response.objects.filter(answer__question__in=questions.values())
    if event_type:
        query = query.filter(response_set__event__type=event_type)
    if funding:
        query = query.filter(response_set__event__funding=funding)
    if target_audience:
        query = query.filter(response_set__event__target_audience=target_audience)
    if additional_platforms:
        query = query.filter(response_set__event__additional_platforms=additional_platforms)
    if node_only and current_node:
        query = query.filter(response_set__event__node=current_node)
    if date_from is not None and date_to is not None:
        query = query.filter(
            Q(response_set__event__date_start__range=[date_from, date_to]) |
            Q(response_set__event__date_end__range=[date_from, date_to])
        )
    if node_only and current_node:
        query = query.filter(event__node=current_node)

    query = query.prefetch_related("answer", "answer__question", "response_set")
    query = (
        query
        .order_by('answer__question__slug', 'answer__slug')
        .values('answer').annotate(count=Count('answer'))
    )

    summary = {
        value["answer"]: value["count"]
        for value in query
    }

    result = [
        {
            "label": question.text,
            "id": question.slug,
            "count": [
                {
                    "label": answer.text,
                    "id": answer.slug,
                    "count": summary.get(answer.id, 0)
                }
                for answer in question.answers.all()
            ]
        }
        for question in questions.values()
    ]

    return JsonResponse({
        "values": result
    })


def _calculate_metrics(data, column):
    column_values = [d.get(column) for d in data]
    count = {}
    for value in column_values:
        if value is not None:
            values = value if type(value) == list else [value]
            for v in values:
                count[v] = count.get(v, 0) + 1
    return count


def _get_filter_params(request):
    event_type = request.GET.get("type", None)
    funding = request.GET.get("funding", None)
    target_audience = request.GET.get("target-audience", None)
    additional_platforms = request.GET.get("additional-platforms", None)
    date_from = request.GET.get("date-from", None)
    date_to = request.GET.get("date-to", None)
    node_only = bool(int(request.GET.get("node-only", "0")))
    current_node = request.user.get_node() if request.user else None

    return (
        event_type,
        funding,
        target_audience,
        additional_platforms,
        date_from,
        date_to,
        node_only,
        current_node
    )


def _value_group(responses):
    value_group = {}
    for r in responses:
        vid = r.answer.question.slug
        vs = value_group.get(vid, [])
        vs.append(r.answer.slug)
        value_group[vid] = vs
    return value_group