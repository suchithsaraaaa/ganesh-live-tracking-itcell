from datetime import timedelta
from django.db import models
from django.test import TestCase
from django.utils import timezone
from django.db import IntegrityError
from apps.accounts.models import User, UserRole
from apps.idols.models import Idol
from apps.assignments.models import Assignment


class AssignmentTests(TestCase):
    def setUp(self):
        self.sho = User.objects.create_user(
            username='sho_cmr', password='password123',
            role=UserRole.SHO, police_station='Charminar'
        )
        self.pc_1 = User.objects.create_user(
            username='pc_1', password='password123',
            role=UserRole.CONSTABLE, police_id='PC-1'
        )
        self.pc_2 = User.objects.create_user(
            username='pc_2', password='password123',
            role=UserRole.CONSTABLE, police_id='PC-2'
        )
        self.idol_1 = Idol.objects.create(
            gpid='HYDCMRZCMNR0112',
            name='Charminar Idol 1',
            police_station='Charminar',
            zone='Charminar',
            idol_height=18.0
        )
        self.idol_2 = Idol.objects.create(
            gpid='HYDCMRZCMNR0113',
            name='Charminar Idol 2',
            police_station='Charminar',
            zone='Charminar',
            idol_height=18.0
        )

    def test_single_active_assignment(self):
        assignment = Assignment.assign_constable(
            idol=self.idol_1,
            constable=self.pc_1,
            assigned_by=self.sho
        )
        self.assertTrue(assignment.is_active)
        self.assertEqual(assignment.constable, self.pc_1)
        self.assertEqual(assignment.idol, self.idol_1)

    def test_double_assignment_prevention_at_db_level(self):
        Assignment.objects.create(
            idol=self.idol_1,
            constable=self.pc_1,
            is_active=True
        )
        # Attempt to assign the same constable to another idol simultaneously
        with self.assertRaises(IntegrityError):
            Assignment.objects.create(
                idol=self.idol_2,
                constable=self.pc_1,
                is_active=True
            )

    def test_atomic_handover_preserves_history(self):
        initial = Assignment.assign_constable(
            idol=self.idol_1,
            constable=self.pc_1,
            assigned_by=self.sho
        )
        self.assertTrue(initial.is_active)

        # Handover to PC-2
        new_assignment = initial.handover_to_constable(
            new_constable=self.pc_2,
            reason='Shift rotation',
            actor=self.sho
        )

        initial.refresh_from_db()
        self.assertFalse(initial.is_active)
        self.assertIsNotNone(initial.ended_at)
        self.assertEqual(initial.handover_to, self.pc_2)
        self.assertEqual(initial.handover_reason, 'Shift rotation')

        self.assertTrue(new_assignment.is_active)
        self.assertEqual(new_assignment.constable, self.pc_2)
        self.assertEqual(new_assignment.idol, self.idol_1)

    def test_historical_assignment_lookup_at_timestamp(self):
        t0 = timezone.now() - timedelta(hours=3)
        t1 = timezone.now() - timedelta(hours=1)
        t2 = timezone.now()

        # Past assignment from t0 to t1
        Assignment.objects.create(
            idol=self.idol_1,
            constable=self.pc_1,
            started_at=t0,
            ended_at=t1,
            is_active=False
        )
        # Next assignment from t1 onwards
        Assignment.objects.create(
            idol=self.idol_1,
            constable=self.pc_2,
            started_at=t1,
            ended_at=None,
            is_active=True
        )

        # Query: Who was responsible for idol_1 at t0 + 1 hour?
        query_time = t0 + timedelta(hours=1)
        responsible = Assignment.objects.filter(
            idol=self.idol_1,
            started_at__lte=query_time
        ).filter(
            models.Q(ended_at__isnull=True) | models.Q(ended_at__gte=query_time)
        ).first()

        self.assertIsNotNone(responsible)
        self.assertEqual(responsible.constable, self.pc_1)


class EndAssignmentAPITests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        from apps.tracking.models import TrackingSession, TrackingSessionStatus, IdolEvent, IdolEventType
        from apps.audit.models import AuditEvent

        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username='admin_test',
            password='password123',
            email='admin@test.gov',
            role=UserRole.MAIN_OFFICER
        )
        self.sho = User.objects.create_user(
            username='sho_cmr',
            password='password123',
            role=UserRole.SHO,
            police_station='Charminar'
        )
        self.other_sho = User.objects.create_user(
            username='sho_other',
            password='password123',
            role=UserRole.SHO,
            police_station='Abids'
        )
        self.pc = User.objects.create_user(
            username='pc_test',
            password='password123',
            role=UserRole.CONSTABLE,
            police_id='PC-101',
            first_name='Ramesh',
            last_name='Goud'
        )
        self.idol = Idol.objects.create(
            gpid='HYDCMRZCMNR0112',
            name='Charminar Test Idol',
            police_station='Charminar',
            zone='SOUTH ZONE',
            division='CHARMINAR',
            latitude=17.3615,
            longitude=78.4745,
            geocoding_confidence='EXACT',
            idol_height=18.0
        )
        self.assignment = Assignment.assign_constable(
            idol=self.idol,
            constable=self.pc,
            assigned_by=self.sho
        )

    def test_authorized_sho_can_end_assignment(self):
        self.client.force_authenticate(user=self.sho)
        res = self.client.post(f'/api/v1/assignments/{self.assignment.id}/end/', {'reason': 'Duty completed'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['message'], 'Assignment ended successfully.')

        self.assignment.refresh_from_db()
        self.assertFalse(self.assignment.is_active)
        self.assertIsNotNone(self.assignment.ended_at)
        self.assertIn('Duty completed', self.assignment.handover_reason)

        # Check IdolEvent and AuditEvent
        from apps.tracking.models import IdolEvent, IdolEventType
        from apps.audit.models import AuditEvent
        self.assertTrue(IdolEvent.objects.filter(idol=self.idol, event_type=IdolEventType.ASSIGNMENT_ENDED).exists())
        self.assertTrue(AuditEvent.objects.filter(action='ASSIGNMENT_ENDED', target_id=str(self.assignment.id)).exists())

    def test_unauthorized_user_cannot_end_assignment(self):
        # Constable cannot end assignment
        self.client.force_authenticate(user=self.pc)
        res = self.client.post(f'/api/v1/assignments/{self.assignment.id}/end/', {})
        self.assertEqual(res.status_code, 403)

        # SHO from different station cannot end assignment
        self.client.force_authenticate(user=self.other_sho)
        res_other = self.client.post(f'/api/v1/assignments/{self.assignment.id}/end/', {})
        self.assertEqual(res_other.status_code, 403)

        self.assignment.refresh_from_db()
        self.assertTrue(self.assignment.is_active)

    def test_nonexistent_assignment_returns_404(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.post('/api/v1/assignments/999999/end/', {})
        self.assertEqual(res.status_code, 404)

    def test_already_ended_assignment_returns_400(self):
        self.assignment.is_active = False
        self.assignment.ended_at = timezone.now()
        self.assignment.save()

        self.client.force_authenticate(user=self.admin)
        res = self.client.post(f'/api/v1/assignments/{self.assignment.id}/end/', {})
        self.assertEqual(res.status_code, 400)
        self.assertIn('already ended', res.data['error'])

    def test_active_tracking_session_blocks_non_admin_and_permits_admin_force_end(self):
        from apps.tracking.models import TrackingSession, TrackingSessionStatus, IdolEventType

        session = TrackingSession.objects.create(
            assignment=self.assignment,
            status=TrackingSessionStatus.ACTIVE
        )

        # 1. Non-admin (SHO) is blocked from ending an assignment with an active tracking session
        self.client.force_authenticate(user=self.sho)
        res_sho = self.client.post(f'/api/v1/assignments/{self.assignment.id}/end/', {})
        self.assertEqual(res_sho.status_code, 400)
        self.assertTrue(res_sho.data.get('has_active_tracking'))
        self.assertIn('Administrative privilege required', res_sho.data['error'])

        # Assignment must remain active
        self.assignment.refresh_from_db()
        self.assertTrue(self.assignment.is_active)

        # 2. Authorized ADMIN can force-end the assignment with active tracking
        self.client.force_authenticate(user=self.admin)
        res_admin = self.client.post(f'/api/v1/assignments/{self.assignment.id}/end/', {'reason': 'Admin force wrap-up'})
        self.assertEqual(res_admin.status_code, 200)
        self.assertTrue(res_admin.data.get('tracking_terminated'))

        # Assignment becomes inactive
        self.assignment.refresh_from_db()
        self.assertFalse(self.assignment.is_active)
        self.assertIsNotNone(self.assignment.ended_at)

        # Session becomes ADMIN_TERMINATED
        session.refresh_from_db()
        self.assertEqual(session.status, TrackingSessionStatus.ADMIN_TERMINATED)
        self.assertIsNotNone(session.ended_at)

    def test_user_deletion_workflow_end_to_end(self):
        self.client.force_authenticate(user=self.admin)

        # Step 1: Deleting user with active assignment is blocked
        res_del_blocked = self.client.delete(f'/api/v1/auth/users/{self.pc.id}/delete/')
        self.assertEqual(res_del_blocked.status_code, 400)
        self.assertIn('active GPID assignment', res_del_blocked.data['error'])

        # Step 2: End assignment
        res_end = self.client.post(f'/api/v1/assignments/{self.assignment.id}/end/', {'reason': 'Duty wrapped up'})
        self.assertEqual(res_end.status_code, 200)

        # Step 3: Deleting user now succeeds
        res_del_ok = self.client.delete(f'/api/v1/auth/users/{self.pc.id}/delete/')
        self.assertEqual(res_del_ok.status_code, 200)

        # Step 4: User is gone from User table
        self.assertFalse(User.objects.filter(id=self.pc.id).exists())

        # Step 5: Historical assignment survives with snapshots
        self.assignment.refresh_from_db()
        self.assertIsNone(self.assignment.constable)
        self.assertEqual(self.assignment.officer_name_snapshot, 'Ramesh Goud')
        self.assertEqual(self.assignment.police_id_snapshot, 'PC-101')
        self.assertFalse(self.assignment.is_active)


class OfficerAssignmentRedesignTests(TestCase):
    """
    Automated test suite verifying all 22 operational requirements + Excel export
    and critical negative tests for the redesigned Officer Assignment workflow.
    """

    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()

        # Users
        self.main_officer = User.objects.create_superuser(
            username='main_officer_test',
            password='password123',
            email='main@test.gov',
            role=UserRole.MAIN_OFFICER
        )
        self.sho_cmr = User.objects.create_user(
            username='sho_cmr_test',
            password='password123',
            role=UserRole.SHO,
            police_station='Charminar',
            zone='Charminar'
        )
        self.sho_abids = User.objects.create_user(
            username='sho_abids_test',
            password='password123',
            role=UserRole.SHO,
            police_station='Abids',
            zone='Central'
        )
        self.pc_avail = User.objects.create_user(
            username='pc_avail_test',
            password='password123',
            role=UserRole.CONSTABLE,
            police_id='PC-100',
            police_station='Charminar',
            zone='Charminar',
            is_active=True
        )
        self.pc_busy = User.objects.create_user(
            username='pc_busy_test',
            password='password123',
            role=UserRole.CONSTABLE,
            police_id='PC-101',
            police_station='Charminar',
            zone='Charminar',
            is_active=True
        )
        self.pc_disabled = User.objects.create_user(
            username='pc_disabled_test',
            password='password123',
            role=UserRole.CONSTABLE,
            police_id='PC-102',
            police_station='Charminar',
            zone='Charminar',
            is_active=False
        )

        # Idols across height categories
        self.idol_12ft = Idol.objects.create(
            gpid='HYDCMRZCMNR0012',
            name='Subthreshold 12ft Idol',
            police_station='Charminar',
            zone='Charminar',
            division='CHARMINAR',
            idol_height=12.0
        )
        self.idol_15ft = Idol.objects.create(
            gpid='HYDCMRZCMNR0015',
            name='Boundary 15ft Idol',
            police_station='Charminar',
            zone='Charminar',
            division='CHARMINAR',
            idol_height=15.0
        )
        self.idol_20ft = Idol.objects.create(
            gpid='HYDCMRZCMNR0020',
            name='Boundary 20ft Idol',
            police_station='Charminar',
            zone='Charminar',
            division='CHARMINAR',
            idol_height=20.0
        )
        self.idol_21ft = Idol.objects.create(
            gpid='HYDCMRZCMNR0021',
            name='Boundary 21ft Idol',
            police_station='Charminar',
            zone='Charminar',
            division='CHARMINAR',
            idol_height=21.0
        )
        self.idol_25ft = Idol.objects.create(
            gpid='HYDCMRZCMNR0025',
            name='Boundary 25ft Idol',
            police_station='Charminar',
            zone='Charminar',
            division='CHARMINAR',
            idol_height=25.0
        )
        self.idol_26ft = Idol.objects.create(
            gpid='HYDCMRZCMNR0026',
            name='Boundary 26ft Idol',
            police_station='Charminar',
            zone='Charminar',
            division='CHARMINAR',
            idol_height=26.0
        )
        self.idol_30ft = Idol.objects.create(
            gpid='HYDCMRZCMNR0030',
            name='Giant 30ft Idol',
            police_station='Charminar',
            zone='Charminar',
            division='CHARMINAR',
            idol_height=30.0
        )
        self.idol_abids = Idol.objects.create(
            gpid='HYDABDZABID0018',
            name='Abids 18ft Idol',
            police_station='Abids',
            zone='Central',
            division='ABIDS',
            idol_height=18.0
        )

    # 1. GPID below 15 FT is included in assignable registry and categorized as below_15
    def test_01_gpid_below_15ft_included_in_registry(self):
        self.client.force_authenticate(user=self.main_officer)
        res = self.client.get('/api/v1/assignments/registry/')
        self.assertEqual(res.status_code, 200)
        gpids = [item['gpid'] for item in res.data['results']]
        self.assertIn(self.idol_12ft.gpid, gpids)

        # Test height bucket filter below_15
        res_below = self.client.get('/api/v1/assignments/registry/?height_bucket=below_15')
        self.assertEqual(res_below.status_code, 200)
        below_gpids = [item['gpid'] for item in res_below.data['results']]
        self.assertIn(self.idol_12ft.gpid, below_gpids)
        self.assertNotIn(self.idol_15ft.gpid, below_gpids)

    # 2. GPID exactly 15 FT is included
    def test_02_gpid_exactly_15ft_included(self):
        self.client.force_authenticate(user=self.main_officer)
        res = self.client.get('/api/v1/assignments/registry/')
        gpids = [item['gpid'] for item in res.data['results']]
        self.assertIn(self.idol_15ft.gpid, gpids)

    # 3. GPID exactly 20 FT is in 15–20 bucket
    def test_03_gpid_exactly_20ft_is_15_20(self):
        self.client.force_authenticate(user=self.main_officer)
        res = self.client.get('/api/v1/assignments/registry/?height_bucket=15_20')
        gpids = [item['gpid'] for item in res.data['results']]
        self.assertIn(self.idol_20ft.gpid, gpids)
        self.assertIn(self.idol_15ft.gpid, gpids)
        self.assertNotIn(self.idol_21ft.gpid, gpids)

    # 4. GPID exactly 21 FT is in 21–25 bucket
    def test_04_gpid_exactly_21ft_is_21_25(self):
        self.client.force_authenticate(user=self.main_officer)
        res = self.client.get('/api/v1/assignments/registry/?height_bucket=21_25')
        gpids = [item['gpid'] for item in res.data['results']]
        self.assertIn(self.idol_21ft.gpid, gpids)
        self.assertNotIn(self.idol_20ft.gpid, gpids)

    # 5. GPID exactly 25 FT is in 21–25 bucket
    def test_05_gpid_exactly_25ft_is_21_25(self):
        self.client.force_authenticate(user=self.main_officer)
        res = self.client.get('/api/v1/assignments/registry/?height_bucket=21_25')
        gpids = [item['gpid'] for item in res.data['results']]
        self.assertIn(self.idol_25ft.gpid, gpids)

    # 6. GPID exactly 26 FT is in 26+ bucket
    def test_06_gpid_exactly_26ft_is_26_plus(self):
        self.client.force_authenticate(user=self.main_officer)
        res = self.client.get('/api/v1/assignments/registry/?height_bucket=26_plus')
        gpids = [item['gpid'] for item in res.data['results']]
        self.assertIn(self.idol_26ft.gpid, gpids)

    # 7. GPID above 26 FT is in 26+ bucket
    def test_07_gpid_above_26ft_is_26_plus(self):
        self.client.force_authenticate(user=self.main_officer)
        res = self.client.get('/api/v1/assignments/registry/?height_bucket=26_plus')
        gpids = [item['gpid'] for item in res.data['results']]
        self.assertIn(self.idol_30ft.gpid, gpids)

    # 8. Search finds subthreshold GPID
    def test_08_search_finds_subthreshold_gpid(self):
        self.client.force_authenticate(user=self.main_officer)
        res = self.client.get(f'/api/v1/assignments/registry/?search={self.idol_12ft.gpid}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['gpid'], self.idol_12ft.gpid)

    # 9. Assignment creation supports sub-15 FT GPIDs
    def test_09_assignment_creation_supports_subthreshold_15ft(self):
        self.client.force_authenticate(user=self.sho_cmr)
        res = self.client.post('/api/v1/assignments/create/', {
            'gpid': self.idol_12ft.gpid,
            'constable_id': self.pc_avail.id
        })
        self.assertEqual(res.status_code, 201)
        self.assertTrue(Assignment.objects.filter(idol=self.idol_12ft, is_active=True).exists())

    # 10. Zone filtering works
    def test_10_zone_filtering_works(self):
        self.client.force_authenticate(user=self.main_officer)
        res = self.client.get('/api/v1/assignments/registry/?zone=Charminar')
        self.assertEqual(res.status_code, 200)
        for item in res.data['results']:
            self.assertEqual(item['zone'].lower(), 'charminar')
        gpids = [item['gpid'] for item in res.data['results']]
        self.assertNotIn(self.idol_abids.gpid, gpids)

    # 11. Police Station filtering works
    def test_11_police_station_filtering_works(self):
        self.client.force_authenticate(user=self.main_officer)
        res = self.client.get('/api/v1/assignments/registry/?police_station=Charminar')
        self.assertEqual(res.status_code, 200)
        for item in res.data['results']:
            self.assertEqual(item['police_station'].lower(), 'charminar')
        gpids = [item['gpid'] for item in res.data['results']]
        self.assertNotIn(self.idol_abids.gpid, gpids)

    # 12. Height filtering works (tested with multiple buckets)
    def test_12_height_filtering_works(self):
        self.client.force_authenticate(user=self.main_officer)
        res_green = self.client.get('/api/v1/assignments/registry/?height_bucket=15_20')
        for item in res_green.data['results']:
            self.assertTrue(15.0 <= float(item['idol_height']) < 21.0)

        res_yellow = self.client.get('/api/v1/assignments/registry/?height_bucket=21_25')
        for item in res_yellow.data['results']:
            self.assertTrue(21.0 <= float(item['idol_height']) < 26.0)

    # 13. Assignment status filtering works
    def test_13_assignment_status_filtering_works(self):
        Assignment.assign_constable(idol=self.idol_20ft, constable=self.pc_busy, assigned_by=self.sho_cmr)
        self.client.force_authenticate(user=self.main_officer)

        # Assigned only
        res_assigned = self.client.get('/api/v1/assignments/registry/?assignment_status=assigned')
        assigned_gpids = [item['gpid'] for item in res_assigned.data['results']]
        self.assertIn(self.idol_20ft.gpid, assigned_gpids)
        self.assertNotIn(self.idol_15ft.gpid, assigned_gpids)

        # Unassigned only
        res_unassigned = self.client.get('/api/v1/assignments/registry/?assignment_status=unassigned')
        unassigned_gpids = [item['gpid'] for item in res_unassigned.data['results']]
        self.assertNotIn(self.idol_20ft.gpid, unassigned_gpids)
        self.assertIn(self.idol_15ft.gpid, unassigned_gpids)

    # 14. Combined filters use AND logic
    def test_14_combined_filters_use_and_logic(self):
        Assignment.assign_constable(idol=self.idol_20ft, constable=self.pc_busy, assigned_by=self.sho_cmr)
        self.client.force_authenticate(user=self.main_officer)

        # Zone=Charminar AND PS=Charminar AND Height=15_20 AND Status=unassigned
        res = self.client.get(
            '/api/v1/assignments/registry/?zone=Charminar&police_station=Charminar&height_bucket=15_20&assignment_status=unassigned'
        )
        gpids = [item['gpid'] for item in res.data['results']]
        self.assertIn(self.idol_15ft.gpid, gpids)
        self.assertNotIn(self.idol_20ft.gpid, gpids) # excluded because it's assigned
        self.assertNotIn(self.idol_21ft.gpid, gpids) # excluded by height
        self.assertNotIn(self.idol_abids.gpid, gpids) # excluded by zone/PS

    # 15. Unauthorized jurisdiction is rejected
    def test_15_unauthorized_jurisdiction_rejected(self):
        self.client.force_authenticate(user=self.sho_abids)
        # Attempting to assign to Charminar idol
        res = self.client.post('/api/v1/assignments/create/', {
            'gpid': self.idol_15ft.gpid,
            'constable_id': self.pc_avail.id
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('jurisdiction', str(res.data).lower())

    # 16. Disabled officer cannot be assigned
    def test_16_disabled_officer_cannot_be_assigned(self):
        self.client.force_authenticate(user=self.sho_cmr)
        res = self.client.post('/api/v1/assignments/create/', {
            'gpid': self.idol_15ft.gpid,
            'constable_id': self.pc_disabled.id
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('disabled', str(res.data).lower())

    # 17. Already assigned officer cannot receive another active assignment
    def test_17_already_assigned_officer_cannot_receive_another_active_assignment(self):
        Assignment.assign_constable(idol=self.idol_20ft, constable=self.pc_busy, assigned_by=self.sho_cmr)
        self.client.force_authenticate(user=self.sho_cmr)
        res = self.client.post('/api/v1/assignments/create/', {
            'gpid': self.idol_15ft.gpid,
            'constable_id': self.pc_busy.id
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('already has an active gpid assignment', str(res.data).lower())

    # 18. Already assigned GPID cannot receive another active officer
    def test_18_already_assigned_gpid_cannot_receive_another_active_officer(self):
        Assignment.assign_constable(idol=self.idol_20ft, constable=self.pc_busy, assigned_by=self.sho_cmr)
        self.client.force_authenticate(user=self.sho_cmr)
        res = self.client.post('/api/v1/assignments/create/', {
            'gpid': self.idol_20ft.gpid,
            'constable_id': self.pc_avail.id
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('already has an active officer assignment', str(res.data).lower())

    # 19. Successful assignment creates Assignment
    def test_19_successful_assignment_creates_assignment(self):
        self.client.force_authenticate(user=self.sho_cmr)
        res = self.client.post('/api/v1/assignments/create/', {
            'gpid': self.idol_15ft.gpid,
            'constable_id': self.pc_avail.id
        })
        self.assertEqual(res.status_code, 201)
        assignment_id = res.data['id']
        assign = Assignment.objects.get(id=assignment_id)
        self.assertTrue(assign.is_active)
        self.assertEqual(assign.constable, self.pc_avail)
        self.assertEqual(assign.idol, self.idol_15ft)

    # 20. Successful assignment creates PROCESSION_ASSIGNED event
    def test_20_successful_assignment_creates_appropriate_event(self):
        from apps.tracking.models import IdolEvent
        from apps.audit.models import AuditEvent

        self.client.force_authenticate(user=self.sho_cmr)
        res = self.client.post('/api/v1/assignments/create/', {
            'gpid': self.idol_15ft.gpid,
            'constable_id': self.pc_avail.id
        })
        self.assertEqual(res.status_code, 201)

        # Check IdolEvent
        event = IdolEvent.objects.filter(idol=self.idol_15ft, event_type='PROCESSION_ASSIGNED').first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor, self.sho_cmr)

        # Check AuditEvent
        audit = AuditEvent.objects.filter(action='PROCESSION_ASSIGNED', target_model='Assignment').first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.details['gpid'], self.idol_15ft.gpid)

    # 21. Ending assignment preserves history
    def test_21_ending_assignment_preserves_history(self):
        assignment = Assignment.assign_constable(idol=self.idol_15ft, constable=self.pc_avail, assigned_by=self.sho_cmr)
        self.client.force_authenticate(user=self.sho_cmr)
        res = self.client.post(f'/api/v1/assignments/{assignment.id}/end/', {'reason': 'Shift completed'})
        self.assertEqual(res.status_code, 200)

        assignment.refresh_from_db()
        self.assertFalse(assignment.is_active)
        self.assertIsNotNone(assignment.ended_at)
        self.assertEqual(assignment.constable, self.pc_avail)

    # 22. Active tracking prevents unsafe assignment ending
    def test_22_active_tracking_prevents_unsafe_assignment_ending(self):
        from apps.tracking.models import TrackingSession, TrackingSessionStatus
        assignment = Assignment.assign_constable(idol=self.idol_15ft, constable=self.pc_avail, assigned_by=self.sho_cmr)
        session = TrackingSession.objects.create(assignment=assignment, status=TrackingSessionStatus.ACTIVE)

        self.client.force_authenticate(user=self.sho_cmr)
        res = self.client.post(f'/api/v1/assignments/{assignment.id}/end/', {})
        self.assertEqual(res.status_code, 400)
        self.assertTrue(res.data.get('has_active_tracking'))

        assignment.refresh_from_db()
        self.assertTrue(assignment.is_active)

    # 23. Excel export returns valid xlsx
    def test_23_excel_export_returns_valid_xlsx(self):
        self.client.force_authenticate(user=self.main_officer)
        res = self.client.get('/api/v1/assignments/export/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment; filename="Hyderabad_Police_Officer_Assignments_', res['Content-Disposition'])
        self.assertGreater(len(res.content), 1000)

    # 24. Subthreshold idol can be assigned and retrieved via registry
    def test_24_subthreshold_lookup_and_assign_allowed(self):
        self.client.force_authenticate(user=self.main_officer)

        # 1. Direct registry detail lookup succeeds for <15 FT
        res_lookup = self.client.get(f'/api/v1/assignments/registry/{self.idol_12ft.gpid}/')
        self.assertEqual(res_lookup.status_code, 200)
        self.assertEqual(res_lookup.data['gpid'], self.idol_12ft.gpid)

        # 2. Assignment creation succeeds for <15 FT
        res_assign = self.client.post('/api/v1/assignments/create/', {
            'gpid': self.idol_12ft.gpid,
            'constable_id': self.pc_avail.id
        })
        self.assertEqual(res_assign.status_code, 201)
        self.assertTrue(Assignment.objects.filter(idol=self.idol_12ft, is_active=True).exists())

    # 25. Eligible officers endpoint matches police station and zone, excludes assigned
    def test_25_eligible_officers_endpoint_matches_station_and_zone(self):
        self.client.force_authenticate(user=self.main_officer)

        # Create another constable in same station and zone
        pc_cmr_2 = User.objects.create_user(
            username='pc_cmr_2', password='password123', role=UserRole.CONSTABLE,
            police_station='Charminar', zone='Charminar', is_active=True
        )
        # Create constable in DIFFERENT station
        pc_other = User.objects.create_user(
            username='pc_other', password='password123', role=UserRole.CONSTABLE,
            police_station='Abids', zone='Central', is_active=True
        )

        res = self.client.get(f'/api/v1/assignments/registry/{self.idol_15ft.gpid}/eligible-officers/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('officers', res.data)
        officer_ids = [o['id'] for o in res.data['officers']]
        self.assertIn(self.pc_avail.id, officer_ids)
        self.assertIn(pc_cmr_2.id, officer_ids)
        self.assertNotIn(pc_other.id, officer_ids)

        # Subthreshold idol gives 200 and returns eligible officers
        res_sub = self.client.get(f'/api/v1/assignments/registry/{self.idol_12ft.gpid}/eligible-officers/')
        self.assertEqual(res_sub.status_code, 200)
        self.assertIn('officers', res_sub.data)

    # 26. Visarjan date filter supports today, tomorrow, and custom dates
    def test_26_visarjan_date_filter_today_and_tomorrow(self):
        from datetime import date, timedelta
        self.client.force_authenticate(user=self.main_officer)

        today = date.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)

        self.idol_15ft.immersion_date = today
        self.idol_15ft.save()

        self.idol_20ft.immersion_date = tomorrow
        self.idol_20ft.save()

        self.idol_21ft.immersion_date = yesterday
        self.idol_21ft.save()

        # Test 'today'
        res_today = self.client.get('/api/v1/assignments/registry/?visarjan_date=today')
        self.assertEqual(res_today.status_code, 200)
        gpids_today = [item['gpid'] for item in res_today.data['results']]
        self.assertIn(self.idol_15ft.gpid, gpids_today)
        self.assertNotIn(self.idol_20ft.gpid, gpids_today)
        self.assertNotIn(self.idol_21ft.gpid, gpids_today)

        # Test 'tomorrow'
        res_tomorrow = self.client.get('/api/v1/assignments/registry/?visarjan_date=tomorrow')
        self.assertEqual(res_tomorrow.status_code, 200)
        gpids_tomorrow = [item['gpid'] for item in res_tomorrow.data['results']]
        self.assertIn(self.idol_20ft.gpid, gpids_tomorrow)
        self.assertNotIn(self.idol_15ft.gpid, gpids_tomorrow)

        # Test custom YYYY-MM-DD
        target_str = today.strftime('%Y-%m-%d')
        res_custom = self.client.get(f'/api/v1/assignments/registry/?visarjan_date={target_str}')
        self.assertEqual(res_custom.status_code, 200)
        gpids_custom = [item['gpid'] for item in res_custom.data['results']]
        self.assertIn(self.idol_15ft.gpid, gpids_custom)
        self.assertNotIn(self.idol_20ft.gpid, gpids_custom)

    # 27. Excel export includes Visarjan Date column
    def test_27_excel_export_includes_visarjan_date_column(self):
        import io, openpyxl
        self.client.force_authenticate(user=self.main_officer)
        res = self.client.get('/api/v1/assignments/export/?visarjan_date=today')
        self.assertEqual(res.status_code, 200)

        wb = openpyxl.load_workbook(io.BytesIO(res.content))
        ws = wb.active
        headers = [ws.cell(row=4, column=col).value for col in range(1, 16)]
        self.assertIn("Visarjan Date", headers)
        self.assertEqual(headers[5], "Visarjan Date")


class AdminForceEndAssignmentTests(TestCase):
    """
    Exhaustive tests for Admin Force-End Assignment, immediate officer release,
    atomic state transitions, historical telemetry preservation, and reassignment.
    """
    def setUp(self):
        from rest_framework.test import APIClient
        from apps.tracking.models import TrackingSession, TrackingSessionStatus, LocationPoint

        self.client = APIClient()
        self.main_officer = User.objects.create_superuser(
            username='admin_boss', password='password123',
            role=UserRole.MAIN_OFFICER, first_name='Police', last_name='Commissioner'
        )
        self.sho_chaderghat = User.objects.create_user(
            username='sho_chaderghat', password='password123',
            role=UserRole.SHO, police_station='Chaderghat', zone='SOUTH ZONE'
        )
        self.sho_charminar = User.objects.create_user(
            username='sho_other', password='password123',
            role=UserRole.SHO, police_station='Charminar', zone='SOUTH ZONE'
        )
        self.constable = User.objects.create_user(
            username='android1', password='password123',
            role=UserRole.CONSTABLE, police_id='TG-CHD-001',
            first_name='Ground', last_name='Staff',
            police_station='Chaderghat', zone='SOUTH ZONE'
        )
        self.idol_a = Idol.objects.create(
            gpid='HYDCMRZCHGT1164',
            name='Chaderghat Idol A',
            police_station='Chaderghat',
            zone='SOUTH ZONE',
            division='CHADERGHAT',
            idol_height=18.0
        )
        self.idol_b = Idol.objects.create(
            gpid='HYDCMRZCHGT1165',
            name='Chaderghat Idol B',
            police_station='Chaderghat',
            zone='SOUTH ZONE',
            division='CHADERGHAT',
            idol_height=22.0
        )

        # Active assignment for idol A
        self.assignment_a = Assignment.assign_constable(
            idol=self.idol_a,
            constable=self.constable,
            assigned_by=self.sho_chaderghat
        )

        # Active tracking session with GPS telemetry breadcrumbs
        self.session_a = TrackingSession.objects.create(
            assignment=self.assignment_a,
            status=TrackingSessionStatus.ACTIVE
        )
        now = timezone.now()
        self.pt1 = LocationPoint.objects.create(
            session=self.session_a,
            latitude=17.3850, longitude=78.4867,
            accuracy=4.5, speed=1.2,
            recorded_at=now - timedelta(minutes=10)
        )
        self.pt2 = LocationPoint.objects.create(
            session=self.session_a,
            latitude=17.3870, longitude=78.4880,
            accuracy=3.8, speed=1.5,
            recorded_at=now - timedelta(minutes=5)
        )

    def test_admin_force_ends_active_assignment_successfully(self):
        """Admin can force-end an assignment even when active tracking session exists."""
        from apps.tracking.models import TrackingSession, TrackingSessionStatus, IdolEvent, IdolEventType
        from apps.audit.models import AuditEvent

        self.client.force_authenticate(user=self.main_officer)
        res = self.client.post(
            f'/api/v1/assignments/{self.assignment_a.id}/end/',
            {'reason': 'Emergency reassignment to high-priority mandap'}
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data.get('tracking_terminated'))

        # 1. Assignment is ended
        self.assignment_a.refresh_from_db()
        self.assertFalse(self.assignment_a.is_active)
        self.assertIsNotNone(self.assignment_a.ended_at)
        self.assertEqual(self.assignment_a.constable, self.constable)
        self.assertIn('Emergency reassignment', self.assignment_a.handover_reason)

        # 2. Tracking session is ADMIN_TERMINATED
        self.session_a.refresh_from_db()
        self.assertEqual(self.session_a.status, TrackingSessionStatus.ADMIN_TERMINATED)
        self.assertIsNotNone(self.session_a.ended_at)

        # 3. Historical telemetry is 100% preserved
        self.assertEqual(self.session_a.location_points.count(), 2)

        # 4. Administrative termination events recorded
        admin_event = IdolEvent.objects.filter(
            idol=self.idol_a,
            event_type=IdolEventType.PROCESSION_ADMIN_TERMINATED
        ).first()
        self.assertIsNotNone(admin_event)
        self.assertEqual(admin_event.actor, self.main_officer)
        self.assertAlmostEqual(admin_event.latitude, 17.3870, places=4)
        self.assertTrue(admin_event.metadata.get('administrative_termination'))

        force_ended_event = IdolEvent.objects.filter(
            idol=self.idol_a,
            event_type=IdolEventType.ASSIGNMENT_FORCE_ENDED
        ).first()
        self.assertIsNotNone(force_ended_event)

        # 5. No fake RETURNED_TO_ORIGIN event created
        self.assertFalse(
            IdolEvent.objects.filter(idol=self.idol_a, event_type=IdolEventType.RETURNED_TO_ORIGIN).exists()
        )

    def test_officer_immediately_freed_and_available_for_reassignment(self):
        """Once force-ended, the officer is immediately available for reassignment to GPID B."""
        from apps.tracking.models import TrackingSessionStatus

        # Admin force-ends assignment A
        self.client.force_authenticate(user=self.main_officer)
        res_end = self.client.post(
            f'/api/v1/assignments/{self.assignment_a.id}/end/',
            {'reason': 'Shift completed'}
        )
        self.assertEqual(res_end.status_code, 200)

        # Check eligible officers for GPID B
        res_eligible = self.client.get(
            f'/api/v1/assignments/registry/{self.idol_b.gpid}/eligible-officers/'
        )
        self.assertEqual(res_eligible.status_code, 200)
        officer_ids = [o['id'] for o in res_eligible.data['officers']]
        self.assertIn(self.constable.id, officer_ids)

        # Check general assignable officers directory with available_only=true
        res_dir = self.client.get('/api/v1/auth/officers/?available_only=true&police_station=Chaderghat')
        self.assertEqual(res_dir.status_code, 200)
        dir_ids = [o['id'] for o in res_dir.data['results']]
        self.assertIn(self.constable.id, dir_ids)

        # Reassign to GPID B
        res_assign = self.client.post('/api/v1/assignments/create/', {
            'gpid': self.idol_b.gpid,
            'constable_id': self.constable.id
        })
        self.assertEqual(res_assign.status_code, 201)

        # Constable is now active on GPID B
        self.assertTrue(
            Assignment.objects.filter(idol=self.idol_b, constable=self.constable, is_active=True).exists()
        )

        # Constable is no longer in available list
        res_dir_after = self.client.get('/api/v1/auth/officers/?available_only=true&police_station=Chaderghat')
        dir_ids_after = [o['id'] for o in res_dir_after.data['results']]
        self.assertNotIn(self.constable.id, dir_ids_after)

    def test_non_admin_cannot_force_end_active_tracking_session(self):
        """Station Officer is blocked from ending assignment when active tracking session exists."""
        self.client.force_authenticate(user=self.sho_chaderghat)
        res = self.client.post(f'/api/v1/assignments/{self.assignment_a.id}/end/', {})
        self.assertEqual(res.status_code, 400)
        self.assertTrue(res.data.get('has_active_tracking'))
        self.assertIn('Administrative privilege required', res.data['error'])

        # Assignment remains active
        self.assignment_a.refresh_from_db()
        self.assertTrue(self.assignment_a.is_active)

    def test_unauthorized_constable_receives_403(self):
        """Field constable cannot end their own assignment via EndAssignmentView."""
        self.client.force_authenticate(user=self.constable)
        res = self.client.post(f'/api/v1/assignments/{self.assignment_a.id}/end/', {})
        self.assertEqual(res.status_code, 403)

    def test_repeated_force_end_is_idempotent(self):
        """Second call to end an already ended assignment returns 400 without crashing."""
        self.client.force_authenticate(user=self.main_officer)
        res1 = self.client.post(f'/api/v1/assignments/{self.assignment_a.id}/end/', {})
        self.assertEqual(res1.status_code, 200)

        res2 = self.client.post(f'/api/v1/assignments/{self.assignment_a.id}/end/', {})
        self.assertEqual(res2.status_code, 400)
        self.assertIn('already ended', res2.data['error'])

    def test_terminated_session_excluded_from_active_tracking_map(self):
        """Once administratively terminated, session is excluded from active live tracking queries."""
        from apps.tracking.models import TrackingSession, TrackingSessionStatus

        self.client.force_authenticate(user=self.main_officer)
        # Verify initially present
        active_before = TrackingSession.objects.filter(status=TrackingSessionStatus.ACTIVE)
        self.assertIn(self.session_a, active_before)

        # Force-end
        self.client.post(f'/api/v1/assignments/{self.assignment_a.id}/end/', {})

        # Verify no longer in active query
        active_after = TrackingSession.objects.filter(status=TrackingSessionStatus.ACTIVE)
        self.assertNotIn(self.session_a, active_after)

        # But present in all sessions
        self.assertTrue(TrackingSession.objects.filter(id=self.session_a.id).exists())


class AllAuthoritativeGPIDsAssignmentTrackingTests(TestCase):
    """
    Targeted test suite verifying:
    1. Sub-15 FT idols (10 FT, 12 FT, 14 FT) are available in assignment registry.
    2. 15 FT and 26+ FT idols remain assignable.
    3. Main Dashboard strictly excludes sub-15 FT idols.
    4. Assignment search finds sub-15 FT GPIDs and pandals.
    5. Sub-15 FT GPID can be assigned with normal conditions.
    6. Assigned but NOT_STARTED GPID does NOT appear on Live Tracking.
    7. Sub-15 FT GPID appears on Live Tracking after valid procession start.
    8. Live marker uses actual telemetry.
    9. One GPID produces one live marker.
    10. Zonal SYS_ADMIN is strictly zone-scoped.
    11. Filters compose with AND logic.
    12. Excel export respects filters and includes all heights.
    """

    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
        from apps.tracking.models import TrackingSession, TrackingSessionStatus, LocationPoint
        from apps.idols.models import ProcessionState
        from datetime import date, timedelta

        self.today = date.today()
        self.tomorrow = self.today + timedelta(days=1)

        # Super Admin / Main Officer (Citywide)
        self.super_admin = User.objects.create_superuser(
            username='city_superadmin', password='password123', email='admin@police.gov.in'
        )

        # Zonal Sys Admin (Charminar Zone only)
        self.zonal_sysadmin_cmr = User.objects.create_user(
            username='sysadmin_cmr', password='password123',
            role=UserRole.SYS_ADMIN, zone='Charminar'
        )

        # Constables
        self.pc_cmr = User.objects.create_user(
            username='pc_charminar', password='password123',
            role=UserRole.CONSTABLE, police_station='Charminar', zone='Charminar',
            police_id='PC-CMR-01', is_active=True
        )
        self.pc_sec = User.objects.create_user(
            username='pc_secunderabad', password='password123',
            role=UserRole.CONSTABLE, police_station='Gopalpuram', zone='Secunderabad',
            police_id='PC-SEC-01', is_active=True
        )

        # Idols: Sub-15 FT
        self.idol_10ft = Idol.objects.create(
            gpid='HYDCMRZCMNR1010', name='Lalitha Pandal 10ft',
            police_station='Charminar', zone='Charminar',
            idol_height=10.0, immersion_date=self.today,
            procession_state=ProcessionState.NOT_STARTED
        )
        self.idol_12ft = Idol.objects.create(
            gpid='HYDCMRZCMNR1012', name='Balanagar Pandal 12ft',
            police_station='Charminar', zone='Charminar',
            idol_height=12.0, immersion_date=self.tomorrow,
            procession_state=ProcessionState.NOT_STARTED
        )
        self.idol_14ft = Idol.objects.create(
            gpid='HYDCMRZCMNR1014', name='Nayapul Pandal 14ft',
            police_station='Charminar', zone='Charminar',
            idol_height=14.0, immersion_date=self.today,
            procession_state=ProcessionState.NOT_STARTED
        )

        # Idols: 15+ FT
        self.idol_18ft = Idol.objects.create(
            gpid='HYDCMRZCMNR1018', name='Gulzar Houz 18ft',
            police_station='Charminar', zone='Charminar',
            idol_height=18.0, immersion_date=self.today,
            procession_state=ProcessionState.NOT_STARTED
        )
        self.idol_28ft = Idol.objects.create(
            gpid='HYDCMRZCMNR1028', name='Charminar Grand 28ft',
            police_station='Charminar', zone='Charminar',
            idol_height=28.0, immersion_date=self.tomorrow,
            procession_state=ProcessionState.NOT_STARTED
        )

        # Idol in Secunderabad Zone
        self.idol_sec_10ft = Idol.objects.create(
            gpid='HYDSECZGPLP2010', name='Secunderabad Idol 10ft',
            police_station='Gopalpuram', zone='Secunderabad',
            idol_height=10.0, immersion_date=self.today,
            procession_state=ProcessionState.NOT_STARTED
        )

    def test_01_sub_15ft_idols_returned_by_assignment_registry(self):
        """10 FT, 12 FT, and 14 FT idols are returned by the assignment registry."""
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.get('/api/v1/assignments/registry/')
        self.assertEqual(res.status_code, 200)
        returned_gpids = [item['gpid'] for item in res.data['results']]
        self.assertIn(self.idol_10ft.gpid, returned_gpids)
        self.assertIn(self.idol_12ft.gpid, returned_gpids)
        self.assertIn(self.idol_14ft.gpid, returned_gpids)
        self.assertIn(self.idol_18ft.gpid, returned_gpids)
        self.assertIn(self.idol_28ft.gpid, returned_gpids)

        # Summary KPIs include count_below_15
        summary = res.data['summary']
        self.assertEqual(summary['count_below_15'], 4)  # 10ft, 12ft, 14ft, sec_10ft
        self.assertEqual(summary['count_15_20'], 1)     # 18ft
        self.assertEqual(summary['count_26_plus'], 1)  # 28ft

    def test_02_non_dashboard_list_strictly_excludes_sub_15ft_while_dashboard_shows_today_visarjans(self):
        """Non-dashboard idol list strictly enforces >= 15 FT, while Main Dashboard shows today's visarjans across all heights."""
        self.client.force_authenticate(user=self.super_admin)
        res_list = self.client.get('/api/v1/idols/')
        self.assertEqual(res_list.status_code, 200)
        dashboard_gpids = [item['gpid'] for item in res_list.data['results']]

        # 15+ FT present in non-dashboard list
        self.assertIn(self.idol_18ft.gpid, dashboard_gpids)
        self.assertIn(self.idol_28ft.gpid, dashboard_gpids)

        # Sub-15 FT strictly absent from non-dashboard list
        self.assertNotIn(self.idol_10ft.gpid, dashboard_gpids)
        self.assertNotIn(self.idol_12ft.gpid, dashboard_gpids)
        self.assertNotIn(self.idol_14ft.gpid, dashboard_gpids)
        self.assertNotIn(self.idol_sec_10ft.gpid, dashboard_gpids)

        # Main Dashboard stats shows TODAY'S visarjans across ALL heights (4 today: 10ft, 14ft, 18ft, sec_10ft)
        res_stats = self.client.get('/api/v1/idols/dashboard/')
        self.assertEqual(res_stats.status_code, 200)
        self.assertEqual(res_stats.data['kpis']['total_idols'], 4)
        self.assertEqual(res_stats.data['kpis']['h_below_15'], 3)
        self.assertEqual(res_stats.data['kpis']['h_15_20'], 1)
        self.assertEqual(res_stats.data['kpis']['h_26_plus'], 0)

    def test_03_assignment_search_finds_sub_15ft_gpid_and_name(self):
        """Search finds sub-15 FT idols by GPID or Pandal Name."""
        self.client.force_authenticate(user=self.super_admin)

        # Search by GPID
        res_gpid = self.client.get(f'/api/v1/assignments/registry/?search={self.idol_10ft.gpid}')
        self.assertEqual(res_gpid.status_code, 200)
        self.assertEqual(len(res_gpid.data['results']), 1)
        self.assertEqual(res_gpid.data['results'][0]['gpid'], self.idol_10ft.gpid)

        # Search by Pandal Name
        res_name = self.client.get('/api/v1/assignments/registry/?search=Lalitha')
        self.assertEqual(res_name.status_code, 200)
        self.assertEqual(len(res_name.data['results']), 1)
        self.assertEqual(res_name.data['results'][0]['gpid'], self.idol_10ft.gpid)

    def test_04_sub_15ft_idol_assignable_subject_to_station_matching(self):
        """Sub-15 FT idol can be assigned when officer matches station and zone."""
        self.client.force_authenticate(user=self.super_admin)

        # Eligible officers returns matching constable
        res_eligible = self.client.get(f'/api/v1/assignments/registry/{self.idol_10ft.gpid}/eligible-officers/')
        self.assertEqual(res_eligible.status_code, 200)
        officer_ids = [o['id'] for o in res_eligible.data['officers']]
        self.assertIn(self.pc_cmr.id, officer_ids)
        self.assertNotIn(self.pc_sec.id, officer_ids)  # Wrong station

        # Assign succeeds
        res_assign = self.client.post('/api/v1/assignments/create/', {
            'gpid': self.idol_10ft.gpid,
            'constable_id': self.pc_cmr.id
        })
        self.assertEqual(res_assign.status_code, 201)
        self.assertTrue(Assignment.objects.filter(idol=self.idol_10ft, constable=self.pc_cmr, is_active=True).exists())

    def test_05_assigned_but_not_started_does_not_appear_on_live_tracking(self):
        """Assigned GPID without started tracking session does NOT appear on Live Tracking."""
        self.client.force_authenticate(user=self.super_admin)

        # Assign 10 FT idol
        Assignment.assign_constable(idol=self.idol_10ft, constable=self.pc_cmr, assigned_by=self.super_admin)

        # Check live tracking endpoint
        res_tracking = self.client.get('/api/v1/tracking/active/')
        self.assertEqual(res_tracking.status_code, 200)
        live_gpids = [m['gpid'] for m in res_tracking.data]
        self.assertNotIn(self.idol_10ft.gpid, live_gpids)

    def test_06_started_sub_15ft_idol_appears_on_live_tracking_with_telemetry(self):
        """Sub-15 FT idol appears on Live Tracking after procession starts with real GPS."""
        from apps.tracking.models import TrackingSession, TrackingSessionStatus, LocationPoint
        from django.utils import timezone

        self.client.force_authenticate(user=self.super_admin)
        assignment = Assignment.assign_constable(idol=self.idol_10ft, constable=self.pc_cmr, assigned_by=self.super_admin)

        # Start tracking session
        session = TrackingSession.objects.create(
            assignment=assignment,
            status=TrackingSessionStatus.ACTIVE,
            started_at=timezone.now()
        )
        # Ingest telemetry point
        telemetry_lat = 17.3616
        telemetry_lon = 78.4747
        LocationPoint.objects.create(
            session=session,
            latitude=telemetry_lat,
            longitude=telemetry_lon,
            speed=2.5,
            heading=90.0,
            accuracy=5.0,
            recorded_at=timezone.now()
        )

        res_tracking = self.client.get('/api/v1/tracking/active/')
        self.assertEqual(res_tracking.status_code, 200)
        live_markers = {m['gpid']: m for m in res_tracking.data}
        self.assertIn(self.idol_10ft.gpid, live_markers)

        marker = live_markers[self.idol_10ft.gpid]
        self.assertAlmostEqual(marker['latitude'], telemetry_lat, places=4)
        self.assertAlmostEqual(marker['longitude'], telemetry_lon, places=4)
        self.assertEqual(marker['idol_height'], 10.0)

    def test_07_one_gpid_produces_one_live_marker(self):
        """Even with multiple location points, exactly one marker per active GPID is returned."""
        from apps.tracking.models import TrackingSession, TrackingSessionStatus, LocationPoint
        from django.utils import timezone

        self.client.force_authenticate(user=self.super_admin)
        assignment = Assignment.assign_constable(idol=self.idol_14ft, constable=self.pc_cmr, assigned_by=self.super_admin)
        session = TrackingSession.objects.create(
            assignment=assignment,
            status=TrackingSessionStatus.ACTIVE,
            started_at=timezone.now()
        )
        # Create multiple telemetry points
        for i in range(5):
            LocationPoint.objects.create(
                session=session,
                latitude=17.3600 + (i * 0.001),
                longitude=78.4700 + (i * 0.001),
                recorded_at=timezone.now() - timedelta(minutes=5 - i)
            )

        res_tracking = self.client.get('/api/v1/tracking/active/')
        self.assertEqual(res_tracking.status_code, 200)
        matching = [m for m in res_tracking.data if m['gpid'] == self.idol_14ft.gpid]
        self.assertEqual(len(matching), 1)

    def test_08_zonal_sysadmin_strictly_zone_scoped(self):
        """Zonal SYS_ADMIN can only see and assign GPIDs in their own zone."""
        self.client.force_authenticate(user=self.zonal_sysadmin_cmr)

        # Registry only returns Charminar idols
        res = self.client.get('/api/v1/assignments/registry/')
        self.assertEqual(res.status_code, 200)
        gpids = [item['gpid'] for item in res.data['results']]
        self.assertIn(self.idol_10ft.gpid, gpids)
        self.assertNotIn(self.idol_sec_10ft.gpid, gpids)

        # Attempting query parameter override for Secunderabad fails to leak records
        res_override = self.client.get('/api/v1/assignments/registry/?zone=Secunderabad')
        self.assertEqual(res_override.status_code, 200)
        self.assertEqual(len(res_override.data['results']), 0)

        # Cannot assign idol in Secunderabad
        res_assign = self.client.post('/api/v1/assignments/create/', {
            'gpid': self.idol_sec_10ft.gpid,
            'constable_id': self.pc_sec.id
        })
        self.assertEqual(res_assign.status_code, 400)
        self.assertIn('outside your assigned zone', str(res_assign.data).lower())

    def test_09_and_filter_composition_across_all_heights(self):
        """Filters compose using AND logic across Zone, PS, Height, Visarjan Date, and Status."""
        self.client.force_authenticate(user=self.super_admin)

        # Zone=Charminar + PS=Charminar + Height=below_15 + Date=today + Status=unassigned
        res = self.client.get(
            f'/api/v1/assignments/registry/?zone=Charminar&police_station=Charminar&height_bucket=below_15&visarjan_date=today&assignment_status=unassigned'
        )
        self.assertEqual(res.status_code, 200)
        gpids = [item['gpid'] for item in res.data['results']]
        # 10ft and 14ft match all 5 conditions (today, below 15, unassigned, charminar)
        self.assertIn(self.idol_10ft.gpid, gpids)
        self.assertIn(self.idol_14ft.gpid, gpids)
        # 12ft does not match (visarjan_date is tomorrow)
        self.assertNotIn(self.idol_12ft.gpid, gpids)
        # 18ft does not match (height is 18ft)
        self.assertNotIn(self.idol_18ft.gpid, gpids)

    def test_10_assignment_excel_export_respects_filters_and_includes_sub_15ft(self):
        """Excel export includes sub-15 FT idols and respects filters."""
        self.client.force_authenticate(user=self.super_admin)

        # Export with height_bucket=below_15
        res = self.client.get('/api/v1/assignments/export/?height_bucket=below_15')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertGreater(len(res.content), 1000)

    def test_11_assignment_kpi_cards_reflect_visarjan_date_filter(self):
        """KPI cards must reflect the SAME filtered population when Visarjan Date is selected."""
        self.client.force_authenticate(user=self.super_admin)

        # 1. All Dates -> reflects all 6 idols
        res_all = self.client.get('/api/v1/assignments/registry/?visarjan_date=all')
        self.assertEqual(res_all.status_code, 200)
        s_all = res_all.data['summary']
        self.assertEqual(s_all['total_eligible'], 6)
        self.assertEqual(s_all['count_below_15'], 4)
        self.assertEqual(s_all['count_15_20'], 1)
        self.assertEqual(s_all['count_26_plus'], 1)

        # 2. Today -> reflects only today's 4 idols (10ft, 14ft, 18ft, sec_10ft)
        res_today = self.client.get('/api/v1/assignments/registry/?visarjan_date=today')
        self.assertEqual(res_today.status_code, 200)
        s_today = res_today.data['summary']
        self.assertEqual(s_today['total_eligible'], 4)
        self.assertEqual(s_today['count_below_15'], 3)
        self.assertEqual(s_today['count_15_20'], 1)
        self.assertEqual(s_today['count_26_plus'], 0)
        self.assertEqual(res_today.data['count'], 4)

        # 3. Tomorrow -> reflects only tomorrow's 2 idols (12ft, 28ft)
        res_tom = self.client.get('/api/v1/assignments/registry/?visarjan_date=tomorrow')
        self.assertEqual(res_tom.status_code, 200)
        s_tom = res_tom.data['summary']
        self.assertEqual(s_tom['total_eligible'], 2)
        self.assertEqual(s_tom['count_below_15'], 1)
        self.assertEqual(s_tom['count_15_20'], 0)
        self.assertEqual(s_tom['count_26_plus'], 1)
        self.assertEqual(res_tom.data['count'], 2)

    def test_12_assignment_kpi_cards_reflect_active_filters_combination(self):
        """KPI cards reflect the exact subset when multiple filters (zone, PS, height) are applied."""
        self.client.force_authenticate(user=self.super_admin)

        # Today + Zone=Charminar: 3 idols (10ft, 14ft, 18ft)
        res_zone = self.client.get('/api/v1/assignments/registry/?visarjan_date=today&zone=Charminar')
        self.assertEqual(res_zone.status_code, 200)
        self.assertEqual(res_zone.data['summary']['total_eligible'], 3)
        self.assertEqual(res_zone.data['count'], 3)

        # Today + Zone=Charminar + Height=below_15: 2 idols (10ft, 14ft)
        res_h = self.client.get('/api/v1/assignments/registry/?visarjan_date=today&zone=Charminar&height_bucket=below_15')
        self.assertEqual(res_h.status_code, 200)
        s_h = res_h.data['summary']
        self.assertEqual(s_h['total_eligible'], 2)
        self.assertEqual(s_h['count_below_15'], 2)
        self.assertEqual(s_h['count_15_20'], 0)
        self.assertEqual(res_h.data['count'], 2)

    def test_13_assignment_status_kpis_filtered(self):
        """Assigned and Unassigned KPI counts match filtered results."""
        self.client.force_authenticate(user=self.super_admin)

        # Assign 10ft idol
        Assignment.assign_constable(idol=self.idol_10ft, constable=self.pc_cmr, assigned_by=self.super_admin)

        # Today + All status: 1 assigned, 3 unassigned
        res_today = self.client.get('/api/v1/assignments/registry/?visarjan_date=today')
        s = res_today.data['summary']
        self.assertEqual(s['total_eligible'], 4)
        self.assertEqual(s['assigned'], 1)
        self.assertEqual(s['unassigned'], 3)

        # Today + Assigned status: 1 total eligible, 1 assigned, 0 unassigned
        res_assigned = self.client.get('/api/v1/assignments/registry/?visarjan_date=today&assignment_status=assigned')
        s_a = res_assigned.data['summary']
        self.assertEqual(s_a['total_eligible'], 1)
        self.assertEqual(s_a['assigned'], 1)
        self.assertEqual(s_a['unassigned'], 0)

        # Today + Unassigned status: 3 total eligible, 0 assigned, 3 unassigned
        res_un = self.client.get('/api/v1/assignments/registry/?visarjan_date=today&assignment_status=unassigned')
        s_u = res_un.data['summary']
        self.assertEqual(s_u['total_eligible'], 3)
        self.assertEqual(s_u['assigned'], 0)
        self.assertEqual(s_u['unassigned'], 3)

    def test_14_reset_filters_restores_global_kpis(self):
        """Resetting filters (calling without query params) restores the global counts."""
        self.client.force_authenticate(user=self.super_admin)

        res = self.client.get('/api/v1/assignments/registry/')
        self.assertEqual(res.status_code, 200)
        s = res.data['summary']
        self.assertEqual(s['total_eligible'], 6)
        self.assertEqual(res.data['count'], 6)


class RajendraNagarZoneAssignmentTests(TestCase):
    """
    Targeted test suite verifying canonical Rajendra Nagar zone filtering,
    backward-compatible normalization, height distribution, and Zonal SYS_ADMIN jurisdiction.
    """

    def setUp(self):
        from rest_framework.test import APIClient
        from apps.idols.models import ProcessionState
        from django.utils import timezone
        from datetime import timedelta
        self.client = APIClient()
        self.today = timezone.localdate()
        self.tomorrow = self.today + timedelta(days=1)

        self.super_admin = User.objects.create_superuser(
            username='super_admin_rn_test', password='password123',
            role=UserRole.SUPER_ADMIN
        )

        # Charminar idol
        self.idol_cmr = Idol.objects.create(
            gpid='HYDCMRZCMNR1010', name='Lalitha Pandal 10ft',
            police_station='Charminar', zone='Charminar',
            idol_height=10.0, immersion_date=self.today,
            procession_state=ProcessionState.NOT_STARTED
        )

        # Secunderabad idol
        self.idol_sec = Idol.objects.create(
            gpid='HYDSECZGPLP2010', name='Secunderabad Idol 10ft',
            police_station='Gopalpuram', zone='Secunderabad',
            idol_height=10.0, immersion_date=self.today,
            procession_state=ProcessionState.NOT_STARTED
        )

        # Rajendra Nagar idols (Authoritative zone name has space)
        self.idol_rn_10ft = Idol.objects.create(
            gpid='HYDRNGZATPR3010', name='Attapur Colony 10ft',
            police_station='Attapur', zone='Rajendra Nagar',
            idol_height=10.0, immersion_date=self.today,
            procession_state=ProcessionState.NOT_STARTED
        )
        self.idol_rn_18ft = Idol.objects.create(
            gpid='HYDRNGZATPR3018', name='Attapur Main 18ft',
            police_station='Attapur', zone='Rajendra Nagar',
            idol_height=18.0, immersion_date=self.today,
            procession_state=ProcessionState.NOT_STARTED
        )
        self.idol_rn_22ft = Idol.objects.create(
            gpid='HYDRNGZRNGR3022', name='Rajendranagar 22ft',
            police_station='Rajendranagar', zone='Rajendra Nagar',
            idol_height=22.0, immersion_date=self.today,
            procession_state=ProcessionState.NOT_STARTED
        )
        self.idol_rn_tom_10ft = Idol.objects.create(
            gpid='HYDRNGZMLDP3011', name='Mailardevpally 10ft Tomorrow',
            police_station='Mailardevpally', zone='Rajendra Nagar',
            idol_height=10.0, immersion_date=self.tomorrow,
            procession_state=ProcessionState.NOT_STARTED
        )

        # Zonal SYS_ADMIN for Rajendra Nagar (stored as Rajendranagar in DB matching production)
        self.sysadmin_rn = User.objects.create_user(
            username='sysadmin_rajendranagar', password='password123',
            role=UserRole.SYS_ADMIN, zone='Rajendranagar'
        )

    def test_01_rajendra_nagar_zone_filter_returns_records(self):
        """Authoritative 'Rajendra Nagar' zone filter returns all Rajendra Nagar records."""
        self.client.force_authenticate(user=self.super_admin)

        # 1. 'Rajendra Nagar' all dates: returns all 4 Rajendra Nagar idols
        res_rn = self.client.get('/api/v1/assignments/registry/?zone=Rajendra Nagar')
        self.assertEqual(res_rn.status_code, 200)
        self.assertEqual(res_rn.data['count'], 4)
        s_rn = res_rn.data['summary']
        self.assertEqual(s_rn['total_eligible'], 4)
        self.assertEqual(s_rn['count_below_15'], 2)  # rn_10ft, rn_tom_10ft
        self.assertEqual(s_rn['count_15_20'], 1)     # rn_18ft
        self.assertEqual(s_rn['count_21_25'], 1)     # rn_22ft

        # 2. Legacy 'Rajendranagar' query resolves identically to canonical
        res_rn_legacy = self.client.get('/api/v1/assignments/registry/?zone=Rajendranagar')
        self.assertEqual(res_rn_legacy.status_code, 200)
        self.assertEqual(res_rn_legacy.data['count'], 4)
        self.assertEqual(res_rn_legacy.data['summary']['total_eligible'], 4)

    def test_02_rajendra_nagar_date_filters(self):
        """Rajendra Nagar + Today and Tomorrow return exact filtered date populations."""
        self.client.force_authenticate(user=self.super_admin)

        # Rajendra Nagar + Today: exactly today's 3 records (10ft, 18ft, 22ft)
        res_today = self.client.get('/api/v1/assignments/registry/?zone=Rajendra Nagar&visarjan_date=today')
        self.assertEqual(res_today.status_code, 200)
        self.assertEqual(res_today.data['count'], 3)
        s_today = res_today.data['summary']
        self.assertEqual(s_today['total_eligible'], 3)
        self.assertEqual(s_today['count_below_15'], 1)
        self.assertEqual(s_today['count_15_20'], 1)
        self.assertEqual(s_today['count_21_25'], 1)
        self.assertEqual(s_today['count_26_plus'], 0)

        # Rajendra Nagar + Tomorrow: exactly tomorrow's 1 record
        res_tom = self.client.get('/api/v1/assignments/registry/?zone=Rajendra Nagar&visarjan_date=tomorrow')
        self.assertEqual(res_tom.status_code, 200)
        self.assertEqual(res_tom.data['count'], 1)
        self.assertEqual(res_tom.data['summary']['total_eligible'], 1)
        self.assertEqual(res_tom.data['results'][0]['gpid'], self.idol_rn_tom_10ft.gpid)

    def test_03_rajendra_nagar_height_and_police_station_filters(self):
        """Rajendra Nagar combined with height buckets and police station cascading."""
        self.client.force_authenticate(user=self.super_admin)

        # Rajendra Nagar + Below 15 FT: 2 records across all dates
        res_sub = self.client.get('/api/v1/assignments/registry/?zone=Rajendra Nagar&height_bucket=below_15')
        self.assertEqual(res_sub.status_code, 200)
        self.assertEqual(res_sub.data['count'], 2)
        self.assertEqual(res_sub.data['summary']['total_eligible'], 2)

        # Rajendra Nagar + 15–20 FT: 1 record
        res_15_20 = self.client.get('/api/v1/assignments/registry/?zone=Rajendra Nagar&height_bucket=15_20')
        self.assertEqual(res_15_20.status_code, 200)
        self.assertEqual(res_15_20.data['count'], 1)
        self.assertEqual(res_15_20.data['summary']['total_eligible'], 1)

        # Rajendra Nagar + Specific Police Station (Attapur): 2 records
        res_ps = self.client.get('/api/v1/assignments/registry/?zone=Rajendra Nagar&police_station=Attapur')
        self.assertEqual(res_ps.status_code, 200)
        self.assertEqual(res_ps.data['count'], 2)
        self.assertEqual(res_ps.data['summary']['total_eligible'], 2)

    def test_04_other_zones_continue_working(self):
        """Selecting other zones continues to return their respective records."""
        self.client.force_authenticate(user=self.super_admin)

        res_cmr = self.client.get('/api/v1/assignments/registry/?zone=Charminar')
        self.assertEqual(res_cmr.status_code, 200)
        self.assertEqual(res_cmr.data['count'], 1)

        res_sec = self.client.get('/api/v1/assignments/registry/?zone=Secunderabad')
        self.assertEqual(res_sec.status_code, 200)
        self.assertEqual(res_sec.data['count'], 1)

    def test_05_rajendra_nagar_zonal_sysadmin_jurisdiction(self):
        """Zonal SYS_ADMIN for Rajendra Nagar can only access Rajendra Nagar idols."""
        self.client.force_authenticate(user=self.sysadmin_rn)

        # Sees all 4 Rajendra Nagar idols
        res = self.client.get('/api/v1/assignments/registry/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['count'], 4)
        for item in res.data['results']:
            self.assertEqual(item['zone'], 'Rajendra Nagar')

        # Attempting override for Charminar fails to leak Charminar idols
        res_override = self.client.get('/api/v1/assignments/registry/?zone=Charminar')
        self.assertEqual(res_override.status_code, 200)
        self.assertEqual(res_override.data['count'], 0)



