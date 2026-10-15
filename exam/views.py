import json
import random
import uuid
from datetime import timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction

from accounts.models import User, Role
from assessments.models import Assessment, AssessmentLink, QuestionType
from exam.models import AssessmentAttempt, AttemptQuestionSnapshot, AttemptResponse
from grading.services import grade_attempt
from core.models import AuditLog


def initialize_attempt(assessment, user, link=None, participant_info=None, ip_address=None, user_agent='', attempt_number=1):
    """
    ClassMarker-standard attempt initiator.
    Selects questions (random pool / shuffle), creates immutable question snapshots and blank response rows.
    """
    now = timezone.now()
    duration_minutes = assessment.duration_minutes
    deadline = now + timedelta(minutes=duration_minutes) if duration_minutes > 0 else now + timedelta(hours=24)

    p_info = participant_info or {}

    with transaction.atomic():
        attempt = AssessmentAttempt.objects.create(
            user=user,
            assessment=assessment,
            link=link,
            participant_name=p_info.get('name', ''),
            participant_email=p_info.get('email', ''),
            participant_employee_id=p_info.get('employee_id', ''),
            participant_department=p_info.get('department', ''),
            assessment_version=assessment.version,
            attempt_number=attempt_number,
            deadline_at=deadline,
            ip_address=ip_address,
            user_agent=user_agent[:250],
        )

        attached_items = list(assessment.assessment_questions.select_related('question').prefetch_related('question__options').all())
        if assessment.random_pool_count > 0 and len(attached_items) > assessment.random_pool_count:
            attached_items = random.sample(attached_items, assessment.random_pool_count)
        elif assessment.shuffle_questions:
            random.shuffle(attached_items)

        total_max_marks = Decimal('0.00')

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
            ip_address=ip_address,
            details={'assessment_code': assessment.code, 'attempt_number': attempt.attempt_number, 'link_code': link.link_code if link else None}
        )

    return attempt


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
        if assessment.allow_save_and_resume:
            return redirect('exam:take_assessment', attempt_id=active_attempt.id)
        else:
            return render(request, 'exam/instruction.html', {
                'assessment': assessment,
                'resume_forbidden': True,
            })

    # Check attempt limit
    completed_attempts = AssessmentAttempt.objects.filter(
        user=user,
        assessment=assessment,
        status__in=[AssessmentAttempt.Status.SUBMITTED, AssessmentAttempt.Status.GRADED]
    ).order_by('-submitted_at')
    completed_attempts_count = completed_attempts.count()

    if assessment.max_attempts > 0 and completed_attempts_count >= assessment.max_attempts:
        return render(request, 'exam/attempt_limit_reached.html', {
            'assessment': assessment,
            'completed_count': completed_attempts_count,
        })

    # Check retake cooldown
    if assessment.retake_cooldown_hours > 0 and completed_attempts.exists():
        last_attempt = completed_attempts.first()
        if last_attempt and last_attempt.submitted_at:
            cooldown_deadline = last_attempt.submitted_at + timedelta(hours=assessment.retake_cooldown_hours)
            if now < cooldown_deadline:
                remaining_seconds = int((cooldown_deadline - now).total_seconds())
                remaining_hours = round(remaining_seconds / 3600, 1)
                return render(request, 'exam/instruction.html', {
                    'assessment': assessment,
                    'cooldown_active': True,
                    'remaining_hours': remaining_hours,
                    'cooldown_deadline': cooldown_deadline,
                })

    access_code_error = False
    if request.method == 'POST':
        # Verify access code PIN if configured
        if assessment.access_code:
            entered_code = request.POST.get('access_code', '').strip()
            if entered_code != assessment.access_code:
                return render(request, 'exam/instruction.html', {
                    'assessment': assessment,
                    'access_code_error': True,
                    'entered_code': entered_code,
                })

        attempt = initialize_attempt(
            assessment=assessment,
            user=user,
            participant_info={
                'name': user.get_full_name() or user.username,
                'email': user.email,
                'employee_id': user.employee_id or '',
                'department': user.department.name if user.department else '',
            },
            ip_address=getattr(request, 'client_ip', None),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            attempt_number=completed_attempts_count + 1
        )
        return redirect('exam:take_assessment', attempt_id=attempt.id)

    return render(request, 'exam/instruction.html', {
        'assessment': assessment,
        'completed_count': completed_attempts_count,
    })


def public_link_entry_view(request, link_code):
    """
    ClassMarker-standard Direct Link Landing and Entry Gateway.
    Allows candidate access with optional PIN, participant metadata collection,
    domain checks, quota enforcement, and instant exam launch.
    """
    link = get_object_or_404(
        AssessmentLink.objects.select_related('assessment', 'assessment__category'),
        link_code__iexact=link_code
    )
    assessment = link.assessment
    now = timezone.now()

    is_available, unavail_reason = link.check_availability()
    if not is_available:
        return render(request, 'exam/link_unavailable.html', {
            'link': link,
            'assessment': assessment,
            'reason': unavail_reason,
        })

    # Check for active in-progress attempt for signed-in user
    if request.user.is_authenticated:
        active_attempt = AssessmentAttempt.objects.filter(
            user=request.user,
            assessment=assessment,
            link=link,
            status=AssessmentAttempt.Status.IN_PROGRESS,
            deadline_at__gt=now
        ).first()
        if active_attempt:
            if assessment.allow_save_and_resume:
                return redirect('exam:take_assessment', attempt_id=active_attempt.id)

    # Check attempt limit for logged-in user
    if request.user.is_authenticated and link.max_attempts_per_user > 0:
        user_attempts_count = AssessmentAttempt.objects.filter(
            user=request.user,
            assessment=assessment,
            link=link,
            status__in=[AssessmentAttempt.Status.SUBMITTED, AssessmentAttempt.Status.GRADED]
        ).count()
        if user_attempts_count >= link.max_attempts_per_user:
            return render(request, 'exam/link_limit_reached.html', {
                'link': link,
                'assessment': assessment,
                'max_attempts': link.max_attempts_per_user,
            })

    form_errors = []

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        employee_id = request.POST.get('employee_id', '').strip()
        department = request.POST.get('department', '').strip()
        access_code = request.POST.get('access_code', '').strip()

        # If user is logged in, fallback to user properties
        if request.user.is_authenticated:
            if not name:
                name = request.user.get_full_name() or request.user.username
            if not email:
                email = request.user.email
            if not employee_id:
                employee_id = request.user.employee_id or ''
            if not department:
                department = request.user.department.name if request.user.department else ''

        # Validation rules
        if link.collect_name and not name:
            form_errors.append("Please enter your Full Name.")

        if link.collect_email:
            if not email:
                form_errors.append("Please enter your Email address.")
            elif link.allowed_email_domains:
                allowed_domains = [d.strip().lower() for d in link.allowed_email_domains.split(',') if d.strip()]
                match_found = any(email.endswith(d) or f"@{email.split('@')[-1]}" == d for d in allowed_domains)
                if not match_found:
                    form_errors.append(f"Email domain not allowed. Permitted: {link.allowed_email_domains}")

        if link.require_employee_id and not employee_id:
            form_errors.append("Employee ID / Candidate ID is required.")

        if link.access_code and access_code != link.access_code:
            form_errors.append("Invalid Access PIN / Password.")

        # Attempt limit check for guest email
        if not request.user.is_authenticated and link.max_attempts_per_user > 0 and email:
            prior_guest_attempts = AssessmentAttempt.objects.filter(
                assessment=assessment,
                link=link,
                participant_email__iexact=email,
                status__in=[AssessmentAttempt.Status.SUBMITTED, AssessmentAttempt.Status.GRADED]
            ).count()
            if prior_guest_attempts >= link.max_attempts_per_user:
                form_errors.append(f"Maximum attempts ({link.max_attempts_per_user}) reached for {email}.")

        if not form_errors:
            # Provision or retrieve candidate user
            if request.user.is_authenticated:
                candidate_user = request.user
            else:
                candidate_user = User.objects.filter(email__iexact=email).first()
                if not candidate_user:
                    username_base = slugify(name)[:20] if name else "candidate"
                    username = f"{username_base}_{uuid.uuid4().hex[:6]}"
                    candidate_user = User.objects.create(
                        username=username,
                        email=email,
                        first_name=name.split(' ')[0] if name else 'Candidate',
                        last_name=' '.join(name.split(' ')[1:]) if (name and ' ' in name) else '',
                        role=Role.EMPLOYEE,
                        employee_id=employee_id,
                    )
                    candidate_user.set_unusable_password()
                    candidate_user.save()

                candidate_user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, candidate_user)

            # Determine attempt count
            attempt_count = AssessmentAttempt.objects.filter(
                user=candidate_user,
                assessment=assessment,
                link=link,
                status__in=[AssessmentAttempt.Status.SUBMITTED, AssessmentAttempt.Status.GRADED]
            ).count()

            attempt = initialize_attempt(
                assessment=assessment,
                user=candidate_user,
                link=link,
                participant_info={
                    'name': name,
                    'email': email,
                    'employee_id': employee_id,
                    'department': department,
                },
                ip_address=getattr(request, 'client_ip', None),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                attempt_number=attempt_count + 1
            )

            return redirect('exam:take_assessment', attempt_id=attempt.id)

    return render(request, 'exam/link_landing.html', {
        'link': link,
        'assessment': assessment,
        'form_errors': form_errors,
        'current_name': request.POST.get('name', request.user.get_full_name() if request.user.is_authenticated else ''),
        'current_email': request.POST.get('email', request.user.email if request.user.is_authenticated else ''),
        'current_emp_id': request.POST.get('employee_id', request.user.employee_id if (request.user.is_authenticated and request.user.employee_id) else ''),
        'current_dept': request.POST.get('department', request.user.department.name if (request.user.is_authenticated and request.user.department) else ''),
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
        AssessmentAttempt.objects.select_related('assessment', 'user', 'user__department').prefetch_related('snapshots__response'),
        id=attempt_id
    )

    is_staff = request.user.is_trainer or request.user.is_assessment_admin or request.user.is_team_lead or request.user.is_super_admin
    if attempt.user != request.user and not is_staff:
        return HttpResponseForbidden("You do not have permission to view this result.")

    certificate = getattr(attempt, 'certificate', None)
    
    can_view_breakdown = is_staff or (
        attempt.assessment.show_result_answers and (
            attempt.assessment.release_results_mode == Assessment.ResultRelease.IMMEDIATE or
            (attempt.assessment.release_results_mode == Assessment.ResultRelease.AFTER_GRADING and attempt.status == AssessmentAttempt.Status.GRADED)
        )
    )

    # ClassMarker-style Category / Domain Performance Breakdown
    category_breakdown = {}
    for snap in attempt.snapshots.select_related('question__category', 'response').all():
        cat_name = snap.question.category.name if (snap.question and snap.question.category) else 'General Domain'
        if cat_name not in category_breakdown:
            category_breakdown[cat_name] = {'possible': Decimal('0.00'), 'earned': Decimal('0.00')}
        category_breakdown[cat_name]['possible'] += snap.marks_allocated
        if hasattr(snap, 'response') and snap.response and snap.response.marks_awarded:
            category_breakdown[cat_name]['earned'] += snap.response.marks_awarded

    for cat_data in category_breakdown.values():
        if cat_data['possible'] > 0:
            cat_data['percentage'] = round((cat_data['earned'] / cat_data['possible']) * 100, 1)
        else:
            cat_data['percentage'] = Decimal('0.00')

    return render(request, 'exam/result.html', {
        'attempt': attempt,
        'assessment': attempt.assessment,
        'certificate': certificate,
        'category_breakdown': category_breakdown,
        'can_view_breakdown': can_view_breakdown,
        'is_staff_view': is_staff and (attempt.user != request.user),
    })
