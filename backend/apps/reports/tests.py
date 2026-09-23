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


class CompletedReportsRegistryTests(TestCase):
    def setUp(self):
        from datetime import date
        from apps.idols.models import ProcessionState
        from apps.tracking.models import IdolEvent, IdolEventType

        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='admin_reports_test',
            password='password123',
            role=UserRole.MAIN_OFFICER
        )
        self.client.force_authenticate(user=self.admin)

        # 1. Qualifying: 16 FT, Charminar PS, Charminar Zone, IMMERSION_COMPLETED
        self.idol_completed = Idol.objects.create(
            gpid='HYDCMRZCMNR9001',
            name='Completed Balapur Ganesh',
            association_name='Balapur Utsav Samithi',
            zone='Charminar',
            police_station='Charminar',
            idol_height=18.0,
            immersion_date=date(2026, 9, 23),
            procession_state=ProcessionState.IMMERSION_COMPLETED
        )

        # 2. Qualifying: 22 FT, Chaderghat PS, Charminar Zone, HOLDING
        self.idol_holding = Idol.objects.create(
            gpid='HYDCMRZCHGT9002',
            name='Holding Chaderghat Ganesh',
            association_name='Chaderghat Youth',
            zone='Charminar',
            police_station='Chaderghat',
            idol_height=23.0,
            immersion_date=date(2026, 9, 23),
            procession_state=ProcessionState.HOLDING
        )

        # 3. Qualifying via event: 27 FT, Begumpet PS, North Zone, event SENT_TO_HOLDING
        self.idol_event_holding = Idol.objects.create(
            gpid='HYDNRZBEGM9003',
            name='North Begumpet Giant',
            association_name='Begumpet Sangham',
            zone='North',
            police_station='Begumpet',
            idol_height=28.0,
            immersion_date=date(2026, 9, 24),
            procession_state=ProcessionState.NOT_STARTED
        )
        from django.utils import timezone
        IdolEvent.objects.create(
            idol=self.idol_event_holding,
            gpid=self.idol_event_holding.gpid,
            event_type=IdolEventType.SENT_TO_HOLDING,
            timestamp=timezone.now(),
            zone='North',
            actor=self.admin
        )

        # 4. NOT Qualifying: Incomplete (TRACKING)
        self.idol_tracking = Idol.objects.create(
            gpid='HYDCMRZCMNR9004',
            name='Active In-Transit Idol',
            zone='Charminar',
            police_station='Charminar',
            idol_height=16.0,
            immersion_date=date(2026, 9, 23),
            procession_state=ProcessionState.TRACKING
        )

        # 5. NOT Qualifying: Under 15 FT (even if IMMERSION_COMPLETED)
        self.idol_small = Idol.objects.create(
            gpid='HYDCMRZCMNR9005',
            name='Small Idol 10 FT',
            zone='Charminar',
            police_station='Charminar',
            idol_height=10.0,
            immersion_date=date(2026, 9, 23),
            procession_state=ProcessionState.IMMERSION_COMPLETED
        )

    def test_registry_filters_only_completed_and_holding_15_plus(self):
        res = self.client.get('/api/v1/reports/registry/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        gpids = [r['gpid'] for r in data['results']]
        self.assertIn('HYDCMRZCMNR9001', gpids)
        self.assertIn('HYDCMRZCHGT9002', gpids)
        self.assertIn('HYDNRZBEGM9003', gpids)
        self.assertNotIn('HYDCMRZCMNR9004', gpids)  # tracking active
        self.assertNotIn('HYDCMRZCMNR9005', gpids)  # < 15 ft
        self.assertEqual(data['summary']['total_eligible'], 3)
        self.assertEqual(data['summary']['count_completed'], 1)
        self.assertEqual(data['summary']['count_holding'], 2)

    def test_zone_and_police_station_filters(self):
        # Filter Zone=Charminar
        res1 = self.client.get('/api/v1/reports/registry/?zone=Charminar')
        self.assertEqual(res1.status_code, 200)
        gpids1 = [r['gpid'] for r in res1.json()['results']]
        self.assertEqual(set(gpids1), {'HYDCMRZCMNR9001', 'HYDCMRZCHGT9002'})

        # Filter Zone=Charminar AND PS=Chaderghat
        res2 = self.client.get('/api/v1/reports/registry/?zone=Charminar&police_station=Chaderghat')
        self.assertEqual(res2.status_code, 200)
        gpids2 = [r['gpid'] for r in res2.json()['results']]
        self.assertEqual(gpids2, ['HYDCMRZCHGT9002'])

    def test_height_bucket_filters(self):
        # 15-20 FT
        res = self.client.get('/api/v1/reports/registry/?height_bucket=15_20')
        self.assertEqual(res.status_code, 200)
        self.assertEqual([r['gpid'] for r in res.json()['results']], ['HYDCMRZCMNR9001'])

        # 21-25 FT
        res = self.client.get('/api/v1/reports/registry/?height_bucket=21_25')
        self.assertEqual(res.status_code, 200)
        self.assertEqual([r['gpid'] for r in res.json()['results']], ['HYDCMRZCHGT9002'])

        # 26+ FT
        res = self.client.get('/api/v1/reports/registry/?height_bucket=26_plus')
        self.assertEqual(res.status_code, 200)
        self.assertEqual([r['gpid'] for r in res.json()['results']], ['HYDNRZBEGM9003'])

    def test_visarjan_date_filter(self):
        res = self.client.get('/api/v1/reports/registry/?visarjan_date=2026-09-24')
        self.assertEqual(res.status_code, 200)
        self.assertEqual([r['gpid'] for r in res.json()['results']], ['HYDNRZBEGM9003'])

    def test_search_and_pagination(self):
        res = self.client.get('/api/v1/reports/registry/?search=Balapur')
        self.assertEqual(res.status_code, 200)
        self.assertEqual([r['gpid'] for r in res.json()['results']], ['HYDCMRZCMNR9001'])

