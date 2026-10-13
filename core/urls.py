from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('audit-logs/', views.audit_logs_view, name='audit_logs'),
    path('health/', views.health_check_view, name='health_check'),
]
