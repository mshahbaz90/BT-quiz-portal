from django.urls import path
from accounts import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('change-password/', views.force_change_password_view, name='change_password'),
    path('profile/', views.profile_view, name='profile'),
    
    # Employee Management
    path('employees/', views.employee_list_view, name='employee_list'),
    path('employees/create/', views.employee_create_view, name='employee_create'),
    path('employees/<int:user_id>/toggle-status/', views.employee_toggle_status_view, name='employee_toggle_status'),
    path('employees/import/', views.bulk_import_employees_view, name='bulk_import'),
    path('employees/export/', views.export_employees_csv_view, name='export_employees'),
    
    # Departments & Teams / Groups
    path('departments/', views.department_list_view, name='department_list'),
    path('teams/', views.team_list_view, name='team_list'),
    path('teams/<int:team_id>/', views.team_detail_view, name='team_detail'),
]
