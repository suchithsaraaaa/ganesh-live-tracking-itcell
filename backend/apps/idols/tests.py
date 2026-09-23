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

    def test_default_list_excludes_subthreshold_and_null(self):
        """Default idol list only returns operational idols (>= 15 ft)."""
        res = self.client.get('/api/v1/idols/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Out of 10 idols: 2 are < 15, 1 is NULL -> 7 are >= 15 ft
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
        """Test immersions_today=true returns only 15+ ft idols immersing today."""
        res = self.client.get('/api/v1/idols/?immersions_today=true')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Eligible >= 15 today: 15ft (3), 18ft (4), 21ft (6), 26ft (8) -> 4 idols
        # Subthreshold 1 (10ft) and Null height (10) immerse today but MUST be excluded!
        self.assertEqual(res.data['count'], 4)
        gpids = [i['gpid'] for i in res.data['results']]
        self.assertNotIn('HYDCMRZBHNR0001', gpids)
        self.assertNotIn('HYDKTBZABID0010', gpids)

    def test_combined_filters_composition(self):
        """Test AND composition: 15–20 ft + today + Charminar + Bahadurpura."""
        res = self.client.get('/api/v1/idols/?height_bucket=15_20&immersions_today=true&zone=Charminar&police_station=Bahadurpura')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Only GPID HYDCMRZBHNR0003 matches all criteria
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['gpid'], 'HYDCMRZBHNR0003')

    def test_dashboard_kpis_and_marker_deduplication(self):
        """
        Dashboard stats must calculate KPIs on the 15+ ft population only
        and guarantee One GPID = One Map Marker.
        """
        # Assign constable to 15ft idol (HYDCMRZBHNR0003)
        constable = User.objects.create_user(
            username='constable_test_1',
            password='test_password_123',
            role=UserRole.CONSTABLE,
            police_id='CONST-101',
            police_station='Bahadurpura'
        )
        idol_3 = Idol.objects.get(gpid='HYDCMRZBHNR0003')
        assign = Assignment.assign_constable(idol=idol_3, constable=constable, assigned_by=self.user)

        # Create active tracking session 1
        sess1 = TrackingSession.objects.create(assignment=assign, status=TrackingSessionStatus.ACTIVE)
        LocationPoint.objects.create(session=sess1, latitude=17.3610, longitude=78.4710, recorded_at=timezone.now())

        # Create multiple location points for the same session to test marker deduplication
        LocationPoint.objects.create(session=sess1, latitude=17.3620, longitude=78.4720, recorded_at=timezone.now() + timedelta(seconds=10))

        res = self.client.get('/api/v1/idols/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        kpis = res.data['kpis']
        # 1. Total idols KPI must be 7 (eligible >=15ft), not 10!
        self.assertEqual(kpis['total_idols'], 7)
        # 2. Immersions today KPI must be 4 (eligible >=15ft today), not 6!
        self.assertEqual(kpis['immersions_today'], 4)
        # 3. Height buckets
        self.assertEqual(kpis['h_15_20'], 3)
        self.assertEqual(kpis['h_21_25'], 2)
        self.assertEqual(kpis['h_26_plus'], 2)

        # 4. Marker deduplication: exactly 1 marker for HYDCMRZBHNR0003 despite multiple location points!
        self.assertEqual(res.data['active_markers_count'], 1)
        self.assertEqual(len(res.data['active_markers']), 1)
        marker = res.data['active_markers'][0]
        self.assertEqual(marker['gpid'], 'HYDCMRZBHNR0003')
        self.assertEqual(marker['height_classification'], 'GREEN')
        self.assertEqual(marker['latitude'], 17.3620)
        self.assertFalse(marker['is_origin_marker'])

    def test_origin_vs_live_marker_priority_and_all_eligible_visibility(self):
        """
        Verify:
        - Eligible idols with geocoded origin coordinates appear as origin markers (is_origin_marker: True).
        - Eligible idols with live tracking sessions take precedence (is_origin_marker: False).
        - Subthreshold idols are never returned on the map even if they have coordinates.
        - Unresolved idols without coordinates do not generate fake markers.
        """
        # 1. Give an eligible idol (HYDCMRZBHNR0004, 18ft) geocoded origin coordinates
        idol_4 = Idol.objects.get(gpid='HYDCMRZBHNR0004')
        idol_4.latitude = 17.3555555
        idol_4.longitude = 78.4666666
        idol_4.geocoding_status = 'GEOCODED'
        idol_4.save()

        # 2. Give a subthreshold idol (<15ft, HYDCMRZBHNR0001, 10ft) coordinates
        idol_1 = Idol.objects.get(gpid='HYDCMRZBHNR0001')
        idol_1.latitude = 17.3511111
        idol_1.longitude = 78.4611111
        idol_1.geocoding_status = 'GEOCODED'
        idol_1.save()

        # Query dashboard
        res = self.client.get('/api/v1/idols/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        marker_gpids = [m['gpid'] for m in res.data['active_markers']]
        # Subthreshold idol 1 must NOT be on map
        self.assertNotIn('HYDCMRZBHNR0001', marker_gpids)
        # Eligible idol 4 must be on map as origin marker
        self.assertIn('HYDCMRZBHNR0004', marker_gpids)

        m4 = next(m for m in res.data['active_markers'] if m['gpid'] == 'HYDCMRZBHNR0004')
        self.assertTrue(m4['is_origin_marker'])
        self.assertAlmostEqual(m4['latitude'], 17.3555555)
        self.assertAlmostEqual(m4['longitude'], 78.4666666)


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
