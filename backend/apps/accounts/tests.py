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
