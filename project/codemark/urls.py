from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path("password_reset", auth_views.PasswordResetView.as_view(template_name='password_reset/request.html', subject_template_name='password_reset/subject.txt', html_email_template_name='password_reset/email.html'), name="password_reset"),
    path("password_reset/done/", auth_views.PasswordResetDoneView.as_view(template_name='password_reset/done.html'), name="password_reset_done"),
    path("password_reset_confirm/<uidb64>/<token>", auth_views.PasswordResetConfirmView.as_view(template_name='password_reset/confirm.html'), name="password_reset_confirm"),
    path("password_reset_complete", auth_views.PasswordResetCompleteView.as_view(template_name='password_reset/complete.html'), name="password_reset_complete"),
    path('', views.index_view, name='index'),
]