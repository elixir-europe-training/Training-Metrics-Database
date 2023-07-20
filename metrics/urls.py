from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from metrics import views
from metrics.forms import UserLoginForm

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('events/', views.events, name='events'),
    path('login/', LoginView.as_view(template_name='metrics/login.html',
                                     authentication_form=UserLoginForm, next_page='/'), name='login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout')
]
