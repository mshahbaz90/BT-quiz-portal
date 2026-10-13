from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from assessments.models import Assessment
from exam.models import AssessmentAttempt
from certificates.models import Certificate
from certificates.utils import generate_certificate_pdf


class CertificatesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="cert.user",
            password="Password123!",
            first_name="Zara",
            last_name="Khan",
            employee_id="BT-777"
        )
        self.assessment = Assessment.objects.create(
            title="Advanced Cyber Security Certification",
            code="BT-SEC-99"
        )
        self.attempt = AssessmentAttempt.objects.create(
            user=self.user,
            assessment=self.assessment,
            status=AssessmentAttempt.Status.GRADED,
            deadline_at=self.assessment.created_at,
            earned_marks=Decimal('95.00'),
            max_possible_marks=Decimal('100.00'),
            percentage=Decimal('95.00'),
            is_passed=True
        )
        self.certificate = Certificate.objects.create(
            user=self.user,
            assessment=self.assessment,
            attempt=self.attempt,
            score_percentage=Decimal('95.00')
        )

    def test_pdf_generation_stream(self):
        buf = generate_certificate_pdf(self.certificate)
        pdf_bytes = buf.getvalue()
        self.assertTrue(len(pdf_bytes) > 1000)
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))

    def test_public_verification_view(self):
        url = reverse('certificates:verify_public', kwargs={'cert_uuid': self.certificate.certificate_id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Authentic & Verified Credential")
        self.assertContains(resp, "Zara Khan")
        self.assertContains(resp, self.certificate.certificate_code)

    def test_download_pdf_view_authenticated(self):
        self.client.login(username="cert.user", password="Password123!")
        url = reverse('certificates:download_pdf', kwargs={'cert_id': self.certificate.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
