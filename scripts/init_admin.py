import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'breakthru_portal.settings')
django.setup()

from accounts.models import User, Role

def create_default_admin():
    username = os.getenv('ADMIN_USERNAME', 'admin')
    email = os.getenv('ADMIN_EMAIL', 'admin@breakthru.pk')
    password = os.getenv('ADMIN_PASSWORD', 'Admin@123456')

    if not User.objects.filter(username=username).exists():
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        user.role = Role.SUPER_ADMIN
        user.save()
        print(f"✅ Default Super Admin '{username}' created successfully!")
    else:
        print(f"ℹ️ Super Admin '{username}' already exists.")

if __name__ == '__main__':
    create_default_admin()
