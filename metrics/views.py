from django.contrib.auth import authenticate
from django.shortcuts import render
from django.urls import reverse

from metrics.forms import UserLoginForm


# Create your views here.
def get_title(view):
    return {
        "title": f"Elixir Tango - {view}",
    }


def test(request):
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


def login(request):
    form = UserLoginForm()
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            # check if credentials correct
            authenticated_user = authenticate(username=form.cleaned_data['username'],
                                              password=form.cleaned_data['password'])
            if authenticated_user is None:
                messages = [
                        {'title': 'Login failed', 'content': 'Invalid credentials', 'type': 'danger'}
                    ]
                return render(request, 'metrics/login.html', context={
                    'example_form': form,
                    'messages': messages
                })
    return render(request, 'metrics/login.html', context={'example_form': form})
