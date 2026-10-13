from django.urls import path
from certificates import views

app_name = 'certificates'

urlpatterns = [
    path('', views.my_certificates_view, name='my_certificates'),
    path('download/<int:cert_id>/', views.download_pdf_view, name='download_pdf'),
    path('verify/<uuid:cert_uuid>/', views.verify_public_view, name='verify_public'),
    path('revoke/<int:cert_id>/', views.revoke_certificate_view, name='revoke_certificate'),
]
