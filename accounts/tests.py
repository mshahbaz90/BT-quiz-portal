import io
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, Department, Role
from core.models import AuditLog


class AccountsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept, _ = Department.objects.get_or_create(code="ENG", defaults={'name': "Engineering"})
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@breakthru.pk",
            password="Password123!",
            employee_id="BT-001",
            role=Role.SUPER_ADMIN,
            department=self.dept
        )
        self.employee = User.objects.create_user(
            username="test.emp",
            email="emp@breakthru.pk",
            password="Password123!",
            employee_id="BT-101",
            role=Role.EMPLOYEE,
            department=self.dept
        )

    def test_login_with_username_and_employee_id(self):
        # 1. Login with username
        resp = self.client.post(reverse('accounts:login'), {
            'username': 'test.emp',
            'password': 'Password123!',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('core:dashboard'))

        # 2. Login with employee ID
        self.client.logout()
        resp2 = self.client.post(reverse('accounts:login'), {
            'username': 'BT-101',
            'password': 'Password123!',
        })
        self.assertEqual(resp2.status_code, 302)

    def test_brute_force_lockout(self):
        for _ in range(5):
            self.client.post(reverse('accounts:login'), {
                'username': 'test.emp',
                'password': 'WrongPassword!',
            })
        self.employee.refresh_from_db()
        self.assertTrue(self.employee.is_locked)

        # Attempt with correct password while locked should fail
        resp = self.client.post(reverse('accounts:login'), {
            'username': 'test.emp',
            'password': 'Password123!',
        })
        self.assertContains(resp, "Account is temporarily locked")

    def test_force_password_change_middleware(self):
        self.employee.must_change_password = True
        self.employee.save()
        self.client.login(username='test.emp', password='Password123!')

        resp = self.client.get(reverse('core:dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('accounts:change_password'))

    def test_role_based_access_control(self):
        # Non-admin cannot access employee management
        self.client.login(username='test.emp', password='Password123!')
        resp = self.client.get(reverse('accounts:employee_list'))
        self.assertEqual(resp.status_code, 403)

        # Admin can access employee management
        self.client.login(username='admin', password='Password123!')
        resp_admin = self.client.get(reverse('accounts:employee_list'))
        self.assertEqual(resp_admin.status_code, 200)

    def test_bulk_employee_csv_import(self):
        self.client.login(username='admin', password='Password123!')
        csv_content = (
            "employee_id,username,email,first_name,last_name,designation,department_code,role\n"
            "BT-CSV-01,csv.user1,u1@breakthru.pk,User,One,Developer,ENG,EMPLOYEE\n"
            "BT-CSV-02,csv.user2,u2@breakthru.pk,User,Two,QA,ENG,EMPLOYEE\n"
        )
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = 'test_import.csv'

        resp = self.client.post(reverse('accounts:bulk_import'), {'csv_file': csv_file})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(User.objects.filter(username='csv.user1').exists())
        self.assertTrue(User.objects.filter(username='csv.user2').exists())

    def test_team_creation_and_member_assignment(self):
        self.client.login(username='admin', password='Password123!')
        
        # 1. Create Team / Group
        resp = self.client.post(reverse('accounts:team_list'), {
            'name': 'Backend Squad Alpha',
            'department': self.dept.id,
            'lead': self.admin.id,
            'is_active': True,
        })
        self.assertEqual(resp.status_code, 302)
        from accounts.models import Team
        team = Team.objects.get(name='Backend Squad Alpha')
        self.assertEqual(team.department, self.dept)

        # 2. View Team Details
        resp_detail = self.client.get(reverse('accounts:team_detail', kwargs={'team_id': team.id}))
        self.assertEqual(resp_detail.status_code, 200)
        self.assertContains(resp_detail, 'Backend Squad Alpha')

        # 3. Add employee to group
        resp_add = self.client.post(reverse('accounts:team_detail', kwargs={'team_id': team.id}), {
            'action': 'add_member',
            'user_id': self.employee.id,
        })
        self.assertEqual(resp_add.status_code, 302)
        self.assertTrue(self.employee.groups_assigned.filter(id=team.id).exists())

        # 4. Remove employee from group
        resp_rem = self.client.post(reverse('accounts:team_detail', kwargs={'team_id': team.id}), {
            'action': 'remove_member',
            'user_id': self.employee.id,
        })
        self.assertEqual(resp_rem.status_code, 302)
        self.assertFalse(self.employee.groups_assigned.filter(id=team.id).exists())

    def test_employee_edit_designation_and_department(self):
        self.client.login(username='admin', password='Password123!')
        new_dept = Department.objects.create(name="Product & Design", code="PRD")

        # GET edit page
        resp_get = self.client.get(reverse('accounts:employee_edit', kwargs={'user_id': self.employee.id}))
        self.assertEqual(resp_get.status_code, 200)
        self.assertContains(resp_get, "Edit Employee")

        # POST update designation and department
        resp_post = self.client.post(reverse('accounts:employee_edit', kwargs={'user_id': self.employee.id}), {
            'username': self.employee.username,
            'employee_id': self.employee.employee_id,
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'email': 'updated@breakthru.pk',
            'role': Role.EMPLOYEE,
            'department': new_dept.id,
            'designation': 'Senior Backend Architect',
            'is_active': True,
        })
        self.assertEqual(resp_post.status_code, 302)
        self.assertEqual(resp_post.url, reverse('accounts:employee_list'))

        self.employee.refresh_from_db()
        self.assertEqual(self.employee.designation, 'Senior Backend Architect')
        self.assertEqual(self.employee.department, new_dept)
        self.assertEqual(self.employee.first_name, 'UpdatedFirst')

    def test_employee_delete_lifecycle(self):
        self.client.login(username='admin', password='Password123!')

        # 1. GET confirmation page
        resp_get = self.client.get(reverse('accounts:employee_delete', kwargs={'user_id': self.employee.id}))
        self.assertEqual(resp_get.status_code, 200)
        self.assertContains(resp_get, "Delete Employee Account?")
        self.assertContains(resp_get, self.employee.username)

        # 2. POST confirmation deletes employee
        emp_id = self.employee.id
        resp_post = self.client.post(reverse('accounts:employee_delete', kwargs={'user_id': emp_id}))
        self.assertEqual(resp_post.status_code, 302)
        self.assertEqual(resp_post.url, reverse('accounts:employee_list'))
        self.assertFalse(User.objects.filter(id=emp_id).exists())

    def test_admin_cannot_delete_self(self):
        self.client.login(username='admin', password='Password123!')
        resp = self.client.post(reverse('accounts:employee_delete', kwargs={'user_id': self.admin.id}))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())

    def test_employee_list_renders_action_buttons(self):
        self.client.login(username='admin', password='Password123!')
        resp = self.client.get(reverse('accounts:employee_list'))
        self.assertEqual(resp.status_code, 200)
        # Edit and Delete links should be rendered
        self.assertContains(resp, reverse('accounts:employee_edit', kwargs={'user_id': self.employee.id}))
        self.assertContains(resp, reverse('accounts:employee_delete', kwargs={'user_id': self.employee.id}))
        self.assertContains(resp, "✏️ Edit")
        self.assertContains(resp, "🗑️ Delete")

    def test_strictly_super_admin_only_can_modify_employees(self):
        # Create a non-super-admin trainer
        trainer = User.objects.create_user(
            username="trainer_test",
            password="Password123!",
            role=Role.TRAINER
        )
        self.client.login(username='trainer_test', password='Password123!')

        # 1. Employee list -> 403
        resp = self.client.get(reverse('accounts:employee_list'))
        self.assertEqual(resp.status_code, 403)

        # 2. Employee create -> 403
        resp = self.client.get(reverse('accounts:employee_create'))
        self.assertEqual(resp.status_code, 403)

        # 3. Employee edit -> 403
        resp = self.client.get(reverse('accounts:employee_edit', kwargs={'user_id': self.employee.id}))
        self.assertEqual(resp.status_code, 403)

        # 4. Employee delete -> 403
        resp = self.client.post(reverse('accounts:employee_delete', kwargs={'user_id': self.employee.id}))
        self.assertEqual(resp.status_code, 403)

        # 5. Employee toggle status -> 403
        resp = self.client.post(reverse('accounts:employee_toggle_status', kwargs={'user_id': self.employee.id}))
        self.assertEqual(resp.status_code, 403)
