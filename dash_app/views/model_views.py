from django.views.generic.edit import FormView, UpdateView
from django.views.generic.list import ListView
from django.shortcuts import get_object_or_404
from metrics import forms
from metrics import models
from django.core import serializers
from collections.abc import Iterable


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


class QualityView(GenericUpdateView):
    model = models.Quality
    fields = [
        "user",
        "event",
        "used_resources_before",
        "used_resources_future",
        "recommend_course",
        "course_rating",
        "balance",
        "email_contact",
    ]

    @property
    def title(self):
        return f"Quality: {self.object.event}"


class EventView(GenericUpdateView):
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


class GenericListView(ListView):
    template_name = "dash_app/model-list.html"

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
        return context


class QualityListView(GenericListView):
    model = models.Quality
    paginate_by = 100
    fields = [
        "user",
        "event",
        "used_resources_before",
        "used_resources_future",
        "recommend_course",
        "course_rating",
        "balance",
        "email_contact",
    ]
    title = "Quality list"


class EventListView(GenericListView):
    model = models.Event
    paginate_by = 100
    fields = [
        "title",
        "date_period",
        "duration",
        "type",
        "organising_institution",
        "location",
        "funding",
        "target_audience",
        "additional_platforms",
        "communities",
        "number_participants",
        "number_trainers",
        "url",
        "status",
    ]
    title = "Event list"