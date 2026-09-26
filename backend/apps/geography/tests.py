from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User, UserRole
from apps.geography.models import PoliceStationBoundary


class GeographyViewsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='geo_admin',
            password='password123',
            role=UserRole.MAIN_OFFICER,
        )
        self.client.force_authenticate(user=self.user)

        PoliceStationBoundary.objects.create(
            ps_name='Charminar PS',
            ps_code='CMNR',
            zone='Charminar',
            division='Charminar',
        )
        PoliceStationBoundary.objects.create(
            ps_name='Banjara Hills PS',
            ps_code='BJRH',
            zone='Jubilee Hills',
            division='Banjara Hills',
        )

    def test_zone_list_view_returns_distinct_zones(self):
        res = self.client.get('/api/v1/geography/zones/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('zones', res.data)
        zones = res.data['zones']
        self.assertIn('Charminar', zones)
        self.assertIn('Jubilee Hills', zones)

    def test_police_stations_filter_by_zone(self):
        res = self.client.get('/api/v1/geography/police-stations/?zone=Charminar')
        self.assertEqual(res.status_code, 200)
        stations = res.data.get('results', res.data)
        self.assertEqual(len(stations), 1)
        self.assertEqual(stations[0]['zone'], 'Charminar')


class LocationJurisdictionServiceTests(TestCase):
    def setUp(self):
        from apps.geography.models import GeocodingCache
        from apps.geography.services import get_bucket

        # Seed test cache entries
        b1_lat, b1_lon = get_bucket(17.37071, 78.49545)
        GeocodingCache.objects.create(
            lat_bucket=b1_lat,
            lon_bucket=b1_lon,
            place_name='Chanchalguda',
            police_station='Dabeerpura PS',
            zone='Charminar',
            division='Dabeerpura'
        )

        b2_lat, b2_lon = get_bucket(17.38074, 78.49163)
        GeocodingCache.objects.create(
            lat_bucket=b2_lat,
            lon_bucket=b2_lon,
            place_name='Malakpet',
            police_station='Malakpet PS',
            zone='Charminar',
            division='Malakpet'
        )

        b3_lat, b3_lon = get_bucket(17.41853, 78.46606)
        GeocodingCache.objects.create(
            lat_bucket=b3_lat,
            lon_bucket=b3_lon,
            place_name="People's Plaza",
            police_station='Khairatabad PS',
            zone='Central',
            division='Khairatabad'
        )

    def test_get_bucket_resolution(self):
        from apps.geography.services import get_bucket
        from decimal import Decimal

        b_lat, b_lon = get_bucket(17.3707123, 78.4954567)
        self.assertEqual(b_lat, Decimal('17.3707'))
        self.assertEqual(b_lon, Decimal('78.4955'))

    def test_extract_place_name_landmarks_and_localities(self):
        from apps.geography.services import extract_place_name

        # 1. Prominent plaza / road
        data1 = {'address': {'road': "People's Plaza", 'suburb': 'Khairatabad'}}
        self.assertEqual(extract_place_name(data1), "People's Plaza, Khairatabad")

        # 2. Local suburb
        data2 = {'address': {'road': 'ibrahim mansion st', 'suburb': 'Dabeerpura'}}
        self.assertEqual(extract_place_name(data2), 'Dabeerpura')

        # 3. Neighbourhood and Suburb
        data3 = {'address': {'road': 'anjuman rd', 'neighbourhood': 'Kala Daira', 'suburb': 'Dabeerpura'}}
        self.assertEqual(extract_place_name(data3), 'Kala Daira, Dabeerpura')

        # 4. Fallback on invalid / empty
        self.assertEqual(extract_place_name({}), 'Location unavailable')
        self.assertEqual(extract_place_name(None), 'Location unavailable')

    def test_resolve_ps_jurisdiction_fallback(self):
        from apps.geography.services import resolve_ps_jurisdiction

        # When boundary polygon is missing or unpopulated, returns 'Jurisdiction unavailable'
        ps, zone, div = resolve_ps_jurisdiction(17.37071, 78.49545)
        self.assertEqual(ps, 'Jurisdiction unavailable')

    def test_bulk_get_cached_locations_zero_network(self):
        from apps.geography.services import bulk_get_cached_locations, get_bucket

        coords = [
            (17.37071, 78.49545),
            (17.38074, 78.49163),
            (17.41853, 78.46606),
            (17.99999, 78.99999),  # Uncached point
        ]

        results = bulk_get_cached_locations(coords)

        # Cached points resolved correctly
        b1 = get_bucket(17.37071, 78.49545)
        self.assertEqual(results[b1][0], 'Chanchalguda')
        self.assertEqual(results[b1][1], 'Dabeerpura PS')

        b2 = get_bucket(17.38074, 78.49163)
        self.assertEqual(results[b2][0], 'Malakpet')
        self.assertEqual(results[b2][1], 'Malakpet PS')

        b3 = get_bucket(17.41853, 78.46606)
        self.assertEqual(results[b3][0], "People's Plaza")
        self.assertEqual(results[b3][1], 'Khairatabad PS')

        # Uncached point safely falls back without throwing error or calling network
        b_miss = get_bucket(17.99999, 78.99999)
        self.assertEqual(results[b_miss][0], 'Location unavailable')
        self.assertEqual(results[b_miss][1], 'Jurisdiction unavailable')
