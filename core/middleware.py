from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from core.models import AuditLog


class EnforcePasswordChangeMiddleware(MiddlewareMixin):
    """
    Forces users with must_change_password=True to change their password
    before accessing any other portal features.
    """
    def process_request(self, request):
        if not request.user.is_authenticated:
            return None

        # Exclude static/media files, logout, and password change endpoints
        exempt_paths = [
            reverse('accounts:change_password'),
            reverse('accounts:logout'),
            '/static/',
            '/media/',
        ]
        
        current_path = request.path
        if any(current_path.startswith(p) for p in exempt_paths):
            return None

        if getattr(request.user, 'must_change_password', False):
            return redirect('accounts:change_password')

        return None


class AuditLoggingMiddleware(MiddlewareMixin):
    """
    Attaches client IP and User-Agent info to request.
    """
    def process_request(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        request.client_ip = ip
        return None
