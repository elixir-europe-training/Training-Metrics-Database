from django.urls import path
from .views import event_report

urlpatterns = [
    path('', event_report, name='event-report'),
]
