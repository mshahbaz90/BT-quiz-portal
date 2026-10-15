from django.urls import path
from assessments import views

app_name = 'assessments'

urlpatterns = [
    # Candidate catalog
    path('catalog/', views.employee_assessment_list_view, name='employee_list'),

    # Assessment Management (Trainers & Admins)
    path('', views.assessment_list_view, name='assessment_list'),
    path('create/', views.assessment_create_view, name='assessment_create'),
    path('<int:assessment_id>/', views.assessment_detail_view, name='assessment_detail'),
    path('<int:assessment_id>/edit/', views.assessment_edit_view, name='assessment_edit'),
    path('<int:assessment_id>/preview/', views.assessment_preview_view, name='assessment_preview'),
    path('<int:assessment_id>/toggle-publish/', views.assessment_toggle_publish_view, name='assessment_toggle_publish'),
    path('<int:assessment_id>/add-question/<int:question_id>/', views.assessment_add_question_view, name='assessment_add_question'),
    path('<int:assessment_id>/remove-question/<int:question_id>/', views.assessment_remove_question_view, name='assessment_remove_question'),

    # Categories Management
    path('categories/', views.category_list_view, name='category_list'),
    path('categories/<int:category_id>/delete/', views.category_delete_view, name='category_delete'),

    # Assessment Lifecycle Actions
    path('<int:assessment_id>/duplicate/', views.assessment_duplicate_view, name='assessment_duplicate'),
    path('<int:assessment_id>/archive/', views.assessment_archive_view, name='assessment_archive'),

    # Central Question Bank
    path('questions/', views.question_bank_list_view, name='question_bank'),
    path('questions/create/', views.question_create_view, name='question_create'),
    path('questions/<int:question_id>/duplicate/', views.question_duplicate_view, name='question_duplicate'),
    path('questions/export/csv/', views.question_export_csv_view, name='question_export_csv'),
    path('questions/import/csv/', views.question_import_csv_view, name='question_import_csv'),
]
