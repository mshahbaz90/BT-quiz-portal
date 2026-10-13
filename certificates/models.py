import uuid
from django.db import models
from django.conf import settings
from assessments.models import Assessment
from exam.models import AssessmentAttempt


def generate_certificate_code():
    import random
    import string
    rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"BT-CERT-{rand}"


class Certificate(models.Model):
    certificate_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    certificate_code = models.CharField(max_length=30, unique=True, default=generate_certificate_code, db_index=True)
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates')
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='issued_certificates')
    attempt = models.OneToOneField(AssessmentAttempt, on_delete=models.CASCADE, related_name='certificate')
    
    score_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='certificates/', blank=True)
    
    is_revoked = models.BooleanField(default=False)
    revoked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='revoked_certificates')
    revocation_reason = models.TextField(blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-issued_at']

    def __str__(self):
        return f"{self.certificate_code} - {self.user.get_full_name() or self.user.username} ({self.assessment.title})"
