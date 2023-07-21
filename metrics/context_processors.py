from django.urls import reverse


def get_navigation(request):
    return {
        "nav_items": [
            {"title": "Tango - the new version of the Training Metrics Database", "icon": "", "url": reverse('dashboard'), "type": "main"},
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
                {"title": title, "icon": icon, "url": url, "type": "user"}
                for title, icon, url in (
                    [
                        (request.user.username, "person-circle", ""),
                        ('Sign out', "box-arrow-left", reverse('logout')),
                    ] if request.user.is_authenticated
                    else [
                        ("Sign in", "box-arrow-in-right", f"{reverse('login')}?next={request.path}"),
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
