from django.contrib.auth import authenticate
from django.shortcuts import render
from django.urls import reverse

from metrics.forms import UserLoginForm


# Create your views here.
def get_title(view):
    return {
        "title": f"Elixir Tango - {view}",
    }


def dashboard(request):
    return render(request, 'metrics/index.html', context={
        "breadcrumbs": [
            {"title": title, "url": url, "state": state}
            for title, url, state in [
                ("Events", reverse('events'), ""),
                ("A specific event", "", "active")
            ]
        ],
        **get_title("Test")
    })


def manage_event():
    pass


def events(request):
    return render(request, 'metrics/events.html')

