import io
import os
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from certificates.models import Certificate


def generate_certificate_pdf(certificate: Certificate) -> io.BytesIO:
    """
    Generates a professional corporate PDF Certificate using ReportLab.
    """
    buffer = io.BytesIO()
    # Landscape Letter (11 x 8.5 inches)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    brand_style = ParagraphStyle(
        'BrandHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=26,
        leading=30,
        textColor=colors.HexColor('#0B192C'),
        alignment=1, # Center
    )

    tagline_style = ParagraphStyle(
        'Tagline',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0284C7'),
        alignment=1,
    )

    title_style = ParagraphStyle(
        'CertTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=30,
        leading=36,
        textColor=colors.HexColor('#0F172A'),
        alignment=1,
    )

    recipient_style = ParagraphStyle(
        'Recipient',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#0284C7'),
        alignment=1,
    )

    body_style = ParagraphStyle(
        'CertBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=18,
        textColor=colors.HexColor('#475569'),
        alignment=1,
    )

    meta_style = ParagraphStyle(
        'CertMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748B'),
        alignment=1,
    )

    elements = []
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("BREAKTHRU", brand_style))
    elements.append(Paragraph("LEARN. PROVE IT. BREAKTHRU.", tagline_style))
    elements.append(Spacer(1, 25))

    elements.append(Paragraph("CERTIFICATE OF ACHIEVEMENT", title_style))
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("This is proudly presented to", body_style))
    elements.append(Spacer(1, 10))

    full_name = getattr(certificate.attempt, 'participant_name', '') or certificate.user.get_full_name() or certificate.user.username
    elements.append(Paragraph(full_name.upper(), recipient_style))
    elements.append(Spacer(1, 10))

    emp_id = getattr(certificate.attempt, 'participant_employee_id', '') or certificate.user.employee_id
    if emp_id:
        elements.append(Paragraph(f"Candidate / Employee ID: {emp_id}", meta_style))
        elements.append(Spacer(1, 10))

    assessment_title = certificate.assessment.title
    score_pct = certificate.score_percentage
    elements.append(Paragraph(
        f"for successfully completing the rigorous assessment in<br/><b>{assessment_title}</b><br/>demonstrating proven professional competency with a score of <b>{score_pct}%</b>.",
        body_style
    ))
    elements.append(Spacer(1, 35))

    # Signatures & Verification Details Table
    date_str = certificate.issued_at.strftime('%B %d, %Y')
    cert_code = certificate.certificate_code
    portal_base = os.getenv('PORTAL_URL', 'https://bt.assesment.pk').rstrip('/')
    verify_url = f"{portal_base}/certificates/verify/{certificate.certificate_id}/"

    footer_data = [
        [
            Paragraph(f"<b>Issue Date:</b><br/>{date_str}", meta_style),
            Paragraph(f"<b>Certificate ID:</b><br/>{cert_code}", meta_style),
            Paragraph(f"<b>Authenticity Verification:</b><br/>{verify_url}", meta_style),
        ]
    ]

    table = Table(footer_data, colWidths=[200, 200, 310])
    table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEABOVE', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(table)

    def draw_borders(c, doc_obj):
        c.saveState()
        # Outer decorative frame
        c.setStrokeColor(colors.HexColor('#0B192C'))
        c.setLineWidth(4)
        c.rect(20, 20, 752, 572)

        # Inner subtle gold/cyan frame
        c.setStrokeColor(colors.HexColor('#0284C7'))
        c.setLineWidth(1.5)
        c.rect(26, 26, 740, 560)
        c.restoreState()

    doc.build(elements, onFirstPage=draw_borders)
    buffer.seek(0)
    return buffer
