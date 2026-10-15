from django.urls import path
from exam import views

app_name = 'exam'

urlpatterns = [
    path('link/<str:link_code>/', views.public_link_entry_view, name='link_entry'),
    path('start/<int:assessment_id>/', views.start_instruction_view, name='start_instruction'),
    path('take/<int:attempt_id>/', views.take_assessment_view, name='take_assessment'),
    path('submit/<int:attempt_id>/', views.submit_assessment_view, name='submit_assessment'),
    path('result/<int:attempt_id>/', views.attempt_result_view, name='attempt_result'),

    # APIs for live exam session
    path('api/<int:attempt_id>/autosave/', views.autosave_response_api, name='api_autosave'),
    path('api/<int:attempt_id>/flag/', views.toggle_flag_api, name='api_flag'),
    path('api/<int:attempt_id>/switch/', views.log_switch_api, name='api_switch'),
]
