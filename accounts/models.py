from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta


class Role(models.TextChoices):
    SUPER_ADMIN = 'SUPER_ADMIN', 'Super Administrator'
    ASSESSMENT_ADMIN = 'ASSESSMENT_ADMIN', 'Assessment Administrator'
    TRAINER = 'TRAINER', 'Trainer / Learning & Development'
    TEAM_LEAD = 'TEAM_LEAD', 'Team Lead / Supervisor'
    EMPLOYEE = 'EMPLOYEE', 'Employee / Assessment Taker'


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=120)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='teams')
    lead = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='led_teams')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('name', 'department')
        ordering = ['name']
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'

    def __str__(self):
        return f"{self.name} - {self.department.name}"


class User(AbstractUser):
    employee_id = models.CharField(max_length=40, unique=True, null=True, blank=True, db_index=True)
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.EMPLOYEE, db_index=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    groups_assigned = models.ManyToManyField(Team, blank=True, related_name='assigned_group_members')
    designation = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    must_change_password = models.BooleanField(default=False)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['first_name', 'last_name', 'username']
        verbose_name = 'BreakThru User'
        verbose_name_plural = 'BreakThru Users'

    def save(self, *args, **kwargs):
        if self.employee_id is not None:
            cleaned_id = str(self.employee_id).strip()
            self.employee_id = cleaned_id if cleaned_id else None
        super().save(*args, **kwargs)

    def __str__(self):
        emp_tag = f" [{self.employee_id}]" if self.employee_id else ""
        return f"{self.get_full_name() or self.username}{emp_tag}"

    @property
    def department_name(self):
        return self.department.name if self.department else ''


    @property
    def is_super_admin(self):
        return self.role == Role.SUPER_ADMIN or self.is_superuser

    @property
    def is_assessment_admin(self):
        return self.is_super_admin or self.role == Role.ASSESSMENT_ADMIN

    @property
    def is_trainer(self):
        return self.is_assessment_admin or self.role == Role.TRAINER

    @property
    def is_team_lead(self):
        return self.is_trainer or self.role == Role.TEAM_LEAD

    @property
    def is_locked(self):
        if self.lockout_until and timezone.now() < self.lockout_until:
            return True
        return False

    def register_failed_login(self, max_attempts=5, lockout_minutes=15):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.lockout_until = timezone.now() + timedelta(minutes=lockout_minutes)
        self.save(update_fields=['failed_login_attempts', 'lockout_until'])

    def reset_failed_logins(self):
        if self.failed_login_attempts > 0 or self.lockout_until:
            self.failed_login_attempts = 0
            self.lockout_until = None
            self.save(update_fields=['failed_login_attempts', 'lockout_until'])
