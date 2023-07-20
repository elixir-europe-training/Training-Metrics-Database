from django.urls import path

from .views import (
    event_report,
    quality_report,
    demographic_report,
    impact_report
)

urlpatterns = [
    path('event', event_report, name='event-report'),
    path('quality', quality_report, name='quality-report'),
    path('demographic', demographic_report, name='demographic-report'),
    path('impact', impact_report, name='impact-report'),
]
