from django.urls import path

from metrics import views

urlpatterns = [
    path('', views.test),
    path('events/', views.events, name='events')
]