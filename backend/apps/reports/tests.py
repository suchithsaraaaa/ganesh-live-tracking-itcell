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
