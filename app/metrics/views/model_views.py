from django.views.generic.edit import FormView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.core.exceptions import FieldDoesNotExist
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.http import urlencode
from metrics import forms
from metrics import models
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
            return self.request.user.get_node() == model_object.node_main
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
        return (
            [
                (reverse("upload-data-event", kwargs={"event_id": self.object.id}), "Upload metrics"),
                (reverse("quality-delete-metrics", kwargs={"pk": self.object.id}), "Delete quality metrics"),
                (reverse("impact-delete-metrics", kwargs={"pk": self.object.id}), "Delete impact metrics"),
                (reverse("demographic-delete-metrics", kwargs={"pk": self.object.id}), "Delete demographic metrics"),
            ] if self.can_edit()
            else []
        )
    
    def can_edit(self):
        model_object = self.get_object()
        return (
            self.request.user.get_node() == model_object.node_main
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
        return [
            *[
                (stat, (value, None))
                for (stat, value) in self.object.stats
            ],
            *field_stats
        ]


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
        context["table_headings"] = [
            *["" for _i in range(max_extras)],
            *[
                self.get_field_label(field)
                for field in self.fields
            ]
        ]
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
        "metrics_status",
    ]

    def get_field_label(self, field):
        try:
            return {
                "date_period": "Date Period",
                "metrics_status": "Metrics Status",
            }[field]
        except KeyError:
            return super().get_field_label(field)

    def get_queryset(self):
        id_list = self.request.GET.getlist("id", None)
        institution_id_list = self.request.GET.getlist("institution_id", None)
        queryset = super().get_queryset().order_by("-id")
        queryset = (
            queryset.filter(node_main=self.request.user.get_node())
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

    def get_entry_extras(self, entry):
        user_node = self.request.user.get_node()
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
        name = self.metrics_model.__name__
        context["title"] = f"Delete {name} metrics for: {self.object}"
        context["abort_url"] = self.get_success_url()
        context["message"] = f"Do you want to delete {name} metrics for the event '{self.object}'?"
        return context

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        success_url = self.get_success_url()
        self.metrics_model.objects.filter(event=self.object).delete()
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
