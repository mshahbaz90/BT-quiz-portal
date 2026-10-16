import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


class QuestionType(models.TextChoices):
    SINGLE_CHOICE = 'SINGLE_CHOICE', 'Single-Choice Multiple Choice'
    MULTIPLE_SELECT = 'MULTIPLE_SELECT', 'Multiple-Select'
    TRUE_FALSE = 'TRUE_FALSE', 'True / False'
    YES_NO = 'YES_NO', 'Yes / No'
    SHORT_ANSWER = 'SHORT_ANSWER', 'Short Answer'
    LONG_ANSWER = 'LONG_ANSWER', 'Long Answer / Essay'
    FILL_BLANK = 'FILL_BLANK', 'Fill in the Blank'
    MATCHING = 'MATCHING', 'Matching Pairs'
    ORDERING = 'ORDERING', 'Ordering / Sequencing'
    NUMERIC = 'NUMERIC', 'Numeric with Tolerance'
    SURVEY = 'SURVEY', 'Survey (Ungraded Feedback)'
    RICH_CONTENT = 'RICH_CONTENT', 'Formatted Text / Media / Case Study'
    EXPLANATION_HINT = 'EXPLANATION_HINT', 'Question with Hint & Explanation'


class Difficulty(models.TextChoices):
    EASY = 'EASY', 'Easy'
    MEDIUM = 'MEDIUM', 'Medium'
    HARD = 'HARD', 'Hard'


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Assessment(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PUBLISHED = 'PUBLISHED', 'Published'
        ARCHIVED = 'ARCHIVED', 'Archived'

    class ResultRelease(models.TextChoices):
        IMMEDIATE = 'IMMEDIATE', 'Immediately on Submission'
        AFTER_CLOSE = 'AFTER_CLOSE', 'After Assessment Close Date'
        MANUAL = 'MANUAL', 'When Released by Administrator'

    title = models.CharField(max_length=200)
    code = models.CharField(max_length=40, unique=True, help_text="e.g. BT-ENG-001")
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True, default="Please read every question carefully before answering.")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='assessments')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    version = models.PositiveIntegerField(default=1)

    duration_minutes = models.PositiveIntegerField(default=30, help_text="Time allowed in minutes (0 for unlimited)")
    pass_mark_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=70.00)
    max_attempts = models.PositiveIntegerField(default=1, help_text="Number of retakes allowed (0 for unlimited)")
    
    shuffle_questions = models.BooleanField(default=True)
    shuffle_options = models.BooleanField(default=True)
    allow_backtracking = models.BooleanField(default=True, help_text="Allow candidate to return to previous questions")
    
    negative_marking = models.BooleanField(default=False)
    negative_mark_penalty = models.DecimalField(max_digits=4, decimal_places=2, default=0.25)
    
    release_results_mode = models.CharField(max_length=20, choices=ResultRelease.choices, default=ResultRelease.IMMEDIATE)
    show_explanations_to_user = models.BooleanField(default=True)

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    
    random_pool_count = models.PositiveIntegerField(default=0, help_text="Draw N random questions from attached pool. 0 uses all attached questions.")
    
    # ClassMarker-style Advanced Assessment Settings
    questions_per_page = models.PositiveIntegerField(default=1, blank=True, help_text="1 for one-question-at-a-time, 0 for all on one page")
    allow_save_and_resume = models.BooleanField(default=True, blank=True, help_text="Allow candidate to save answers and resume within duration")
    pass_message = models.TextField(blank=True, default="Congratulations! You have successfully passed the assessment.")
    fail_message = models.TextField(blank=True, default="Unfortunately, you did not meet the passing score for this assessment. Please review the material and try again if permitted.")
    access_code = models.CharField(max_length=50, blank=True, help_text="Optional password / PIN required to start this assessment")
    retake_cooldown_hours = models.PositiveIntegerField(default=0, blank=True, help_text="Minimum hours to wait between attempts")
    certificate_enabled = models.BooleanField(default=True, blank=True, help_text="Issue certificate upon passing")
    show_result_score = models.BooleanField(default=True, blank=True, help_text="Show score and percentage on submission")
    show_result_answers = models.BooleanField(default=True, blank=True, help_text="Show question-by-question breakdown and correct answers when released")
    is_archived = models.BooleanField(default=False, blank=True, db_index=True)
    
    # Eligibility scope (assigned departments or teams)
    assigned_departments = models.ManyToManyField('accounts.Department', blank=True, related_name='assigned_assessments')
    assigned_teams = models.ManyToManyField('accounts.Team', blank=True, related_name='assigned_assessments')

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_assessments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.code}-{self.title}")
            self.slug = base_slug[:220]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.title} (v{self.version})"

    @property
    def total_marks(self):
        total = sum(item.effective_marks for item in self.assessment_questions.all())
        return total or 0


class AssessmentLink(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='links')
    name = models.CharField(max_length=150, help_text="e.g. Q1 Graduate Recruitment Link")
    link_code = models.CharField(max_length=32, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)

    # Access Protection & PIN
    access_code = models.CharField(max_length=50, blank=True, help_text="Optional password / PIN required to open this link")
    allowed_email_domains = models.CharField(max_length=255, blank=True, help_text="Comma-separated allowed domains, e.g. @breakthru.pk")

    # Participant Details to Collect
    require_employee_id = models.BooleanField(default=True, help_text="Require Employee ID / Roll number")
    collect_name = models.BooleanField(default=True, help_text="Collect Candidate Name")
    collect_email = models.BooleanField(default=True, help_text="Collect Candidate Email")
    collect_department = models.BooleanField(default=False, help_text="Collect Candidate Department")

    # Limits & Scheduling
    max_completions = models.PositiveIntegerField(default=0, help_text="0 for unlimited total participants")
    max_attempts_per_user = models.PositiveIntegerField(default=1, help_text="Max attempts per candidate")
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_links')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.link_code:
            self.link_code = str(uuid.uuid4()).replace('-', '')[:10].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.link_code}) - {self.assessment.code}"

    def check_availability(self):
        now = timezone.now()
        if not self.is_active:
            return False, "This assessment link has been paused by the administrator."
        if self.start_date and now < self.start_date:
            return False, f"This assessment link is not open yet. It opens on {self.start_date.strftime('%Y-%m-%d %H:%M')}."
        if self.end_date and now > self.end_date:
            return False, f"This assessment link expired on {self.end_date.strftime('%Y-%m-%d %H:%M')}."
        if self.max_completions > 0 and self.link_attempts.count() >= self.max_completions:
            return False, "This assessment link has reached its maximum participant capacity."
        return True, ""


class Question(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')
    question_type = models.CharField(max_length=30, choices=QuestionType.choices, default=QuestionType.SINGLE_CHOICE, db_index=True)
    question_text = models.TextField()
    rich_content = models.TextField(blank=True, help_text="HTML or Markdown for code snippets, tables, or case studies")
    image = models.ImageField(upload_to='questions/', blank=True, null=True)
    
    default_marks = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    difficulty = models.CharField(max_length=20, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    
    explanation = models.TextField(blank=True, help_text="Explanation shown when feedback is released")
    hint = models.CharField(max_length=255, blank=True)
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated keywords")

    # Type-specific fields
    numeric_answer = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    numeric_tolerance = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000)
    short_answer_accepted = models.TextField(blank=True, help_text="Pipe-separated list of acceptable case-insensitive answers (e.g. SQL|Structured Query Language)")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_questions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        from core.sanitizer import sanitize_rich_text
        if self.question_text:
            self.question_text = sanitize_rich_text(self.question_text)
        if self.rich_content:
            self.rich_content = sanitize_rich_text(self.rich_content)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.get_question_type_display()}] {self.question_text[:70]}"


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    
    # Used for MATCHING questions (e.g. Left column: option_text, Right column: match_target)
    match_target = models.CharField(max_length=255, blank=True)
    
    # Used for ORDERING / SEQUENCING questions (1, 2, 3...)
    correct_order = models.PositiveIntegerField(default=0)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'id']

    def __str__(self):
        return f"{self.option_text[:50]} (Correct: {self.is_correct})"


class AssessmentQuestion(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='assessment_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='assessment_usages')
    order = models.PositiveIntegerField(default=0)
    marks_override = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['order', 'id']
        unique_together = ('assessment', 'question')

    @property
    def effective_marks(self):
        return self.marks_override if self.marks_override is not None else self.question.default_marks

    def __str__(self):
        return f"{self.assessment.code} -> Q#{self.question.id} ({self.effective_marks} pts)"
