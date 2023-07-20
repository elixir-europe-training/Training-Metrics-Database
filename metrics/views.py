from django.shortcuts import render
from django.urls import reverse

# Create your views here.

def get_navgation(request):
    return {
        "nav_items": [
            {"title": "Dashboard", "icon": "speedometer2", "url": "", "type": "main"},
            *[
                {"title": title, "icon": icon, "url": url, "type": "side"}
                for title, icon, url in [
                    ("All events", "calendar3", ""),
                ]
            ],
            *[
                {"title": title, "icon": "clipboard-data", "url": url, "type": "reports"}
                for title, url in [
                    ("Events report", ""),
                    ("Quality metrics report", ""),
                    ("Demographics metrics report", ""),
                    ("Impact metrics report", "")
                ]
            ],
            *[
                {"title": title, "icon": icon, "url": url, "type": "about"}
                for title, icon, url in [
                    ("Help", "question-circle", "https://github.com/elixir-europe-training/ELIXIR-TrP-Training-Metrics-Database-Tango"),
                    ("About", "info-circle", "https://github.com/elixir-europe-training/ELIXIR-TrP-Training-Metrics-Database-Tango"),
                    ("Contribute", "github", "https://github.com/elixir-europe-training/ELIXIR-TrP-Training-Metrics-Database-Tango"),
                ]
            ],
            *[
                {"title": title, "icon": icon, "url": url, "type": "user"}
                for title, icon, url in (
                    [
                        (request.user.username, "person-circle", ""),
                    ] if request.user.is_authenticated
                    else [
                        ("Sign in", "box-arrow-in-right", ""),
                    ]
                )
            ],
            *(
                [
                    {"title": title, "icon": icon, "url": url, "type": "auth"}
                    for title, icon, url in [
                        ("Sign out", "box-arrow-right", ""),
                    ]
                ] if request.user.is_authenticated
                else []
            )
        ]
    }


def get_title(view):
    return {
        "title": f"Elixir Tango - {view}",
    }


def test(request):
    return render(request, 'metrics/index.html', context={
        "breadcrumbs": [
            {"title": title, "url": url, "state": state}
            for title, url, state in [
                ("Events", "#", ""),
                ("A specific event", "", "active")
            ]
        ],
        **get_title("Test"),
        **get_navgation(request)
    })


def manage_event():
    pass