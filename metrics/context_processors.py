from django.urls import reverse


def get_navigation(request):
    return {
        "nav_items": [
            {"title": "TMD - a new version of the Training Metrics Database", "icon": "", "url": reverse('all-events'), "type": "main"},
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
        ]
    }
