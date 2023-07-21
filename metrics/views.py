from django.contrib.auth import authenticate
from django.shortcuts import render
from django.urls import reverse
from .forms import EventForm
from django.views.generic.edit import FormView


class EventFormView(FormView):
    template_name = "metrics/manage-events.html"
    form_class = EventForm
