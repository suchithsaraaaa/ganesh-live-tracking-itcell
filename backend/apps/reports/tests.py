from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User, UserRole
from apps.idols.models import Idol
from apps.reports.services import generate_idol_pdf_report


class ReportGenerationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.officer = User.objects.create_user(
            username='sho_reports', password='password123',
            role=UserRole.SHO, police_station='Charminar'
        )
        self.idol = Idol.objects.create(
            gpid='HYDCMRZCMNR1749',
            name='Charminar Report Ganesh',
            police_station='Charminar',
            zone='Charminar',
            idol_height=12.5,
            pandal_height=20.0
        )
        self.client.force_authenticate(user=self.officer)

    def test_pure_server_side_pdf_generation(self):
        pdf_bytes, report_id = generate_idol_pdf_report(
            gpid=self.idol.gpid,
            generated_by_user=self.officer
        )
        self.assertIsNotNone(pdf_bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        # Verify valid PDF file signature
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))
        self.assertTrue(report_id.startswith('HYD-REP-'))

    def test_report_download_api_endpoint(self):
        res = self.client.get(reverse('download-idol-report', kwargs={'gpid': self.idol.gpid}))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')
        self.assertIn('attachment;', res['Content-Disposition'])
        self.assertIn(f"{self.idol.gpid}_official_report.pdf", res['Content-Disposition'])
        self.assertTrue(res.has_header('X-Report-Id'))

    def test_session_scoped_report_and_timeline(self):
        """Tests that reports generate cleanly for specific sessions with operational timeline."""
        from django.utils import timezone
        from apps.assignments.models import Assignment
        from apps.tracking.models import TrackingSession, LocationPoint, TrackingSessionStatus, IdolEvent, IdolEventType

        constable = User.objects.create_user(
            username='pc_rep_constable', password='password123',
            role=UserRole.CONSTABLE, police_id='PC-888'
        )
        assignment = Assignment.assign_constable(
            idol=self.idol,
            constable=constable,
            assigned_by=self.officer
        )
        t0 = timezone.now()
        session = TrackingSession.objects.create(
            assignment=assignment,
            status=TrackingSessionStatus.ACTIVE,
            started_at=t0
        )
        LocationPoint.objects.create(session=session, latitude=17.3616, longitude=78.4747, accuracy=5.0, recorded_at=t0)
        IdolEvent.objects.create(
            idol=self.idol,
            gpid=self.idol.gpid,
            event_type=IdolEventType.TRACKING_STARTED,
            timestamp=t0,
            latitude=17.3616,
            longitude=78.4747,
            actor=constable,
            tracking_session=session
        )

        # Generate report scoped to session
        pdf_bytes, report_id = generate_idol_pdf_report(
            gpid=self.idol.gpid,
            session_id=session.id,
            generated_by_user=self.officer
        )
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))
        self.assertTrue(report_id.startswith('HYD-REP-'))

        # Download via API with query param
        res = self.client.get(f"/api/v1/reports/idols/{self.idol.gpid}/?session_id={session.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')

