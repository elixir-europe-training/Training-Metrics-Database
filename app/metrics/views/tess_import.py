from django.shortcuts import render

from metrics.models import UserProfile
from .common import get_tabs
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from .model_views import TessImportEventView


@login_required
def tess_import(request, tess_id=None):
    node = UserProfile.get_node(request.user)

    if not node:
        raise PermissionDenied("You have to be associated with a node to upload data.")

    if tess_id is not None:
        return TessImportEventView.as_view(tess_id=tess_id)(request)
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
