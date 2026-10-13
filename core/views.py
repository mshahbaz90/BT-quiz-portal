import time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.db import connection
from django.utils import timezone
from django.core.paginator import Paginator

from accounts.models import User, Department
from assessments.models import Assessment
from exam.models import AssessmentAttempt
from certificates.models import Certificate
from core.models import AuditLog, Notification


@login_required
def dashboard_view(request):
    user = request.user
    now = timezone.now()

    if user.is_super_admin:
        # Super Admin Enterprise Dashboard
        total_employees = User.objects.filter(is_active=True).count()
        total_assessments = Assessment.objects.count()
        total_attempts = AssessmentAttempt.objects.count()
        graded_attempts = AssessmentAttempt.objects.filter(status=AssessmentAttempt.Status.GRADED)
        
        passed_count = graded_attempts.filter(is_passed=True).count()
        graded_count = graded_attempts.count()
        pass_rate = round((passed_count / graded_count * 100), 1) if graded_count > 0 else 0

        recent_attempts = AssessmentAttempt.objects.select_related('user', 'assessment').order_by('-started_at')[:8]
        recent_audits = AuditLog.objects.select_related('user').order_by('-timestamp')[:6]

        context = {
            'role_mode': 'ADMIN',
            'total_employees': total_employees,
            'total_assessments': total_assessments,
            'total_attempts': total_attempts,
            'pass_rate': pass_rate,
            'recent_attempts': recent_attempts,
            'recent_audits': recent_audits,
        }
        return render(request, 'core/admin_dashboard.html', context)

    elif user.is_trainer or user.is_team_lead:
        # Trainer & Team Lead Dashboard
        created_assessments = Assessment.objects.filter(created_by=user) if user.is_trainer else Assessment.objects.all()
        recent_submissions = AssessmentAttempt.objects.select_related('user', 'assessment').order_by('-started_at')[:10]
        pending_grading_count = AssessmentAttempt.objects.filter(status=AssessmentAttempt.Status.SUBMITTED).count()

        context = {
            'role_mode': 'TRAINER',
            'created_assessments': created_assessments[:5],
            'recent_submissions': recent_submissions,
            'pending_grading_count': pending_grading_count,
        }
        return render(request, 'core/trainer_dashboard.html', context)

    else:
        # Employee Dashboard
        # Fetch assessments available to employee
        assigned_assessments = Assessment.objects.filter(
            status=Assessment.Status.PUBLISHED
        ).prefetch_related('attempts').distinct()

        user_attempts = AssessmentAttempt.objects.filter(user=user).select_related('assessment')
        user_certificates = Certificate.objects.filter(user=user, is_revoked=False).select_related('assessment')

        # Categorize assessments into Pending, Completed
        completed_assessment_ids = user_attempts.filter(
            status__in=[AssessmentAttempt.Status.GRADED, AssessmentAttempt.Status.SUBMITTED]
        ).values_list('assessment_id', flat=True)

        pending_assessments = assigned_assessments.exclude(id__in=completed_assessment_ids)
        in_progress_attempt = user_attempts.filter(
            status=AssessmentAttempt.Status.IN_PROGRESS,
            deadline_at__gt=now
        ).first()

        context = {
            'role_mode': 'EMPLOYEE',
            'pending_assessments': pending_assessments,
            'user_attempts': user_attempts.order_by('-started_at')[:5],
            'user_certificates': user_certificates[:5],
            'in_progress_attempt': in_progress_attempt,
        }
        return render(request, 'core/employee_dashboard.html', context)


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(recipient=request.user)
    if request.method == 'POST':
        notifications.update(is_read=True)
        return redirect('core:notifications')

    return render(request, 'core/notifications.html', {'notifications': notifications})


@login_required
def audit_logs_view(request):
    if not request.user.is_super_admin:
        return HttpResponseForbidden("Access restricted to Super Administrators.")

    logs = AuditLog.objects.select_related('user').all()
    paginator = Paginator(logs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'core/audit_logs.html', {'page_obj': page_obj})


def health_check_view(request):
    start_time = time.time()
    db_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
    except Exception as e:
        db_ok = False

    latency_ms = round((time.time() - start_time) * 1000, 2)
    return JsonResponse({
        'status': 'healthy' if db_ok else 'unhealthy',
        'database': 'connected' if db_ok else 'error',
        'latency_ms': latency_ms,
        'timestamp': timezone.now().isoformat(),
        'portal': 'BreakThru Assessments'
    })
