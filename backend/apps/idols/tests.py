from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from django.db import IntegrityError
from rest_framework.test import APIClient
from rest_framework import status

from apps.idols.models import Idol, ImportRun, ImportIssue, ImportIssueType
from apps.idols.views import get_height_classification
from apps.accounts.models import User, UserRole
from apps.assignments.models import Assignment
from apps.tracking.models import TrackingSession, LocationPoint, TrackingSessionStatus


class IdolModelTests(TestCase):
    def test_create_idol_with_gpid(self):
        idol = Idol.objects.create(
            gpid='HYDCMRZCMNR0112',
            ref_no='REF1001',
            name='Vinayaka Association',
            zone='Charminar',
            division='Charminar',
            police_station='Charminar',
            ps_code='CMNR'
        )
        self.assertEqual(str(idol), 'HYDCMRZCMNR0112 - Vinayaka Association')
        self.assertEqual(idol.procession_state, 'NOT_STARTED')

    def test_gpid_uniqueness_enforced_at_db_level(self):
        Idol.objects.create(
            gpid='HYDCMRZCMNR0112',
            name='First Idol'
        )
        with self.assertRaises(IntegrityError):
            Idol.objects.create(
                gpid='HYDCMRZCMNR0112',
                name='Duplicate Idol'
            )

    def test_import_issue_creation(self):
        run = ImportRun.objects.create(file_name='test.xls', total_rows=10)
        issue = ImportIssue.objects.create(
            import_run=run,
            row_number=5,
            gpid='',
            issue_type=ImportIssueType.MISSING_GPID,
            error_message='Source record has no GPID.'
        )
        self.assertEqual(run.issues.count(), 1)
        self.assertEqual(issue.issue_type, ImportIssueType.MISSING_GPID)


class IdolHeightClassificationTests(TestCase):
    """
    Verification of Section 58 Height Test Matrix:
    - < 15.00 -> SUBTHRESHOLD (excluded)
    - 15.00 <= height < 21.00 -> GREEN (15–20 ft band)
    - 21.00 <= height < 26.00 -> YELLOW (21–25 ft band)
    - height >= 26.00 -> RED (26+ ft band)
    - NULL -> UNKNOWN (excluded)
    """
    def test_height_classification_matrix(self):
        self.assertEqual(get_height_classification(14.00), 'SUBTHRESHOLD')
        self.assertEqual(get_height_classification(14.99), 'SUBTHRESHOLD')
        self.assertEqual(get_height_classification(15.00), 'GREEN')
        self.assertEqual(get_height_classification(15.01), 'GREEN')
        self.assertEqual(get_height_classification(20.00), 'GREEN')
        self.assertEqual(get_height_classification(20.99), 'GREEN')
        self.assertEqual(get_height_classification(21.00), 'YELLOW')
        self.assertEqual(get_height_classification(21.01), 'YELLOW')
        self.assertEqual(get_height_classification(25.00), 'YELLOW')
        self.assertEqual(get_height_classification(25.99), 'YELLOW')
        self.assertEqual(get_height_classification(26.00), 'RED')
        self.assertEqual(get_height_classification(30.00), 'RED')
        self.assertEqual(get_height_classification(69.00), 'RED')
        self.assertEqual(get_height_classification(None), 'UNKNOWN')


class IdolOperationalFilterAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='main_test_officer',
            password='test_password_123',
            role=UserRole.MAIN_OFFICER,
            police_id='POL-001',
            zone='All',
            division='All',
            police_station='All'
        )
        self.client.force_authenticate(user=self.user)

        self.today = timezone.localdate()
        self.yesterday = self.today - timedelta(days=1)
        self.tomorrow = self.today + timedelta(days=1)

        # 1. Idol below threshold (10 ft) - Today
        Idol.objects.create(
            gpid='HYDCMRZBHNR0001',
            name='Subthreshold 1',
            idol_height=10.0,
            immersion_date=self.today,
            zone='Charminar',
            police_station='Bahadurpura'
        )
        # 2. Idol below threshold (14.99 ft) - Yesterday
        Idol.objects.create(
            gpid='HYDCMRZBHNR0002',
            name='Subthreshold 2',
            idol_height=14.99,
            immersion_date=self.yesterday,
            zone='Charminar',
            police_station='Bahadurpura'
        )
        # 3. Idol 15 ft (Green) - Today
        Idol.objects.create(
            gpid='HYDCMRZBHNR0003',
            name='Green 15ft',
            idol_height=15.0,
            immersion_date=self.today,
            zone='Charminar',
            police_station='Bahadurpura'
        )
        # 4. Idol 18 ft (Green) - Today
        Idol.objects.create(
            gpid='HYDCMRZBHNR0004',
            name='Green 18ft',
            idol_height=18.0,
            immersion_date=self.today,
            zone='Charminar',
            police_station='Charminar'
        )
        # 5. Idol 20 ft (Green) - Tomorrow
        Idol.objects.create(
            gpid='HYDGLKZGOLC0005',
            name='Green 20ft',
            idol_height=20.0,
            immersion_date=self.tomorrow,
            zone='Golconda',
            police_station='Golconda'
        )
        # 6. Idol 21 ft (Yellow) - Today
        Idol.objects.create(
            gpid='HYDGLKZGOLC0006',
            name='Yellow 21ft',
            idol_height=21.0,
            immersion_date=self.today,
            zone='Golconda',
            police_station='Golconda'
        )
        # 7. Idol 25 ft (Yellow) - Yesterday
        Idol.objects.create(
            gpid='HYDGLKZGOLC0007',
            name='Yellow 25ft',
            idol_height=25.0,
            immersion_date=self.yesterday,
            zone='Golconda',
            police_station='Golconda'
        )
        # 8. Idol 26 ft (Red) - Today
        Idol.objects.create(
            gpid='HYDKTBZABID0008',
            name='Red 26ft',
            idol_height=26.0,
            immersion_date=self.today,
            zone='Khairatabad',
            police_station='Abids'
        )
        # 9. Idol 30 ft (Red) - Tomorrow
        Idol.objects.create(
            gpid='HYDKTBZABID0009',
            name='Red 30ft',
            idol_height=30.0,
            immersion_date=self.tomorrow,
            zone='Khairatabad',
            police_station='Abids'
        )
        # 10. Idol with NULL height
        Idol.objects.create(
            gpid='HYDKTBZABID0010',
            name='Null Height',
            idol_height=None,
            immersion_date=self.today,
            zone='Khairatabad',
            police_station='Abids'
        )
        # 11. Idol 14 ft (Below 15ft) - Today
        Idol.objects.create(
            gpid='HYDCMRZBHNR0011',
            name='Subthreshold 14ft',
            idol_height=14.0,
            immersion_date=self.today,
            zone='Charminar',
            police_station='Bahadurpura'
        )

    def test_default_list_excludes_subthreshold_and_null(self):
        """Default idol list (/api/v1/idols/) still returns operational idols (>= 15 ft)."""
        res = self.client.get('/api/v1/idols/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Out of 11 idols: 3 are < 15 (10ft, 14ft, 14.99ft), 1 is NULL -> 7 are >= 15 ft
        self.assertEqual(res.data['count'], 7)
        for item in res.data['results']:
            self.assertGreaterEqual(float(item['idol_height']), 15.0)
            self.assertTrue(item['is_operational_eligible'])

    def test_height_bucket_15_20(self):
        """Test height_bucket=15_20 returns only green 15–20 ft idols."""
        res = self.client.get('/api/v1/idols/?height_bucket=15_20')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # 15ft, 18ft, 20ft -> 3 idols
        self.assertEqual(res.data['count'], 3)
        for item in res.data['results']:
            self.assertEqual(item['height_classification'], 'GREEN')

    def test_height_bucket_21_25(self):
        """Test height_bucket=21_25 returns only yellow 21–25 ft idols."""
        res = self.client.get('/api/v1/idols/?height_bucket=21_25')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # 21ft, 25ft -> 2 idols
        self.assertEqual(res.data['count'], 2)
        for item in res.data['results']:
            self.assertEqual(item['height_classification'], 'YELLOW')

    def test_height_bucket_above_25(self):
        """Test height_bucket=above_25 returns only red 26+ ft idols."""
        res = self.client.get('/api/v1/idols/?height_bucket=above_25')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # 26ft, 30ft -> 2 idols
        self.assertEqual(res.data['count'], 2)
        for item in res.data['results']:
            self.assertEqual(item['height_classification'], 'RED')

    def test_immersions_today_filter(self):
        """Test immersions_today=true returns only 15+ ft idols immersing today for list view."""
        res = self.client.get('/api/v1/idols/?immersions_today=true')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Eligible >= 15 today: 15ft (3), 18ft (4), 21ft (6), 26ft (8) -> 4 idols
        self.assertEqual(res.data['count'], 4)
        gpids = [i['gpid'] for i in res.data['results']]
        self.assertNotIn('HYDCMRZBHNR0001', gpids)
        self.assertNotIn('HYDCMRZBHNR0011', gpids)
        self.assertNotIn('HYDKTBZABID0010', gpids)

    def test_combined_filters_composition(self):
        """Test AND composition: 15–20 ft + today + Charminar + Bahadurpura."""
        res = self.client.get('/api/v1/idols/?height_bucket=15_20&immersions_today=true&zone=Charminar&police_station=Bahadurpura')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Only GPID HYDCMRZBHNR0003 matches all criteria
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['gpid'], 'HYDCMRZBHNR0003')

    def test_main_dashboard_today_visarjan_across_all_heights(self):
        """
        Main Dashboard must show ALL authoritative GPIDs whose immersion_date is TODAY
        across all heights (10ft, 14ft, 15ft, 18ft, 21ft, 26ft, NULL).
        Yesterday and tomorrow idols must NOT appear in today's dashboard population.
        """
        res = self.client.get('/api/v1/idols/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        kpis = res.data['kpis']
        # Today idols: 10ft (1), 14ft (11), 15ft (3), 18ft (4), 21ft (6), 26ft (8), NULL (10) -> exactly 7 idols!
        self.assertEqual(kpis['total_idols'], 7)
        self.assertEqual(kpis['immersions_today'], 7)

        # Height distribution across today's complete population
        self.assertEqual(kpis['h_below_15'], 3)  # 10ft, 14ft, NULL
        self.assertEqual(kpis['h_15_20'], 2)     # 15ft, 18ft
        self.assertEqual(kpis['h_21_25'], 1)     # 21ft
        self.assertEqual(kpis['h_26_plus'], 1)   # 26ft

    def test_yesterday_and_tomorrow_excluded_from_main_dashboard(self):
        """Yesterday and tomorrow idols must NOT be included in today's population."""
        res = self.client.get('/api/v1/idols/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Check zone totals for today
        zone_stats = {z['zone']: z['total'] for z in res.data['zone_stats']}
        # Yesterday's 14.99ft in Charminar, 25ft in Golconda must be excluded
        # Tomorrow's 20ft in Golconda, 30ft in Khairatabad must be excluded
        # Today in Charminar: 10ft, 14ft, 15ft, 18ft -> 4
        # Today in Golconda: 21ft -> 1
        # Today in Khairatabad: 26ft, NULL -> 2
        self.assertEqual(zone_stats.get('Charminar'), 4)
        self.assertEqual(zone_stats.get('Golconda'), 1)
        self.assertEqual(zone_stats.get('Khairatabad'), 2)

    def test_today_gpid_without_coordinates_has_no_fabricated_map_marker(self):
        """
        Today's GPIDs without valid coordinates remain in population/KPIs,
        but must NOT have fabricated map markers.
        """
        res = self.client.get('/api/v1/idols/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # None of the setUp idols have coordinates yet, and no active tracking session
        self.assertEqual(res.data['kpis']['total_idols'], 7)
        self.assertEqual(res.data['active_markers_count'], 0)
        self.assertEqual(len(res.data['active_markers']), 0)

    def test_today_gpid_with_valid_coordinates_gets_map_marker(self):
        """
        Today's idols across all heights with valid coordinates get map markers.
        """
        # Give 10ft idol (HYDCMRZBHNR0001) coordinates
        idol_1 = Idol.objects.get(gpid='HYDCMRZBHNR0001')
        idol_1.latitude = 17.3510
        idol_1.longitude = 78.4610
        idol_1.geocoding_status = 'GEOCODED'
        idol_1.save()

        # Give 18ft idol (HYDCMRZBHNR0004) coordinates
        idol_4 = Idol.objects.get(gpid='HYDCMRZBHNR0004')
        idol_4.latitude = 17.3550
        idol_4.longitude = 78.4660
        idol_4.geocoding_status = 'GEOCODED'
        idol_4.save()

        # Give tomorrow's idol (HYDGLKZGOLC0005) coordinates
        idol_5 = Idol.objects.get(gpid='HYDGLKZGOLC0005')
        idol_5.latitude = 17.3800
        idol_5.longitude = 78.4200
        idol_5.geocoding_status = 'GEOCODED'
        idol_5.save()

        res = self.client.get('/api/v1/idols/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        marker_gpids = [m['gpid'] for m in res.data['active_markers']]
        # Today's idols with coordinates appear on map
        self.assertIn('HYDCMRZBHNR0001', marker_gpids)
        self.assertIn('HYDCMRZBHNR0004', marker_gpids)
        # Tomorrow's idol does NOT appear on map
        self.assertNotIn('HYDGLKZGOLC0005', marker_gpids)
        # 10ft idol has SUBTHRESHOLD classification
        m1 = next(m for m in res.data['active_markers'] if m['gpid'] == 'HYDCMRZBHNR0001')
        self.assertEqual(m1['height_classification'], 'SUBTHRESHOLD')

    def test_dashboard_height_filters_on_today_population(self):
        """Height filters applied on Main Dashboard filter today's population."""
        # Below 15ft: 10ft, 14ft, NULL -> 3
        res = self.client.get('/api/v1/idols/dashboard/?height_bucket=below_15')
        self.assertEqual(res.data['kpis']['total_idols'], 3)

        # 15–20ft: 15ft, 18ft -> 2
        res = self.client.get('/api/v1/idols/dashboard/?height_bucket=15_20')
        self.assertEqual(res.data['kpis']['total_idols'], 2)

        # 21–25ft: 21ft -> 1
        res = self.client.get('/api/v1/idols/dashboard/?height_bucket=21_25')
        self.assertEqual(res.data['kpis']['total_idols'], 1)

        # 26+ ft: 26ft -> 1
        res = self.client.get('/api/v1/idols/dashboard/?height_bucket=above_25')
        self.assertEqual(res.data['kpis']['total_idols'], 1)

        # ALL: all 7
        res = self.client.get('/api/v1/idols/dashboard/?height_bucket=ALL')
        self.assertEqual(res.data['kpis']['total_idols'], 7)

    def test_dashboard_active_tracking_session_marker_priority(self):
        """Active tracking sessions take marker precedence and deduplicate properly."""
        constable = User.objects.create_user(
            username='constable_dash_1',
            password='test_password_123',
            role=UserRole.CONSTABLE,
            police_id='CONST-201',
            police_station='Bahadurpura'
        )
        idol_3 = Idol.objects.get(gpid='HYDCMRZBHNR0003')
        assign = Assignment.assign_constable(idol=idol_3, constable=constable, assigned_by=self.user)

        sess = TrackingSession.objects.create(assignment=assign, status=TrackingSessionStatus.ACTIVE)
        LocationPoint.objects.create(session=sess, latitude=17.3610, longitude=78.4710, recorded_at=timezone.now())
        LocationPoint.objects.create(session=sess, latitude=17.3620, longitude=78.4720, recorded_at=timezone.now() + timedelta(seconds=10))

        res = self.client.get('/api/v1/idols/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data['active_markers_count'], 1)
        marker = res.data['active_markers'][0]
        self.assertEqual(marker['gpid'], 'HYDCMRZBHNR0003')
        self.assertFalse(marker['is_origin_marker'])
        self.assertEqual(marker['latitude'], 17.3620)


class GeocodingServiceTests(TestCase):
    def test_sanitize_address_strips_house_numbers(self):
        from apps.idols.services.geocoding import sanitize_address_for_geocoding
        raw_1 = "H.No 21-4-330/1, Ghansi Bazar, Charminar"
        cleaned_1 = sanitize_address_for_geocoding(raw_1)
        self.assertNotIn("21-4-330/1", cleaned_1)
        self.assertIn("Ghansi Bazar", cleaned_1)
        self.assertIn("Charminar", cleaned_1)

        raw_2 = "Plot No 45, Road No 12, Banjara Hills"
        cleaned_2 = sanitize_address_for_geocoding(raw_2)
        self.assertNotIn("Plot No", cleaned_2)
        self.assertIn("Banjara Hills", cleaned_2)

    def test_mock_geocoder_resolves_within_hyderabad_bounds(self):
        from apps.idols.services.geocoding import MockGeocoder, is_within_hyderabad_bounds
        geocoder = MockGeocoder()
        lat, lon, name, kind = geocoder.geocode_query("Charminar, Hyderabad")
        self.assertTrue(is_within_hyderabad_bounds(lat, lon))
        self.assertTrue(17.15 <= lat <= 17.70)
        self.assertTrue(78.15 <= lon <= 78.75)

    def test_pin_code_and_landmarks_preserved_in_sanitization(self):
        from apps.idols.services.geocoding import sanitize_address_for_geocoding
        raw = "H.No 18-3-465 Near Mahankali Temple, Lal Darwaza, 500053"
        cleaned = sanitize_address_for_geocoding(raw)
        self.assertIn("500053", cleaned, "PIN code must NOT be stripped from address")
        self.assertIn("Mahankali Temple", cleaned, "Landmark must be preserved")
        self.assertIn("Lal Darwaza", cleaned)

    def test_latitude_longitude_order_no_reversal(self):
        """
        Explicitly assert latitude = 17.xx (North) and longitude = 78.xx (East).
        Never reversed.
        """
        from apps.idols.services.geocoding import geocode_idol, MockGeocoder
        idol = Idol.objects.create(
            gpid='HYDTESTGEO001',
            address='Lal Darwaza, 500053',
            instal_street='Ganesh Nagar',
            instal_village='Lal Darwaza',
            instal_pin='500053',
            police_station='Chatrinaka'
        )
        res = geocode_idol(idol, geocoder=MockGeocoder())
        self.assertIsNotNone(res['latitude'])
        self.assertIsNotNone(res['longitude'])
        lat = float(res['latitude'])
        lon = float(res['longitude'])

        # Latitude must be ~17 (Hyderabad North)
        self.assertTrue(17.0 <= lat <= 18.0, f"Latitude was {lat}, expected ~17.xx (possible reversal!)")
        # Longitude must be ~78 (Hyderabad East)
        self.assertTrue(78.0 <= lon <= 79.0, f"Longitude was {lon}, expected ~78.xx (possible reversal!)")

    def test_generic_city_centroid_rejected(self):
        """
        Verify that Mecca Masjid / generic Charminar city centroid (17.360589, 78.4740613)
        is rejected and never assigned as a valid idol location.
        """
        from apps.idols.services.geocoding import score_candidate, CITY_CENTROID_LAT, CITY_CENTROID_LON
        idol = Idol.objects.create(
            gpid='HYDTESTCENTROID',
            instal_street='Random Street',
            instal_pin='500018'
        )
        fake_centroid_cand = {
            'lat': str(CITY_CENTROID_LAT),
            'lon': str(CITY_CENTROID_LON),
            'display_name': 'Hyderabad, Telangana, India',
            'type': 'city',
            'address': {'state': 'Telangana', 'city': 'Hyderabad'}
        }
        scored = score_candidate(fake_centroid_cand, idol, 'street')
        self.assertIsNone(scored, "Generic city centroid must be rejected!")

    def test_out_of_state_candidate_rejected(self):
        """
        Candidates from outside Telangana (e.g. Karnataka JP Nagar) must be rejected.
        """
        from apps.idols.services.geocoding import score_candidate
        idol = Idol.objects.create(
            gpid='HYDTESTOUTSTATE',
            instal_street='JP Nagar',
            instal_pin='500053'
        )
        karnataka_cand = {
            'lat': '12.9096941',
            'lon': '77.5866067',
            'display_name': 'JP Nagar, Bengaluru, Karnataka, India',
            'type': 'suburb',
            'address': {'state': 'Karnataka', 'city': 'Bengaluru'}
        }
        scored = score_candidate(karnataka_cand, idol, 'street')
        self.assertIsNone(scored, "Out-of-state candidates must be rejected!")

    def test_confidence_classification(self):
        from apps.idols.services.geocoding import score_candidate
        from apps.idols.models import GeocodingConfidence
        idol = Idol.objects.create(
            gpid='HYDTESTCONF',
            instal_street='Temple Road',
            instal_pin='500053'
        )
        exact_cand = {
            'lat': '17.3450', 'lon': '78.4750',
            'display_name': 'Hanuman Temple, Lal Darwaza',
            'type': 'place_of_worship',
            'address': {'state': 'Telangana', 'postcode': '500053'}
        }
        scored = score_candidate(exact_cand, idol, 'street')
        self.assertIsNotNone(scored)
        self.assertEqual(scored[4], GeocodingConfidence.EXACT)

        high_cand = {
            'lat': '17.3450', 'lon': '78.4750',
            'display_name': 'Temple Road, Lal Darwaza',
            'type': 'residential',
            'address': {'state': 'Telangana', 'postcode': '500053'}
        }
        scored_high = score_candidate(high_cand, idol, 'street')
        self.assertIsNotNone(scored_high)
        self.assertEqual(scored_high[4], GeocodingConfidence.HIGH)


class HoldingPointsConsistencyTests(TestCase):
    """
    Regression test suite for authoritative 'IN HOLDING' consistency across:
    - Main Dashboard KPIs
    - Main Dashboard Active Markers / Active Processions Table
    - Holding Points Page API (/api/v1/idols/?procession_state=HOLDING)
    - Jurisdiction Scoping
    - Backward-compatibility with sub-15ft operational states
    """
    def setUp(self):
        self.client = APIClient()
        self.super_admin = User.objects.create_user(
            username='admin_holding_test',
            password='test_password_123',
            role=UserRole.SUPER_ADMIN,
            police_id='ADM-001'
        )
        self.sec_admin = User.objects.create_user(
            username='sec_admin_test',
            password='test_password_123',
            role=UserRole.SYS_ADMIN,
            police_id='SEC-ADM-001',
            zone='Secunderabad'
        )
        self.rn_admin = User.objects.create_user(
            username='rn_admin_test',
            password='test_password_123',
            role=UserRole.SYS_ADMIN,
            police_id='RN-ADM-001',
            zone='Rajendra Nagar'
        )
        self.today = timezone.localdate()

        # 1. Held idol (sub-15ft: 12 FT, Amberpet, Secunderabad) - mimics production record HYDSECZAMBT1702
        self.idol_holding_sec = Idol.objects.create(
            gpid='HYDSECZAMBT1702',
            name='Raghavender reddy',
            zone='Secunderabad',
            police_station='Amberpet',
            ps_code='AMBT',
            idol_height=12.0,
            immersion_date=self.today,
            procession_state='HOLDING'
        )
        # Create assignment, tracking session, and GPS points
        constable = User.objects.create_user(
            username='constable_holding_1',
            password='test_password_123',
            role=UserRole.CONSTABLE,
            police_id='CONST-001'
        )
        asgn = Assignment.objects.create(
            idol=self.idol_holding_sec,
            constable=constable,
            is_active=True
        )
        sess = TrackingSession.objects.create(
            assignment=asgn,
            status=TrackingSessionStatus.STOPPED,
            started_at=timezone.now() - timedelta(minutes=30),
            ended_at=timezone.now() - timedelta(minutes=10)
        )
        LocationPoint.objects.create(
            session=sess,
            latitude=17.3870,
            longitude=78.5248,
            speed=0.0,
            recorded_at=timezone.now() - timedelta(minutes=11)
        )

        # 2. Moving idol (18 FT, Secunderabad)
        self.idol_moving_sec = Idol.objects.create(
            gpid='HYDSECZAMBT1800',
            name='Moving Ganesh',
            zone='Secunderabad',
            police_station='Amberpet',
            ps_code='AMBT',
            idol_height=18.0,
            immersion_date=self.today,
            procession_state='MOVING',
            latitude=17.3820,
            longitude=78.5270
        )

        # 3. Not started idol (10 FT, Secunderabad)
        self.idol_not_started = Idol.objects.create(
            gpid='HYDSECZAMBT1000',
            name='Small Unstarted Ganesh',
            zone='Secunderabad',
            police_station='Amberpet',
            ps_code='AMBT',
            idol_height=10.0,
            immersion_date=self.today,
            procession_state='NOT_STARTED'
        )

        # 4. Immersed idol (22 FT, Secunderabad)
        self.idol_immersed = Idol.objects.create(
            gpid='HYDSECZAMBT2200',
            name='Immersed Ganesh',
            zone='Secunderabad',
            police_station='Amberpet',
            ps_code='AMBT',
            idol_height=22.0,
            immersion_date=self.today,
            procession_state='IMMERSION_COMPLETED',
            latitude=17.3810,
            longitude=78.5260
        )

    def test_gpid_in_holding_appears_in_dashboard_kpi_and_holding_points(self):
        """Holding GPID (even sub-15ft) appears in Dashboard KPI and Holding Points API with equal counts."""
        self.client.force_authenticate(user=self.super_admin)

        # A. Main Dashboard API
        res_dash = self.client.get('/api/v1/idols/dashboard/')
        self.assertEqual(res_dash.status_code, status.HTTP_200_OK)
        dash_holding_kpi = res_dash.data['kpis']['holding']
        self.assertEqual(dash_holding_kpi, 1)

        # Active markers includes holding idol with its GPS location
        markers = res_dash.data['active_markers']
        marker_gpids = [m['gpid'] for m in markers]
        self.assertIn(self.idol_holding_sec.gpid, marker_gpids)
        holding_marker = next(m for m in markers if m['gpid'] == self.idol_holding_sec.gpid)
        self.assertEqual(holding_marker['procession_state'], 'HOLDING')
        self.assertAlmostEqual(holding_marker['latitude'], 17.3870, places=4)
        self.assertAlmostEqual(holding_marker['longitude'], 78.5248, places=4)

        # B. Holding Points Page API (/api/v1/idols/?procession_state=HOLDING)
        res_holding = self.client.get('/api/v1/idols/?procession_state=HOLDING')
        self.assertEqual(res_holding.status_code, status.HTTP_200_OK)
        holding_count = res_holding.data['count']
        holding_gpids = [item['gpid'] for item in res_holding.data['results']]

        self.assertEqual(dash_holding_kpi, holding_count)
        self.assertEqual(holding_count, 1)
        self.assertIn(self.idol_holding_sec.gpid, holding_gpids)

    def test_non_holding_gpids_do_not_appear_in_holding_points(self):
        """MOVING, NOT_STARTED, and IMMERSION_COMPLETED idols do not appear in holding query."""
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get('/api/v1/idols/?procession_state=HOLDING')
        holding_gpids = [item['gpid'] for item in res.data['results']]

        self.assertNotIn(self.idol_moving_sec.gpid, holding_gpids)
        self.assertNotIn(self.idol_not_started.gpid, holding_gpids)
        self.assertNotIn(self.idol_immersed.gpid, holding_gpids)

    def test_jurisdiction_scoping_on_holding_data(self):
        """Holding data is properly scoped by caller jurisdiction."""
        # 1. Secunderabad Admin sees 1 holding idol
        self.client.force_authenticate(user=self.sec_admin)
        res_sec_dash = self.client.get('/api/v1/idols/dashboard/')
        self.assertEqual(res_sec_dash.data['kpis']['holding'], 1)
        res_sec_list = self.client.get('/api/v1/idols/?procession_state=HOLDING')
        self.assertEqual(res_sec_list.data['count'], 1)
        self.assertEqual(res_sec_list.data['results'][0]['gpid'], self.idol_holding_sec.gpid)

        # 2. Rajendra Nagar Admin sees 0 holding idols
        self.client.force_authenticate(user=self.rn_admin)
        res_rn_dash = self.client.get('/api/v1/idols/dashboard/')
        self.assertEqual(res_rn_dash.data['kpis']['holding'], 0)
        res_rn_list = self.client.get('/api/v1/idols/?procession_state=HOLDING')
        self.assertEqual(res_rn_list.data['count'], 0)

    def test_general_registry_browsing_still_excludes_sub_15ft(self):
        """General idol list (/api/v1/idols/ without state filter) preserves standard >= 15 FT threshold."""
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get('/api/v1/idols/')
        gpids = [item['gpid'] for item in res.data['results']]

        # 18ft and 22ft included
        self.assertIn(self.idol_moving_sec.gpid, gpids)
        self.assertIn(self.idol_immersed.gpid, gpids)
        # 10ft unstarted and 12ft (sub-15ft in general browsing) excluded
        self.assertNotIn(self.idol_not_started.gpid, gpids)
        self.assertNotIn(self.idol_holding_sec.gpid, gpids)

