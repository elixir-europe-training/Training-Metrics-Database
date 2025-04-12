from django.http import JsonResponse, Http404
from metrics.models import (
    Event,
    QuestionSuperSet,
    Response,
    Quality,
    Impact,
    Demographic,
    UserProfile,
    SystemSettings,
)
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from metrics.views.common import get_tabs
from metrics.forms import MetricsFilterForm
from django.urls import reverse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.views import View
import csv
import io
import base64


class MetricsView(View):
    def get_metrics(
        self,
        event_type=None,
        event_funding=None,
        event_target_audience=None,
        event_additional_platforms=None,
        event_node=None,
        date_to=None,
        date_from=None,
    ):
        return []

    def metrics_to_csv(self, metrics: list):
        fieldnames = ["question", "option", "count"]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        data = [
            {
                "question": entry["label"],
                "option": option["label"],
                "count": option["count"]
            }
            for entry in metrics
            for option in entry["options"]
        ]
        writer.writeheader()
        for entry in data:
            writer.writerow(entry)

        return output.getvalue()

    def csv_to_base64_url(self, csv_data: str):
        data = base64.b64encode(csv_data.encode('utf-8')).decode("utf-8").strip()
        uri = f"data:text/csv;base64,{data}"
        return uri

    def get_download_name(self):
        return "metrics"

    def get_download_label(self):
        return "Download metrics"

    def get_title(self):
        return getattr(self, "title", "Metrics")

    def get(self, request, *args, **kwargs):
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
        metrics = self.get_metrics(
            event_type=event_type,
            event_funding=funding,
            event_target_audience=target_audience,
            event_additional_platforms=additional_platforms,
            event_node=node_only and current_node,
            date_to=date_to,
            date_from=date_from,
        )
        title = self.get_title()
        data_csv = self.metrics_to_csv(metrics)
        data_url = self.csv_to_base64_url(data_csv)
        filename = f"{self.get_download_name()}.csv"
        chart_type = {"pie": "pie", "bar": "bar"}.get(request.GET.get("chart_type", None), "pie")
        filter_form = MetricsFilterForm(request.GET or None)
        return render(
            request,
            "metrics/metrics.html",
            context={
                **get_tabs(request),
                "title": title,
                "metrics": metrics,
                "chart_type": chart_type,
                "filter_form": filter_form,
                "download": {
                    "label": self.get_download_label(),
                    "href": data_url,
                    "filename": filename
                }
            }
        )


class EventMetricsView(MetricsView):
    def get_download_name(self):
        return "event-metrics"

    def get_download_label(self):
        return "Download event metrics"

    def get_title(self):
        return "Event Metrics"

    def get_metrics(
        self,
        **kwargs
    ):
        return get_event_info(
            **kwargs
        )


class SuperSetMetricsView(MetricsView):
    def get_download_name(self):
        question_set_id = self.kwargs["question_set_id"]
        return f"{question_set_id}-metrics"

    def get_download_label(self):
        return f"Download {self.superset.name} metrics"

    def get_title(self):
        return f"{self.superset.name} Metrics"

    def get_metrics(
        self,
        **kwargs
    ):
        question_set_id = self.kwargs["question_set_id"]
        superset = get_object_or_404(QuestionSuperSet, slug=question_set_id, use_for_metrics=True)
        self.superset = superset
        current_node = UserProfile.get_node(self.request.user)
        if (superset.node is not None and superset.node != current_node):
            raise PermissionDenied("This set is not publicly available")

        return get_metrics_info(
            superset,
            **kwargs
        )


class LegacyMetricsView(MetricsView):
    def get_download_name(self):
        question_set_id = self.kwargs["question_set_id"]
        return f"{question_set_id}-metrics"

    def get_download_label(self):
        return f"Download {self.model._meta.verbose_name} metrics"

    def get_title(self):
        return f"{self.model._meta.verbose_name.title()} Metrics"

    def get_metrics(
        self,
        **kwargs
    ):
        question_set_id = self.kwargs["question_set_id"]
        self.model = get_metrics_model_or_404(question_set_id)
        return get_legacy_metrics_info(
            self.model,
            **kwargs
        )


def get_metrics_model_or_404(model_id):
    model = {
        "quality": Quality,
        "impact": Impact,
        "demographic": Demographic
    }.get(model_id, None)
    if model is None:
        raise Http404(f"Model could nog be found: {model_id}")
    return model


def get_metrics_view(request, *args, **kwargs):
    settings = SystemSettings.get_settings(request.user)

    if settings.has_flag("use_new_model_stats"):
        return SuperSetMetricsView.as_view()(request, *args, **kwargs)
    else:
        return LegacyMetricsView.as_view()(request, *args, **kwargs)


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
            "title": "Training Metrics Database",
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

    result = get_event_info(
        event_type=event_type,
        event_funding=funding,
        event_target_audience=target_audience,
        event_additional_platforms=additional_platforms,
        event_node=node_only and current_node,
        date_to=date_to,
        date_from=date_from,
    )

    return JsonResponse({
        "values": result
    })


def question_api(request, question_set_id: str):
    (
        _event_type,
        _funding,
        _target_audience,
        _additional_platforms,
        _date_from,
        _date_to,
        _node_only,
        current_node
    ) = _get_filter_params(request)

    superset = get_object_or_404(QuestionSuperSet, slug=question_set_id, use_for_metrics=True)
    if (superset.node is not None and superset.node != current_node):
        raise PermissionDenied("This set is not publicly available")

    result = get_question_info(superset)

    return JsonResponse({
        "values": result
    })


def event_properties_api(request):
    filterable_only = "filterable-only" in request.GET
    result = get_event_properties(filterable_only)

    return JsonResponse({
        "values": result
    })


def get_metrics_api(request, *args, **kwargs):
    settings = SystemSettings.get_settings(request.user)

    if settings.has_flag("use_new_model_stats"):
        return metrics_api(request, *args, **kwargs)
    else:
        return legacy_metrics_api(request, *args, **kwargs)


def metrics_api(request, question_set_id: str):
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

    result = get_metrics_info(
        superset,
        event_type=event_type,
        event_funding=funding,
        event_target_audience=target_audience,
        event_additional_platforms=additional_platforms,
        event_node=node_only and current_node,
        date_to=date_to,
        date_from=date_from,
    )

    return JsonResponse({
        "values": result,
    })


def legacy_metrics_api(request, question_set_id: str):
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

    metrics_type = get_metrics_model_or_404(question_set_id)

    result = get_legacy_metrics_info(
        metrics_type,
        event_type=event_type,
        event_funding=funding,
        event_target_audience=target_audience,
        event_additional_platforms=additional_platforms,
        event_node=node_only and current_node,
        date_to=date_to,
        date_from=date_from,
    )

    return JsonResponse({
        "values": result,
    })


def get_event_info(
    event_type=None,
    event_funding=None,
    event_target_audience=None,
    event_additional_platforms=None,
    event_node=None,
    date_to=None,
    date_from=None,
):
    field_options = _get_model_field_options(Event)
    options = {
        field.name: options
        for field, options in field_options
    }
    query = Event.objects.all()
    if event_type:
        query = query.filter(type=event_type)
    if event_funding:
        query = query.filter(funding__contains=event_funding)
    if event_target_audience:
        query = query.filter(target_audience__contains=event_target_audience)
    if event_additional_platforms:
        query = query.filter(additional_platforms__contains=event_additional_platforms)

    date_from_filter = Q(date_end__gte=date_from) if date_from else Q()
    date_to_filter = Q(date_start__lte=date_to) if date_to else Q()
    query = query.filter(date_from_filter & date_to_filter)

    if event_node:
        query = query.filter(node__in=[event_node])

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
    return [
        {
            "label": params.get(key),
            "id": key,
            "options": sorted(list({
                **{
                    option: {
                        "label": option,
                        "id": option,
                        "count": 0
                    }
                    for (option, _option) in options[key]
                },
                **{
                    param: {
                        "label": param,
                        "id": param,
                        "count": count
                    }
                    for param, count in summary[key].items()
                }
            }.values()), key=lambda v: -v["count"])
        }
        for key in params.keys()
    ]


def get_question_info(question_superset):
    return [
        {
            "label": question.text,
            "id": question.slug,
            "options": [
                {
                    "label": answer.text,
                    "id": answer.slug,
                }
                for answer in question.answers.all()
            ]
        }
        for question_set in question_superset.question_sets.all()
        for question in question_set.questions.all()
    ]


def get_event_properties(filterable_only=False):
    field_options = _get_model_field_options(Event)
    type_map = {
        "CharField": "string",
        "DateField": "date",
        "DecimalField": "number",
        "DateTimeField": "datetime",
        "PositiveIntegerField": "number",
        "BooleanField": "bool",
    }

    filterable_fields = {
        "type",
        "funding",
        "target_audience",
        "additional_platforms",
        "date_start",
        "date_end"
    }

    return [
        {
            "label": field.verbose_name.title(),
            "id": field.name,
            "type": "choice" if options else type_map[field.get_internal_type()],
            "filterable": field.name in filterable_fields,
            **({
                "options": [
                    {
                        "label": option[1],
                        "id": option[0],
                    }
                    for option in options
                ]
            } if options else {})
        }
        for (field, options) in field_options
        if (
            field.get_internal_type() not in {"ForeignKey", "ManyToManyField"} and
            field.name not in {"id", "created", "modified", "code", "locked"} and
            (not filterable_only or field.name in filterable_fields)
        )
    ]


def get_metrics_info(
    question_superset,
    event_type=None,
    event_funding=None,
    event_target_audience=None,
    event_additional_platforms=None,
    event_node=None,
    date_to=None,
    date_from=None,
):
    questions = {
        q.slug: q
        for qs in question_superset.question_sets.all()
        for q in qs.questions.all()
    }

    query = Response.objects.filter(answer__question__in=questions.values())
    if event_type:
        query = query.filter(response_set__event__type=event_type)
    if event_funding:
        query = query.filter(response_set__event__funding__contains=event_funding)
    if event_target_audience:
        query = query.filter(response_set__event__target_audience__contains=event_target_audience)
    if event_additional_platforms:
        query = query.filter(response_set__event__additional_platforms__contains=event_additional_platforms)
    if event_node:
        query = query.filter(response_set__event__node__in=[event_node])

    date_from_filter = Q(response_set__event__date_end__gte=date_from) if date_from else Q()
    date_to_filter = Q(response_set__event__date_start__lte=date_to) if date_to else Q()
    query = query.filter(date_from_filter & date_to_filter)

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

    return [
        {
            "label": question.text,
            "id": question.slug,
            "options": sorted([
                {
                    "label": answer.text,
                    "id": answer.slug,
                    "count": summary.get(answer.id, 0)
                }
                for answer in question.answers.all()
            ], key=lambda v: -v["count"])
        }
        for question in questions.values()
    ]


def get_legacy_metrics_info(
    metrics_type,
    event_type=None,
    event_funding=None,
    event_target_audience=None,
    event_additional_platforms=None,
    event_node=None,
    date_to=None,
    date_from=None,
):
    field_options = _get_model_field_options(metrics_type)
    mapped_options = {
        field.name: options
        for field, options in field_options
    }
    query = metrics_type.objects.all()
    if event_type:
        query = query.filter(event__type=event_type)
    if event_funding:
        query = query.filter(event__funding__contains=event_funding)
    if event_target_audience:
        query = query.filter(event__target_audience__contains=event_target_audience)
    if event_additional_platforms:
        query = query.filter(event__additional_platforms__contains=event_additional_platforms)

    date_from_filter = Q(event__date_end__gte=date_from) if date_from else Q()
    date_to_filter = Q(event__date_start__lte=date_to) if date_to else Q()
    query = query.filter(date_from_filter & date_to_filter)

    if event_node:
        query = query.filter(event__node__in=[event_node])

    ignored_fields = {
        "id",
        "event",
        "user",
        "event_id",
        "user_id",
        "created",
        "modified"
    }

    result = {}
    for value in query.values():
        for key, value in value.items():
            if key not in ignored_fields:
                result[key] = result.get(key, {})
                values = value if isinstance(value, list) else [value]
                for v in values:
                    result[key][v] = result[key].get(v, 0) + 1

    return [
        {
            "label": metrics_type._meta.get_field(key).verbose_name,
            "id": key,
            "options": sorted(list(
                {
                    option: {
                        "label": label,
                        "id": option,
                        "count": result.get(key, {}).get(option, 0)
                    }
                    for label, option in options
                }.values()
            ), key=lambda v: -v["count"])
        }
        for key, options in mapped_options.items()
        if key not in ignored_fields
    ]


def _calculate_metrics(data, column):
    column_values = [d.get(column) for d in data]
    count = {}
    for value in column_values:
        if value is not None:
            values = value if type(value) is list else [value]
            for v in values:
                count[v] = count.get(v, 0) + 1
    return count


def _get_filter_params(request):
    event_type = request.GET.get("type", None)
    funding = request.GET.getlist("funding", None)
    target_audience = request.GET.getlist("target_audience", None)
    additional_platforms = request.GET.getlist("additional_platforms", None)
    date_from = request.GET.get("date_from", None) or None
    date_to = request.GET.get("date_to", None) or None
    node_only = bool(int(request.GET.get("node_only", "0")))
    current_node = UserProfile.get_node(request.user) if request.user.is_authenticated else None

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


def _get_field_options(field):
    choices = getattr(field, "choices", [])
    choices = getattr(
        getattr(field, "base_field", None),
        "choices",
        []
    ) if not choices else choices
    return (
        []
        if not choices
        else choices
    )


def _get_model_field_options(model):
    return (
        (field, _get_field_options(field))
        for field in model._meta.get_fields()
    )
