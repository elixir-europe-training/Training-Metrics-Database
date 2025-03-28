from django.views.generic.edit import FormView, UpdateView, DeleteView, CreateView
from django.views.generic.list import ListView
from django.core.exceptions import FieldDoesNotExist
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import get_object_or_404
from django.utils.http import urlencode
from metrics import forms, models
from metrics.models import UserProfile, SystemSettings
from django.core import serializers
from collections.abc import Iterable
from .common import get_tabs
from django.urls import reverse_lazy, reverse
import requests
import re


class GenericUpdateView(UpdateView):
    template_name = "metrics/model-form.html"
    model = models.Quality
    view_name = None

    @property
    def title(self):
        name = self.model.__name__
        return f"{name}: {self.object}"

    def get_actions(self):
        return []
    
    def get_stats(self):
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        for field in context["form"]:
            field.field.widget.attrs.update({
                "class": "form-control",
            })
        context["actions"] = self.get_actions()
        context["stats"] = self.get_stats()
        view_name = self.get_view_name()
        context.update(get_tabs(self.request, view_name))
        context["can_edit"] = self.can_edit()
        return context

    def can_edit(self):
        return True

    def get_view_name(self):
        return self.view_name
    
    def get_form(self):
        form = super().get_form()
        if not self.can_edit():
            for field in form.fields.values():
                field.disabled = True
        return form


class UserHasNodeMixin(UserPassesTestMixin):
    def test_func(self):
        try:
            model_object = self.get_object()
            return UserProfile.get_node(self.request.user) == model_object.node_main
        except self.model.DoesNotExist:
            return True


class EventView(LoginRequiredMixin, GenericUpdateView):
    model = models.Event
    fields = [
        "user",
        "title",
        "node",
        "date_start",
        "date_end",
        "duration",
        "type",
        "organising_institution",
        "location_city",
        "location_country",
        "funding",
        "target_audience",
        "additional_platforms",
        "communities",
        "number_participants",
        "number_trainers",
        "url",
        "status",
    ]
    view_name = "event-list"

    @property
    def title(self):
        return f"Event: {self.object}"
    
    def get_actions(self):
        settings = SystemSettings.get_settings(self.request.user)
        upload_action = (reverse("upload-data-event", kwargs={"event_id": self.object.id}), "Upload metrics")
        if settings.has_flag("use_new_model_upload"):
            supersets = settings.get_upload_sets()
            return (
                [
                    upload_action,
                    *[
                        (
                            reverse(
                                "superset-delete-responses",
                                kwargs={"pk": self.object.id, "superset_slug": superset.slug}
                            ),
                            f"Delete {superset.name}"
                        )
                        for superset in supersets
                    ]
                ] if self.can_edit()
                else []
            )
        else:
            return (
                [
                    upload_action,
                    (reverse("quality-delete-metrics", kwargs={"pk": self.object.id}), "Delete quality metrics"),
                    (reverse("impact-delete-metrics", kwargs={"pk": self.object.id}), "Delete impact metrics"),
                    (reverse("demographic-delete-metrics", kwargs={"pk": self.object.id}), "Delete demographic metrics"),
                ] if self.can_edit()
                else []
            )
    
    def can_edit(self):
        model_object = self.get_object()
        return (
            UserProfile.get_node(self.request.user) == model_object.node_main
            and not self.object.is_locked
        )

    def get_stats(self):
        stat_fields = [
            "code",
            "node_main",
        ]
        field_stats = [
            (self.model._meta.get_field(field).verbose_name.title(), (getattr(self.object, field), None))
            for field in stat_fields
        ]
        metrics_counts = [
            (label, (value, None))
            for label, value in get_metrics_counts(self.object, self.request.user)
        ]
        return [
            *metrics_counts,
            *field_stats
        ]


class TessImportEventView(LoginRequiredMixin, CreateView):
    # Figure out how to avoid duplicating this from EventView
    model = models.Event
    fields = [
        "title",
        "node",
        "date_start",
        "date_end",
        "duration",
        "type",
        "organising_institution",
        "location_city",
        "location_country",
        "funding",
        "target_audience",
        "additional_platforms",
        "communities",
        "number_participants",
        "number_trainers",
        "url",
        "status",
    ]
    template_name = "metrics/tess-import-form.html"
    tess_id = None
    title = "Import from TeSS"
    tess_metadata = {}
    converted_metadata = {}
    tess_url = None

    def get_actions(self):
        return []

    def get_stats(self):
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        for field in context["form"]:
            field.field.widget.attrs.update({
                "class": "form-control",
            })
        context["actions"] = self.get_actions()
        context["stats"] = self.get_stats()
        context.update(get_tabs(self.request))
        context["can_edit"] = self.can_edit()
        context["tess_metadata"] = self.tess_metadata
        # Tidy up tess metadata to remove blank/irrelevant fields
        ignored = ('external-id', 'slug', 'last-scraped', 'scraper-record', 'cost-basis')
        for key in ignored:
            context["tess_metadata"].pop(key, None)
        for key in list(context["tess_metadata"]):
            value = context["tess_metadata"][key]
            if type(value) is not bool and type(value) != 0 and not value:  # Preserve False and 0
                del context["tess_metadata"][key]
        context["tess_url"] = self.tess_url
        return context

    def can_edit(self):
        return True

    def form_valid(self, form):
        obj = form.save(commit = False)
        obj.user = self.request.user
        obj.node_main = UserProfile.get_node(self.request.user)
        return super().form_valid(form)

    def get_initial(self):
        initial = super().initial.copy()
        for key in self.converted_metadata:
            initial[key] = self.converted_metadata.get(key, "")
        return initial

    def get(self, form_class=None):
        if self.tess_id:
            tess_metadata = self.import_from_tess(self.tess_id)
            if tess_metadata is None:
                return HttpResponseNotFound(f"Could not fetch event {self.tess_id} from TeSS")
            self.tess_metadata = tess_metadata["data"]["attributes"]
            self.converted_metadata = self.convert_tess_metadata(tess_metadata)
            self.tess_url = "https://tess.elixir-europe.org" + tess_metadata["data"]["links"]["self"]
        return super().get(form_class)

    def import_from_tess(self, tess_id):
        tess_url = f"https://tess.elixir-europe.org/events/{tess_id}.json_api"
        response = requests.get(tess_url, allow_redirects=True)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def convert_tess_metadata(self, tess_metadata):
        # Take just the date part from the full date/time string
        def convert_date(date):
            if date:
                return date[:10]

        converted = {
            "title": tess_metadata["data"]["attributes"]["title"],
            "url": tess_metadata["data"]["attributes"]["url"],
            "date_start": convert_date(tess_metadata["data"]["attributes"]["start"]),
            "date_end": convert_date(tess_metadata["data"]["attributes"]["end"]),
            "location_city": tess_metadata["data"]["attributes"]["city"],
            "location_country": tess_metadata["data"]["attributes"]["country"],
            "duration": tess_metadata["data"]["attributes"]["duration"]
        }

        return converted


class InstitutionView(LoginRequiredMixin, GenericUpdateView):
    model = models.OrganisingInstitution
    fields = []
    view_name = "institution-list"
    
    def get_stats(self):
        stat_fields = [
            "name",
            "country",
            "ror_id",
        ]
        field_stats = [
            (self.model._meta.get_field(field).verbose_name.title(), self.get_stat(field))
            for field in stat_fields
        ]
        return [
            *field_stats,
            self.get_event_stat()
        ]

    def get_stat(self, field):
        value = getattr(self.object, field)
        if field == "ror_id":
            return (value, value)
        else:
            return (value, None)

    def form_valid(self, form):
        result = super().form_valid(form)
        self.object.update_ror_data()
        self.object.save()
        
        return result

    def get_event_stat(self):
        base_url = reverse("event-list")
        query_params = {"institution_id": self.object.id}
        view_list_url = f"{base_url}?{urlencode(query_params, doseq=True)}"
        return (
            "Events",
            (models.Event.objects.filter(organising_institution=self.object).count(), view_list_url)
        )


class GenericListView(ListView):
    template_name = "metrics/model-list.html"
    paginate_by = 10
    max_paginate_by = 50
    min_paginate_by = 10

    @property
    def title(self):
        name = self.model.__name__
        return f"{name} list"

    def get_field_label(self, field):
        try:
            return self.model._meta.get_field(field).verbose_name.title()
        except FieldDoesNotExist:
            return field

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        extras_list = [
            self.get_entry_extras(entry)
            for entry in context["object_list"]
        ]
        max_extras = (
            max(len(e) for e in extras_list)
            if len(extras_list) > 0
            else 0
        )
        context["table_headings"] = self.get_headers(max_extras)
        context["table_items"] = [
            [
                *extras,
                *self.get_values(entry)
            ]
            for extras, entry in zip(extras_list, context["object_list"])
        ]
        context["node_only"] = self.node_only
        context["page_size"] = self.get_paginate_by(None)
        context.update(get_tabs(self.request))
        return context

    @property
    def node_only(self):
        return "node_only" in self.request.GET

    def get_entry_extras(self, entry):
        return []

    def get_paginate_by(self, queryset):
        try:
            requested_paginate_by = int(self.request.GET.get("page_size", self.paginate_by))
            return max(
                min(self.max_paginate_by, requested_paginate_by),
                self.min_paginate_by
            )
        except ValueError:
            return self.paginate_by

    def get_headers(self, max_extras):
        return [
            *["" for _i in range(max_extras)],
            *[
                self.get_field_label(field)
                for field in self.fields
            ]
        ]

    def get_values(self, entry):
        return [self.get_value(entry, fieldname) for fieldname in self.fields]
    
    def get_value(self, entry, fieldname):
        value = self.parse_value(getattr(entry, fieldname))
        return (
            value,
            value.get_absolute_url() if hasattr(value, "get_absolute_url") else None
        )

    def parse_value(self, value):
        if value is None:
            return None

        value_list = (
            list(value.all())
            if hasattr(value, "all")
            else (
                value
                if type(value) in [list, tuple]
                else [value]
            )
        )
        return ", ".join([str(v) for v in value_list])


class EventListView(LoginRequiredMixin, GenericListView):
    model = models.Event
    paginate_by = 30
    fields = [
        "code",
        "id",
        "title",
        "node",
        "node_main",
        "date_period",
        "type",
        "organising_institution",
    ]

    def get_field_label(self, field):
        try:
            return {
                "date_period": "Date Period",
            }[field]
        except KeyError:
            return super().get_field_label(field)

    def get_queryset(self):
        id_list = self.request.GET.getlist("id", None)
        institution_id_list = self.request.GET.getlist("institution_id", None)
        queryset = super().get_queryset().order_by("-id")
        queryset = (
            queryset.filter(node_main=UserProfile.get_node(self.request.user))
            if self.node_only
            else queryset
        )
        queryset = (
            queryset.filter(id__in=id_list)
            if id_list
            else queryset
        )
        queryset = (
            queryset.filter(organising_institution__in=institution_id_list)
            if institution_id_list
            else queryset
        )
        return queryset

    def get_headers(self, max_extras):
        headers = super().get_headers(max_extras)
        return [
            *headers,
            "Metrics Status"
        ]

    def get_values(self, entry):
        values = super().get_values(entry)
        return [
            *values,
            (get_metrics_status(entry, self.request.user), None)
        ]

    def get_entry_extras(self, entry):
        user_node = UserProfile.get_node(self.request.user)
        can_edit = user_node == entry.node_main and not entry.is_locked
        return [
            ("Edit" if can_edit else "View", entry.get_absolute_url()),
            (
                "Upload metrics",
                reverse("upload-data-event", kwargs={"event_id": entry.id})
            ) if can_edit else ("", None),
        ]


class InstitutionListView(LoginRequiredMixin, GenericListView):
    model = models.OrganisingInstitution
    paginate_by = 30
    ordering = ['name']
    fields = [
        "name",
        "country",
        "ror_id",
    ]

    def get_entry_extras(self, entry):
        return [
            ("View", entry.get_absolute_url()),
        ]

    def get_value(self, entry, fieldname):
        (value, url) = super().get_value(entry, fieldname)
        if fieldname == "ror_id" and value:
            return (value, value)
        else:
            return (value, url)


class GenericEventMetricsDeleteView(
    LoginRequiredMixin,
    UserHasNodeMixin,
    DeleteView,
):
    template_name = "metrics/confirm.html"
    model = models.Event

    def test_func(self):
        result = super().test_func()
        model_object = self.get_object()
        return result and not model_object.is_locked

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        name = self.get_name()
        context["title"] = f"Delete {name} metrics for: {self.object}"
        context["abort_url"] = self.get_success_url()
        context["message"] = f"Do you want to delete {name} metrics for the event '{self.object}'?"
        return context

    def get_name(self):
        return self.metrics_model.__name__

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        success_url = self.get_success_url()
        self.metrics_model.objects.filter(event=self.object).delete()
        return HttpResponseRedirect(success_url)


class SuperSetMetricsDeleteView(
    GenericEventMetricsDeleteView
):
    metrics_model = models.ResponseSet

    def get_superset(self):
        superset_slug = self.kwargs["superset_slug"]
        return get_object_or_404(models.QuestionSuperSet, slug=superset_slug)

    def get_name(self):
        superset = self.get_superset()
        return superset.name

    def form_valid(self, form):
        success_url = self.get_success_url()
        superset = self.get_superset()
        question_sets = list(superset.question_sets.all())
        self.metrics_model.objects.filter(
            event=self.object,
            question_set__in=question_sets
        ).delete()
        return HttpResponseRedirect(success_url)


class QualityMetricsDeleteView(
    GenericEventMetricsDeleteView
):
    metrics_model = models.Quality


class ImpactMetricsDeleteView(
    GenericEventMetricsDeleteView
):
    metrics_model = models.Impact


class DemographicMetricsDeleteView(
    GenericEventMetricsDeleteView
):
    metrics_model = models.Demographic


def get_metrics_counts(event, user):
    settings = SystemSettings.get_settings(user)
    return (
        [
            (
                superset.name,
                max((
                    models.ResponseSet.objects.filter(
                        event=event,
                        question_set=question_set
                    ).count()
                    for question_set in superset.question_sets.all()
                ))
            )
            for superset in settings.get_upload_sets()
        ]
        if settings.has_flag("use_new_model_upload")
        else [
            (name, related.count())
            for name, related in [
                ("Quality metrics", event.quality),
                ("Impact metrics", event.impact),
                ("Demographic metrics", event.demographic)
            ]
        ]
    )


def get_metrics_status(event, user):
    counts = get_metrics_counts(event, user)
    count = sum([1 if v > 0 else 0 for _n, v in counts])
    if count == 0:
        return "None"
    elif count < len(counts):
        return "Partial"
    else:
        return "Full"
