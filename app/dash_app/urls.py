from django.urls import path

from .views.allevents import all_events
from .views.group_report import group_report
from django.shortcuts import redirect


urlpatterns = [
    path('', lambda request: redirect('world-map', permanent=True)),
    path('all-events', all_events, name='all-events'),
    path('report/<str:group_id>', group_report, name='metrics-group-report'),
]
