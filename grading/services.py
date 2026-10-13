from decimal import Decimal
from django.utils import timezone
from exam.models import AssessmentAttempt, AttemptResponse, AttemptQuestionSnapshot
from grading.models import ManualGradingQueue
from assessments.models import QuestionType
from certificates.models import Certificate


def grade_attempt(attempt: AssessmentAttempt) -> bool:
    """
    Grades all objective questions in an attempt.
    If any subjective questions (e.g. LONG_ANSWER) are present, adds them to the ManualGradingQueue.
    Returns True if fully graded, False if pending manual grading.
    """
    responses = attempt.responses.select_related('snapshot').all()
    total_earned = Decimal('0.00')
    has_pending_manual = False

    penalty = attempt.assessment.negative_mark_penalty if attempt.assessment.negative_marking else Decimal('0.00')

    for resp in responses:
        snap = resp.snapshot
        q_type = snap.question_type
        alloc_marks = snap.marks_allocated
        resp_data = resp.response_data or {}
        earned = Decimal('0.00')

        if q_type in [QuestionType.SINGLE_CHOICE, QuestionType.TRUE_FALSE, QuestionType.YES_NO]:
            selected_id = resp_data.get('selected_option_id')
            correct_id = snap.snapshot_data.get('correct_option_id')
            if selected_id is not None and str(selected_id) == str(correct_id):
                earned = alloc_marks
            elif selected_id is not None and penalty > 0:
                earned = -penalty

            resp.marks_awarded = max(Decimal('0.00'), earned) if penalty == 0 else earned
            resp.is_evaluated = True
            resp.evaluated_automatically = True
            resp.save(update_fields=['marks_awarded', 'is_evaluated', 'evaluated_automatically'])
            total_earned += resp.marks_awarded

        elif q_type == QuestionType.MULTIPLE_SELECT:
            selected_ids = set(str(x) for x in resp_data.get('selected_option_ids', []))
            correct_ids = set(str(x) for x in snap.snapshot_data.get('correct_option_ids', []))
            if selected_ids and selected_ids == correct_ids:
                earned = alloc_marks
            elif selected_ids and correct_ids:
                # Partial credit: proportion of correct choices minus incorrect choices
                correct_picks = len(selected_ids.intersection(correct_ids))
                incorrect_picks = len(selected_ids - correct_ids)
                ratio = max(0, (correct_picks - incorrect_picks) / len(correct_ids))
                earned = round(alloc_marks * Decimal(str(ratio)), 2)
            resp.marks_awarded = max(Decimal('0.00'), earned)
            resp.is_evaluated = True
            resp.evaluated_automatically = True
            resp.save(update_fields=['marks_awarded', 'is_evaluated', 'evaluated_automatically'])
            total_earned += resp.marks_awarded

        elif q_type in [QuestionType.SHORT_ANSWER, QuestionType.FILL_BLANK]:
            cand_text = str(resp_data.get('text_answer', '')).strip().lower()
            accepted = [a.strip().lower() for a in snap.snapshot_data.get('accepted_answers', []) if a.strip()]
            if cand_text and cand_text in accepted:
                earned = alloc_marks
            elif cand_text and penalty > 0:
                earned = -penalty
            resp.marks_awarded = max(Decimal('0.00'), earned)
            resp.is_evaluated = True
            resp.evaluated_automatically = True
            resp.save(update_fields=['marks_awarded', 'is_evaluated', 'evaluated_automatically'])
            total_earned += resp.marks_awarded

        elif q_type == QuestionType.NUMERIC:
            cand_num = resp_data.get('numeric_value')
            target = snap.snapshot_data.get('numeric_answer')
            tolerance = Decimal(str(snap.snapshot_data.get('numeric_tolerance', '0.00')))
            if cand_num is not None and target is not None:
                try:
                    c_val = Decimal(str(cand_num))
                    t_val = Decimal(str(target))
                    if abs(c_val - t_val) <= tolerance:
                        earned = alloc_marks
                except Exception:
                    pass
            resp.marks_awarded = earned
            resp.is_evaluated = True
            resp.evaluated_automatically = True
            resp.save(update_fields=['marks_awarded', 'is_evaluated', 'evaluated_automatically'])
            total_earned += resp.marks_awarded

        elif q_type == QuestionType.MATCHING:
            cand_matches = resp_data.get('matches', {}) # dict of {prompt: target}
            target_pairs = snap.snapshot_data.get('matching_pairs', {}) # dict of {prompt: target}
            if target_pairs:
                correct_count = sum(1 for p, t in target_pairs.items() if cand_matches.get(p) == t)
                ratio = correct_count / len(target_pairs)
                earned = round(alloc_marks * Decimal(str(ratio)), 2)
            resp.marks_awarded = earned
            resp.is_evaluated = True
            resp.evaluated_automatically = True
            resp.save(update_fields=['marks_awarded', 'is_evaluated', 'evaluated_automatically'])
            total_earned += resp.marks_awarded

        elif q_type == QuestionType.ORDERING:
            cand_order = [str(x) for x in resp_data.get('order', [])]
            target_order = [str(x) for x in snap.snapshot_data.get('correct_order', [])]
            if cand_order and cand_order == target_order:
                earned = alloc_marks
            resp.marks_awarded = earned
            resp.is_evaluated = True
            resp.evaluated_automatically = True
            resp.save(update_fields=['marks_awarded', 'is_evaluated', 'evaluated_automatically'])
            total_earned += resp.marks_awarded

        elif q_type == QuestionType.LONG_ANSWER:
            has_pending_manual = True
            ManualGradingQueue.objects.get_or_create(
                attempt=attempt,
                snapshot=snap,
                defaults={'response': resp, 'status': ManualGradingQueue.Status.PENDING}
            )

        else:
            # Default objective fallback
            resp.is_evaluated = True
            resp.save(update_fields=['is_evaluated'])

    # Determine attempt score and pass/fail
    attempt.earned_marks = max(Decimal('0.00'), total_earned)
    if attempt.max_possible_marks > 0:
        pct = round((attempt.earned_marks / attempt.max_possible_marks) * 100, 2)
        attempt.percentage = pct
        attempt.is_passed = (pct >= attempt.assessment.pass_mark_percentage)
    else:
        attempt.percentage = Decimal('100.00')
        attempt.is_passed = True

    if not has_pending_manual:
        attempt.status = AssessmentAttempt.Status.GRADED
        attempt.save(update_fields=['status', 'earned_marks', 'percentage', 'is_passed'])

        # Auto-issue Certificate if passed
        if attempt.is_passed:
            Certificate.objects.get_or_create(
                attempt=attempt,
                defaults={
                    'user': attempt.user,
                    'assessment': attempt.assessment,
                    'score_percentage': attempt.percentage,
                }
            )
        return True
    else:
        attempt.status = AssessmentAttempt.Status.SUBMITTED
        attempt.save(update_fields=['status', 'earned_marks', 'percentage', 'is_passed'])
        return False
