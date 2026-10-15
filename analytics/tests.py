from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, Department, Role, Team
from assessments.models import Assessment
from exam.models import AssessmentAttempt


class AnalyticsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(name="Quality Assurance", code="QA")
        self.team = Team.objects.create(name="Automation Team", department=self.dept)
        
        self.trainer = User.objects.create_user(
            username="qa.trainer",
            email="trainer@breakthru.pk",
            password="Password123!",
            role=Role.TRAINER,
            department=self.dept
        )
        self.candidate = User.objects.create_user(
            username="qa.candidate",
            email="cand@breakthru.pk",
            password="Password123!",
            employee_id="BT-QA-10",
            role=Role.EMPLOYEE,
            department=self.dept,
            team=self.team
        )
        self.assessment = Assessment.objects.create(
            title="Selenium & PyTest Certification",
            code="BT-QA-01",
            duration_minutes=45,
            pass_mark_percentage=75,
            status=Assessment.Status.PUBLISHED,
            created_by=self.trainer
        )
        self.attempt = AssessmentAttempt.objects.create(
            user=self.candidate,
            assessment=self.assessment,
            assessment_version=1,
            attempt_number=1,
            status=AssessmentAttempt.Status.GRADED,
            earned_marks=Decimal('18.00'),
            max_possible_marks=Decimal('20.00'),
            percentage=Decimal('90.00'),
            is_passed=True,
            deadline_at=timezone.now() + timezone.timedelta(minutes=45),
            submitted_at=timezone.now()
        )

    def test_executive_reports_overview(self):
        self.client.login(username="qa.trainer", password="Password123!")
        resp = self.client.get(reverse('analytics:reports_overview'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Quality Assurance")
        self.assertContains(resp, "Selenium &amp; PyTest Certification")

    def test_results_list_view_and_filters(self):
        self.client.login(username="qa.trainer", password="Password123!")
        
        # 1. Base results list
        resp = self.client.get(reverse('analytics:results_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "BT-QA-10")
        self.assertContains(resp, "90.0%")
        self.assertContains(resp, "PASSED")

        # 2. Filter by search query
        resp_q = self.client.get(reverse('analytics:results_list'), {'q': 'BT-QA-10'})
        self.assertEqual(resp_q.status_code, 200)
        self.assertContains(resp_q, "BT-QA-10")

        # 3. Filter by result 'pass'
        resp_pass = self.client.get(reverse('analytics:results_list'), {'result': 'pass'})
        self.assertEqual(resp_pass.status_code, 200)
        self.assertContains(resp_pass, "BT-QA-10")

        # 4. Filter by result 'fail' (should be empty)
        resp_fail = self.client.get(reverse('analytics:results_list'), {'result': 'fail'})
        self.assertEqual(resp_fail.status_code, 200)
        self.assertContains(resp_fail, "No assessment attempts found")

    def test_csv_and_excel_export(self):
        self.client.login(username="qa.trainer", password="Password123!")
        
        # CSV Export
        resp_csv = self.client.get(reverse('analytics:export_csv'))
        self.assertEqual(resp_csv.status_code, 200)
        self.assertEqual(resp_csv['Content-Type'], 'text/csv')
        self.assertIn(b'BT-QA-10', resp_csv.content)

        # Excel Export
        resp_excel = self.client.get(reverse('analytics:export_excel'))
        self.assertEqual(resp_excel.status_code, 200)
        self.assertIn('spreadsheetml', resp_excel['Content-Type'])
