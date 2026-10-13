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
