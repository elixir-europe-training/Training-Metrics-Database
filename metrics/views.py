from django.shortcuts import render


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
        **request.navigation
    })


def manage_event():
    pass


def events(request):
    return render(request, 'metrics/events.html')
