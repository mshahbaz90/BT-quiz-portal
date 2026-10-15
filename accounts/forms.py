from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from accounts.models import User, Department, Team, Role


class LoginForm(forms.Form):
    username = forms.CharField(
        label="Username or Employee ID",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your username or Employee ID',
            'autocomplete': 'username',
            'autofocus': True,
            'id': 'login-identifier',
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
            'id': 'login-password',
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'id': 'remember-me-checkbox'})
    )

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if identifier and password:
            # Check if identifier matches employee_id or username
            user_candidate = User.objects.filter(employee_id__iexact=identifier).first() or \
                             User.objects.filter(username__iexact=identifier).first()
            
            if user_candidate:
                if user_candidate.is_locked:
                    raise forms.ValidationError("Account is temporarily locked due to multiple failed login attempts. Please try again later or contact your administrator.")
                if not user_candidate.is_active:
                    raise forms.ValidationError("This account has been deactivated. Please contact HR or your system administrator.")
                
                user = authenticate(username=user_candidate.username, password=password)
                if user is None:
                    user_candidate.register_failed_login()
                    remaining = max(0, 5 - user_candidate.failed_login_attempts)
                    if remaining > 0:
                        raise forms.ValidationError(f"Invalid credentials. You have {remaining} attempt(s) remaining before temporary lockout.")
                    else:
                        raise forms.ValidationError("Account has been locked due to 5 consecutive failed login attempts.")
                else:
                    user_candidate.reset_failed_logins()
                    cleaned_data['user'] = user
            else:
                raise forms.ValidationError("Invalid credentials. Please check your username/employee ID and password.")

        return cleaned_data


class ForcePasswordChangeForm(forms.Form):
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'id': 'new-password'}),
        help_text="Must be at least 8 characters long."
    )
    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'id': 'confirm-password'})
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password')
        p2 = cleaned_data.get('confirm_password')

        if p1 and p2:
            if p1 != p2:
                raise forms.ValidationError("Passwords do not match.")
            validate_password(p1, self.user)
        return cleaned_data


class EmployeeCreateForm(forms.ModelForm):
    initial_password = forms.CharField(
        required=False,
        label="Initial Password",
        help_text="Leave blank to generate a secure temporary password.",
        widget=forms.PasswordInput(attrs={'class': 'form-input'})
    )
    require_password_change = forms.BooleanField(
        required=False,
        initial=True,
        label="Require password change on first sign in"
    )

    class Meta:
        model = User
        fields = [
            'username', 'employee_id', 'first_name', 'last_name',
            'email', 'role', 'department', 'designation', 'phone'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. BT-1042'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'designation': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.filter(is_active=True).order_by('name')
        self.fields['department'].empty_label = "- Select an option -"


class BulkEmployeeImportForm(forms.Form):
    csv_file = forms.FileField(
        label="Employee CSV File",
        help_text="Upload a CSV file containing columns: employee_id, username, email, first_name, last_name, designation, department_code, role"
    )


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'code', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. ENG, HR, MKT'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'department', 'lead', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'lead': forms.Select(attrs={'class': 'form-select'}),
        }
