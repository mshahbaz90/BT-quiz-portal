from django.urls import path
from grading import views

app_name = 'grading'

urlpatterns = [
    path('queue/', views.grading_queue_view, name='queue'),
    path('evaluate/<int:attempt_id>/', views.evaluate_attempt_view, name='evaluate_attempt'),
    path('adjust/<int:attempt_id>/', views.adjust_score_view, name='adjust_score'),
]
