import json
import random
from datetime import timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.utils import timezone
from django.db import transaction

from assessments.models import Assessment, QuestionType
from exam.models import AssessmentAttempt, AttemptQuestionSnapshot, AttemptResponse
from grading.services import grade_attempt
from core.models import AuditLog


@login_required
def start_instruction_view(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id, status=Assessment.Status.PUBLISHED)
    user = request.user
    now = timezone.now()

    # Check for active in-progress attempt to resume
    active_attempt = AssessmentAttempt.objects.filter(
        user=user,
        assessment=assessment,
        status=AssessmentAttempt.Status.IN_PROGRESS,
        deadline_at__gt=now
    ).first()

    if active_attempt:
        return redirect('exam:take_assessment', attempt_id=active_attempt.id)

    # Check attempt limit
    completed_attempts_count = AssessmentAttempt.objects.filter(
        user=user,
        assessment=assessment,
        status__in=[AssessmentAttempt.Status.SUBMITTED, AssessmentAttempt.Status.GRADED]
    ).count()

    if assessment.max_attempts > 0 and completed_attempts_count >= assessment.max_attempts:
        return render(request, 'exam/attempt_limit_reached.html', {
            'assessment': assessment,
            'completed_count': completed_attempts_count,
        })

    if request.method == 'POST':
        # Initiate new assessment attempt with snapshotting
        with transaction.atomic():
            attempt_number = completed_attempts_count + 1
            duration_minutes = assessment.duration_minutes
            deadline = now + timedelta(minutes=duration_minutes)

            attempt = AssessmentAttempt.objects.create(
                user=user,
                assessment=assessment,
                assessment_version=assessment.version,
                attempt_number=attempt_number,
                deadline_at=deadline,
                ip_address=getattr(request, 'client_ip', None),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:250],
            )

            # Gather questions from assessment
            attached_items = list(assessment.assessment_questions.select_related('question').prefetch_related('question__options').all())
            if assessment.random_pool_count > 0 and len(attached_items) > assessment.random_pool_count:
                attached_items = random.sample(attached_items, assessment.random_pool_count)
            elif assessment.shuffle_questions:
                random.shuffle(attached_items)

            total_max_marks = Decimal('0.00')

            # Create snapshots
            for index, item in enumerate(attached_items, start=1):
                q = item.question
                alloc_marks = item.effective_marks
                total_max_marks += alloc_marks

                snapshot_data = {}
                q_type = q.question_type

                if q_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_SELECT, QuestionType.TRUE_FALSE, QuestionType.YES_NO]:
                    options = list(q.options.all())
                    if assessment.shuffle_options and q_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_SELECT]:
                        random.shuffle(options)

                    choices_list = []
                    correct_ids = []
                    correct_single = None

                    for opt in options:
                        choices_list.append({
                            'id': opt.id,
                            'text': opt.option_text,
                        })
                        if opt.is_correct:
                            correct_ids.append(opt.id)
                            correct_single = opt.id

                    snapshot_data['choices'] = choices_list
                    snapshot_data['correct_option_ids'] = correct_ids
                    snapshot_data['correct_option_id'] = correct_single

                elif q_type in [QuestionType.SHORT_ANSWER, QuestionType.FILL_BLANK]:
                    accepted = [a.strip() for a in q.short_answer_accepted.split('|') if a.strip()]
                    snapshot_data['accepted_answers'] = accepted

                elif q_type == QuestionType.NUMERIC:
                    snapshot_data['numeric_answer'] = str(q.numeric_answer) if q.numeric_answer is not None else None
                    snapshot_data['numeric_tolerance'] = str(q.numeric_tolerance)

                elif q_type == QuestionType.MATCHING:
                    options = list(q.options.all())
                    pairs = {}
                    targets = []
                    for opt in options:
                        pairs[opt.option_text] = opt.match_target
                        targets.append(opt.match_target)
                    random.shuffle(targets)
                    snapshot_data['prompts'] = list(pairs.keys())
                    snapshot_data['target_choices'] = targets
                    snapshot_data['matching_pairs'] = pairs

                elif q_type == QuestionType.ORDERING:
                    options = sorted(list(q.options.all()), key=lambda x: x.correct_order)
                    correct_order = [opt.option_text for opt in options]
                    shuffled_items = list(correct_order)
                    random.shuffle(shuffled_items)
                    snapshot_data['items'] = shuffled_items
                    snapshot_data['correct_order'] = correct_order

                snapshot = AttemptQuestionSnapshot.objects.create(
                    attempt=attempt,
                    question=q,
                    order_index=index,
                    question_type=q_type,
                    question_text=q.question_text,
                    rich_content=q.rich_content,
                    marks_allocated=alloc_marks,
                    hint=q.hint,
                    explanation=q.explanation,
                    snapshot_data=snapshot_data
                )

                AttemptResponse.objects.create(
                    attempt=attempt,
                    snapshot=snapshot,
                    response_data={}
                )

            attempt.total_questions = len(attached_items)
            attempt.max_possible_marks = total_max_marks
            attempt.save(update_fields=['total_questions', 'max_possible_marks'])

            AuditLog.objects.create(
                user=user,
                action='ATTEMPT_STARTED',
                target_model='AssessmentAttempt',
                target_id=str(attempt.id),
                ip_address=getattr(request, 'client_ip', None),
                details={'assessment_code': assessment.code, 'attempt_number': attempt.attempt_number}
            )

        return redirect('exam:take_assessment', attempt_id=attempt.id)

    return render(request, 'exam/instruction.html', {
        'assessment': assessment,
        'completed_count': completed_attempts_count,
    })


@login_required
def take_assessment_view(request, attempt_id):
    attempt = get_object_or_404(
        AssessmentAttempt.objects.select_related('assessment', 'user'),
        id=attempt_id,
        user=request.user
    )

    # If attempt was already submitted, redirect to result
    if attempt.status in [AssessmentAttempt.Status.SUBMITTED, AssessmentAttempt.Status.GRADED]:
        return redirect('exam:attempt_result', attempt_id=attempt.id)

    # Server-authoritative timeout check
    if timezone.now() >= attempt.deadline_at:
        # Time expired: auto finalize attempt
        return submit_assessment_view(request, attempt_id)

    snapshots = attempt.snapshots.prefetch_related('response').order_by('order_index')

    return render(request, 'exam/take_exam.html', {
        'attempt': attempt,
        'assessment': attempt.assessment,
        'snapshots': snapshots,
        'seconds_remaining': attempt.seconds_remaining,
        'deadline_iso': attempt.deadline_at.isoformat(),
    })


@login_required
def autosave_response_api(request, attempt_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("POST required")

    attempt = get_object_or_404(AssessmentAttempt, id=attempt_id, user=request.user)

    if not attempt.is_active:
        return JsonResponse({'status': 'expired', 'message': 'Assessment session has ended.'}, status=403)

    try:
        data = json.loads(request.body)
        snapshot_id = data.get('snapshot_id')
        response_data = data.get('response_data', {})

        snapshot = AttemptQuestionSnapshot.objects.filter(id=snapshot_id, attempt=attempt).first()
        if not snapshot:
            return JsonResponse({'status': 'error', 'message': 'Invalid snapshot ID'}, status=400)

        response = AttemptResponse.objects.filter(attempt=attempt, snapshot=snapshot).first()
        if response:
            response.response_data = response_data
            response.is_answered = True
            response.save(update_fields=['response_data', 'is_answered', 'last_saved_at'])

        return JsonResponse({
            'status': 'saved',
            'seconds_remaining': attempt.seconds_remaining,
            'saved_at': timezone.now().strftime('%H:%M:%S')
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def toggle_flag_api(request, attempt_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("POST required")

    attempt = get_object_or_404(AssessmentAttempt, id=attempt_id, user=request.user)
    data = json.loads(request.body)
    snapshot_id = data.get('snapshot_id')

    snapshot = AttemptQuestionSnapshot.objects.filter(id=snapshot_id, attempt=attempt).first()
    if snapshot:
        snapshot.is_flagged = not snapshot.is_flagged
        snapshot.save(update_fields=['is_flagged'])
        return JsonResponse({'status': 'ok', 'is_flagged': snapshot.is_flagged})

    return JsonResponse({'status': 'error'}, status=400)


@login_required
def log_switch_api(request, attempt_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("POST required")

    attempt = get_object_or_404(AssessmentAttempt, id=attempt_id, user=request.user)
    if attempt.is_active:
        attempt.browser_switch_count += 1
        attempt.save(update_fields=['browser_switch_count'])
    return JsonResponse({'status': 'ok', 'count': attempt.browser_switch_count})


@login_required
def submit_assessment_view(request, attempt_id):
    """
    Idempotent submission endpoint. Multiple submissions or duplicate calls safely return the finalized result.
    """
    attempt = get_object_or_404(AssessmentAttempt, id=attempt_id, user=request.user)

    with transaction.atomic():
        if attempt.status == AssessmentAttempt.Status.IN_PROGRESS:
            attempt.submitted_at = timezone.now()
            attempt.status = AssessmentAttempt.Status.SUBMITTED
            attempt.save(update_fields=['submitted_at', 'status'])

            # Automatically grade objective parts
            grade_attempt(attempt)

            AuditLog.objects.create(
                user=request.user,
                action='ATTEMPT_SUBMITTED',
                target_model='AssessmentAttempt',
                target_id=str(attempt.id),
                ip_address=getattr(request, 'client_ip', None),
                details={'percentage': str(attempt.percentage), 'is_passed': attempt.is_passed}
            )

    return redirect('exam:attempt_result', attempt_id=attempt.id)


@login_required
def attempt_result_view(request, attempt_id):
    attempt = get_object_or_404(
        AssessmentAttempt.objects.select_related('assessment', 'user').prefetch_related('snapshots__response'),
        id=attempt_id,
        user=request.user
    )

    certificate = getattr(attempt, 'certificate', None)

    return render(request, 'exam/result.html', {
        'attempt': attempt,
        'assessment': attempt.assessment,
        'certificate': certificate,
        'can_view_breakdown': attempt.assessment.release_results_mode == Assessment.ResultRelease.IMMEDIATE,
    })
