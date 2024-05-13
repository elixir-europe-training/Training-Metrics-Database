from django.shortcuts import render
from .common import get_tabs


def upload_data(request):
    return render(
        request,
        'dash_app/upload.html',
        context={
            "title": "Upload data",
            **get_tabs(request),
        }
    )