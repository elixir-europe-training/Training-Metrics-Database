from django.shortcuts import render

from metrics.management.commands.load_data import get_data_sources
from metrics.models import Node
from .common import get_tabs
from django import forms
from django.forms.widgets import FileInput, Select, CheckboxInput
import re
import csv
import io
from metrics import import_utils, models
import traceback
from django.core.exceptions import ValidationError
from django.db import transaction
import datetime
from django.contrib.auth.decorators import login_required
import requests

from .model_views import EventView, TessImportEventView

DATA_SOURCES = get_data_sources()
NODE_COUNTRIES = {}
with open(DATA_SOURCES[Node]) as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        NODE_COUNTRIES[row['name']] = row['country']

@login_required
def tess_import(request, tess_id=None):
    if tess_id is not None:
        return TessImportEventView.as_view(tess_id = tess_id)(request)
    else:
        return render(
            request,
            'metrics/tess-import.html',
            context={
                "title": "Import from TeSS",
                **get_tabs(request),
                "node": NODE_COUNTRIES.get(request.user.get_node().name)
            }
        )
