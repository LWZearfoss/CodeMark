from django.urls import path
from django.contrib.auth.views import LoginView

from . import views

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.index_view, name='index'),
]