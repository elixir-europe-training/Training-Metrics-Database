from django.urls import path

from .views.allevents import all_events
from .views.worldmap import world_map
from .views.group_report import group_report


urlpatterns = [
    path('', all_events, name='all-events'),
    path('report/<str:group_id>', group_report, name='metrics-group-report'),
    path('world-map', world_map, name='world-map'),
]
