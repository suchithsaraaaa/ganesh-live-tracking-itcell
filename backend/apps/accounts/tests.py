from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User, UserRole
from apps.idols.models import Idol


class RBACAndJurisdictionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Users
        self.main_officer = User.objects.create_user(
            username='main_officer', password='password123',
            role=UserRole.MAIN_OFFICER
        )
        self.acp_charminar = User.objects.create_user(
            username='acp_cmr', password='password123',
            role=UserRole.ACP, division='Charminar'
        )
        self.sho_charminar = User.objects.create_user(
            username='sho_cmr', password='password123',
            role=UserRole.SHO, police_station='Charminar'
        )
        self.sho_malakpet = User.objects.create_user(
            username='sho_mlp', password='password123',
            role=UserRole.SHO, police_station='Malakpet'
        )
        self.constable = User.objects.create_user(
            username='pc_101', password='password123',
            role=UserRole.CONSTABLE, police_id='PC-101'
        )

        # Idols in different police stations
        self.idol_cmr = Idol.objects.create(
            gpid='HYDCMRZCMNR0112',
            name='Charminar Ganesh',
            police_station='Charminar',
            division='Charminar',
            zone='Charminar',
            raw_metadata={'mobile_no': '9876543210'}
        )
        self.idol_mlp = Idol.objects.create(
            gpid='HYDCMRZMLPT0112',
            name='Malakpet Ganesh',
            police_station='Malakpet',
            division='Malakpet',
            zone='Charminar',
            raw_metadata={'mobile_no': '9123456780'}
        )

    def test_sho_jurisdiction_restricted_to_own_ps(self):
        self.client.force_authenticate(user=self.sho_charminar)
        res = self.client.get(reverse('idol-list'))
        self.assertEqual(res.status_code, 200)
        gpids = [item['gpid'] for item in res.data['results']]
        self.assertIn('HYDCMRZCMNR0112', gpids)
        self.assertNotIn('HYDCMRZMLPT0112', gpids)

    def test_main_officer_sees_all_jurisdictions(self):
        self.client.force_authenticate(user=self.main_officer)
        res = self.client.get(reverse('idol-list'))
        self.assertEqual(res.status_code, 200)
        gpids = [item['gpid'] for item in res.data['results']]
        self.assertIn('HYDCMRZCMNR0112', gpids)
        self.assertIn('HYDCMRZMLPT0112', gpids)

    def test_unassigned_constable_cannot_browse_arbitrary_idols(self):
        self.client.force_authenticate(user=self.constable)
        res = self.client.get(reverse('idol-list'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['results']), 0)
