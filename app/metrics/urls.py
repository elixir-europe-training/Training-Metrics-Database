from django.contrib.auth.views import LoginView, LogoutView, FormView
from django.urls import path
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect

from metrics import views
from metrics.forms import UserLoginForm
from metrics.views.tess_import import tess_import
from metrics.views.upload import upload_data, download_template
from metrics.views import metrics
from metrics.views.model_views import (
    EventView,
    InstitutionView,
    EventListView,
    InstitutionListView,
    QualityMetricsDeleteView,
    DemographicMetricsDeleteView,
    ImpactMetricsDeleteView,
    SuperSetMetricsDeleteView,
)

urlpatterns = [
    path('', lambda request: redirect('world-map', permanent=True)),
    path('login/', LoginView.as_view(
        template_name='metrics/login.html',
        authentication_form=UserLoginForm, next_page='/'),
        name='login'
    ),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('upload-data', upload_data, name='upload-data'),
    path('tess-import', tess_import, name='tess-import'),
    path('tess-import/<int:tess_id>', tess_import, name='tess-import'),
    path('download-template/<str:data_type>/<str:slug>', download_template, name='download_template'),
    path('event/<int:pk>', EventView.as_view(), name='event-edit'),
    path('event/<int:event_id>/upload-data', upload_data, name='upload-data-event'),
    path('institution/<int:pk>', InstitutionView.as_view(), name='institution-edit'),
    path('event/list', EventListView.as_view(), name='event-list'),
    path('institution/list', InstitutionListView.as_view(), name='institution-list'),
    path('event/delete-metrics/demographic/<int:pk>',
        DemographicMetricsDeleteView.as_view(),
        name="demographic-delete-metrics"
    ),
    path('event/delete-metrics/impact/<int:pk>',
        ImpactMetricsDeleteView.as_view(),
        name="impact-delete-metrics"
    ),
    path('event/delete-metrics/quality/<int:pk>',
        QualityMetricsDeleteView.as_view(),
        name="quality-delete-metrics"
    ),
    path('event/delete-metrics/superset/<int:pk>/<str:superset_slug>',
        SuperSetMetricsDeleteView.as_view(),
        name="superset-delete-responses"
    ),

    path('metrics/world-map', metrics.world_map_api, name="world-map-api"),
    path('metrics/event', metrics.event_api, name="event-api"),
    path('metrics/set/<str:question_set_id>', metrics.metrics_api, name="metrics-api"),
    path('properties/set/<str:question_set_id>', metrics.question_api, name="properties-set-api"),
    path('properties/event', metrics.event_properties_api, name="properties-event-api"),
    
    path('world-map', metrics.world_map_event_count, name='world-map'),

    path('report/event', metrics.EventMetricsView.as_view(), name='metrics-event-report'),
    path('report/set/<str:question_set_id>', metrics.get_metrics_view().as_view(), name='metrics-set-report'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset_done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
