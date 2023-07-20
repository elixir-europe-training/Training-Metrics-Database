from django.urls import path

from .views.allevents import all_events
from .views.event import event_report
from .views.demographic import demographic_report
from .views.impact import impact_report
from .views.quality import quality_report


urlpatterns = [
    path('allevents', all_events, name='all-events'),
    path('event', event_report, name='event-report'),
    path('quality', quality_report, name='quality-report'),
    path('demographic', demographic_report, name='demographic-report'),
    path('impact', impact_report, name='impact-report'),
]
