from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.contrib import messages

from certificates.models import Certificate
from certificates.utils import generate_certificate_pdf
from core.models import AuditLog


@login_required
def my_certificates_view(request):
    certificates = Certificate.objects.filter(user=request.user, is_revoked=False).select_related('assessment')
    return render(request, 'certificates/my_certificates.html', {'certificates': certificates})


@login_required
def download_pdf_view(request, cert_id):
    cert = get_object_or_404(Certificate.objects.select_related('user', 'assessment'), id=cert_id)

    # Permission check: owner or admin/trainer
    if cert.user != request.user and not (request.user.is_trainer or request.user.is_super_admin):
        return HttpResponseForbidden("Not authorized to download this certificate.")

    if cert.is_revoked:
        messages.error(request, "This certificate has been revoked and cannot be downloaded.")
        return redirect('certificates:my_certificates')

    pdf_buffer = generate_certificate_pdf(cert)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    filename = f"BreakThru_Certificate_{cert.certificate_code}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def verify_public_view(request, cert_uuid):
    """
    Public verification endpoint for employees, supervisors, and external auditors.
    Reveals only authorized authenticity proof without exposing private candidate data.
    """
    cert = Certificate.objects.filter(certificate_id=cert_uuid).select_related('assessment', 'user').first()
    return render(request, 'certificates/verify.html', {'certificate': cert})


@login_required
def revoke_certificate_view(request, cert_id):
    if not request.user.is_super_admin:
        return HttpResponseForbidden("Revocation restricted to Super Administrators.")

    cert = get_object_or_404(Certificate, id=cert_id)
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        cert.is_revoked = True
        cert.revoked_by = request.user
        cert.revocation_reason = reason or "Revoked by Super Administrator"
        cert.revoked_at = timezone.now()
        cert.save()

        AuditLog.objects.create(
            user=request.user,
            action='CERTIFICATE_REVOKED',
            target_model='Certificate',
            target_id=str(cert.id),
            details={'code': cert.certificate_code, 'reason': cert.revocation_reason}
        )
        messages.warning(request, f"Certificate {cert.certificate_code} has been REVOKED.")

    return redirect('analytics:reports_overview')
