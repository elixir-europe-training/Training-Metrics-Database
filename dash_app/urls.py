from django.urls import path

from .views.allevents import all_events
from .views.event import event_report
from .views.demographic import demographic_report
from .views.impact import impact_report
from .views.quality import quality_report
from .views.worldmap import world_map
from .views.upload import upload_data
from .views.model_views import EventView, EventListView, EventMetricsDeleteView


urlpatterns = [
    path('', all_events, name='all-events'),
    path('event', event_report, name='event-report'),
    path('quality', quality_report, name='quality-report'),
    path('demographic', demographic_report, name='demographic-report'),
    path('impact', impact_report, name='impact-report'),
    path('world-map', world_map, name='world-map'),
    path('upload-data', upload_data, name='upload-data'),
    path('event/<int:pk>', EventView.as_view(), name='event-edit'),
    path('event/list', EventListView.as_view(), name='event-list'),
    path('event/delete-metrics/<int:pk>', EventMetricsDeleteView.as_view(), name="event-delete-metrics")
]
