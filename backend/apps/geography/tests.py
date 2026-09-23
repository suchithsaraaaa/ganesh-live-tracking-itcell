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
