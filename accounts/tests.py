import io
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, Department, Role
from core.models import AuditLog


class AccountsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(name="Engineering", code="ENG")
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
