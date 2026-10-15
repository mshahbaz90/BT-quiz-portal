from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from exam import views as exam_views

urlpatterns = [
    # ClassMarker Direct Assessment Link Gateway
    path('links/<str:link_code>/', exam_views.public_link_entry_view, name='public_link_entry'),

    # Core & Dashboard
    path('', include('core.urls')),

    # Accounts & User Management
    path('accounts/', include('accounts.urls')),

    # Assessments & Question Bank
    path('assessments/', include('assessments.urls')),

    # Live Exam Session & Runner
    path('exam/', include('exam.urls')),

    # Grading & Evaluation Queue
    path('grading/', include('grading.urls')),

    # Analytics & Reports
    path('analytics/', include('analytics.urls')),

    # Certificates & Public Verification
    path('certificates/', include('certificates.urls')),

    # Django Admin Site
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
