from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from assessments.models import Assessment, Question


class AssessmentAttempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        SUBMITTED = 'SUBMITTED', 'Submitted (Pending Grading)'
        GRADED = 'GRADED', 'Graded & Finalized'
        EXPIRED = 'EXPIRED', 'Time Expired'
        ABANDONED = 'ABANDONED', 'Abandoned'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assessment_attempts')
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='attempts')
    link = models.ForeignKey('assessments.AssessmentLink', on_delete=models.SET_NULL, null=True, blank=True, related_name='link_attempts')
    participant_name = models.CharField(max_length=150, blank=True)
    participant_email = models.EmailField(blank=True)
    participant_employee_id = models.CharField(max_length=50, blank=True)
    participant_department = models.CharField(max_length=120, blank=True)

    assessment_version = models.PositiveIntegerField(default=1)
    attempt_number = models.PositiveIntegerField(default=1)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS, db_index=True)
    started_at = models.DateTimeField(auto_now_add=True)
    deadline_at = models.DateTimeField(db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    total_questions = models.PositiveIntegerField(default=0)
    max_possible_marks = models.DecimalField(max_digits=7, decimal_places=2, default=0.00)
    earned_marks = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_passed = models.BooleanField(null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    browser_switch_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['assessment', 'status']),
            models.Index(fields=['deadline_at', 'status']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.assessment.code} Attempt #{self.attempt_number} ({self.status})"

    @property
    def is_active(self):
        return self.status == self.Status.IN_PROGRESS and timezone.now() < self.deadline_at

    @property
    def seconds_remaining(self):
        if not self.is_active:
            return 0
        diff = (self.deadline_at - timezone.now()).total_seconds()
        return max(0, int(diff))


class AttemptQuestionSnapshot(models.Model):
    attempt = models.ForeignKey(AssessmentAttempt, on_delete=models.CASCADE, related_name='snapshots')
    question = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True, blank=True, related_name='snapshot_usages')
    order_index = models.PositiveIntegerField(default=1)
    question_type = models.CharField(max_length=30)
    question_text = models.TextField()
    rich_content = models.TextField(blank=True)
    image_url = models.CharField(max_length=300, blank=True)
    marks_allocated = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    hint = models.CharField(max_length=255, blank=True)
    explanation = models.TextField(blank=True)
    
    # Complete frozen options payload (shuffled or ordered, keys included for server-side grading)
    snapshot_data = models.JSONField(default=dict)
    is_flagged = models.BooleanField(default=False)

    class Meta:
        ordering = ['order_index', 'id']
        unique_together = ('attempt', 'order_index')

    def __str__(self):
        return f"Attempt #{self.attempt_id} - Q#{self.order_index} ({self.question_type})"


class AttemptResponse(models.Model):
    attempt = models.ForeignKey(AssessmentAttempt, on_delete=models.CASCADE, related_name='responses')
    snapshot = models.OneToOneField(AttemptQuestionSnapshot, on_delete=models.CASCADE, related_name='response')
    response_data = models.JSONField(default=dict, blank=True)
    is_answered = models.BooleanField(default=False, db_index=True)
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    is_evaluated = models.BooleanField(default=False)
    evaluated_automatically = models.BooleanField(default=False)
    last_saved_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['snapshot__order_index']

    def __str__(self):
        return f"Resp Attempt #{self.attempt_id} - Q#{self.snapshot.order_index} (Marks: {self.marks_awarded})"
