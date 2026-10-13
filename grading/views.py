from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.db import transaction

from exam.models import AssessmentAttempt, AttemptResponse
from grading.models import ManualGradingQueue, GradeAdjustmentAudit
from core.models import AuditLog, Notification
from certificates.models import Certificate


@login_required
def grading_queue_view(request):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Trainers and Administrators.")

    pending_items = ManualGradingQueue.objects.filter(
        status=ManualGradingQueue.Status.PENDING
    ).select_related('attempt__user', 'attempt__assessment', 'snapshot')

    return render(request, 'grading/queue.html', {'pending_items': pending_items})


@login_required
def evaluate_attempt_view(request, attempt_id):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Trainers and Administrators.")

    attempt = get_object_or_404(
        AssessmentAttempt.objects.select_related('user', 'assessment').prefetch_related('snapshots__response'),
        id=attempt_id
    )

    queue_items = ManualGradingQueue.objects.filter(attempt=attempt).select_related('snapshot', 'response')

    if request.method == 'POST':
        with transaction.atomic():
            for item in queue_items:
                marks_str = request.POST.get(f'marks_{item.id}', '').strip()
                feedback = request.POST.get(f'feedback_{item.id}', '').strip()

                if marks_str != '':
                    marks = min(Decimal(marks_str), item.snapshot.marks_allocated)
                    item.marks_awarded = max(Decimal('0.00'), marks)
                    item.grader_feedback = feedback
                    item.grader = request.user
                    item.status = ManualGradingQueue.Status.COMPLETED
                    item.evaluated_at = timezone.now()
                    item.save()

                    # Update response marks
                    resp = item.response
                    resp.marks_awarded = item.marks_awarded
                    resp.is_evaluated = True
                    resp.save(update_fields=['marks_awarded', 'is_evaluated'])

            # Recalculate full score
            total_earned = sum(r.marks_awarded for r in attempt.responses.all())
            attempt.earned_marks = total_earned
            if attempt.max_possible_marks > 0:
                attempt.percentage = round((total_earned / attempt.max_possible_marks) * 100, 2)
                attempt.is_passed = (attempt.percentage >= attempt.assessment.pass_mark_percentage)

            attempt.status = AssessmentAttempt.Status.GRADED
            attempt.save(update_fields=['earned_marks', 'percentage', 'is_passed', 'status'])

            # If passed, issue certificate
            if attempt.is_passed:
                Certificate.objects.get_or_create(
                    attempt=attempt,
                    defaults={
                        'user': attempt.user,
                        'assessment': attempt.assessment,
                        'score_percentage': attempt.percentage,
                    }
                )

            # Send Notification to candidate
            Notification.objects.create(
                recipient=attempt.user,
                title="Assessment Evaluation Completed",
                message=f"Your responses for {attempt.assessment.title} have been evaluated. Final score: {attempt.percentage}%.",
                notification_type=Notification.NotificationType.SUCCESS if attempt.is_passed else Notification.NotificationType.INFO,
                link=f"/exam/result/{attempt.id}/"
            )

            AuditLog.objects.create(
                user=request.user,
                action='MANUAL_EVALUATION_COMPLETED',
                target_model='AssessmentAttempt',
                target_id=str(attempt.id),
                details={'percentage': str(attempt.percentage), 'is_passed': attempt.is_passed}
            )

        messages.success(request, f"Evaluation saved! Candidate result finalized ({attempt.percentage}% - {'PASSED' if attempt.is_passed else 'FAILED'}).")
        return redirect('grading:queue')

    return render(request, 'grading/evaluate.html', {
        'attempt': attempt,
        'queue_items': queue_items,
    })


@login_required
def adjust_score_view(request, attempt_id):
    if not request.user.is_super_admin:
        return HttpResponseForbidden("Score adjustment restricted to Super Administrators.")

    attempt = get_object_or_404(AssessmentAttempt, id=attempt_id)

    if request.method == 'POST':
        new_score_str = request.POST.get('new_score')
        reason = request.POST.get('reason', '').strip()

        if not reason:
            messages.error(request, "An audit reason is mandatory for score adjustments.")
            return redirect('grading:evaluate_attempt', attempt_id=attempt.id)

        try:
            new_score = Decimal(new_score_str)
            old_score = attempt.earned_marks or Decimal('0.00')
            old_pct = attempt.percentage or Decimal('0.00')

            new_pct = round((new_score / attempt.max_possible_marks) * 100, 2) if attempt.max_possible_marks > 0 else Decimal('100.00')

            with transaction.atomic():
                GradeAdjustmentAudit.objects.create(
                    attempt=attempt,
                    adjusted_by=request.user,
                    old_score=old_score,
                    new_score=new_score,
                    old_percentage=old_pct,
                    new_percentage=new_pct,
                    reason=reason
                )

                attempt.earned_marks = new_score
                attempt.percentage = new_pct
                attempt.is_passed = (new_pct >= attempt.assessment.pass_mark_percentage)
                attempt.save(update_fields=['earned_marks', 'percentage', 'is_passed'])

                if attempt.is_passed:
                    Certificate.objects.get_or_create(
                        attempt=attempt,
                        defaults={
                            'user': attempt.user,
                            'assessment': attempt.assessment,
                            'score_percentage': attempt.percentage,
                        }
                    )

            messages.success(request, f"Score adjusted to {new_score} ({new_pct}%). Audit record created.")
        except Exception as e:
            messages.error(request, f"Failed to adjust score: {e}")

    return redirect('grading:evaluate_attempt', attempt_id=attempt.id)
