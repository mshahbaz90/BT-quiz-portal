from django import forms
from assessments.models import Assessment, AssessmentLink, Question, QuestionOption, Category, QuestionType, Difficulty
from accounts.models import Department


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = [
            'title', 'code', 'category', 'status', 'duration_minutes',
            'pass_mark_percentage', 'max_attempts', 'retake_cooldown_hours',
            'questions_per_page', 'allow_save_and_resume', 'access_code',
            'shuffle_questions', 'shuffle_options', 'allow_backtracking',
            'negative_marking', 'negative_mark_penalty', 'release_results_mode',
            'show_result_score', 'show_result_answers', 'show_explanations_to_user',
            'certificate_enabled', 'random_pool_count', 'assigned_departments',
            'assigned_teams', 'pass_message', 'fail_message', 'description', 'instructions'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Python Backend Proficiency Assessment'}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. BT-TECH-01'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'placeholder': 'Minutes (0 for unlimited)'}),
            'pass_mark_percentage': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.5', 'min': 0, 'max': 100}),
            'max_attempts': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'placeholder': '0 for unlimited retakes'}),
            'retake_cooldown_hours': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'placeholder': 'Hours to wait before retake'}),
            'questions_per_page': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'placeholder': '1 for one-at-a-time, 0 for all-in-one'}),
            'access_code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Optional password/PIN for access'}),
            'negative_mark_penalty': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.05', 'min': 0}),
            'random_pool_count': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'placeholder': '0 uses all attached questions'}),
            'release_results_mode': forms.Select(attrs={'class': 'form-select'}),
            'assigned_departments': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 4}),
            'assigned_teams': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 4}),
            'pass_message': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Custom message displayed upon passing'}),
            'fail_message': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Custom message displayed upon failing'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'instructions': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in [
            'category', 'questions_per_page', 'retake_cooldown_hours', 'access_code',
            'pass_message', 'fail_message', 'description', 'instructions',
            'assigned_departments', 'assigned_teams'
        ]:
            if f in self.fields:
                self.fields[f].required = False


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Category Name (e.g. Core Engineering)'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Optional category description'}),
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            'category', 'question_type', 'question_text', 'rich_content',
            'image', 'default_marks', 'difficulty', 'explanation', 'hint',
            'tags', 'numeric_answer', 'numeric_tolerance', 'short_answer_accepted'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'question_type': forms.Select(attrs={'class': 'form-select', 'id': 'question-type-select'}),
            'question_text': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Enter the question stem...'}),
            'rich_content': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Optional code block, Markdown table, or case scenario.'}),
            'default_marks': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.5', 'min': 0.5}),
            'difficulty': forms.Select(attrs={'class': 'form-select'}),
            'explanation': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Explanation displayed once results are released.'}),
            'hint': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Optional hint available during test'}),
            'tags': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Comma-separated keywords (e.g. Django, ORM, SQL)'}),
            'numeric_answer': forms.NumberInput(attrs={'class': 'form-input', 'step': 'any'}),
            'numeric_tolerance': forms.NumberInput(attrs={'class': 'form-input', 'step': 'any'}),
            'short_answer_accepted': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Pipe-separated answers (e.g. SQL|Structured Query Language)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in [
            'category', 'rich_content', 'explanation', 'hint', 'tags',
            'numeric_answer', 'numeric_tolerance', 'short_answer_accepted', 'image'
        ]:
            if f in self.fields:
                self.fields[f].required = False


class AssessmentLinkForm(forms.ModelForm):
    class Meta:
        model = AssessmentLink
        fields = [
            'name', 'assessment', 'access_code', 'allowed_email_domains',
            'require_employee_id', 'collect_name', 'collect_email', 'collect_department',
            'max_completions', 'max_attempts_per_user', 'start_date', 'end_date', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Q4 Campus Recruitment / External Candidate Link'
            }),
            'assessment': forms.Select(attrs={'class': 'form-select'}),
            'access_code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Optional Link Password / PIN'
            }),
            'allowed_email_domains': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. @breakthru.com, @techcorp.pk (leave blank for any)'
            }),
            'max_completions': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 0,
                'placeholder': '0 for unlimited total respondents'
            }),
            'max_attempts_per_user': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 1,
                'placeholder': '1'
            }),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-input',
                'type': 'datetime-local'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-input',
                'type': 'datetime-local'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ['access_code', 'allowed_email_domains', 'start_date', 'end_date']:
            if f in self.fields:
                self.fields[f].required = False
