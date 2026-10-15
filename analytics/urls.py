from django.urls import path
from analytics import views

app_name = 'analytics'

urlpatterns = [
    path('', views.reports_overview_view, name='reports_overview'),
    path('results/', views.results_list_view, name='results_list'),
    path('export/csv/', views.export_attempts_csv_view, name='export_csv'),
    path('export/excel/', views.export_attempts_excel_view, name='export_excel'),
]
