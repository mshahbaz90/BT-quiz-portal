from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.db import models
from django.core.paginator import Paginator

from assessments.models import (
    Assessment, Question, QuestionOption, AssessmentQuestion,
    Category, QuestionType, Difficulty
)
from assessments.forms import AssessmentForm, QuestionForm
from core.models import AuditLog


@login_required
def assessment_list_view(request):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Trainers and Administrators.")

    status_filter = request.GET.get('status', '')
    query = request.GET.get('q', '').strip()

    assessments = Assessment.objects.select_related('category', 'created_by').prefetch_related('assessment_questions').all()

    if status_filter:
        assessments = assessments.filter(status=status_filter)
    if query:
        assessments = assessments.filter(
            models.Q(title__icontains=query) | models.Q(code__icontains=query)
        )

    paginator = Paginator(assessments, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'assessments/assessment_list.html', {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'statuses': Assessment.Status.choices,
    })


@login_required
def assessment_create_view(request):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Trainers and Administrators.")

    form = AssessmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        assessment = form.save(commit=False)
        assessment.created_by = request.user
        assessment.save()
        form.save_m2m()

        AuditLog.objects.create(
            user=request.user,
            action='ASSESSMENT_CREATED',
            target_model='Assessment',
            target_id=str(assessment.id),
            details={'code': assessment.code, 'title': assessment.title}
        )
        messages.success(request, f"Assessment '{assessment.title}' initialized! Add questions to complete setup.")
        return redirect('assessments:assessment_detail', assessment_id=assessment.id)

    return render(request, 'assessments/assessment_form.html', {
        'form': form,
        'title': 'Create New Assessment'
    })


@login_required
def assessment_edit_view(request, assessment_id):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Trainers and Administrators.")

    assessment = get_object_or_404(Assessment, id=assessment_id)
    form = AssessmentForm(request.POST or None, instance=assessment)

    if request.method == 'POST' and form.is_valid():
        assessment = form.save(commit=False)
        # Increment version when modified
        assessment.version += 1
        assessment.save()
        form.save_m2m()

        AuditLog.objects.create(
            user=request.user,
            action='ASSESSMENT_UPDATED',
            target_model='Assessment',
            target_id=str(assessment.id),
            details={'version': assessment.version}
        )
        messages.success(request, f"Assessment '{assessment.title}' updated (v{assessment.version}).")
        return redirect('assessments:assessment_detail', assessment_id=assessment.id)

    return render(request, 'assessments/assessment_form.html', {
        'form': form,
        'title': f'Edit Assessment: {assessment.title}',
        'assessment': assessment
    })


@login_required
def assessment_detail_view(request, assessment_id):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Trainers and Administrators.")

    assessment = get_object_or_404(
        Assessment.objects.prefetch_related('assessment_questions__question__options'),
        id=assessment_id
    )

    # Question Bank available to add (not yet in this assessment)
    attached_ids = assessment.assessment_questions.values_list('question_id', flat=True)
    available_bank_questions = Question.objects.exclude(id__in=attached_ids)[:30]

    return render(request, 'assessments/assessment_detail.html', {
        'assessment': assessment,
        'available_bank_questions': available_bank_questions,
    })


@login_required
def assessment_add_question_view(request, assessment_id, question_id):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted.")

    assessment = get_object_or_404(Assessment, id=assessment_id)
    question = get_object_or_404(Question, id=question_id)

    if not AssessmentQuestion.objects.filter(assessment=assessment, question=question).exists():
        next_order = assessment.assessment_questions.count() + 1
        AssessmentQuestion.objects.create(
            assessment=assessment,
            question=question,
            order=next_order
        )
        messages.success(request, f"Question #{question.id} added to {assessment.code}.")

    return redirect('assessments:assessment_detail', assessment_id=assessment.id)


@login_required
def assessment_remove_question_view(request, assessment_id, question_id):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted.")

    assessment = get_object_or_404(Assessment, id=assessment_id)
    AssessmentQuestion.objects.filter(assessment=assessment, question_id=question_id).delete()
    messages.info(request, "Question removed from assessment.")
    return redirect('assessments:assessment_detail', assessment_id=assessment.id)


@login_required
def assessment_toggle_publish_view(request, assessment_id):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted.")

    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    if assessment.status != Assessment.Status.PUBLISHED:
        # Validate that assessment has questions
        if assessment.assessment_questions.count() == 0:
            messages.error(request, "Cannot publish an assessment with zero questions! Add at least one question first.")
            return redirect('assessments:assessment_detail', assessment_id=assessment.id)
        
        assessment.status = Assessment.Status.PUBLISHED
        messages.success(request, f"Assessment '{assessment.title}' is now PUBLISHED and available to candidates!")
    else:
        assessment.status = Assessment.Status.DRAFT
        messages.warning(request, f"Assessment '{assessment.title}' has been reverted to DRAFT.")

    assessment.save(update_fields=['status'])
    AuditLog.objects.create(
        user=request.user,
        action='ASSESSMENT_STATUS_TOGGLED',
        target_model='Assessment',
        target_id=str(assessment.id),
        details={'status': assessment.status}
    )
    return redirect('assessments:assessment_detail', assessment_id=assessment.id)


@login_required
def assessment_preview_view(request, assessment_id):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted.")

    assessment = get_object_or_404(
        Assessment.objects.prefetch_related('assessment_questions__question__options'),
        id=assessment_id
    )
    return render(request, 'assessments/assessment_preview.html', {'assessment': assessment})


@login_required
def question_bank_list_view(request):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Trainers and Administrators.")

    type_filter = request.GET.get('type', '')
    diff_filter = request.GET.get('diff', '')
    query = request.GET.get('q', '').strip()

    questions = Question.objects.select_related('category', 'created_by').prefetch_related('options').all()

    if type_filter:
        questions = questions.filter(question_type=type_filter)
    if diff_filter:
        questions = questions.filter(difficulty=diff_filter)
    if query:
        questions = questions.filter(
            models.Q(question_text__icontains=query) | models.Q(tags__icontains=query)
        )

    paginator = Paginator(questions, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'assessments/question_bank.html', {
        'page_obj': page_obj,
        'types': QuestionType.choices,
        'difficulties': Difficulty.choices,
        'type_filter': type_filter,
        'diff_filter': diff_filter,
        'query': query,
    })


@login_required
def question_create_view(request):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted.")

    form = QuestionForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        question = form.save(commit=False)
        question.created_by = request.user
        question.save()

        # Handle options from POST based on type
        q_type = question.question_type
        if q_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_SELECT]:
            option_texts = request.POST.getlist('option_text[]')
            correct_flags = request.POST.getlist('is_correct[]')
            for idx, text in enumerate(option_texts):
                if text.strip():
                    is_corr = str(idx) in correct_flags or ('opt_' + str(idx)) in correct_flags
                    QuestionOption.objects.create(
                        question=question,
                        option_text=text.strip(),
                        is_correct=is_corr,
                        display_order=idx + 1
                    )
        elif q_type in [QuestionType.TRUE_FALSE, QuestionType.YES_NO]:
            correct_val = request.POST.get('binary_correct', 'true')
            opt1_text = "True" if q_type == QuestionType.TRUE_FALSE else "Yes"
            opt2_text = "False" if q_type == QuestionType.TRUE_FALSE else "No"
            QuestionOption.objects.create(question=question, option_text=opt1_text, is_correct=(correct_val == 'true'), display_order=1)
            QuestionOption.objects.create(question=question, option_text=opt2_text, is_correct=(correct_val == 'false'), display_order=2)
        elif q_type == QuestionType.MATCHING:
            prompts = request.POST.getlist('match_prompt[]')
            targets = request.POST.getlist('match_target[]')
            for idx, (p, t) in enumerate(zip(prompts, targets)):
                if p.strip() and t.strip():
                    QuestionOption.objects.create(
                        question=question,
                        option_text=p.strip(),
                        match_target=t.strip(),
                        display_order=idx + 1
                    )
        elif q_type == QuestionType.ORDERING:
            order_items = request.POST.getlist('order_item[]')
            for idx, item in enumerate(order_items):
                if item.strip():
                    QuestionOption.objects.create(
                        question=question,
                        option_text=item.strip(),
                        correct_order=idx + 1,
                        display_order=idx + 1
                    )

        AuditLog.objects.create(
            user=request.user,
            action='QUESTION_CREATED',
            target_model='Question',
            target_id=str(question.id),
            details={'type': question.question_type}
        )
        messages.success(request, f"Question #{question.id} ({question.get_question_type_display()}) saved to bank.")
        return redirect('assessments:question_bank')

    return render(request, 'assessments/question_form.html', {
        'form': form,
        'title': 'Add Question to Bank'
    })


@login_required
def employee_assessment_list_view(request):
    """
    Employee / Candidate view of all accessible assessments, including history.
    """
    assessments = Assessment.objects.filter(status=Assessment.Status.PUBLISHED).prefetch_related('attempts')
    return render(request, 'assessments/employee_list.html', {'assessments': assessments})
