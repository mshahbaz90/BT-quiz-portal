from decimal import Decimal
from django.core.management.base import BaseCommand
from accounts.models import User, Department, Team, Role
from assessments.models import Assessment, Category, Question, QuestionOption, AssessmentQuestion, QuestionType, Difficulty


class Command(BaseCommand):
    help = 'Seeds initial departments, roles, user accounts, question bank, and sample assessments for BreakThru Assessments.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding BreakThru initial data...")

        # 1. Departments
        depts_data = [
            ("ISR", "ISR", "Inside Sales Representative"),
            ("Chat Specialist", "CHAT", "Chat Specialist Operations"),
            ("T&D", "TD", "Training & Development"),
            ("QA", "QA", "Quality Assurance"),
            ("Teamlead", "TL", "Team Lead & Supervisory"),
            ("IT", "IT", "Information Technology & Systems"),
            ("HR", "HR", "Human Resources"),
        ]
        created_depts = {}
        for name, code, desc in depts_data:
            dept = Department.objects.filter(code=code).first() or Department.objects.filter(name=name).first()
            if dept:
                dept.name = name
                dept.code = code
                dept.description = desc
                dept.is_active = True
                dept.save()
            else:
                dept = Department.objects.create(name=name, code=code, description=desc, is_active=True)
            created_depts[code] = dept

        Department.objects.exclude(code__in=[c for _, c, _ in depts_data]).update(is_active=False)

        it_dept = created_depts["IT"]
        hr_dept = created_depts["HR"]

        # 2. Teams
        backend_team, _ = Team.objects.get_or_create(name="Backend Engineering", department=it_dept)
        frontend_team, _ = Team.objects.get_or_create(name="Frontend & Web Apps", department=it_dept)

        # 3. Users
        from core.models import AuditLog
        deleted_usernames = set()
        for log in AuditLog.objects.filter(action='EMPLOYEE_DELETED'):
            if log.details and 'username' in log.details:
                deleted_usernames.add(log.details['username'])

        # Super Administrator
        admin_user = User.objects.filter(username="admin").first()
        if not admin_user:
            admin_user = User.objects.create_superuser(
                username="admin",
                email="admin@breakthru.pk",
                password="BreakThru2026!",
                employee_id="BT-EXEC-001",
                first_name="Shahbaz",
                last_name="Executive",
                role=Role.SUPER_ADMIN,
                designation="Chief Technology Officer",
                department=it_dept
            )
            self.stdout.write("Created Super Admin: admin / BreakThru2026!")

        # Trainer
        trainer = None
        if "trainer.ali" not in deleted_usernames:
            trainer = User.objects.filter(username="trainer.ali").first()
            if not trainer:
                trainer = User.objects.create_user(
                    username="trainer.ali",
                    email="ali.trainer@breakthru.pk",
                    password="BreakThru2026!",
                    employee_id="BT-TRN-101",
                    first_name="Ali",
                    last_name="Raza",
                    role=Role.TRAINER,
                    designation="Lead Technical Trainer",
                    department=hr_dept
                )
                self.stdout.write("Created Trainer: trainer.ali / BreakThru2026!")

        if not trainer:
            trainer = User.objects.filter(role=Role.TRAINER).first() or admin_user

        # Team Lead
        lead = None
        if "lead.kamran" not in deleted_usernames:
            lead = User.objects.filter(username="lead.kamran").first()
            if not lead:
                lead = User.objects.create_user(
                    username="lead.kamran",
                    email="kamran.lead@breakthru.pk",
                    password="BreakThru2026!",
                    employee_id="BT-ENG-201",
                    first_name="Kamran",
                    last_name="Akhtar",
                    role=Role.TEAM_LEAD,
                    designation="Engineering Team Lead",
                    department=it_dept,
                    team=backend_team
                )
                self.stdout.write("Created Team Lead: lead.kamran / BreakThru2026!")
        if lead:
            backend_team.lead = lead
            backend_team.save()

        # Candidates / Employees
        emp1 = None
        if "emp.zara" not in deleted_usernames:
            emp1 = User.objects.filter(username="emp.zara").first()
            if not emp1:
                emp1 = User.objects.create_user(
                    username="emp.zara",
                    email="zara.khan@breakthru.pk",
                    password="BreakThru2026!",
                    employee_id="BT-ENG-301",
                    first_name="Zara",
                    last_name="Khan",
                    role=Role.EMPLOYEE,
                    designation="Full Stack Software Engineer",
                    department=it_dept,
                    team=backend_team
                )
                self.stdout.write("Created Employee: emp.zara / BreakThru2026!")

        emp2 = None
        if "emp.bilal" not in deleted_usernames:
            emp2 = User.objects.filter(username="emp.bilal").first()
            if not emp2:
                emp2 = User.objects.create_user(
                    username="emp.bilal",
                    email="bilal.tariq@breakthru.pk",
                    password="BreakThru2026!",
                    employee_id="BT-ENG-302",
                    first_name="Bilal",
                    last_name="Tariq",
                    role=Role.EMPLOYEE,
                    designation="Frontend Developer",
                    department=it_dept,
                    team=frontend_team
                )
                self.stdout.write("Created Employee: emp.bilal / BreakThru2026!")

        # 4. Categories
        cat_tech, _ = Category.objects.get_or_create(name="Technical Proficiency", defaults={'description': "Core software architecture, programming & tools"})
        cat_sec, _ = Category.objects.get_or_create(name="Cyber Security & Compliance", defaults={'description': "Data protection, secure coding & threat response"})

        # 5. Question Bank (12 Question Types)
        # Type 1: Single Choice
        q1, _ = Question.objects.get_or_create(
            question_text="Which Python built-in data type is mutable and maintains insertion order?",
            defaults={
                'question_type': QuestionType.SINGLE_CHOICE,
                'category': cat_tech,
                'default_marks': Decimal('2.00'),
                'difficulty': Difficulty.EASY,
                'explanation': "Lists and Dictionaries in modern Python preserve insertion order and are mutable.",
                'created_by': trainer,
            }
        )
        if not q1.options.exists():
            QuestionOption.objects.create(question=q1, option_text="Tuple", is_correct=False, display_order=1)
            QuestionOption.objects.create(question=q1, option_text="List", is_correct=True, display_order=2)
            QuestionOption.objects.create(question=q1, option_text="Frozenset", is_correct=False, display_order=3)
            QuestionOption.objects.create(question=q1, option_text="String", is_correct=False, display_order=4)

        # Type 2: Multiple Select
        q2, _ = Question.objects.get_or_create(
            question_text="Which of the following HTTP status codes indicate successful responses? (Select all that apply)",
            defaults={
                'question_type': QuestionType.MULTIPLE_SELECT,
                'category': cat_tech,
                'default_marks': Decimal('2.00'),
                'difficulty': Difficulty.MEDIUM,
                'explanation': "200 OK and 201 Created belong to the 2xx success class. 404 is client error, 500 is server error.",
                'created_by': trainer,
            }
        )
        if not q2.options.exists():
            QuestionOption.objects.create(question=q2, option_text="200 OK", is_correct=True, display_order=1)
            QuestionOption.objects.create(question=q2, option_text="201 Created", is_correct=True, display_order=2)
            QuestionOption.objects.create(question=q2, option_text="404 Not Found", is_correct=False, display_order=3)
            QuestionOption.objects.create(question=q2, option_text="500 Internal Server Error", is_correct=False, display_order=4)

        # Type 3: True / False
        q3, _ = Question.objects.get_or_create(
            question_text="HTTPS traffic is encrypted in transit using Transport Layer Security (TLS).",
            defaults={
                'question_type': QuestionType.TRUE_FALSE,
                'category': cat_sec,
                'default_marks': Decimal('1.00'),
                'difficulty': Difficulty.EASY,
                'explanation': "HTTPS uses TLS to encrypt communication between web browser and server.",
                'created_by': trainer,
            }
        )
        if not q3.options.exists():
            QuestionOption.objects.create(question=q3, option_text="True", is_correct=True, display_order=1)
            QuestionOption.objects.create(question=q3, option_text="False", is_correct=False, display_order=2)

        # Type 4: Yes / No
        q4, _ = Question.objects.get_or_create(
            question_text="Should API keys or database passwords ever be committed to a public Git repository?",
            defaults={
                'question_type': QuestionType.YES_NO,
                'category': cat_sec,
                'default_marks': Decimal('1.00'),
                'difficulty': Difficulty.EASY,
                'explanation': "Secrets should always be managed using environment variables or a secret vault.",
                'created_by': trainer,
            }
        )
        if not q4.options.exists():
            QuestionOption.objects.create(question=q4, option_text="Yes", is_correct=False, display_order=1)
            QuestionOption.objects.create(question=q4, option_text="No", is_correct=True, display_order=2)

        # Type 5: Short Answer
        q5, _ = Question.objects.get_or_create(
            question_text="What standard query language is used to manage and query relational databases?",
            defaults={
                'question_type': QuestionType.SHORT_ANSWER,
                'category': cat_tech,
                'default_marks': Decimal('2.00'),
                'difficulty': Difficulty.EASY,
                'short_answer_accepted': "SQL|Structured Query Language",
                'explanation': "SQL (Structured Query Language) is the domain-specific language used for RDBMS.",
                'created_by': trainer,
            }
        )

        # Type 6: Fill in the Blank
        q6, _ = Question.objects.get_or_create(
            question_text="In Git, the command to switch between branches or create a new branch is 'git ______'.",
            defaults={
                'question_type': QuestionType.FILL_BLANK,
                'category': cat_tech,
                'default_marks': Decimal('1.00'),
                'difficulty': Difficulty.EASY,
                'short_answer_accepted': "checkout|switch",
                'explanation': "Both 'checkout' and 'switch' are used to change branches in Git.",
                'created_by': trainer,
            }
        )

        # Type 7: Numeric with Tolerance
        q7, _ = Question.objects.get_or_create(
            question_text="What is the standard HTTP port number used for unencrypted web communication?",
            defaults={
                'question_type': QuestionType.NUMERIC,
                'category': cat_tech,
                'default_marks': Decimal('1.00'),
                'difficulty': Difficulty.EASY,
                'numeric_answer': Decimal('80.00'),
                'numeric_tolerance': Decimal('0.00'),
                'explanation': "Port 80 is the standard port for HTTP, whereas Port 443 is used for HTTPS.",
                'created_by': trainer,
            }
        )

        # Type 8: Matching Pairs
        q8, _ = Question.objects.get_or_create(
            question_text="Match each networking protocol to its standard default port number:",
            defaults={
                'question_type': QuestionType.MATCHING,
                'category': cat_tech,
                'default_marks': Decimal('3.00'),
                'difficulty': Difficulty.MEDIUM,
                'created_by': trainer,
            }
        )
        if not q8.options.exists():
            QuestionOption.objects.create(question=q8, option_text="SSH", match_target="Port 22", display_order=1)
            QuestionOption.objects.create(question=q8, option_text="HTTPS", match_target="Port 443", display_order=2)
            QuestionOption.objects.create(question=q8, option_text="DNS", match_target="Port 53", display_order=3)

        # Type 9: Ordering / Sequencing
        q9, _ = Question.objects.get_or_create(
            question_text="Arrange the standard Software Development Life Cycle (SDLC) phases in chronological order:",
            defaults={
                'question_type': QuestionType.ORDERING,
                'category': cat_tech,
                'default_marks': Decimal('3.00'),
                'difficulty': Difficulty.MEDIUM,
                'created_by': trainer,
            }
        )
        if not q9.options.exists():
            QuestionOption.objects.create(question=q9, option_text="Requirements Gathering", correct_order=1, display_order=1)
            QuestionOption.objects.create(question=q9, option_text="System Architecture & Design", correct_order=2, display_order=2)
            QuestionOption.objects.create(question=q9, option_text="Implementation & Coding", correct_order=3, display_order=3)
            QuestionOption.objects.create(question=q9, option_text="QA Testing & Verification", correct_order=4, display_order=4)
            QuestionOption.objects.create(question=q9, option_text="Production Deployment & Maintenance", correct_order=5, display_order=5)

        # Type 10: Rich Content / Case Study with Code Block
        q10, _ = Question.objects.get_or_create(
            question_text="Review the following Python snippet. What will be the output when executed?",
            defaults={
                'question_type': QuestionType.RICH_CONTENT,
                'category': cat_tech,
                'default_marks': Decimal('2.00'),
                'difficulty': Difficulty.MEDIUM,
                'rich_content': "def process(items=[]):\n    items.append(1)\n    return items\n\nprint(process())\nprint(process())",
                'explanation': "Default mutable arguments in Python are evaluated once at function definition time, accumulating modifications.",
                'created_by': trainer,
            }
        )
        if not q10.options.exists():
            QuestionOption.objects.create(question=q10, option_text="[1] and [1]", is_correct=False, display_order=1)
            QuestionOption.objects.create(question=q10, option_text="[1] and [1, 1]", is_correct=True, display_order=2)
            QuestionOption.objects.create(question=q10, option_text="TypeError: mutable argument not allowed", is_correct=False, display_order=3)
            QuestionOption.objects.create(question=q10, option_text="[1, 1] and [1, 1]", is_correct=False, display_order=4)

        # Type 11: Question with Hint & Explanation
        q11, _ = Question.objects.get_or_create(
            question_text="Which Django ORM method is used to avoid the N+1 query problem by performing a SQL JOIN across foreign key relationships?",
            defaults={
                'question_type': QuestionType.EXPLANATION_HINT,
                'category': cat_tech,
                'default_marks': Decimal('2.00'),
                'difficulty': Difficulty.MEDIUM,
                'hint': "It starts with 'select_...'",
                'explanation': "select_related() creates a SQL JOIN and includes the fields of the related object in the SELECT statement.",
                'created_by': trainer,
            }
        )
        if not q11.options.exists():
            QuestionOption.objects.create(question=q11, option_text="prefetch_related()", is_correct=False, display_order=1)
            QuestionOption.objects.create(question=q11, option_text="select_related()", is_correct=True, display_order=2)
            QuestionOption.objects.create(question=q11, option_text="all()", is_correct=False, display_order=3)
            QuestionOption.objects.create(question=q11, option_text="filter()", is_correct=False, display_order=4)

        # Type 12: Long Answer / Essay
        q12, _ = Question.objects.get_or_create(
            question_text="Explain the key differences between monolithic and microservices software architectures, detailing two advantages and two trade-offs of each approach.",
            defaults={
                'question_type': QuestionType.LONG_ANSWER,
                'category': cat_tech,
                'default_marks': Decimal('5.00'),
                'difficulty': Difficulty.HARD,
                'explanation': "Monoliths offer simplicity of deployment and transaction management at the cost of blast radius. Microservices allow independent scaling and tech diversity at the cost of network latency and operational complexity.",
                'created_by': trainer,
            }
        )

        # 6. Sample Published Assessment: BreakThru Full Stack & Security Fundamentals
        assessment, _ = Assessment.objects.get_or_create(
            code="BT-ASSESS-01",
            defaults={
                'title': "BreakThru Engineering & Security Competency Assessment",
                'category': cat_tech,
                'status': Assessment.Status.PUBLISHED,
                'duration_minutes': 25,
                'pass_mark_percentage': Decimal('70.00'),
                'max_attempts': 2,
                'shuffle_questions': False,
                'shuffle_options': True,
                'allow_backtracking': True,
                'negative_marking': False,
                'release_results_mode': Assessment.ResultRelease.IMMEDIATE,
                'show_explanations_to_user': True,
                'created_by': trainer,
                'description': "Comprehensive evaluation covering software engineering, API design, database querying, and cybersecurity principles.",
                'instructions': "Welcome to the BreakThru Competency Assessment. Ensure a stable internet connection. All answers are autosaved in real-time. You may navigate between questions using the Question Navigator."
            }
        )

        # Attach all 12 questions to the assessment
        questions_to_attach = [q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11, q12]
        for order, q in enumerate(questions_to_attach, start=1):
            AssessmentQuestion.objects.get_or_create(
                assessment=assessment,
                question=q,
                defaults={'order': order, 'marks_override': q.default_marks}
            )

        self.stdout.write(self.style.SUCCESS("BreakThru initial data seed complete! Assessment 'BT-ASSESS-01' published with all 12 question types."))
