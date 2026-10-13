from django import forms
from assessments.models import Assessment, Question, QuestionOption, Category, QuestionType, Difficulty
from accounts.models import Department


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = [
            'title', 'code', 'category', 'status', 'duration_minutes',
            'pass_mark_percentage', 'max_attempts', 'shuffle_questions',
            'shuffle_options', 'allow_backtracking', 'negative_marking',
            'negative_mark_penalty', 'release_results_mode', 'show_explanations_to_user',
            'random_pool_count', 'assigned_departments', 'description', 'instructions'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Python Backend Proficiency Assessment'}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. BT-TECH-01'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-input', 'min': 1}),
            'pass_mark_percentage': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.5', 'min': 0, 'max': 100}),
            'max_attempts': forms.NumberInput(attrs={'class': 'form-input', 'min': 1}),
            'negative_mark_penalty': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.05', 'min': 0}),
            'random_pool_count': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'release_results_mode': forms.Select(attrs={'class': 'form-select'}),
            'assigned_departments': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 4}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'instructions': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
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
