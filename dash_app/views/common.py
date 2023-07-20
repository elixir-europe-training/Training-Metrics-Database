from django.urls import reverse

def get_tabs(request):
    view_name = request.resolver_match.view_name
    return {
        "tabs": [
            {"title": title, "url": reverse(name), "active": view_name == name}
            for title, name in [
                ("Events", "event-report"),
                ("Quality metrics", "quality-report"),
                ("Demographics metrics", "demographic-report"),
                ("Impact metrics", "impact-report")
            ]
        ]
    }