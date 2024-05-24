from django.views.generic.edit import FormView, UpdateView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.shortcuts import get_object_or_404
from metrics import forms
from metrics import models
from django.core import serializers
from collections.abc import Iterable
from .common import get_tabs


class GenericUpdateView(UpdateView):
    template_name = "dash_app/model-form.html"
    model = models.Quality

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        for field in context["form"]:
            field.field.widget.attrs.update({
                "class": "form-control",
            })
        return context


class EventView(LoginRequiredMixin, UserPassesTestMixin, GenericUpdateView):
    model = models.Event
    fields = [
        "user",
        "code",
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

    def test_func(self):
        model_object = self.model.objects.get(pk=self.kwargs["pk"])
        return self.request.user.get_node() in list(model_object.node.all())


class GenericListView(ListView):
    template_name = "dash_app/model-list.html"
    paginate_by = 10
    max_paginate_by = 50
    min_paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        context["table_headings"] = [
            "",
            *self.fields
        ]
        context["table_items"] = [
            [
                ("View", entry.get_absolute_url()),
                *[
                    (
                        ", ".join([str(item) for item in value]) if type(value) in [list, tuple] else (
                            ", ".join([str(item) for item in value.all()])
                            if hasattr(value, "all")
                            else str(value)
                        ),
                        value.get_absolute_url() if hasattr(value, "get_absolute_url") else None
                    )
                    for value in [getattr(entry, fieldname) for fieldname in self.fields]
                ]
            ]
            for entry in context["object_list"]
        ]
        context["node_only"] = self.node_only
        context["page_size"] = self.get_paginate_by(None)
        context.update(get_tabs(self.request))
        return context

    @property
    def node_only(self):
        return "node_only" in self.request.GET
    
    def get_paginate_by(self, queryset):
        try:
            requested_paginate_by = int(self.request.GET.get("page_size", self.paginate_by))
            return max(
                min(self.max_paginate_by, requested_paginate_by),
                self.min_paginate_by
            )
        except ValueError:
            return self.paginate_by


class EventListView(LoginRequiredMixin, GenericListView):
    model = models.Event
    paginate_by = 30
    fields = [
        "title",
        "date_period",
        "node",
        "type",
        "organising_institution",
        "location",
        "number_participants",
        "number_trainers",
        "status",
    ]
    title = "Event list"

    def get_queryset(self):
        queryset = super().get_queryset()
        return (
            queryset.filter(node=self.request.user.get_node())
            if self.node_only
            else queryset
        )
    