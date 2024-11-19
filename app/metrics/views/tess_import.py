from django.shortcuts import render

from metrics.models import Node
from .common import get_tabs
from django import forms
from django.forms.widgets import FileInput, Select, CheckboxInput
import re
import csv
import io
from metrics import import_utils, models
import traceback
from django.core.exceptions import PermissionDenied
from django.db import transaction
import datetime
from django.contrib.auth.decorators import login_required
import requests

from .model_views import EventView, TessImportEventView


@login_required
def tess_import(request, tess_id=None):
    node = request.user.get_node()

    if not node:
        raise PermissionDenied(f"You have to be associated with a node to upload data.")

    if tess_id is not None:
        return TessImportEventView.as_view(tess_id = tess_id)(request)
    else:
        return render(
            request,
            'metrics/tess-import.html',
            context={
                "title": "Import from TeSS",
                **get_tabs(request),
                "node": node.country
            }
        )
