import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponseBadRequest, HttpResponse
from django.db import models
from django.core.paginator import Paginator

from assessments.models import (
    Assessment, AssessmentLink, Question, QuestionOption, AssessmentQuestion,
    Category, QuestionType, Difficulty
)
from assessments.forms import AssessmentForm, QuestionForm, CategoryForm, AssessmentLinkForm
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

    # Assessment Links created for this assessment
    links = assessment.links.prefetch_related('link_attempts').all()

    return render(request, 'assessments/assessment_detail.html', {
        'assessment': assessment,
        'available_bank_questions': available_bank_questions,
        'links': links,
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
    user = request.user
    assessments = Assessment.objects.filter(
        status=Assessment.Status.PUBLISHED,
        is_archived=False
    ).prefetch_related('attempts')
    
    # Filter by user's department or team eligibility if not superadmin
    if not (user.is_super_admin or user.is_trainer):
        assessments = assessments.filter(
            models.Q(assigned_departments__isnull=True, assigned_teams__isnull=True) |
            models.Q(assigned_departments=user.department) |
            models.Q(assigned_teams=user.team) |
            models.Q(assigned_teams__in=user.groups_assigned.all())
        ).distinct()

    return render(request, 'assessments/employee_list.html', {'assessments': assessments})


# ==============================================================================
# Categories Management
# ==============================================================================

@login_required
def category_list_view(request):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted.")

    form = CategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cat = form.save()
        AuditLog.objects.create(
            user=request.user,
            action='CATEGORY_CREATED',
            target_model='Category',
            target_id=str(cat.id),
            details={'name': cat.name}
        )
        messages.success(request, f"Category '{cat.name}' created successfully!")
        return redirect('assessments:category_list')

    categories = Category.objects.annotate(
        questions_count=models.Count('questions', distinct=True),
        assessments_count=models.Count('assessments', distinct=True)
    ).all()

    return render(request, 'assessments/category_list.html', {
        'categories': categories,
        'form': form
    })


@login_required
def category_delete_view(request, category_id):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted.")

    category = get_object_or_404(Category, id=category_id)
    name = category.name
    category.delete()

    AuditLog.objects.create(
        user=request.user,
        action='CATEGORY_DELETED',
        target_model='Category',
        target_id=str(category_id),
        details={'name': name}
    )
    messages.info(request, f"Category '{name}' deleted.")
    return redirect('assessments:category_list')


# ==============================================================================
# Assessment Lifecycle: Duplicate & Archive
# ==============================================================================

@login_required
def assessment_duplicate_view(request, assessment_id):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted.")

    original = get_object_or_404(Assessment, id=assessment_id)
    
    # Create clone
    import uuid
    short_uid = str(uuid.uuid4())[:4].upper()
    new_code = f"{original.code}-COPY-{short_uid}"[:40]
    new_title = f"{original.title} (Copy)"[:200]
    
    clone = Assessment.objects.create(
        title=new_title,
        code=new_code,
        description=original.description,
        instructions=original.instructions,
        category=original.category,
        status=Assessment.Status.DRAFT,
        version=1,
        duration_minutes=original.duration_minutes,
        pass_mark_percentage=original.pass_mark_percentage,
        max_attempts=original.max_attempts,
        retake_cooldown_hours=original.retake_cooldown_hours,
        questions_per_page=original.questions_per_page,
        allow_save_and_resume=original.allow_save_and_resume,
        pass_message=original.pass_message,
        fail_message=original.fail_message,
        access_code=original.access_code,
        shuffle_questions=original.shuffle_questions,
        shuffle_options=original.shuffle_options,
        allow_backtracking=original.allow_backtracking,
        negative_marking=original.negative_marking,
        negative_mark_penalty=original.negative_mark_penalty,
        release_results_mode=original.release_results_mode,
        show_result_score=original.show_result_score,
        show_result_answers=original.show_result_answers,
        show_explanations_to_user=original.show_explanations_to_user,
        certificate_enabled=original.certificate_enabled,
        random_pool_count=original.random_pool_count,
        created_by=request.user
    )
    clone.assigned_departments.set(original.assigned_departments.all())
    clone.assigned_teams.set(original.assigned_teams.all())

    # Clone attached questions
    for aq in original.assessment_questions.all():
        AssessmentQuestion.objects.create(
            assessment=clone,
            question=aq.question,
            order=aq.order,
            marks_override=aq.marks_override
        )

    AuditLog.objects.create(
        user=request.user,
        action='ASSESSMENT_DUPLICATED',
        target_model='Assessment',
        target_id=str(clone.id),
        details={'original_id': original.id, 'new_code': clone.code}
    )
    messages.success(request, f"Assessment duplicated as '{clone.title}' ({clone.code}) in Draft status.")
    return redirect('assessments:assessment_detail', assessment_id=clone.id)


@login_required
def assessment_archive_view(request, assessment_id):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted.")

    assessment = get_object_or_404(Assessment, id=assessment_id)
    assessment.is_archived = not assessment.is_archived
    assessment.save(update_fields=['is_archived'])

    action = "archived" if assessment.is_archived else "restored from archive"
    messages.info(request, f"Assessment '{assessment.title}' has been {action}.")
    return redirect('assessments:assessment_list')


# ==============================================================================
# Question Bank: Duplicate, Export CSV, Import CSV
# ==============================================================================

@login_required
def question_duplicate_view(request, question_id):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted.")

    original = get_object_or_404(Question, id=question_id)
    
    # Clone question
    clone = Question.objects.create(
        category=original.category,
        question_type=original.question_type,
        question_text=f"{original.question_text} (Copy)",
        rich_content=original.rich_content,
        default_marks=original.default_marks,
        difficulty=original.difficulty,
        explanation=original.explanation,
        hint=original.hint,
        tags=original.tags,
        numeric_answer=original.numeric_answer,
        numeric_tolerance=original.numeric_tolerance,
        short_answer_accepted=original.short_answer_accepted,
        created_by=request.user
    )

    # Clone options
    for opt in original.options.all():
        QuestionOption.objects.create(
            question=clone,
            option_text=opt.option_text,
            is_correct=opt.is_correct,
            match_target=opt.match_target,
            correct_order=opt.correct_order,
            display_order=opt.display_order
        )

    AuditLog.objects.create(
        user=request.user,
        action='QUESTION_DUPLICATED',
        target_model='Question',
        target_id=str(clone.id),
        details={'original_id': original.id}
    )
    messages.success(request, f"Question #{clone.id} duplicated successfully.")
    return redirect('assessments:question_bank')


@login_required
def question_export_csv_view(request):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted.")

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="breakthru_questions_bank.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Type', 'Question Text', 'Category', 'Difficulty',
        'Default Marks', 'Hint', 'Explanation', 'Tags', 'Options_Pipe_Separated'
    ])

    for q in Question.objects.select_related('category').prefetch_related('options').all():
        # Encode options for export
        options_encoded = " | ".join([
            f"{opt.option_text} [correct={opt.is_correct}]" for opt in q.options.all()
        ]) if q.options.exists() else q.short_answer_accepted

        writer.writerow([
            q.id,
            q.question_type,
            q.question_text,
            q.category.name if q.category else 'General',
            q.difficulty,
            q.default_marks,
            q.hint,
            q.explanation,
            q.tags,
            options_encoded
        ])

    return response


@login_required
def question_import_csv_view(request):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted.")

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Invalid file format. Please upload a standard CSV (.csv) file.")
            return redirect('assessments:question_bank')

        try:
            decoded_file = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded_file))
            imported_count = 0

            for row in reader:
                q_text = row.get('Question Text') or row.get('question_text')
                if not q_text:
                    continue

                q_type = (row.get('Type') or row.get('question_type') or 'SINGLE_CHOICE').strip().upper()
                if q_type not in QuestionType.values:
                    q_type = QuestionType.SINGLE_CHOICE

                cat_name = (row.get('Category') or row.get('category') or 'General').strip()
                cat, _ = Category.objects.get_or_create(name=cat_name)

                diff = (row.get('Difficulty') or row.get('difficulty') or 'MEDIUM').strip().upper()
                if diff not in Difficulty.values:
                    diff = Difficulty.MEDIUM

                marks = row.get('Default Marks') or row.get('default_marks') or '1.0'
                try:
                    marks = float(marks)
                except ValueError:
                    marks = 1.0

                question = Question.objects.create(
                    category=cat,
                    question_type=q_type,
                    question_text=q_text.strip(),
                    default_marks=marks,
                    difficulty=diff,
                    hint=(row.get('Hint') or '').strip(),
                    explanation=(row.get('Explanation') or '').strip(),
                    tags=(row.get('Tags') or '').strip(),
                    created_by=request.user
                )

                # Parse options if provided
                raw_opts = row.get('Options_Pipe_Separated') or row.get('options') or ''
                if raw_opts:
                    parts = raw_opts.split('|')
                    for idx, part in enumerate(parts):
                        part = part.strip()
                        if not part:
                            continue
                        is_corr = '[correct=True]' in part or '[correct=true]' in part
                        clean_opt = part.replace('[correct=True]', '').replace('[correct=true]', '').replace('[correct=False]', '').replace('[correct=false]', '').strip()
                        if clean_opt:
                            QuestionOption.objects.create(
                                question=question,
                                option_text=clean_opt,
                                is_correct=is_corr,
                                display_order=idx + 1
                            )

                imported_count += 1

            AuditLog.objects.create(
                user=request.user,
                action='QUESTIONS_BULK_IMPORTED',
                target_model='Question',
                target_id='bulk',
                details={'count': imported_count}
            )
            messages.success(request, f"Successfully imported {imported_count} questions into the Question Bank!")
        except Exception as e:
            messages.error(request, f"CSV Import failed: {str(e)}")

        return redirect('assessments:question_bank')

    return redirect('assessments:question_bank')


# -------------------------------------------------------------
# Assessment Links (ClassMarker-Style Direct Test Delivery Links)
# -------------------------------------------------------------

@login_required
def assessment_link_list_view(request):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Trainers and Administrators.")

    query = request.GET.get('q', '').strip()
    assessment_id = request.GET.get('assessment_id', '').strip()
    status_filter = request.GET.get('status', '').strip()

    links = AssessmentLink.objects.select_related('assessment', 'created_by').prefetch_related('link_attempts').all()

    if query:
        links = links.filter(
            models.Q(name__icontains=query) | models.Q(link_code__icontains=query) | models.Q(assessment__title__icontains=query)
        )
    if assessment_id:
        links = links.filter(assessment_id=assessment_id)
    if status_filter == 'active':
        links = links.filter(is_active=True)
    elif status_filter == 'inactive':
        links = links.filter(is_active=False)

    paginator = Paginator(links, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    assessments = Assessment.objects.filter(is_archived=False).order_by('title')

    return render(request, 'assessments/link_list.html', {
        'page_obj': page_obj,
        'assessments': assessments,
        'query': query,
        'selected_assessment': assessment_id,
        'status_filter': status_filter,
    })


@login_required
def assessment_link_create_view(request):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Trainers and Administrators.")

    initial = {}
    selected_assessment_id = request.GET.get('assessment')
    if selected_assessment_id:
        initial['assessment'] = selected_assessment_id

    form = AssessmentLinkForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        link = form.save(commit=False)
        link.created_by = request.user
        link.save()

        AuditLog.objects.create(
            user=request.user,
            action='ASSESSMENT_LINK_CREATED',
            target_model='AssessmentLink',
            target_id=str(link.id),
            details={'link_code': link.link_code, 'name': link.name, 'assessment': link.assessment.code}
        )
        messages.success(request, f"Assessment link '{link.name}' successfully created!")
        return redirect('assessments:link_detail', link_id=link.id)

    return render(request, 'assessments/link_form.html', {
        'form': form,
        'title': 'Generate Assessment Link (ClassMarker Style)',
        'button_text': 'Generate Direct Link',
    })


@login_required
def assessment_link_detail_view(request, link_id):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Trainers and Administrators.")

    link = get_object_or_404(
        AssessmentLink.objects.select_related('assessment', 'created_by'),
        id=link_id
    )

    attempts = link.link_attempts.select_related('user').order_by('-started_at')
    total_attempts = attempts.count()
    completed_attempts = attempts.filter(status__in=['SUBMITTED', 'GRADED'])
    passed_attempts = completed_attempts.filter(is_passed=True).count()
    failed_attempts = completed_attempts.filter(is_passed=False).count()
    
    avg_score = None
    if completed_attempts.exists():
        avg_score = round(completed_attempts.aggregate(models.Avg('percentage'))['percentage__avg'] or 0, 1)

    return render(request, 'assessments/link_detail.html', {
        'link': link,
        'attempts': attempts[:50],
        'total_attempts': total_attempts,
        'completed_count': completed_attempts.count(),
        'passed_count': passed_attempts,
        'failed_count': failed_attempts,
        'avg_score': avg_score,
    })


@login_required
def assessment_link_edit_view(request, link_id):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted.")

    link = get_object_or_404(AssessmentLink, id=link_id)
    form = AssessmentLinkForm(request.POST or None, instance=link)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Assessment link '{link.name}' updated successfully.")
        return redirect('assessments:link_detail', link_id=link.id)

    return render(request, 'assessments/link_form.html', {
        'form': form,
        'title': f'Edit Link: {link.name}',
        'link': link,
        'button_text': 'Save Link Settings',
    })


@login_required
def assessment_link_toggle_view(request, link_id):
    if not (request.user.is_trainer or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted.")

    link = get_object_or_404(AssessmentLink, id=link_id)
    if request.method == 'POST':
        link.is_active = not link.is_active
        link.save(update_fields=['is_active'])
        status_str = "Activated" if link.is_active else "Paused"
        messages.success(request, f"Assessment link '{link.name}' is now {status_str}.")

    return redirect('assessments:link_detail', link_id=link.id)


@login_required
def assessment_link_delete_view(request, link_id):
    if not (request.user.is_assessment_admin or request.user.is_super_admin):
        return HttpResponseForbidden("Only Administrators can delete assessment links.")

    link = get_object_or_404(AssessmentLink, id=link_id)
    if request.method == 'POST':
        name = link.name
        link.delete()
        messages.success(request, f"Assessment link '{name}' has been deleted.")
        return redirect('assessments:link_list')

    return render(request, 'assessments/link_confirm_delete.html', {'link': link})
