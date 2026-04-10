from django.http import JsonResponse
from metrics.models import (
    Event,
    Question,
    QuestionSuperSet,
    Response,
    UserProfile,
    Dataset,
)
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from metrics.views.common import get_tabs, get_event_filter_query, dict_to_querydict
from metrics.forms import MetricsFilterForm
from django.urls import reverse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.views import View
from django.utils.dateparse import parse_date
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
            current_node,
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
        filter_params = dict_to_querydict(filter_form.cleaned_data if filter_form.is_valid() else {})
        return render(
            request,
            "metrics/metrics.html",
            context={
                **get_tabs(request),
                "title": title,
                "metrics": metrics,
                "chart_type": chart_type,
                "filter_form": filter_form,
                "filter_params": filter_params,
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
            get_superset_questions([superset]),
            **kwargs
        )


def get_metrics_view(request, *args, **kwargs):
    return SuperSetMetricsView.as_view()(request, *args, **kwargs)


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
        current_node,
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


def properties_api(request):
    (
        _event_type,
        _funding,
        _target_audience,
        _additional_platforms,
        _date_from,
        _date_to,
        _node_only,
        current_node,
    ) = _get_filter_params(request)
    questionset_ids = parse_csv(request.GET.get("question_sets", ""))
    question_ids = parse_csv(request.GET.get("questions", ""))

    questions = get_questions(questionset_ids, question_ids, current_node)

    result = get_question_info(questions)

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
    return metrics_api(request, *args, **kwargs)


def parse_csv(csv_str):
    items = [
        item.strip()
        for item in csv_str.split(",")
    ]
    return [
        item
        for item in items
        if item != ""
    ]


def metrics_api(request):
    (
        event_type,
        funding,
        target_audience,
        additional_platforms,
        date_from,
        date_to,
        node_only,
        current_node,
    ) = _get_filter_params(request)
    questionset_ids = parse_csv(request.GET.get("question_sets", ""))
    question_ids = parse_csv(request.GET.get("questions", ""))
    dataset_id = request.GET.get("dataset")
    dataset = (
        None
        if dataset_id is None
        else get_object_or_404(Dataset.objects.filter(uuid=dataset_id))
    )

    if dataset is not None:
        node_only = True
        current_node = dataset.node
        date_to = (
            dataset.date_to
            if date_to is None
            else date_to
        )
        date_to = (
            date_to
            if dataset.date_to is None
            else min(date_to, dataset.date_to)
        )

        date_from = (
            dataset.date_from
            if date_from is None
            else date_from
        )
        date_from = (
            date_from
            if dataset.date_from is None
            else max(date_from, dataset.date_from)
        )

    questions = get_questions(questionset_ids, question_ids, current_node)
    event_node = node_only and current_node

    result = get_metrics_info(
        questions,
        event_type=event_type,
        event_funding=funding,
        event_target_audience=target_audience,
        event_additional_platforms=additional_platforms,
        event_node=event_node,
        date_to=date_to,
        date_from=date_from,
        normalized=True
    )

    return JsonResponse({
        "_meta": _params_to_meta(
            dataset=dataset_id,
            questions=question_ids,
            question_sets=questionset_ids,
            event_type=event_type,
            funding=funding,
            target_audience=target_audience,
            additional_platforms=additional_platforms,
            date_from=date_from,
            date_to=date_to,
            event_node=event_node,
        ),
        "values": result,
    })


def get_questions(questionset_ids, question_ids, current_node):
    question_set_questions = get_superset_questions(
        list(QuestionSuperSet.objects.filter(
            Q(slug__in=questionset_ids, use_for_metrics=True) & (Q(node__isnull=True) | Q(node=current_node))
        ))
    )
    questions = list(
        Question.objects.filter(
            Q(slug__in=question_ids) & (Q(node__isnull=True) | Q(node=current_node))
        )
    )

    return set([*question_set_questions, *questions])


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
    query = Event.objects.filter(get_event_filter_query(
        event_type,
        event_funding,
        event_target_audience,
        event_additional_platforms,
        event_node,
        date_to,
        date_from
    ))

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


def get_question_info(question_list):
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
        for question in question_list
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


def get_superset_questions(supersets):
    return [
        q
        for superset in supersets
        for qs in superset.question_sets.all()
        for q in qs.questions.all()
    ]


def get_metrics_info(
    question_list,
    event_type=None,
    event_funding=None,
    event_target_audience=None,
    event_additional_platforms=None,
    event_node=None,
    date_to=None,
    date_from=None,
    normalized=False
):
    questions = {
        q.slug: q
        for q in question_list
    }

    query = Response.objects.filter(answer__question__in=questions.values())
    query = query.filter(get_event_filter_query(
        event_type,
        event_funding,
        event_target_audience,
        event_additional_platforms,
        event_node,
        date_to,
        date_from,
        prefix="response_set__event__"
    ))

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
            "options": parse_options(question, summary, normalized)
        }
        for question in questions.values()
    ]


def parse_options(question, summary, normalized=False):
    all_answers = list(question.answers.all())
    answer_sum = (
        sum([summary.get(answer.id, 0) for answer in all_answers])
        if normalized
        else None
    )

    def _normalize(value):
        return (
            (value / answer_sum if answer_sum > 0 else 0)
            if normalized
            else value
        )

    return sorted([
        {
            "label": answer.text,
            "id": answer.slug,
            "count": _normalize(summary.get(answer.id, 0))
        }
        for answer in all_answers
    ], key=lambda v: -v["count"])


def get_question_query(questions):
    return (
        Q()
        if questions is None or len(questions) == 0
        else Q(slug__in=questions)
    )


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
    date_from_str = request.GET.get("date_from", None) or None
    date_from = parse_date(date_from_str) if date_from_str else None
    date_to_str = request.GET.get("date_to", None) or None
    date_to = parse_date(date_to_str) if date_to_str else None
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
        current_node,
    )


def _params_to_meta(**kwargs):
    serializer = {
        "date_from": lambda d: d.isoformat(),
        "date_to": lambda d: d.isoformat(),
        "event_node": lambda n: n.name,
    }
    return {
        key: serializer[key](value) if key in serializer else value
        for key, value in kwargs.items()
        if value
    }


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
