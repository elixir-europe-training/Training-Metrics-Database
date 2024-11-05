from django.views.generic.edit import FormView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
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
        context.update(get_tabs(self.request))
        context["can_edit"] = self.can_edit()
        return context

    def can_edit(self):
        return True
    
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
        "node_main",
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

    @property
    def title(self):
        return f"Event: {self.object}"
    
    def get_actions(self):
        return (
            [
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
        ]
        field_stats = [
            (field, getattr(self.object, field))
            for field in stat_fields
        ]
        return [
            *self.object.stats,
            *field_stats
        ]


class InstitutionView(LoginRequiredMixin, GenericUpdateView):
    model = models.OrganisingInstitution
    fields = []
    
    def get_stats(self):
        stat_fields = [
            "name",
            "country",
            "ror_id",
        ]
        field_stats = [
            (field, getattr(self.object, field))
            for field in stat_fields
        ]
        return [
            *field_stats,
            ("Events", models.Event.objects.filter(organising_institution=self.object).count()),
        ]

    def form_valid(self, form):
        result = super().form_valid(form)
        self.object.update_ror_data()
        self.object.save()
        
        return result


class GenericListView(ListView):
    template_name = "metrics/model-list.html"
    paginate_by = 10
    max_paginate_by = 50
    min_paginate_by = 10

    @property
    def title(self):
        name = self.model.__name__
        return f"{name} list"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        extras_list = [
            self.get_entry_extras(entry)
            for entry in context["object_list"]
        ]
        max_extras = max(len(e) for e in extras_list)
        context["table_headings"] = [
            *["" for _i in range(max_extras)],
            *self.fields
        ]
        context["table_items"] = [
            [
                *extras,
                *[
                    (
                        self.parse_value(value),
                        value.get_absolute_url() if hasattr(value, "get_absolute_url") else None
                    )
                    for value in self.get_values(entry)
                ]
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
        return [getattr(entry, fieldname) for fieldname in self.fields]

    def parse_value(self, value):
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

    def get_queryset(self):
        queryset = super().get_queryset().order_by("-id")
        return (
            queryset.filter(node_main=self.request.user.get_node())
            if self.node_only
            else queryset
        )

    def get_entry_extras(self, entry):
        user_node = self.request.user.get_node()
        can_edit = user_node == entry.node_main and not entry.is_locked
        return [
            ("Edit" if can_edit else "View", entry.get_absolute_url()),
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


class GenericEventMetricsDeleteView(
    LoginRequiredMixin,
    UserHasNodeMixin,
    DeleteView,
):
    template_name = "dash_app/confirm.html"
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