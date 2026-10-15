from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, Role
from assessments.models import Assessment, Question, QuestionOption, AssessmentQuestion, QuestionType


class AssessmentsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.trainer = User.objects.create_user(
            username="trainer1",
            email="trainer@breakthru.pk",
            password="Password123!",
            role=Role.TRAINER
        )
        self.client.login(username="trainer1", password="Password123!")

    def test_assessment_creation_and_question_attachment(self):
        # 1. Create assessment
        resp = self.client.post(reverse('assessments:assessment_create'), {
            'title': 'Python Backend Assessment',
            'code': 'BT-TEST-01',
            'duration_minutes': 20,
            'pass_mark_percentage': 70.0,
            'max_attempts': 1,
            'status': Assessment.Status.DRAFT,
            'shuffle_questions': True,
            'shuffle_options': True,
            'allow_backtracking': True,
            'negative_mark_penalty': 0.25,
            'release_results_mode': Assessment.ResultRelease.IMMEDIATE,
            'random_pool_count': 0,
        })
        self.assertEqual(resp.status_code, 302)
        assessment = Assessment.objects.get(code='BT-TEST-01')

        # 2. Cannot publish with 0 questions
        resp_pub = self.client.post(reverse('assessments:assessment_toggle_publish', kwargs={'assessment_id': assessment.id}))
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, Assessment.Status.DRAFT)

        # 3. Create question
        q = Question.objects.create(
            question_text="What does WSGI stand for?",
            question_type=QuestionType.SINGLE_CHOICE,
            default_marks=Decimal('2.00'),
            created_by=self.trainer
        )
        QuestionOption.objects.create(question=q, option_text="Web Server Gateway Interface", is_correct=True)
        QuestionOption.objects.create(question=q, option_text="Wide Socket Global Interface", is_correct=False)

        # 4. Attach question
        self.client.post(reverse('assessments:assessment_add_question', kwargs={'assessment_id': assessment.id, 'question_id': q.id}))
        self.assertEqual(assessment.assessment_questions.count(), 1)

        # 5. Now publishing succeeds
        self.client.post(reverse('assessments:assessment_toggle_publish', kwargs={'assessment_id': assessment.id}))
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, Assessment.Status.PUBLISHED)

    def test_category_lifecycle(self):
        # Create category
        resp = self.client.post(reverse('assessments:category_list'), {
            'name': 'DevOps & Cloud',
            'description': 'Infrastructure, CI/CD, and Docker topics'
        })
        self.assertEqual(resp.status_code, 302)
        from assessments.models import Category
        cat = Category.objects.get(name='DevOps & Cloud')
        self.assertEqual(cat.description, 'Infrastructure, CI/CD, and Docker topics')

        # List categories
        resp_list = self.client.get(reverse('assessments:category_list'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertContains(resp_list, 'DevOps')

        # Delete category
        resp_del = self.client.get(reverse('assessments:category_delete', kwargs={'category_id': cat.id}))
        self.assertEqual(resp_del.status_code, 302)
        self.assertFalse(Category.objects.filter(id=cat.id).exists())

    def test_assessment_duplication_and_archive(self):
        assessment = Assessment.objects.create(
            title='Security Fundamentals',
            code='BT-SEC-01',
            duration_minutes=30,
            pass_mark_percentage=80,
            status=Assessment.Status.PUBLISHED,
            created_by=self.trainer
        )
        q = Question.objects.create(
            question_text="What is a CSRF token?",
            question_type=QuestionType.SINGLE_CHOICE,
            default_marks=Decimal('1.00'),
            created_by=self.trainer
        )
        AssessmentQuestion.objects.create(assessment=assessment, question=q, order=1)

        # Duplicate
        resp = self.client.get(reverse('assessments:assessment_duplicate', kwargs={'assessment_id': assessment.id}))
        self.assertEqual(resp.status_code, 302)
        clones = Assessment.objects.filter(title__contains='Security Fundamentals (Copy)')
        self.assertTrue(clones.exists())
        clone = clones.first()
        self.assertEqual(clone.status, Assessment.Status.DRAFT)
        self.assertEqual(clone.assessment_questions.count(), 1)

        # Archive
        self.assertFalse(assessment.is_archived)
        resp_arch = self.client.get(reverse('assessments:assessment_archive', kwargs={'assessment_id': assessment.id}))
        self.assertEqual(resp_arch.status_code, 302)
        assessment.refresh_from_db()
        self.assertTrue(assessment.is_archived)

    def test_question_duplicate_and_csv_export(self):
        q = Question.objects.create(
            question_text="Explain Python GIL",
            question_type=QuestionType.LONG_ANSWER,
            default_marks=Decimal('5.00'),
            created_by=self.trainer
        )

        # Duplicate Question
        resp_dup = self.client.get(reverse('assessments:question_duplicate', kwargs={'question_id': q.id}))
        self.assertEqual(resp_dup.status_code, 302)
        self.assertTrue(Question.objects.filter(question_text="Explain Python GIL (Copy)").exists())

        # Export CSV
        resp_exp = self.client.get(reverse('assessments:question_export_csv'))
        self.assertEqual(resp_exp.status_code, 200)
        self.assertEqual(resp_exp['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn(b'Explain Python GIL', resp_exp.content)

    def test_assessment_link_lifecycle_and_candidate_access(self):
        from assessments.models import AssessmentLink
        from exam.models import AssessmentAttempt

        # 1. Create published assessment with 1 question
        assessment = Assessment.objects.create(
            title='ClassMarker Direct Link Assessment',
            code='BT-LINK-01',
            duration_minutes=25,
            pass_mark_percentage=60,
            status=Assessment.Status.PUBLISHED,
            created_by=self.trainer
        )
        q = Question.objects.create(
            question_text="Is Django a Python web framework?",
            question_type=QuestionType.TRUE_FALSE,
            default_marks=Decimal('2.00'),
            created_by=self.trainer
        )
        QuestionOption.objects.create(question=q, option_text="True", is_correct=True)
        QuestionOption.objects.create(question=q, option_text="False", is_correct=False)
        AssessmentQuestion.objects.create(assessment=assessment, question=q, order=1)

        # 2. Trainer creates a ClassMarker Link
        resp_create = self.client.post(reverse('assessments:link_create'), {
            'name': 'Batch 2026 Campus Hiring Link',
            'assessment': assessment.id,
            'access_code': 'PIN1234',
            'allowed_email_domains': '@breakthru.com, @breakthru.pk',
            'require_employee_id': True,
            'collect_name': True,
            'collect_email': True,
            'collect_department': True,
            'max_completions': 100,
            'max_attempts_per_user': 1,
            'is_active': True,
        })
        self.assertEqual(resp_create.status_code, 302)
        link = AssessmentLink.objects.get(name='Batch 2026 Campus Hiring Link')
        self.assertTrue(bool(link.link_code))
        self.assertEqual(link.access_code, 'PIN1234')

        # 3. View link list & detail
        resp_list = self.client.get(reverse('assessments:link_list'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertContains(resp_list, 'Batch 2026 Campus Hiring Link')

        resp_detail = self.client.get(reverse('assessments:link_detail', kwargs={'link_id': link.id}))
        self.assertEqual(resp_detail.status_code, 200)
        self.assertContains(resp_detail, link.link_code)

        # 4. Anonymous external candidate accesses public link landing
        guest_client = Client()
        resp_landing = guest_client.get(f'/links/{link.link_code}/')
        self.assertEqual(resp_landing.status_code, 200)
        self.assertContains(resp_landing, 'ClassMarker Direct Link Assessment')

        # 5. Invalid PIN validation
        resp_bad_pin = guest_client.post(f'/links/{link.link_code}/', {
            'name': 'Alice Candidate',
            'email': 'alice@breakthru.com',
            'employee_id': 'CAND-001',
            'access_code': 'WRONG_PIN',
        })
        self.assertEqual(resp_bad_pin.status_code, 200)
        self.assertContains(resp_bad_pin, 'Invalid Access PIN')

        # 6. Disallowed email domain validation
        resp_bad_domain = guest_client.post(f'/links/{link.link_code}/', {
            'name': 'Alice Candidate',
            'email': 'alice@personal-email.org',
            'employee_id': 'CAND-001',
            'access_code': 'PIN1234',
        })
        self.assertEqual(resp_bad_domain.status_code, 200)
        self.assertContains(resp_bad_domain, 'Email domain not allowed')

        # 7. Valid candidate submission launches attempt
        resp_start = guest_client.post(f'/links/{link.link_code}/', {
            'name': 'Alice Candidate',
            'email': 'alice@breakthru.com',
            'employee_id': 'CAND-001',
            'department': 'Product Engineering',
            'access_code': 'PIN1234',
        })
        self.assertEqual(resp_start.status_code, 302)

        # Verify attempt record has link and candidate details
        attempt = AssessmentAttempt.objects.filter(link=link).first()
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt.participant_name, 'Alice Candidate')
        self.assertEqual(attempt.participant_email, 'alice@breakthru.com')
        self.assertEqual(attempt.participant_employee_id, 'CAND-001')
        self.assertEqual(attempt.participant_department, 'Product Engineering')
        self.assertEqual(attempt.assessment, assessment)
        self.assertEqual(attempt.total_questions, 1)

        # 8. Pause link and verify unavailable notice
        self.client.post(reverse('assessments:link_toggle', kwargs={'link_id': link.id}))
        link.refresh_from_db()
        self.assertFalse(link.is_active)

        resp_paused = guest_client.get(f'/links/{link.link_code}/')
        self.assertEqual(resp_paused.status_code, 200)
        self.assertContains(resp_paused, 'Assessment Link Unavailable')
