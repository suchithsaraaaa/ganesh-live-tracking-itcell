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
        session_id = request.query_params.get('session_id')

        pdf_bytes, report_id = generate_idol_pdf_report(
            gpid=idol.gpid,
            session_id=session_id,
            generated_by_user=request.user
        )

        # Archive to S3 if configured
        s3_uri = None
        try:
            from .s3 import upload_report_to_s3
            s3_uri = upload_report_to_s3(pdf_bytes, f"{idol.gpid}_{report_id}.pdf")
        except Exception:
            pass

        # Log operational event and audit event
        try:
            from django.utils import timezone
            from apps.tracking.models import IdolEvent, IdolEventType, TrackingSession
            sess = None
            if session_id and str(session_id).isdigit():
                sess = TrackingSession.objects.filter(id=int(session_id)).first()
            IdolEvent.objects.create(
                idol=idol,
                gpid=idol.gpid,
                event_type=IdolEventType.REPORT_GENERATED,
                timestamp=timezone.now(),
                zone=idol.zone,
                actor=request.user,
                tracking_session=sess,
                metadata={'report_id': report_id, 'session_id': session_id}
            )
        except Exception:
            pass

        try:
            AuditEvent.objects.create(
                actor=request.user,
                action='DOWNLOAD_REPORT',
                target_model='Idol',
                target_id=idol.gpid,
                details={'report_id': report_id, 's3_uri': s3_uri, 'session_id': session_id},
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception:
            pass

        response = HttpResponse(pdf_bytes, content_type='application/pdf')

        filename = f"{idol.gpid}_official_report.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Report-Id'] = report_id
        return response
