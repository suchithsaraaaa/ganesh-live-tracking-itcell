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


class ProductionSettingsValidationTests(TestCase):
    """
    Tests that config.settings.prod fails fast on missing or insecure environment variables.
    """
    def test_missing_secret_key_raises_improperly_configured(self):
        import os, importlib
        from unittest.mock import patch
        from django.core.exceptions import ImproperlyConfigured
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                import config.settings.prod
                importlib.reload(config.settings.prod)
            self.assertIn("SECRET_KEY", str(ctx.exception))

    def test_insecure_secret_key_raises_improperly_configured(self):
        import os, importlib
        from unittest.mock import patch
        from django.core.exceptions import ImproperlyConfigured
        env = {'SECRET_KEY': 'police_secret_key_change_in_production'}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                import config.settings.prod
                importlib.reload(config.settings.prod)
            self.assertIn("Insecure placeholder SECRET_KEY", str(ctx.exception))

    def test_missing_allowed_hosts_raises_improperly_configured(self):
        import os, importlib
        from unittest.mock import patch
        from django.core.exceptions import ImproperlyConfigured
        env = {'SECRET_KEY': 'test-genuine-secret-key-abcdef-12345'}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                import config.settings.prod
                importlib.reload(config.settings.prod)
            self.assertIn("ALLOWED_HOSTS", str(ctx.exception))

    def test_wildcard_allowed_hosts_raises_improperly_configured(self):
        import os, importlib
        from unittest.mock import patch
        from django.core.exceptions import ImproperlyConfigured
        env = {
            'SECRET_KEY': 'test-genuine-secret-key-abcdef-12345',
            'ALLOWED_HOSTS': '*',
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                import config.settings.prod
                importlib.reload(config.settings.prod)
            self.assertIn("Wildcard", str(ctx.exception))

    def test_missing_db_password_raises_improperly_configured(self):
        import os, importlib
        from unittest.mock import patch
        from django.core.exceptions import ImproperlyConfigured
        env = {
            'SECRET_KEY': 'test-genuine-secret-key-abcdef-12345',
            'ALLOWED_HOSTS': 'tracking.police.gov.in',
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                import config.settings.prod
                importlib.reload(config.settings.prod)
            self.assertIn("DB_PASSWORD", str(ctx.exception))

    def test_valid_production_config_succeeds(self):
        import os, importlib
        from unittest.mock import patch
        env = {
            'SECRET_KEY': 'test-genuine-secret-key-abcdef-12345',
            'ALLOWED_HOSTS': 'tracking.police.gov.in,13.235.10.20',
            'DB_PASSWORD': 'strong_prod_db_pass_99812#',
            'GDAL_LIBRARY_PATH': os.environ.get('GDAL_LIBRARY_PATH', ''),
            'GEOS_LIBRARY_PATH': os.environ.get('GEOS_LIBRARY_PATH', ''),
        }
        with patch.dict(os.environ, env, clear=True):
            import config.settings.prod
            mod = importlib.reload(config.settings.prod)
            self.assertEqual(mod.ALLOWED_HOSTS, ['tracking.police.gov.in', '13.235.10.20'])
            self.assertEqual(mod.DATABASES['default']['PASSWORD'], 'strong_prod_db_pass_99812#')
            self.assertEqual(mod.DATABASES['default']['HOST'], 'db')
            self.assertEqual(mod.DATABASES['default']['PORT'], '5432')


class AuthenticationLifecycleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='auth_test_user',
            password='TestPassword123!',
            role=UserRole.SHO,
            police_station='Charminar'
        )

    def test_login_logout_and_session_invalidation(self):
        # 1. Invalid login
        res_bad = self.client.post('/api/v1/auth/login/', {'username': 'auth_test_user', 'password': 'WrongPassword'})
        self.assertEqual(res_bad.status_code, 401)

        # 2. Valid login
        res_login = self.client.post('/api/v1/auth/login/', {'username': 'auth_test_user', 'password': 'TestPassword123!'})
        self.assertEqual(res_login.status_code, 200)
        self.assertEqual(res_login.data['username'], 'auth_test_user')
        self.assertIn('permissions', res_login.data)
        self.assertIn('view_dashboard', res_login.data['permissions'])

        # 3. Authenticated request
        res_me = self.client.get('/api/v1/auth/me/')
        self.assertEqual(res_me.status_code, 200)
        self.assertEqual(res_me.data['username'], 'auth_test_user')

        # 4. Logout
        res_logout = self.client.post('/api/v1/auth/logout/')
        self.assertEqual(res_logout.status_code, 200)

        # 5. Subsequent request must be rejected
        res_after = self.client.get('/api/v1/auth/me/')
        self.assertIn(res_after.status_code, [401, 403])

    def test_disabled_account_login_rejected(self):
        self.user.is_active = False
        self.user.save()
        res = self.client.post('/api/v1/auth/login/', {'username': 'auth_test_user', 'password': 'TestPassword123!'})
        self.assertEqual(res.status_code, 403)


class UserManagementAndOfficerDirectoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.main_officer = User.objects.create_user(
            username='admin_main', password='AdminPass123!',
            role=UserRole.MAIN_OFFICER
        )
        self.sho = User.objects.create_user(
            username='sho_cmr', password='ShoPass123!',
            role=UserRole.SHO, police_station='Charminar'
        )
        self.constable = User.objects.create_user(
            username='pc_cmr_1', password='PcPass123!',
            role=UserRole.CONSTABLE, police_station='Charminar',
            police_id='PC-1001', phone_number='9876543210'
        )
        self.constable_mlp = User.objects.create_user(
            username='pc_mlp_1', password='PcPass123!',
            role=UserRole.CONSTABLE, police_station='Malakpet',
            police_id='PC-1002', phone_number='9876543211'
        )
        self.idol = Idol.objects.create(
            gpid='HYDCMRZCMNR1749',
            name='Test Idol',
            police_station='Charminar',
            zone='Charminar'
        )

    def test_main_officer_can_list_and_create_users(self):
        self.client.force_authenticate(user=self.main_officer)
        # List users
        res_list = self.client.get('/api/v1/auth/users/')
        self.assertEqual(res_list.status_code, 200)
        self.assertGreaterEqual(res_list.data['count'], 4)

        # Create user
        payload = {
            'username': 'new_acp_user',
            'password': 'NewPassword123!',
            'first_name': 'Ramesh',
            'last_name': 'Rao',
            'role': 'ACP',
            'police_id': 'ACP-5501',
            'zone': 'Charminar',
            'division': 'Charminar'
        }
        res_create = self.client.post('/api/v1/auth/users/', payload)
        self.assertEqual(res_create.status_code, 201)
        self.assertEqual(res_create.data['username'], 'new_acp_user')
        self.assertEqual(res_create.data['name'], 'Ramesh Rao')
        self.assertIn('view_reports', res_create.data['permissions'])

    def test_invalid_permission_name_rejected_server_side(self):
        self.client.force_authenticate(user=self.main_officer)
        payload = {
            'username': 'bad_perm_user',
            'password': 'NewPassword123!',
            'role': 'CONSTABLE',
            'custom_permissions': ['invalid_super_admin_hack']
        }
        res = self.client.post('/api/v1/auth/users/', payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn('custom_permissions', res.data)

    def test_user_update_and_toggle_active(self):
        self.client.force_authenticate(user=self.main_officer)
        # Toggle active
        res_toggle = self.client.post(f'/api/v1/auth/users/{self.constable.id}/toggle-active/')
        self.assertEqual(res_toggle.status_code, 200)
        self.assertFalse(res_toggle.data['is_active'])

        # Toggle back
        res_toggle2 = self.client.post(f'/api/v1/auth/users/{self.constable.id}/toggle-active/')
        self.assertEqual(res_toggle2.status_code, 200)
        self.assertTrue(res_toggle2.data['is_active'])

        # Patch details with valid custom permissions
        res_patch = self.client.patch(f'/api/v1/auth/users/{self.constable.id}/', {
            'first_name': 'Kavitha',
            'custom_permissions': ['view_dashboard', 'view_live_map']
        })
        self.assertEqual(res_patch.status_code, 200)
        self.assertEqual(res_patch.data['permissions'], ['view_dashboard', 'view_live_map'])

    def test_unauthorized_user_management_rejected(self):
        # SHO attempt
        self.client.force_authenticate(user=self.sho)
        res = self.client.get('/api/v1/auth/users/')
        self.assertEqual(res.status_code, 403)

        # Constable attempt
        self.client.force_authenticate(user=self.constable)
        res2 = self.client.get('/api/v1/auth/users/')
        self.assertEqual(res2.status_code, 403)

    def test_officer_directory_jurisdiction_and_no_phone_exposure(self):
        from apps.assignments.models import Assignment
        # Assign pc_cmr_1 to idol
        Assignment.assign_constable(idol=self.idol, constable=self.constable, assigned_by=self.sho)

        # Authenticate as SHO Charminar
        self.client.force_authenticate(user=self.sho)
        res = self.client.get('/api/v1/auth/officers/')
        self.assertEqual(res.status_code, 200)

        results = res.data['results']
        user_ids = [o['id'] for o in results]
        self.assertIn(self.constable.id, user_ids)
        self.assertNotIn(self.constable_mlp.id, user_ids)  # Malakpet officer excluded

        # Check assigned officer status
        cmr_officer = next(o for o in results if o['id'] == self.constable.id)
        self.assertTrue(cmr_officer['currently_assigned'])
        self.assertEqual(cmr_officer['assigned_gpid'], self.idol.gpid)

        # STRICT PRIVACY CHECK: phone_number must NOT be in output
        for o in results:
            self.assertNotIn('phone_number', o)
            self.assertNotIn('phone', o)

    def test_geography_police_stations_master_endpoint(self):
        from apps.geography.models import PoliceStationBoundary
        PoliceStationBoundary.objects.get_or_create(
            ps_name='Charminar',
            defaults={'ps_code': 'CMNR', 'zone': 'Charminar', 'division': 'Charminar'}
        )
        self.client.force_authenticate(user=self.sho)
        res = self.client.get('/api/v1/geography/police-stations/')
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.data['count'], 1)
        names = [s['ps_name'] for s in res.data['results']]
        self.assertIn('Charminar', names)
