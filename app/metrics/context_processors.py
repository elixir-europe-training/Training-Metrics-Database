from django.urls import reverse
from django.conf import settings
import re


def apply_static_messages(request):
    static_messages = settings.STATIC_MESSAGES
    path = request.get_full_path()
    messages = [
        {
            "type": message.get("type", "info"),
            "title": message.get("title", "Message"),
            "content": message.get("content"),
        }
        for message in static_messages
        if "match" not in message or re.match(message["match"], path)
    ]
    return {
        "static_messages": messages
    }


def get_navigation(request):
    return {
        "nav_items": [
            {"title": "TMD - a new version of the Training Metrics Database", "icon": "", "url": reverse("world-map"), "type": "main"},
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
