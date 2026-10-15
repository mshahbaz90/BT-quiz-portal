import csv
import io
import secrets
import string
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.core.paginator import Paginator

from accounts.models import User, Department, Team, Role
from accounts.forms import (
    LoginForm, ForcePasswordChangeForm, EmployeeCreateForm, EmployeeEditForm,
    BulkEmployeeImportForm, DepartmentForm, TeamForm
)
from core.models import AuditLog


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.cleaned_data['user']
        remember_me = form.cleaned_data.get('remember_me', True)

        login(request, user)
        if not remember_me:
            request.session.set_expiry(0)  # expires upon browser close

        # Audit log login
        AuditLog.objects.create(
            user=user,
            action='LOGIN_SUCCESS',
            target_model='User',
            target_id=str(user.id),
            ip_address=getattr(request, 'client_ip', None),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:250],
            details={'method': 'credentials'}
        )

        messages.success(request, f"Welcome back, {user.first_name or user.username}!")
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('core:dashboard')

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        AuditLog.objects.create(
            user=request.user,
            action='LOGOUT',
            target_model='User',
            target_id=str(request.user.id),
            ip_address=getattr(request, 'client_ip', None),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:250],
        )
    logout(request)
    messages.info(request, "You have been safely signed out.")
    return redirect('accounts:login')


@login_required
def force_change_password_view(request):
    form = ForcePasswordChangeForm(user=request.user, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        new_password = form.cleaned_data['new_password']
        request.user.set_password(new_password)
        request.user.must_change_password = False
        request.user.save(update_fields=['password', 'must_change_password'])
        update_session_auth_hash(request, request.user)

        AuditLog.objects.create(
            user=request.user,
            action='PASSWORD_CHANGED',
            target_model='User',
            target_id=str(request.user.id),
            ip_address=getattr(request, 'client_ip', None),
            details={'forced': True}
        )
        messages.success(request, "Your password has been successfully updated.")
        return redirect('core:dashboard')

    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'user': request.user})


@login_required
def employee_list_view(request):
    if not (request.user.is_super_admin or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Administrators.")

    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '')
    dept_filter = request.GET.get('dept', '')

    employees = User.objects.select_related('department', 'team').all()

    if query:
        employees = employees.filter(
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query) |
            models.Q(username__icontains=query) |
            models.Q(employee_id__icontains=query) |
            models.Q(email__icontains=query)
        )
    if role_filter:
        employees = employees.filter(role=role_filter)
    if dept_filter:
        employees = employees.filter(department_id=dept_filter)

    paginator = Paginator(employees, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    departments = Department.objects.filter(is_active=True)

    return render(request, 'accounts/employee_list.html', {
        'page_obj': page_obj,
        'query': query,
        'role_filter': role_filter,
        'dept_filter': dept_filter,
        'departments': departments,
        'roles': Role.choices,
        'total_count': employees.count(),
    })


@login_required
def employee_create_view(request):
    if not (request.user.is_super_admin or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Administrators.")

    form = EmployeeCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        init_pass = form.cleaned_data.get('initial_password')
        if not init_pass:
            # Generate random temporary password
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            init_pass = ''.join(secrets.choice(alphabet) for _ in range(12))

        user.set_password(init_pass)
        user.must_change_password = form.cleaned_data.get('require_password_change', True)
        user.save()

        AuditLog.objects.create(
            user=request.user,
            action='EMPLOYEE_CREATED',
            target_model='User',
            target_id=str(user.id),
            ip_address=getattr(request, 'client_ip', None),
            details={'username': user.username, 'employee_id': user.employee_id}
        )

        messages.success(request, f"Employee {user.get_full_name() or user.username} created successfully! Temporary password: {init_pass}")
        return redirect('accounts:employee_list')

    return render(request, 'accounts/employee_form.html', {'form': form, 'title': 'Create New Employee', 'is_edit': False})


@login_required
def employee_edit_view(request, user_id):
    if not (request.user.is_super_admin or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Administrators.")

    target_user = get_object_or_404(User, id=user_id)
    if target_user.is_super_admin and not request.user.is_super_admin:
        messages.error(request, "Only Super Administrators can edit Super Administrator accounts.")
        return redirect('accounts:employee_list')

    form = EmployeeEditForm(request.POST or None, instance=target_user)

    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        reset_pass = form.cleaned_data.get('reset_password')
        if reset_pass:
            user.set_password(reset_pass)
            user.must_change_password = True

        user.save()

        AuditLog.objects.create(
            user=request.user,
            action='EMPLOYEE_UPDATED',
            target_model='User',
            target_id=str(user.id),
            ip_address=getattr(request, 'client_ip', None),
            details={'username': user.username, 'employee_id': user.employee_id}
        )

        messages.success(request, f"Employee {user.get_full_name() or user.username} updated successfully!")
        return redirect('accounts:employee_list')

    return render(request, 'accounts/employee_form.html', {
        'form': form,
        'title': f"Edit Employee: {target_user.get_full_name() or target_user.username}",
        'is_edit': True,
        'target_user': target_user
    })


@login_required
def employee_delete_view(request, user_id):
    if not (request.user.is_super_admin or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Administrators.")

    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('accounts:employee_list')

    if target_user.is_super_admin and not request.user.is_super_admin:
        messages.error(request, "Only Super Administrators can delete Super Administrator accounts.")
        return redirect('accounts:employee_list')

    if request.method == 'POST':
        emp_name = target_user.get_full_name() or target_user.username
        emp_id = target_user.employee_id or ''
        target_user.delete()

        AuditLog.objects.create(
            user=request.user,
            action='EMPLOYEE_DELETED',
            target_model='User',
            target_id=str(user_id),
            ip_address=getattr(request, 'client_ip', None),
            details={'name': emp_name, 'employee_id': emp_id}
        )

        messages.success(request, f"Employee account '{emp_name}' was permanently deleted.")
        return redirect('accounts:employee_list')

    attempts_count = target_user.assessment_attempts.count() if hasattr(target_user, 'assessment_attempts') else 0
    certificates_count = target_user.certificates.count() if hasattr(target_user, 'certificates') else 0

    return render(request, 'accounts/employee_confirm_delete.html', {
        'target_user': target_user,
        'attempts_count': attempts_count,
        'certificates_count': certificates_count,
    })


@login_required
def employee_toggle_status_view(request, user_id):
    if not (request.user.is_super_admin or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Administrators.")

    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, "You cannot suspend your own account.")
        return redirect('accounts:employee_list')

    if target_user.is_super_admin and not request.user.is_super_admin:
        messages.error(request, "Only Super Administrators can modify Super Administrator accounts.")
        return redirect('accounts:employee_list')

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=['is_active'])

    AuditLog.objects.create(
        user=request.user,
        action='EMPLOYEE_STATUS_CHANGED',
        target_model='User',
        target_id=str(target_user.id),
        ip_address=getattr(request, 'client_ip', None),
        details={'is_active': target_user.is_active}
    )

    state_str = "reactivated" if target_user.is_active else "suspended"
    messages.success(request, f"Employee {target_user.username} has been {state_str}.")
    return redirect('accounts:employee_list')


@login_required
def bulk_import_employees_view(request):
    if not (request.user.is_super_admin or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Administrators.")

    form = BulkEmployeeImportForm(request.POST or None, request.FILES or None)
    results = None

    if request.method == 'POST' and form.is_valid():
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded_file))

        success_count = 0
        errors = []
        row_num = 1

        for row in reader:
            row_num += 1
            emp_id = row.get('employee_id', '').strip()
            username = row.get('username', '').strip()
            email = row.get('email', '').strip()
            first_name = row.get('first_name', '').strip()
            last_name = row.get('last_name', '').strip()
            designation = row.get('designation', '').strip()
            dept_code = row.get('department_code', '').strip()
            role_str = row.get('role', 'EMPLOYEE').strip()

            if not username or not emp_id:
                errors.append(f"Row {row_num}: Username and Employee ID are required.")
                continue

            if User.objects.filter(username__iexact=username).exists():
                errors.append(f"Row {row_num}: Username '{username}' already exists.")
                continue

            if User.objects.filter(employee_id__iexact=emp_id).exists():
                errors.append(f"Row {row_num}: Employee ID '{emp_id}' already exists.")
                continue

            dept = None
            if dept_code:
                dept = Department.objects.filter(code__iexact=dept_code).first()

            role = Role.EMPLOYEE
            if role_str in Role.values:
                role = role_str

            # Create employee with default temporary password
            temp_pass = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
            new_user = User.objects.create_user(
                username=username,
                email=email,
                password=temp_pass,
                employee_id=emp_id,
                first_name=first_name,
                last_name=last_name,
                designation=designation,
                department=dept,
                role=role,
                must_change_password=True
            )
            success_count += 1

        results = {'success_count': success_count, 'errors': errors}
        AuditLog.objects.create(
            user=request.user,
            action='BULK_EMPLOYEE_IMPORT',
            target_model='User',
            target_id='bulk',
            ip_address=getattr(request, 'client_ip', None),
            details={'success_count': success_count, 'error_count': len(errors)}
        )
        if success_count > 0:
            messages.success(request, f"Successfully imported {success_count} employee accounts.")

    return render(request, 'accounts/bulk_import.html', {'form': form, 'results': results})


@login_required
def export_employees_csv_view(request):
    if not (request.user.is_super_admin or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Administrators.")

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="breakthru_employees.csv"'

    writer = csv.writer(response)
    writer.writerow(['Employee ID', 'Username', 'Full Name', 'Email', 'Role', 'Department', 'Designation', 'Status', 'Date Joined'])

    for u in User.objects.select_related('department').all():
        writer.writerow([
            u.employee_id or '',
            u.username,
            u.get_full_name(),
            u.email,
            u.get_role_display(),
            u.department.name if u.department else '',
            u.designation,
            'Active' if u.is_active else 'Suspended',
            u.date_joined.strftime('%Y-%m-%d')
        ])

    return response


@login_required
def department_list_view(request):
    if not (request.user.is_super_admin or request.user.is_assessment_admin):
        return HttpResponseForbidden("Access restricted to Administrators.")

    departments = Department.objects.prefetch_related('members', 'teams').all()
    form = DepartmentForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        dept = form.save()
        messages.success(request, f"Department '{dept.name}' created successfully.")
        return redirect('accounts:department_list')

    return render(request, 'accounts/department_list.html', {'departments': departments, 'form': form})


@login_required
def team_list_view(request):
    if not (request.user.is_trainer or request.user.is_assessment_admin or request.user.is_super_admin):
        return HttpResponseForbidden("Access restricted to Administrators and Trainers.")

    form = TeamForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        team = form.save()
        AuditLog.objects.create(
            user=request.user,
            action='TEAM_CREATED',
            target_model='Team',
            target_id=str(team.id),
            details={'name': team.name, 'department': team.department.name}
        )
        messages.success(request, f"Group / Team '{team.name}' created successfully.")
        return redirect('accounts:team_list')

    teams = Team.objects.select_related('department', 'lead').prefetch_related('members', 'assigned_group_members', 'assigned_assessments').all()

    return render(request, 'accounts/team_list.html', {
        'teams': teams,
        'form': form,
    })


@login_required
def team_detail_view(request, team_id):
    if not (request.user.is_trainer or request.user.is_assessment_admin or request.user.is_super_admin):
        return HttpResponseForbidden("Access restricted.")

    team = get_object_or_404(Team.objects.select_related('department', 'lead').prefetch_related('assigned_assessments'), id=team_id)
    
    # Combined members (primary team OR assigned groups)
    members = User.objects.filter(models.Q(team=team) | models.Q(groups_assigned=team)).distinct().order_by('first_name', 'last_name')

    # Handle member actions
    if request.method == 'POST':
        action = request.POST.get('action')
        target_user_id = request.POST.get('user_id')
        if target_user_id:
            target_user = get_object_or_404(User, id=target_user_id)
            if action == 'add_member':
                target_user.groups_assigned.add(team)
                messages.success(request, f"Added {target_user.get_full_name() or target_user.username} to {team.name}.")
            elif action == 'remove_member':
                target_user.groups_assigned.remove(team)
                if target_user.team == team:
                    target_user.team = None
                    target_user.save(update_fields=['team'])
                messages.info(request, f"Removed {target_user.get_full_name() or target_user.username} from {team.name}.")
            return redirect('accounts:team_detail', team_id=team.id)

    # Assessments assigned to this group
    assigned_assessments = team.assigned_assessments.all()

    # Calculate group performance metrics
    from exam.models import AssessmentAttempt
    group_attempts = AssessmentAttempt.objects.filter(
        user__in=members,
        assessment__in=assigned_assessments
    ) if assigned_assessments.exists() else AssessmentAttempt.objects.none()

    total_attempts = group_attempts.count()
    graded_attempts = group_attempts.filter(status=AssessmentAttempt.Status.GRADED)
    passed_attempts = graded_attempts.filter(is_passed=True).count()
    pass_rate = round((passed_attempts / graded_attempts.count() * 100), 1) if graded_attempts.exists() else 0
    avg_score = graded_attempts.aggregate(models.Avg('percentage'))['percentage__avg']
    avg_score = round(avg_score, 1) if avg_score else 0

    # Non-members available to add
    available_users = User.objects.exclude(id__in=members.values_list('id', flat=True)).filter(is_active=True).order_by('first_name', 'last_name')[:100]

    return render(request, 'accounts/team_detail.html', {
        'team': team,
        'members': members,
        'assigned_assessments': assigned_assessments,
        'total_attempts': total_attempts,
        'pass_rate': pass_rate,
        'avg_score': avg_score,
        'available_users': available_users,
    })
