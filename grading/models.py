from django.db import models
from django.conf import settings
from exam.models import AssessmentAttempt, AttemptQuestionSnapshot, AttemptResponse


class ManualGradingQueue(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Manual Evaluation'
        COMPLETED = 'COMPLETED', 'Graded & Evaluated'

    attempt = models.ForeignKey(AssessmentAttempt, on_delete=models.CASCADE, related_name='manual_grading_items')
    snapshot = models.ForeignKey(AttemptQuestionSnapshot, on_delete=models.CASCADE, related_name='grading_queue_entries')
    response = models.ForeignKey(AttemptResponse, on_delete=models.CASCADE, related_name='grading_queue_entries')
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    grader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_gradings')
    grader_feedback = models.TextField(blank=True)
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['status', 'created_at']
        unique_together = ('attempt', 'snapshot')

    def __str__(self):
        return f"Queue #{self.id} Attempt #{self.attempt_id} Q#{self.snapshot.order_index} ({self.status})"


class GradeAdjustmentAudit(models.Model):
    attempt = models.ForeignKey(AssessmentAttempt, on_delete=models.CASCADE, related_name='grade_adjustments')
    adjusted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    old_score = models.DecimalField(max_digits=7, decimal_places=2)
    new_score = models.DecimalField(max_digits=7, decimal_places=2)
    old_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    new_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField()
    adjusted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-adjusted_at']

    def __str__(self):
        return f"Attempt #{self.attempt_id} adjusted from {self.old_score} to {self.new_score} by {self.adjusted_by}"
