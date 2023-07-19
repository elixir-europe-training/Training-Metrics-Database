from django.shortcuts import render

# Create your views here.
def test(request):
    return render(request, 'metrics/index.html', context={
        "nav_items": [
            {"title": "Dashboard", "icon": "speedometer2", "url": "", "type": "main"},
            *[
                {"title": title, "icon": icon, "url": url, "type": "side"}
                for title, icon, url in [
                    ("About", "info-circle", ""),
                    ("All events", "calendar3", ""),
                    ("Reports", "graph-up", ""),
                    ("Help", "question-circle", "")
                ]
            ],
        ]
    })