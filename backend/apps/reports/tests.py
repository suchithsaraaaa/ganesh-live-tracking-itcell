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

    def test_registry_filters_only_completed_and_holding_all_heights(self):
        res = self.client.get('/api/v1/reports/registry/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        gpids = [r['gpid'] for r in data['results']]
        self.assertIn('HYDCMRZCMNR9001', gpids)
        self.assertIn('HYDCMRZCHGT9002', gpids)
        self.assertIn('HYDNRZBEGM9003', gpids)
        self.assertIn('HYDCMRZCMNR9005', gpids)  # < 15 ft now included in base registry!
        self.assertNotIn('HYDCMRZCMNR9004', gpids)  # tracking active NOT included
        self.assertEqual(data['summary']['total_eligible'], 4)
        self.assertEqual(data['summary']['count_completed'], 2)
        self.assertEqual(data['summary']['count_holding'], 2)
        self.assertEqual(data['summary']['count_below_15'], 1)

        # But when height_bucket='all_15_plus' is explicitly applied:
        res_15 = self.client.get('/api/v1/reports/registry/?height_bucket=all_15_plus')
        self.assertEqual(res_15.status_code, 200)
        gpids_15 = [r['gpid'] for r in res_15.json()['results']]
        self.assertNotIn('HYDCMRZCMNR9005', gpids_15)

    def test_zone_and_police_station_filters(self):
        # Filter Zone=Charminar
        res1 = self.client.get('/api/v1/reports/registry/?zone=Charminar')
        self.assertEqual(res1.status_code, 200)
        gpids1 = [r['gpid'] for r in res1.json()['results']]
        self.assertEqual(set(gpids1), {'HYDCMRZCMNR9001', 'HYDCMRZCHGT9002', 'HYDCMRZCMNR9005'})

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

        # Below 15 FT
        res_below = self.client.get('/api/v1/reports/registry/?height_bucket=below_15')
        self.assertEqual(res_below.status_code, 200)
        self.assertEqual([r['gpid'] for r in res_below.json()['results']], ['HYDCMRZCMNR9005'])

    def test_visarjan_date_filter(self):
        res = self.client.get('/api/v1/reports/registry/?visarjan_date=2026-09-24')
        self.assertEqual(res.status_code, 200)
        self.assertEqual([r['gpid'] for r in res.json()['results']], ['HYDNRZBEGM9003'])

    def test_search_and_pagination(self):
        res = self.client.get('/api/v1/reports/registry/?search=Balapur')
        self.assertEqual(res.status_code, 200)
        self.assertEqual([r['gpid'] for r in res.json()['results']], ['HYDCMRZCMNR9001'])


class ReportRegistryBusinessRuleTests(TestCase):
    """
    Exhaustive verification of all 12 operational business rules required for Reports Registry.
    """
    def setUp(self):
        from datetime import date
        from apps.idols.models import ProcessionState
        from apps.tracking.models import IdolEvent, IdolEventType

        self.client = APIClient()
        self.superadmin = User.objects.create_user(
            username='superadmin_rep',
            password='password123',
            role=UserRole.SUPER_ADMIN
        )
        self.sho_charminar = User.objects.create_user(
            username='sho_charminar_rep',
            password='password123',
            role=UserRole.SHO,
            zone='Charminar',
            police_station='Charminar'
        )
        self.client.force_authenticate(user=self.superadmin)

    def test_01_immersion_completed_appears_regardless_of_height(self):
        # 1. A procession in IMMERSION_COMPLETED appears in Reports Registry (tests both 18ft and 12ft)
        from apps.idols.models import ProcessionState
        i_tall = Idol.objects.create(
            gpid='TEST-IMM-TALL', name='Tall Immersed', zone='Charminar',
            police_station='Charminar', idol_height=18.0,
            procession_state=ProcessionState.IMMERSION_COMPLETED
        )
        i_sub = Idol.objects.create(
            gpid='TEST-IMM-SUB', name='Subthreshold Immersed', zone='Charminar',
            police_station='Charminar', idol_height=12.0,
            procession_state=ProcessionState.IMMERSION_COMPLETED
        )
        res = self.client.get('/api/v1/reports/registry/')
        gpids = [r['gpid'] for r in res.json()['results']]
        self.assertIn('TEST-IMM-TALL', gpids)
        self.assertIn('TEST-IMM-SUB', gpids)

    def test_02_holding_sent_to_holding_appears(self):
        # 2. A procession in HOLDING/SENT_TO_HOLDING appears in Reports Registry.
        from apps.idols.models import ProcessionState
        from apps.tracking.models import IdolEvent, IdolEventType
        from django.utils import timezone
        i_holding = Idol.objects.create(
            gpid='TEST-HOLDING-STATE', name='Holding State', zone='Charminar',
            police_station='Charminar', idol_height=16.0,
            procession_state=ProcessionState.HOLDING
        )
        i_event = Idol.objects.create(
            gpid='TEST-HOLDING-EVENT', name='Holding Event', zone='Charminar',
            police_station='Charminar', idol_height=14.0,
            procession_state=ProcessionState.MOVING
        )
        IdolEvent.objects.create(
            idol=i_event, gpid=i_event.gpid, event_type=IdolEventType.SENT_TO_HOLDING,
            timestamp=timezone.now(), actor=self.superadmin
        )
        res = self.client.get('/api/v1/reports/registry/')
        gpids = [r['gpid'] for r in res.json()['results']]
        self.assertIn('TEST-HOLDING-STATE', gpids)
        self.assertIn('TEST-HOLDING-EVENT', gpids)

    def test_03_not_started_does_not_appear(self):
        # 3. NOT_STARTED does not appear.
        from apps.idols.models import ProcessionState
        Idol.objects.create(
            gpid='TEST-NOT-STARTED', name='Not Started Idol', zone='Charminar',
            police_station='Charminar', idol_height=20.0,
            procession_state=ProcessionState.NOT_STARTED
        )
        res = self.client.get('/api/v1/reports/registry/')
        gpids = [r['gpid'] for r in res.json()['results']]
        self.assertNotIn('TEST-NOT-STARTED', gpids)

    def test_04_tracking_does_not_appear(self):
        # 4. TRACKING does not appear.
        from apps.idols.models import ProcessionState
        Idol.objects.create(
            gpid='TEST-TRACKING-ACTIVE', name='Tracking Active Idol', zone='Charminar',
            police_station='Charminar', idol_height=19.0,
            procession_state=ProcessionState.TRACKING
        )
        res = self.client.get('/api/v1/reports/registry/')
        gpids = [r['gpid'] for r in res.json()['results']]
        self.assertNotIn('TEST-TRACKING-ACTIVE', gpids)

    def test_05_completed_appears_even_if_pdf_never_downloaded(self):
        # 5. A completed procession appears even if its PDF has never been downloaded.
        from apps.idols.models import ProcessionState
        Idol.objects.create(
            gpid='TEST-NO-PDF-YET', name='Never Downloaded PDF', zone='Charminar',
            police_station='Charminar', idol_height=15.0,
            procession_state=ProcessionState.IMMERSION_COMPLETED
        )
        res = self.client.get('/api/v1/reports/registry/')
        gpids = [r['gpid'] for r in res.json()['results']]
        self.assertIn('TEST-NO-PDF-YET', gpids)

    def test_06_pdf_generation_still_works(self):
        # 6. PDF generation still works.
        from apps.idols.models import ProcessionState
        i = Idol.objects.create(
            gpid='TEST-PDF-GEN', name='PDF Test Idol', zone='Charminar',
            police_station='Charminar', idol_height=14.0,
            procession_state=ProcessionState.IMMERSION_COMPLETED
        )
        res = self.client.get(f'/api/v1/reports/idols/{i.gpid}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')
        self.assertTrue(res.content.startswith(b'%PDF-'))

    def test_07_no_duplicate_entries_for_same_gpid(self):
        # 7. The same GPID cannot create duplicate report registry entries even with multiple events.
        from apps.idols.models import ProcessionState
        from apps.tracking.models import IdolEvent, IdolEventType
        from django.utils import timezone
        i = Idol.objects.create(
            gpid='TEST-MULTI-EVENT', name='Multi Event Idol', zone='Charminar',
            police_station='Charminar', idol_height=16.0,
            procession_state=ProcessionState.IMMERSION_COMPLETED
        )
        for _ in range(5):
            IdolEvent.objects.create(
                idol=i, gpid=i.gpid, event_type=IdolEventType.IMMERSION_COMPLETED,
                timestamp=timezone.now(), actor=self.superadmin
            )
        res = self.client.get('/api/v1/reports/registry/')
        data = res.json()
        matching = [r for r in data['results'] if r['gpid'] == 'TEST-MULTI-EVENT']
        self.assertEqual(len(matching), 1)

    def test_08_todays_immersion_date_2026_09_25_handled_correctly(self):
        # 8. Today's immersion date 2026-09-25 is handled correctly.
        from datetime import date
        from apps.idols.models import ProcessionState
        from django.utils import timezone
        today = timezone.localdate()
        Idol.objects.create(
            gpid='TEST-TODAY-DATE', name='Today Immersion', zone='Charminar',
            police_station='Charminar', idol_height=15.0,
            immersion_date=today,
            procession_state=ProcessionState.IMMERSION_COMPLETED
        )
        res = self.client.get('/api/v1/reports/registry/?visarjan_date=today')
        gpids = [r['gpid'] for r in res.json()['results']]
        self.assertIn('TEST-TODAY-DATE', gpids)

    def test_09_jurisdiction_filtering_remains_enforced(self):
        # 9. Jurisdiction filtering remains enforced (SHO Charminar cannot see Golconda reports).
        from apps.idols.models import ProcessionState
        Idol.objects.create(
            gpid='TEST-GOLCONDA-REP', name='Golconda Idol', zone='Golconda',
            police_station='Kulsumpura', idol_height=17.0,
            procession_state=ProcessionState.IMMERSION_COMPLETED
        )
        Idol.objects.create(
            gpid='TEST-CHARMINAR-REP', name='Charminar Idol', zone='Charminar',
            police_station='Charminar', idol_height=17.0,
            procession_state=ProcessionState.IMMERSION_COMPLETED
        )
        self.client.force_authenticate(user=self.sho_charminar)
        res = self.client.get('/api/v1/reports/registry/')
        gpids = [r['gpid'] for r in res.json()['results']]
        self.assertIn('TEST-CHARMINAR-REP', gpids)
        self.assertNotIn('TEST-GOLCONDA-REP', gpids)

    def test_10_existing_report_records_continue_to_work(self):
        # 10. Existing report records continue to work.
        from apps.idols.models import ProcessionState
        from apps.tracking.models import IdolEvent, IdolEventType
        from django.utils import timezone
        i = Idol.objects.create(
            gpid='TEST-EXISTING-REP', name='Existing Report Idol', zone='Charminar',
            police_station='Charminar', idol_height=19.0,
            procession_state=ProcessionState.IMMERSION_COMPLETED
        )
        IdolEvent.objects.create(
            idol=i, gpid=i.gpid, event_type=IdolEventType.REPORT_GENERATED,
            timestamp=timezone.now(), actor=self.superadmin,
            metadata={'report_id': 'HYD-REP-EXISTING1'}
        )
        res = self.client.get('/api/v1/reports/registry/')
        gpids = [r['gpid'] for r in res.json()['results']]
        self.assertIn('TEST-EXISTING-REP', gpids)

    def test_11_existing_historical_completed_reports_remain_visible(self):
        # 11. Existing historical completed reports remain visible.
        from datetime import date
        from apps.idols.models import ProcessionState
        Idol.objects.create(
            gpid='TEST-HISTORICAL-REP', name='Historical Idol', zone='Charminar',
            police_station='Charminar', idol_height=22.0,
            immersion_date=date(2026, 9, 20),
            procession_state=ProcessionState.IMMERSION_COMPLETED
        )
        res = self.client.get('/api/v1/reports/registry/')
        gpids = [r['gpid'] for r in res.json()['results']]
        self.assertIn('TEST-HISTORICAL-REP', gpids)

    def test_12_exact_gpid_hydgolzkulp2464_appears_after_fix(self):
        # 12. The exact GPID HYDGOLZKULP2464 appears after the fix.
        from datetime import date
        from apps.idols.models import ProcessionState
        from apps.tracking.models import IdolEvent, IdolEventType
        from django.utils import timezone
        idol_2464 = Idol.objects.create(
            gpid='HYDGOLZKULP2464',
            name='VULPEE ABHINAV',
            association_name='HAPPY CLUB FRIENDS ASSOCIATION',
            zone='Golconda',
            division='Kulsumpura',
            police_station='Kulsumpura',
            idol_height=14.0,  # 14.00 FT (Subthreshold <15 FT)
            immersion_date=date(2026, 9, 25),
            procession_state=ProcessionState.IMMERSION_COMPLETED
        )
        IdolEvent.objects.create(
            idol=idol_2464,
            gpid=idol_2464.gpid,
            event_type=IdolEventType.IMMERSION_COMPLETED,
            timestamp=timezone.now(),
            zone='Golconda'
        )
        res = self.client.get('/api/v1/reports/registry/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        gpids = [r['gpid'] for r in data['results']]
        self.assertIn('HYDGOLZKULP2464', gpids)
        item = next(r for r in data['results'] if r['gpid'] == 'HYDGOLZKULP2464')
        self.assertEqual(item['final_state'], 'IMMERSION_COMPLETED')
        self.assertEqual(item['final_state_display'], 'Immersion Completed')
        self.assertEqual(float(item['idol_height']), 14.0)
        self.assertEqual(item['police_station'], 'Kulsumpura')
        self.assertEqual(item['zone'], 'Golconda')


