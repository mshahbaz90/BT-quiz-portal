import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, Role
from assessments.models import Assessment, Question, QuestionOption, AssessmentQuestion, QuestionType
from exam.models import AssessmentAttempt, AttemptQuestionSnapshot, AttemptResponse
from certificates.models import Certificate


class ExamAndGradingTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.candidate = User.objects.create_user(
            username="candidate1",
            password="Password123!",
            employee_id="BT-501",
            role=Role.EMPLOYEE
        )
        self.client.login(username="candidate1", password="Password123!")

        # Create Assessment
        self.assessment = Assessment.objects.create(
            title="Full Objective Exam",
            code="BT-OBJ-01",
            duration_minutes=30,
            pass_mark_percentage=Decimal('50.00'),
            max_attempts=2,
            status=Assessment.Status.PUBLISHED,
            release_results_mode=Assessment.ResultRelease.IMMEDIATE
        )

        # 1. Single Choice
        self.q1 = Question.objects.create(
            question_text="Capital of Pakistan?",
            question_type=QuestionType.SINGLE_CHOICE,
            default_marks=Decimal('5.00')
        )
        self.opt1_corr = QuestionOption.objects.create(question=self.q1, option_text="Islamabad", is_correct=True)
        self.opt1_inc = QuestionOption.objects.create(question=self.q1, option_text="Karachi", is_correct=False)
        AssessmentQuestion.objects.create(assessment=self.assessment, question=self.q1, order=1)

        # 2. Short Answer
        self.q2 = Question.objects.create(
            question_text="What does CSS stand for?",
            question_type=QuestionType.SHORT_ANSWER,
            default_marks=Decimal('5.00'),
            short_answer_accepted="Cascading Style Sheets"
        )
        AssessmentQuestion.objects.create(assessment=self.assessment, question=self.q2, order=2)

    def test_complete_exam_flow_autosave_and_grading(self):
        # 1. Start Exam
        start_resp = self.client.post(reverse('exam:start_instruction', kwargs={'assessment_id': self.assessment.id}))
        self.assertEqual(start_resp.status_code, 302)

        attempt = AssessmentAttempt.objects.filter(user=self.candidate, assessment=self.assessment).first()
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt.snapshots.count(), 2)

        snap1 = attempt.snapshots.get(order_index=1)
        snap2 = attempt.snapshots.get(order_index=2)

        # 2. Autosave Question 1 (Select correct option)
        payload1 = {'snapshot_id': snap1.id, 'response_data': {'selected_option_id': self.opt1_corr.id}}
        save_resp1 = self.client.post(
            reverse('exam:api_autosave', kwargs={'attempt_id': attempt.id}),
            data=json.dumps(payload1),
            content_type='application/json'
        )
        self.assertEqual(save_resp1.status_code, 200)
        self.assertEqual(save_resp1.json()['status'], 'saved')

        # 3. Autosave Question 2 (Type correct short answer)
        payload2 = {'snapshot_id': snap2.id, 'response_data': {'text_answer': 'Cascading Style Sheets'}}
        save_resp2 = self.client.post(
            reverse('exam:api_autosave', kwargs={'attempt_id': attempt.id}),
            data=json.dumps(payload2),
            content_type='application/json'
        )
        self.assertEqual(save_resp2.status_code, 200)

        # 4. Final Submit
        submit_resp = self.client.post(reverse('exam:submit_assessment', kwargs={'attempt_id': attempt.id}))
        self.assertEqual(submit_resp.status_code, 302)

        attempt.refresh_from_db()
        self.assertEqual(attempt.status, AssessmentAttempt.Status.GRADED)
        self.assertEqual(attempt.earned_marks, Decimal('10.00'))
        self.assertEqual(attempt.percentage, Decimal('100.00'))
        self.assertTrue(attempt.is_passed)

        # 5. Certificate automatically issued
        cert = Certificate.objects.filter(attempt=attempt).first()
        self.assertIsNotNone(cert)
        self.assertEqual(cert.score_percentage, Decimal('100.00'))

        # 6. Test idempotent repeat submit does not crash or corrupt
        repeat_submit = self.client.post(reverse('exam:submit_assessment', kwargs={'attempt_id': attempt.id}))
        self.assertEqual(repeat_submit.status_code, 302)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, AssessmentAttempt.Status.GRADED)
