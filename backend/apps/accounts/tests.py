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

        # Idols in different police stations (operational 15+ ft)
        self.idol_cmr = Idol.objects.create(
            gpid='HYDCMRZCMNR0112',
            name='Charminar Ganesh',
            police_station='Charminar',
            division='Charminar',
            zone='Charminar',
            idol_height=18.0,
            raw_metadata={'mobile_no': '9876543210'}
        )
        self.idol_mlp = Idol.objects.create(
            gpid='HYDCMRZMLPT0112',
            name='Malakpet Ganesh',
            police_station='Malakpet',
            division='Malakpet',
            zone='Charminar',
            idol_height=18.0,
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
            zone='Charminar',
            police_id='PC-1001', phone_number='9876543210'
        )
        self.constable_mlp = User.objects.create_user(
            username='pc_mlp_1', password='PcPass123!',
            role=UserRole.CONSTABLE, police_station='Malakpet',
            zone='Charminar',
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


class UserAccountDeletionTests(TestCase):
    """
    Tests covering the permanent account deletion feature.

    Invariants verified:
    1.  MAIN_OFFICER can hard-delete an unassigned account.
    2.  Deleted user can no longer log in.
    3.  Self-deletion is rejected with 400.
    4.  SHO cannot delete accounts (insufficient permission → 403).
    5.  Constable with active assignment is blocked → 400.
    6.  After deletion: Assignment row is preserved (constable SET_NULL).
    7.  After deletion: officer_name_snapshot and police_id_snapshot are retained.
    8.  After deletion: TrackingSession row is preserved.
    9.  After deletion: LocationPoint rows are preserved.
    10. After deletion: AuditEvent USER_DELETED entry exists.
    11. Deleting non-existent user returns 404.
    12. Assignment snapshot is populated on assignment creation.
    """

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='del_admin', password='AdminPass123!',
            role=UserRole.MAIN_OFFICER
        )
        self.sho = User.objects.create_user(
            username='del_sho', password='ShoPass123!',
            role=UserRole.SHO, police_station='Charminar'
        )
        self.victim = User.objects.create_user(
            username='del_victim', password='VictimPass123!',
            first_name='Ravi', last_name='Kumar',
            role=UserRole.CONSTABLE, police_station='Charminar',
            police_id='PC-9999'
        )
        self.idol = Idol.objects.create(
            gpid='HYDTEST0001',
            name='Test Idol',
            police_station='Charminar',
            zone='Charminar'
        )

    def _delete_url(self, user_id):
        return f'/api/v1/auth/users/{user_id}/delete/'

    # --- Test 1: Successful deletion of unassigned account ---
    def test_admin_can_delete_unassigned_constable(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.delete(self._delete_url(self.victim.id))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(User.objects.filter(id=self.victim.id).exists())

    # --- Test 2: Deleted user cannot log in ---
    def test_deleted_user_cannot_login(self):
        uid = self.victim.id
        self.client.force_authenticate(user=self.admin)
        self.client.delete(self._delete_url(uid))
        # Reset client auth and attempt login
        self.client.force_authenticate(user=None)
        res = self.client.post('/api/v1/auth/login/', {
            'username': 'del_victim', 'password': 'VictimPass123!'
        })
        self.assertIn(res.status_code, [400, 401, 403])

    # --- Test 3: Self-deletion rejected ---
    def test_self_deletion_rejected(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.delete(self._delete_url(self.admin.id))
        self.assertEqual(res.status_code, 400)
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())

    # --- Test 4: SHO cannot delete accounts ---
    def test_sho_cannot_delete_accounts(self):
        self.client.force_authenticate(user=self.sho)
        res = self.client.delete(self._delete_url(self.victim.id))
        self.assertEqual(res.status_code, 403)
        self.assertTrue(User.objects.filter(id=self.victim.id).exists())

    # --- Test 5: Constable with active assignment is blocked ---
    def test_cannot_delete_constable_with_active_assignment(self):
        from apps.assignments.models import Assignment
        Assignment.assign_constable(idol=self.idol, constable=self.victim, assigned_by=self.admin)
        self.client.force_authenticate(user=self.admin)
        res = self.client.delete(self._delete_url(self.victim.id))
        self.assertEqual(res.status_code, 400)
        self.assertIn('active GPID assignment', res.data['error'])
        self.assertTrue(User.objects.filter(id=self.victim.id).exists())

    # --- Test 6: Assignment row is preserved after deletion (SET_NULL) ---
    def test_assignment_preserved_after_user_deletion(self):
        from apps.assignments.models import Assignment
        assignment = Assignment.assign_constable(
            idol=self.idol, constable=self.victim, assigned_by=self.admin
        )
        # End the assignment so deletion is not blocked
        assignment.is_active = False
        assignment.save(update_fields=['is_active'])

        self.client.force_authenticate(user=self.admin)
        self.client.delete(self._delete_url(self.victim.id))

        # Assignment row must survive
        assignment.refresh_from_db()
        self.assertIsNone(assignment.constable)  # SET_NULL applied
        self.assertEqual(assignment.idol.gpid, 'HYDTEST0001')

    # --- Test 7: Snapshot fields retain officer identity after deletion ---
    def test_officer_snapshot_retained_after_deletion(self):
        from apps.assignments.models import Assignment
        assignment = Assignment.assign_constable(
            idol=self.idol, constable=self.victim, assigned_by=self.admin
        )
        assignment.is_active = False
        assignment.save(update_fields=['is_active'])

        self.client.force_authenticate(user=self.admin)
        self.client.delete(self._delete_url(self.victim.id))

        assignment.refresh_from_db()
        self.assertEqual(assignment.officer_name_snapshot, 'Ravi Kumar')
        self.assertEqual(assignment.police_id_snapshot, 'PC-9999')

    # --- Test 8: TrackingSession row is preserved after user deletion ---
    def test_tracking_session_preserved_after_user_deletion(self):
        from apps.assignments.models import Assignment
        from apps.tracking.models import TrackingSession
        assignment = Assignment.assign_constable(
            idol=self.idol, constable=self.victim, assigned_by=self.admin
        )
        session = TrackingSession.objects.create(assignment=assignment, device_info='TestDevice')
        assignment.is_active = False
        assignment.save(update_fields=['is_active'])

        self.client.force_authenticate(user=self.admin)
        self.client.delete(self._delete_url(self.victim.id))

        self.assertTrue(TrackingSession.objects.filter(id=session.id).exists())

    # --- Test 9: LocationPoint rows are preserved after user deletion ---
    def test_location_points_preserved_after_user_deletion(self):
        from apps.assignments.models import Assignment
        from apps.tracking.models import TrackingSession, LocationPoint
        from django.utils import timezone
        assignment = Assignment.assign_constable(
            idol=self.idol, constable=self.victim, assigned_by=self.admin
        )
        session = TrackingSession.objects.create(assignment=assignment, device_info='TestDevice')
        now = timezone.now()
        lp = LocationPoint.objects.create(
            session=session, latitude=17.36, longitude=78.47, recorded_at=now
        )
        assignment.is_active = False
        assignment.save(update_fields=['is_active'])

        self.client.force_authenticate(user=self.admin)
        self.client.delete(self._delete_url(self.victim.id))

        self.assertTrue(LocationPoint.objects.filter(id=lp.id).exists())

    # --- Test 10: AuditEvent USER_DELETED entry is written ---
    def test_audit_event_written_on_user_deletion(self):
        from apps.audit.models import AuditEvent
        self.client.force_authenticate(user=self.admin)
        self.client.delete(self._delete_url(self.victim.id))
        event = AuditEvent.objects.filter(action='USER_DELETED').first()
        self.assertIsNotNone(event)
        self.assertEqual(event.details.get('username'), 'del_victim')

    # --- Test 11: Deleting non-existent user returns 404 ---
    def test_delete_nonexistent_user_returns_404(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.delete(self._delete_url(99999))
        self.assertEqual(res.status_code, 404)

    # --- Test 12: Assignment snapshot is populated at creation ---
    def test_assignment_snapshot_populated_at_creation(self):
        from apps.assignments.models import Assignment
        assignment = Assignment.assign_constable(
            idol=self.idol, constable=self.victim, assigned_by=self.admin
        )
        self.assertEqual(assignment.officer_name_snapshot, 'Ravi Kumar')
        self.assertEqual(assignment.police_id_snapshot, 'PC-9999')


class OfficerCreationCascadingTests(TestCase):
    def setUp(self):
        from apps.geography.models import PoliceStationBoundary
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='admin_boss', password='password123', role=UserRole.MAIN_OFFICER
        )
        self.client.force_authenticate(user=self.admin)

        PoliceStationBoundary.objects.create(
            ps_name='Charminar',
            ps_code='CMNR',
            zone='Charminar',
            division='Charminar',
        )
        PoliceStationBoundary.objects.create(
            ps_name='Banjara Hills',
            ps_code='BJRH',
            zone='Jubilee Hills',
            division='Banjara Hills',
        )

    def test_constable_creation_missing_zone_or_station_fails(self):
        # Missing zone
        res = self.client.post('/api/v1/auth/users/', {
            'username': 'pc_no_zone',
            'password': 'password123',
            'role': 'CONSTABLE',
            'police_station': 'Charminar',
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('Zone is required for Constable', str(res.data))

        # Missing police station
        res2 = self.client.post('/api/v1/auth/users/', {
            'username': 'pc_no_ps',
            'password': 'password123',
            'role': 'CONSTABLE',
            'zone': 'Charminar',
        })
        self.assertEqual(res2.status_code, 400)
        self.assertIn('Police Station is required for Constable', str(res2.data))

    def test_constable_creation_mismatched_station_and_zone_fails(self):
        res = self.client.post('/api/v1/auth/users/', {
            'username': 'pc_mismatch',
            'password': 'password123',
            'role': 'CONSTABLE',
            'zone': 'Charminar',
            'police_station': 'Banjara Hills',
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('does not belong to', str(res.data))

    def test_constable_creation_valid_station_and_zone_succeeds(self):
        res = self.client.post('/api/v1/auth/users/', {
            'username': 'pc_valid',
            'password': 'password123',
            'role': 'CONSTABLE',
            'zone': 'Charminar',
            'police_station': 'Charminar',
            'first_name': 'Ramesh',
            'last_name': 'Patel',
            'police_id': 'PC-8888',
        })
        self.assertEqual(res.status_code, 201)
        created_user = User.objects.get(username='pc_valid')
        self.assertEqual(created_user.zone, 'Charminar')
        self.assertEqual(created_user.police_station, 'Charminar')

    def test_assignable_officers_directory_filter_by_zone(self):
        User.objects.create_user(
            username='pc_cmr_test',
            password='password123',
            role=UserRole.CONSTABLE,
            zone='Charminar',
            police_station='Charminar',
        )
        User.objects.create_user(
            username='pc_bjrh_test',
            password='password123',
            role=UserRole.CONSTABLE,
            zone='Jubilee Hills',
            police_station='Banjara Hills',
        )

        res = self.client.get('/api/v1/auth/officers/?zone=Charminar')
        self.assertEqual(res.status_code, 200)
        usernames = [u['username'] for u in res.data['results']]
        self.assertIn('pc_cmr_test', usernames)
        self.assertNotIn('pc_bjrh_test', usernames)


class UserManagementFilteringAndAdminPasswordTests(TestCase):
    def setUp(self):
        from apps.geography.models import PoliceStationBoundary
        self.client = APIClient()

        # Admin user
        self.admin = User.objects.create_user(
            username='admin_main', password='adminpassword123',
            role=UserRole.MAIN_OFFICER, first_name='Admin', last_name='Officer'
        )

        # ACP user with manage_users permission
        self.acp_charminar = User.objects.create_user(
            username='acp_cmr_filter', password='password123',
            role=UserRole.ACP, zone='Charminar', division='Charminar',
            first_name='ACP', last_name='Charminar',
            custom_permissions=['manage_users']
        )

        # SHO users
        self.sho_chaderghat = User.objects.create_user(
            username='sho_chaderghat', password='password123',
            role=UserRole.SHO, zone='Charminar', police_station='Chaderghat',
            first_name='SHO', last_name='Chaderghat'
        )
        self.sho_banjara = User.objects.create_user(
            username='sho_banjara', password='password123',
            role=UserRole.SHO, zone='Jubilee Hills', police_station='Banjara Hills',
            first_name='SHO', last_name='Banjara'
        )

        # Constables
        self.pc_active = User.objects.create_user(
            username='android1', password='password123',
            role=UserRole.CONSTABLE, zone='Charminar', police_station='Chaderghat',
            police_id='PC-1001', is_active=True, first_name='Ravi', last_name='Kumar',
            phone_number='9876500001'
        )
        self.pc_inactive = User.objects.create_user(
            username='pc_inactive_cmr', password='password123',
            role=UserRole.CONSTABLE, zone='Charminar', police_station='Chaderghat',
            police_id='PC-1002', is_active=False, first_name='Suresh', last_name='Rao',
            phone_number='9876500002'
        )
        self.pc_banjara = User.objects.create_user(
            username='pc_banjara_active', password='password123',
            role=UserRole.CONSTABLE, zone='Jubilee Hills', police_station='Banjara Hills',
            police_id='PC-2001', is_active=True, first_name='Mahesh', last_name='Reddy',
            phone_number='9876500003'
        )

        # Boundaries
        PoliceStationBoundary.objects.create(
            ps_name='Chaderghat', ps_code='CDGT', zone='Charminar', division='Charminar'
        )
        PoliceStationBoundary.objects.create(
            ps_name='Banjara Hills', ps_code='BJRH', zone='Jubilee Hills', division='Banjara Hills'
        )

    # 1. No filters -> returns all authorized accounts and correct counts
    def test_no_filters_returns_all_users_and_counts(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/v1/auth/users/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['count'], 7)
        self.assertEqual(res.data['total_count'], 7)
        usernames = [u['username'] for u in res.data['results']]
        self.assertIn('admin_main', usernames)
        self.assertIn('android1', usernames)
        self.assertIn('pc_inactive_cmr', usernames)

    # 2. Zone filter
    def test_zone_filter(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/v1/auth/users/?zone=Charminar')
        self.assertEqual(res.status_code, 200)
        usernames = [u['username'] for u in res.data['results']]
        self.assertEqual(set(usernames), {'acp_cmr_filter', 'sho_chaderghat', 'android1', 'pc_inactive_cmr'})
        self.assertEqual(res.data['count'], 4)
        self.assertEqual(res.data['total_count'], 7)

    # 3. Police Station filter
    def test_police_station_filter(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/v1/auth/users/?police_station=Chaderghat')
        self.assertEqual(res.status_code, 200)
        usernames = [u['username'] for u in res.data['results']]
        self.assertEqual(set(usernames), {'sho_chaderghat', 'android1', 'pc_inactive_cmr'})

    # 4. Officer Level filter
    def test_officer_level_filter(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/v1/auth/users/?officer_level=CONSTABLE')
        self.assertEqual(res.status_code, 200)
        usernames = [u['username'] for u in res.data['results']]
        self.assertEqual(set(usernames), {'android1', 'pc_inactive_cmr', 'pc_banjara_active'})

    # 5. Role filter compatibility
    def test_role_filter_compatibility(self):
        self.client.force_authenticate(user=self.admin)
        res_role = self.client.get('/api/v1/auth/users/?role=SHO')
        res_level = self.client.get('/api/v1/auth/users/?officer_level=SHO')
        self.assertEqual(res_role.status_code, 200)
        self.assertEqual(res_level.status_code, 200)
        self.assertEqual(
            [u['username'] for u in res_role.data['results']],
            [u['username'] for u in res_level.data['results']]
        )
        self.assertEqual(set(u['username'] for u in res_role.data['results']), {'sho_chaderghat', 'sho_banjara'})

    # 6. Status filter
    def test_status_filter_active_and_inactive(self):
        self.client.force_authenticate(user=self.admin)
        # Active only
        res_active = self.client.get('/api/v1/auth/users/?status=active')
        self.assertEqual(res_active.status_code, 200)
        active_usernames = [u['username'] for u in res_active.data['results']]
        self.assertNotIn('pc_inactive_cmr', active_usernames)
        self.assertIn('android1', active_usernames)

        # Inactive only
        res_inactive = self.client.get('/api/v1/auth/users/?status=inactive')
        self.assertEqual(res_inactive.status_code, 200)
        inactive_usernames = [u['username'] for u in res_inactive.data['results']]
        self.assertEqual(inactive_usernames, ['pc_inactive_cmr'])

    # 7. Search filter
    def test_search_filter(self):
        self.client.force_authenticate(user=self.admin)
        # Search by username
        res = self.client.get('/api/v1/auth/users/?search=android1')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['username'], 'android1')

        # Search by police_id
        res_pid = self.client.get('/api/v1/auth/users/?search=PC-1001')
        self.assertEqual(res_pid.status_code, 200)
        self.assertEqual(res_pid.data['results'][0]['username'], 'android1')

        # Search by first name
        res_name = self.client.get('/api/v1/auth/users/?search=Ravi')
        self.assertEqual(res_name.status_code, 200)
        self.assertEqual(res_name.data['results'][0]['username'], 'android1')

    # 8. Combined Zone + PS
    def test_combined_zone_and_ps(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/v1/auth/users/?zone=Charminar&police_station=Chaderghat')
        self.assertEqual(res.status_code, 200)
        usernames = [u['username'] for u in res.data['results']]
        self.assertEqual(set(usernames), {'sho_chaderghat', 'android1', 'pc_inactive_cmr'})

    # 9. Combined Zone + Officer Level
    def test_combined_zone_and_officer_level(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/v1/auth/users/?zone=Charminar&officer_level=SHO')
        self.assertEqual(res.status_code, 200)
        usernames = [u['username'] for u in res.data['results']]
        self.assertEqual(usernames, ['sho_chaderghat'])

    # 10. Combined PS + Officer Level
    def test_combined_ps_and_officer_level(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/v1/auth/users/?police_station=Chaderghat&officer_level=CONSTABLE')
        self.assertEqual(res.status_code, 200)
        usernames = [u['username'] for u in res.data['results']]
        self.assertEqual(set(usernames), {'android1', 'pc_inactive_cmr'})

    # 11. Combined Zone + PS + Officer Level
    def test_combined_zone_ps_and_officer_level(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/v1/auth/users/?zone=Charminar&police_station=Chaderghat&officer_level=CONSTABLE')
        self.assertEqual(res.status_code, 200)
        usernames = [u['username'] for u in res.data['results']]
        self.assertEqual(set(usernames), {'android1', 'pc_inactive_cmr'})

    # 12. All filters together (Search + Zone + PS + Officer Level + Status)
    def test_all_filters_together(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(
            '/api/v1/auth/users/?search=android1&zone=Charminar&police_station=Chaderghat&officer_level=CONSTABLE&status=active'
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['username'], 'android1')

    # 13. Invalid Zone/PS combinations
    def test_invalid_zone_ps_combinations(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/v1/auth/users/?zone=Charminar&police_station=Banjara Hills')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['results']), 0)
        self.assertEqual(res.data['count'], 0)
        self.assertEqual(res.data['total_count'], 7)

    # 14. Dependent PS filtering
    def test_dependent_ps_filtering(self):
        self.client.force_authenticate(user=self.admin)
        # PS without zone
        res = self.client.get('/api/v1/auth/users/?police_station=Banjara Hills')
        self.assertEqual(res.status_code, 200)
        usernames = [u['username'] for u in res.data['results']]
        self.assertEqual(set(usernames), {'sho_banjara', 'pc_banjara_active'})

    # 15. Pagination with filters
    def test_pagination_with_filters(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/v1/auth/users/?zone=Charminar&page=1&page_size=2')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['results']), 2)
        self.assertEqual(res.data['count'], 4)
        self.assertEqual(res.data['total_count'], 7)

    # 16. Server-side jurisdiction restriction enforced
    def test_jurisdiction_restricts_user_list_for_acp(self):
        self.client.force_authenticate(user=self.acp_charminar)
        # ACP Charminar should ONLY see Charminar users (4 users), even with no filters
        res = self.client.get('/api/v1/auth/users/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['total_count'], 4)
        self.assertEqual(res.data['count'], 4)
        usernames = [u['username'] for u in res.data['results']]
        self.assertNotIn('admin_main', usernames)
        self.assertNotIn('sho_banjara', usernames)
        self.assertNotIn('pc_banjara_active', usernames)

        # Attempting to filter outside their jurisdiction must return 0 results
        res_outside = self.client.get('/api/v1/auth/users/?zone=Jubilee Hills')
        self.assertEqual(res_outside.status_code, 200)
        self.assertEqual(len(res_outside.data['results']), 0)
        self.assertEqual(res_outside.data['count'], 0)
        self.assertEqual(res_outside.data['total_count'], 4)

    # 17. No duplicate users
    def test_no_duplicate_users(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/v1/auth/users/?search=a')
        self.assertEqual(res.status_code, 200)
        user_ids = [u['id'] for u in res.data['results']]
        self.assertEqual(len(user_ids), len(set(user_ids)))

    # 18. Admin can reset password without providing old password
    def test_admin_can_reset_password_without_old_password(self):
        self.client.force_authenticate(user=self.admin)
        patch_res = self.client.patch(f'/api/v1/auth/users/{self.pc_active.id}/', {
            'password': 'newpassword999'
        })
        self.assertEqual(patch_res.status_code, 200)
        # Password must not be in response
        self.assertNotIn('password', patch_res.data)

        # Verify new password works
        from django.contrib.auth import authenticate
        user = authenticate(username='android1', password='newpassword999')
        self.assertIsNotNone(user)
        self.assertEqual(user.id, self.pc_active.id)

    # 19. Blank reset password preserves existing password
    def test_blank_reset_password_preserves_existing_password(self):
        self.client.force_authenticate(user=self.admin)
        patch_res = self.client.patch(f'/api/v1/auth/users/{self.pc_active.id}/', {
            'password': '',
            'first_name': 'Ravinder'
        })
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.data['first_name'], 'Ravinder')

        # Verify original password still works
        from django.contrib.auth import authenticate
        user = authenticate(username='android1', password='password123')
        self.assertIsNotNone(user)

    # 20. Unauthorized user cannot change password
    def test_unauthorized_user_cannot_change_password(self):
        self.client.force_authenticate(user=self.pc_active)
        res = self.client.patch(f'/api/v1/auth/users/{self.sho_chaderghat.id}/', {
            'password': 'hackedpassword123'
        })
        self.assertEqual(res.status_code, 403)


class ZonedSysAdminJurisdictionRBACTests(TestCase):
    """
    Production RBAC Verification for Zone-Scoped System Administrators.
    Verifies that:
    1. Existing and future SYS_ADMIN accounts with a zone are strictly scoped to that zone.
    2. Cross-zone operations (view, edit, delete, password reset, toggle active, create) are rejected server-side.
    3. Global unzoned MAIN_OFFICER and superuser retain city-wide jurisdiction.
    4. ACP/SHO jurisdiction behaviors are preserved.
    """
    def setUp(self):
        self.client = APIClient()

        # Global Administrators (City-Wide, no zone assigned)
        self.global_main_officer = User.objects.create_user(
            username='global_boss',
            password='Password123!',
            role=UserRole.MAIN_OFFICER,
            zone=''
        )
        self.superuser = User.objects.create_superuser(
            username='global_super',
            password='Password123!',
            role=UserRole.MAIN_OFFICER,
            zone=''
        )

        # Existing Zone-Scoped SYS_ADMIN (Created with role=MAIN_OFFICER and zone)
        self.sys_admin_cmr = User.objects.create_user(
            username='sysadmin_charminar',
            password='Password123!',
            role=UserRole.MAIN_OFFICER,
            zone='Charminar'
        )
        self.sys_admin_sec = User.objects.create_user(
            username='sysadmin_secunderabad',
            password='Password123!',
            role=UserRole.MAIN_OFFICER,
            zone='Secunderabad'
        )

        # Future Zone-Scoped SYS_ADMIN (Created with role=SYS_ADMIN and zone)
        self.future_sys_admin_cmr = User.objects.create_user(
            username='future_admin_cmr',
            password='Password123!',
            role=UserRole.SYS_ADMIN,
            zone='Charminar'
        )

        # Zone 1 Users (Charminar)
        self.user_cmr_constable = User.objects.create_user(
            username='cmr_pc_5001',
            password='Password123!',
            role=UserRole.CONSTABLE,
            zone='Charminar',
            police_station='Charminar',
            police_id='PC-5001'
        )
        self.acp_cmr = User.objects.create_user(
            username='acp_cmr_5002',
            password='Password123!',
            role=UserRole.ACP,
            zone='Charminar',
            division='Charminar'
        )
        self.sho_cmr = User.objects.create_user(
            username='sho_cmr_5003',
            password='Password123!',
            role=UserRole.SHO,
            zone='Charminar',
            police_station='Charminar'
        )

        # Zone 2 Users (Secunderabad)
        self.user_sec_constable = User.objects.create_user(
            username='sec_pc_6001',
            password='Password123!',
            role=UserRole.CONSTABLE,
            zone='Secunderabad',
            police_station='Amberpet',
            police_id='PC-6001'
        )

    # 1. Existing Zone 1 SYS_ADMIN sees only Zone 1 users
    def test_1_existing_zone_1_sys_admin_sees_only_zone_1_users(self):
        self.client.force_authenticate(user=self.sys_admin_cmr)
        res = self.client.get('/api/v1/auth/users/')
        self.assertEqual(res.status_code, 200)
        usernames = [u['username'] for u in res.data['results']]
        self.assertIn('cmr_pc_5001', usernames)
        self.assertIn('sysadmin_charminar', usernames)
        self.assertNotIn('sec_pc_6001', usernames)
        self.assertNotIn('sysadmin_secunderabad', usernames)

    # 2. Existing Zone 2 SYS_ADMIN sees only Zone 2 users
    def test_2_existing_zone_2_sys_admin_sees_only_zone_2_users(self):
        self.client.force_authenticate(user=self.sys_admin_sec)
        res = self.client.get('/api/v1/auth/users/')
        self.assertEqual(res.status_code, 200)
        usernames = [u['username'] for u in res.data['results']]
        self.assertIn('sec_pc_6001', usernames)
        self.assertIn('sysadmin_secunderabad', usernames)
        self.assertNotIn('cmr_pc_5001', usernames)
        self.assertNotIn('sysadmin_charminar', usernames)

    # 3. Existing Zone 1 SYS_ADMIN cannot retrieve Zone 2 user (404)
    def test_3_existing_zone_1_sys_admin_cannot_retrieve_zone_2_user(self):
        self.client.force_authenticate(user=self.sys_admin_cmr)
        res = self.client.get(f'/api/v1/auth/users/{self.user_sec_constable.id}/')
        self.assertEqual(res.status_code, 404)

    # 4. Existing Zone 1 SYS_ADMIN cannot edit Zone 2 user
    def test_4_existing_zone_1_sys_admin_cannot_edit_zone_2_user(self):
        self.client.force_authenticate(user=self.sys_admin_cmr)
        res = self.client.patch(f'/api/v1/auth/users/{self.user_sec_constable.id}/', {
            'first_name': 'Hacked'
        })
        self.assertEqual(res.status_code, 404)
        self.user_sec_constable.refresh_from_db()
        self.assertNotEqual(self.user_sec_constable.first_name, 'Hacked')

    # 5. Existing Zone 1 SYS_ADMIN cannot delete Zone 2 user
    def test_5_existing_zone_1_sys_admin_cannot_delete_zone_2_user(self):
        self.client.force_authenticate(user=self.sys_admin_cmr)
        res = self.client.delete(f'/api/v1/auth/users/{self.user_sec_constable.id}/delete/')
        self.assertEqual(res.status_code, 404)
        self.assertTrue(User.objects.filter(id=self.user_sec_constable.id).exists())

    # 6. Existing Zone 1 SYS_ADMIN cannot reset Zone 2 password
    def test_6_existing_zone_1_sys_admin_cannot_reset_zone_2_password(self):
        self.client.force_authenticate(user=self.sys_admin_cmr)
        res = self.client.patch(f'/api/v1/auth/users/{self.user_sec_constable.id}/', {
            'password': 'AttackerNewPassword123!'
        })
        self.assertEqual(res.status_code, 404)
        from django.contrib.auth import authenticate
        self.assertIsNone(authenticate(username='sec_pc_6001', password='AttackerNewPassword123!'))
        self.assertIsNotNone(authenticate(username='sec_pc_6001', password='Password123!'))

    # 7. Existing Zone 1 SYS_ADMIN cannot disable Zone 2 user
    def test_7_existing_zone_1_sys_admin_cannot_disable_zone_2_user(self):
        self.client.force_authenticate(user=self.sys_admin_cmr)
        res = self.client.delete(f'/api/v1/auth/users/{self.user_sec_constable.id}/')
        self.assertEqual(res.status_code, 404)
        self.user_sec_constable.refresh_from_db()
        self.assertTrue(self.user_sec_constable.is_active)

    # 8. Existing Zone 1 SYS_ADMIN cannot enable Zone 2 user
    def test_8_existing_zone_1_sys_admin_cannot_enable_zone_2_user(self):
        self.user_sec_constable.is_active = False
        self.user_sec_constable.save(update_fields=['is_active'])

        self.client.force_authenticate(user=self.sys_admin_cmr)
        res = self.client.post(f'/api/v1/auth/users/{self.user_sec_constable.id}/toggle-active/')
        self.assertEqual(res.status_code, 404)
        self.user_sec_constable.refresh_from_db()
        self.assertFalse(self.user_sec_constable.is_active)

    # 9. Existing Zone 1 SYS_ADMIN cannot change another user's zone to Zone 2
    def test_9_existing_zone_1_sys_admin_cannot_change_user_zone_to_zone_2(self):
        self.client.force_authenticate(user=self.sys_admin_cmr)
        res = self.client.patch(f'/api/v1/auth/users/{self.user_cmr_constable.id}/', {
            'zone': 'Secunderabad'
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('zone', res.data)
        self.user_cmr_constable.refresh_from_db()
        self.assertEqual(self.user_cmr_constable.zone, 'Charminar')

    # 10. Existing Zone 1 SYS_ADMIN can manage permitted Zone 1 users
    def test_10_existing_zone_1_sys_admin_can_manage_permitted_zone_1_users(self):
        self.client.force_authenticate(user=self.sys_admin_cmr)
        # 1. Edit
        edit_res = self.client.patch(f'/api/v1/auth/users/{self.user_cmr_constable.id}/', {
            'first_name': 'Ramesh'
        })
        self.assertEqual(edit_res.status_code, 200)
        self.assertEqual(edit_res.data['first_name'], 'Ramesh')

        # 2. Reset password
        pwd_res = self.client.patch(f'/api/v1/auth/users/{self.user_cmr_constable.id}/', {
            'password': 'NewPolicePass2026!'
        })
        self.assertEqual(pwd_res.status_code, 200)
        from django.contrib.auth import authenticate
        self.assertIsNotNone(authenticate(username='cmr_pc_5001', password='NewPolicePass2026!'))

        # 3. Toggle active
        toggle_res = self.client.post(f'/api/v1/auth/users/{self.user_cmr_constable.id}/toggle-active/')
        self.assertEqual(toggle_res.status_code, 200)
        self.assertFalse(toggle_res.data['is_active'])

    # 11. Zone 1 SYS_ADMIN cannot create Zone 2 user
    def test_11_zone_1_sys_admin_cannot_create_zone_2_user(self):
        self.client.force_authenticate(user=self.sys_admin_cmr)
        res = self.client.post('/api/v1/auth/users/', {
            'username': 'illegal_sec_officer',
            'password': 'Password123!',
            'role': UserRole.CONSTABLE,
            'zone': 'Secunderabad',
            'police_station': 'Amberpet',
            'police_id': 'PC-9999'
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('zone', res.data)
        self.assertFalse(User.objects.filter(username='illegal_sec_officer').exists())

    # 12. Future Zone 1 SYS_ADMIN behaves identically
    def test_12_future_zone_1_sys_admin_behaves_identically(self):
        self.client.force_authenticate(user=self.future_sys_admin_cmr)
        # Can see Zone 1
        res = self.client.get('/api/v1/auth/users/')
        self.assertEqual(res.status_code, 200)
        usernames = [u['username'] for u in res.data['results']]
        self.assertIn('cmr_pc_5001', usernames)
        self.assertNotIn('sec_pc_6001', usernames)

        # Cannot edit Zone 2
        patch_res = self.client.patch(f'/api/v1/auth/users/{self.user_sec_constable.id}/', {
            'first_name': 'Disallowed'
        })
        self.assertEqual(patch_res.status_code, 404)

        # Cannot create Zone 2
        create_res = self.client.post('/api/v1/auth/users/', {
            'username': 'future_illegal_sec',
            'password': 'Password123!',
            'role': UserRole.CONSTABLE,
            'zone': 'Secunderabad',
            'police_station': 'Amberpet'
        })
        self.assertEqual(create_res.status_code, 400)

    # 13. MAIN_OFFICER behavior remains unchanged (global/city-wide when unzoned)
    def test_13_global_main_officer_retains_city_wide_authority(self):
        self.client.force_authenticate(user=self.global_main_officer)
        res = self.client.get('/api/v1/auth/users/')
        self.assertEqual(res.status_code, 200)
        usernames = [u['username'] for u in res.data['results']]
        self.assertIn('cmr_pc_5001', usernames)
        self.assertIn('sec_pc_6001', usernames)

        # Can retrieve both
        r1 = self.client.get(f'/api/v1/auth/users/{self.user_cmr_constable.id}/')
        r2 = self.client.get(f'/api/v1/auth/users/{self.user_sec_constable.id}/')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)

    # 14. Existing ACP/SHO behavior remains unchanged
    def test_14_existing_acp_sho_behavior_remains_unchanged(self):
        # ACP Charminar cannot manage users unless granted manage_users
        self.client.force_authenticate(user=self.acp_cmr)
        res = self.client.get('/api/v1/auth/users/')
        self.assertEqual(res.status_code, 403)

        # SHO Charminar cannot manage users
        self.client.force_authenticate(user=self.sho_cmr)
        res_sho = self.client.get('/api/v1/auth/users/')
        self.assertEqual(res_sho.status_code, 403)

    # 15. Direct API requests cannot bypass frontend filtering
    def test_15_direct_api_requests_cannot_bypass_frontend_filtering(self):
        self.client.force_authenticate(user=self.sys_admin_cmr)
        # Attempt to bypass scope by passing ?zone=Secunderabad
        res = self.client.get('/api/v1/auth/users/?zone=Secunderabad')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['count'], 0)
        self.assertEqual(len(res.data['results']), 0)

        # Attempt to bypass by searching for Zone 2 officer's username
        res_search = self.client.get('/api/v1/auth/users/?search=sec_pc_6001')
        self.assertEqual(res_search.status_code, 200)
        self.assertEqual(res_search.data['count'], 0)


class SuperAdminAndRoleTemplatesTests(TestCase):
    def setUp(self):
        from apps.audit.models import AuditEvent
        from apps.accounts.models import RolePermissionTemplate
        self.client = APIClient()

        # Create SUPER_ADMIN SuchithSara
        self.super_admin = User.objects.create_user(
            username='SuchithSara',
            first_name='Suchith',
            last_name='Sara',
            password='SuperPassword123!',
            role=UserRole.SUPER_ADMIN,
        )

        # Create another global MAIN_OFFICER
        self.main_officer = User.objects.create_user(
            username='main_headquarters',
            password='Password123!',
            role=UserRole.MAIN_OFFICER,
        )

        # Create SYS_ADMIN in Charminar
        self.sys_admin_cmr = User.objects.create_user(
            username='sys_admin_cmr',
            password='Password123!',
            role=UserRole.SYS_ADMIN,
            zone='Charminar',
        )

        # Create Officers in different zones
        self.user_cmr = User.objects.create_user(
            username='pc_cmr_test',
            password='Password123!',
            role=UserRole.CONSTABLE,
            zone='Charminar',
            police_station='Charminar',
        )
        self.user_sec = User.objects.create_user(
            username='pc_sec_test',
            password='Password123!',
            role=UserRole.CONSTABLE,
            zone='Secunderabad',
            police_station='Amberpet',
        )

    def test_super_admin_has_unrestricted_global_access(self):
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get('/api/v1/auth/users/')
        self.assertEqual(res.status_code, 200)
        usernames = [u['username'] for u in res.data['results']]
        self.assertIn('pc_cmr_test', usernames)
        self.assertIn('pc_sec_test', usernames)

    def test_super_admin_can_create_any_role_including_super_admin(self):
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.post('/api/v1/auth/users/', {
            'username': 'second_super_admin',
            'password': 'Password123!',
            'role': UserRole.SUPER_ADMIN,
        })
        self.assertEqual(res.status_code, 201)
        created = User.objects.get(username='second_super_admin')
        self.assertEqual(created.role, UserRole.SUPER_ADMIN)

    def test_non_super_admin_cannot_create_super_admin(self):
        # MAIN_OFFICER attempt
        self.client.force_authenticate(user=self.main_officer)
        res_main = self.client.post('/api/v1/auth/users/', {
            'username': 'illegal_super_from_main',
            'password': 'Password123!',
            'role': UserRole.SUPER_ADMIN,
        })
        self.assertEqual(res_main.status_code, 400)
        self.assertIn('role', res_main.data)

        # SYS_ADMIN attempt
        self.client.force_authenticate(user=self.sys_admin_cmr)
        res_sys = self.client.post('/api/v1/auth/users/', {
            'username': 'illegal_super_from_sys',
            'password': 'Password123!',
            'role': UserRole.SUPER_ADMIN,
            'zone': 'Charminar',
            'police_station': 'Charminar',
        })
        self.assertEqual(res_sys.status_code, 400)

    def test_sys_admin_cannot_create_main_officer(self):
        self.client.force_authenticate(user=self.sys_admin_cmr)
        res = self.client.post('/api/v1/auth/users/', {
            'username': 'illegal_main_from_sys',
            'password': 'Password123!',
            'role': UserRole.MAIN_OFFICER,
            'zone': 'Charminar',
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('role', res.data)

    def test_cannot_demote_or_delete_or_disable_last_super_admin(self):
        self.client.force_authenticate(user=self.super_admin)
        
        # Demote attempt
        demote_res = self.client.patch(f'/api/v1/auth/users/{self.super_admin.id}/', {
            'role': UserRole.MAIN_OFFICER,
        })
        self.assertEqual(demote_res.status_code, 400)
        self.super_admin.refresh_from_db()
        self.assertEqual(self.super_admin.role, UserRole.SUPER_ADMIN)

        # Disable attempt via toggle-active
        disable_res = self.client.post(f'/api/v1/auth/users/{self.super_admin.id}/toggle-active/')
        self.assertEqual(disable_res.status_code, 400)
        self.super_admin.refresh_from_db()
        self.assertTrue(self.super_admin.is_active)

        # Hard delete attempt
        delete_res = self.client.delete(f'/api/v1/auth/users/{self.super_admin.id}/delete/')
        self.assertEqual(delete_res.status_code, 400)
        self.assertTrue(User.objects.filter(username='SuchithSara').exists())

    def test_role_change_by_super_admin_is_audited(self):
        from apps.audit.models import AuditEvent
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.patch(f'/api/v1/auth/users/{self.user_cmr.id}/', {
            'role': UserRole.SHO,
            'police_station': 'Charminar',
        })
        self.assertEqual(res.status_code, 200)
        self.user_cmr.refresh_from_db()
        self.assertEqual(self.user_cmr.role, UserRole.SHO)

        # Audit event checked
        event = AuditEvent.objects.filter(action='ROLE_CHANGED', target_id=str(self.user_cmr.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.details['previous_role'], UserRole.CONSTABLE)
        self.assertEqual(event.details['new_role'], UserRole.SHO)

    def test_role_templates_list_and_update(self):
        from apps.audit.models import AuditEvent
        self.client.force_authenticate(user=self.super_admin)

        # List templates
        list_res = self.client.get('/api/v1/auth/role-templates/')
        self.assertEqual(list_res.status_code, 200)
        self.assertIn('results', list_res.data)
        self.assertIn('canonical_permissions', list_res.data)
        roles_in_list = [r['role'] for r in list_res.data['results']]
        self.assertIn('SUPER_ADMIN', roles_in_list)
        self.assertIn('SYS_ADMIN', roles_in_list)

        # Non-super admin cannot modify templates
        self.client.force_authenticate(user=self.main_officer)
        unauth_update = self.client.put('/api/v1/auth/role-templates/SYS_ADMIN/', {
            'permissions': ['view_dashboard'],
        }, format='json')
        self.assertEqual(unauth_update.status_code, 403)

        # Super admin CAN modify templates
        self.client.force_authenticate(user=self.super_admin)
        new_perms = ['view_dashboard', 'view_live_map', 'view_reports']
        update_res = self.client.put('/api/v1/auth/role-templates/SYS_ADMIN/', {
            'permissions': new_perms,
            'description': 'Updated SYS_ADMIN default capabilities',
        }, format='json')
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.data['permissions'], sorted(new_perms))
        self.assertIn('added', update_res.data)
        self.assertIn('removed', update_res.data)

        # Audit event verified
        audit = AuditEvent.objects.filter(action='ROLE_TEMPLATE_UPDATED', target_id='SYS_ADMIN').first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.details['role'], 'SYS_ADMIN')
        self.assertIn('view_dashboard', audit.details['permissions'])

    def test_custom_permissions_privilege_escalation_blocked(self):
        # SYS_ADMIN cannot grant 'manage_role_templates'
        self.client.force_authenticate(user=self.sys_admin_cmr)
        res = self.client.post('/api/v1/auth/users/', {
            'username': 'escalated_user',
            'password': 'Password123!',
            'role': UserRole.CONSTABLE,
            'zone': 'Charminar',
            'police_station': 'Charminar',
            'custom_permissions': ['manage_role_templates'],
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('custom_permissions', res.data)





