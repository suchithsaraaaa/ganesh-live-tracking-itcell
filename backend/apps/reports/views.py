from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .services import generate_idol_pdf_report
from apps.idols.models import Idol
from apps.audit.models import AuditEvent


class DownloadIdolReportView(APIView):
    """
    Produces and streams real server-generated PDF operational report for a GPID.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, gpid):
        idol = get_object_or_404(Idol, gpid__iexact=gpid)

        pdf_bytes, report_id = generate_idol_pdf_report(
            gpid=idol.gpid,
            generated_by_user=request.user
        )

        # Archive to S3 if configured
        s3_uri = None
        try:
            from .s3 import upload_report_to_s3
            s3_uri = upload_report_to_s3(pdf_bytes, f"{idol.gpid}_{report_id}.pdf")
        except Exception:
            pass

        # Audit log the report generation
        try:
            AuditEvent.objects.create(
                actor=request.user,
                action='DOWNLOAD_REPORT',
                target_model='Idol',
                target_id=idol.gpid,
                details={'report_id': report_id, 's3_uri': s3_uri},
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception:
            pass

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"{idol.gpid}_official_report.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Report-Id'] = report_id
        return response
