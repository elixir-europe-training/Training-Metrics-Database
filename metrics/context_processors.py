from django.urls import reverse


def get_navigation(request):
    return {
        "nav_items": [
            {"title": "Dashboard", "icon": "speedometer2", "url": "", "type": "main"},
            *[
                {"title": title, "icon": icon, "url": url, "type": "side"}
                for title, icon, url in [
                    ("All events", "calendar3", reverse('all-events')),
                ]
            ],
            *[
                {"title": title, "icon": "clipboard-data", "url": reverse(name), "type": "reports"}
                for title, name in [
                    ("Events report", "event-report"),
                    ("Quality metrics report", "quality-report"),
                    ("Demographics metrics report", "demographic-report"),
                    ("Impact metrics report", "impact-report")
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
                        ("Sign in", "box-arrow-in-right", f"{reverse('admin:login')}?next={request.path}"),
                    ]
                )
            ],
            *(
                [
                    {"title": title, "icon": icon, "url": url, "type": "auth"}
                    for title, icon, url in [
                        ("Sign out", "box-arrow-right", f"{reverse('admin:logout')}?next={request.path}"),
                    ]
                ] if request.user.is_authenticated
                else []
            )
        ]
    }
