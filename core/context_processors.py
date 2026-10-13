import os
from django.conf import settings
from core.models import Notification


def branding_context(request):
    unread_count = 0
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    return {
        'COMPANY_NAME': os.getenv('COMPANY_NAME', 'BreakThru'),
        'COMPANY_TAGLINE': os.getenv('COMPANY_TAGLINE', 'Learn. Prove It. BreakThru.'),
        'COMPANY_DOMAIN': os.getenv('COMPANY_DOMAIN', 'breakthru.pk'),
        'PORTAL_URL': os.getenv('PORTAL_URL', 'https://assessments.breakthru.pk'),
        'UNREAD_NOTIFICATIONS_COUNT': unread_count,
        'CURRENT_YEAR': 2026,
    }
