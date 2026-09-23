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

    def test_active_tracking_session_blocks_end_assignment(self):
        from apps.tracking.models import TrackingSession, TrackingSessionStatus
        session = TrackingSession.objects.create(
            assignment=self.assignment,
            status=TrackingSessionStatus.ACTIVE
        )

        self.client.force_authenticate(user=self.admin)
        res = self.client.post(f'/api/v1/assignments/{self.assignment.id}/end/', {})
        self.assertEqual(res.status_code, 400)
        self.assertTrue(res.data.get('has_active_tracking'))
        self.assertIn('active tracking session', res.data['error'])

        # Assignment must remain active
        self.assignment.refresh_from_db()
        self.assertTrue(self.assignment.is_active)

        # Once session is stopped, end assignment succeeds
        session.stop_session()
        res_ok = self.client.post(f'/api/v1/assignments/{self.assignment.id}/end/', {})
        self.assertEqual(res_ok.status_code, 200)

        self.assignment.refresh_from_db()
        self.assertFalse(self.assignment.is_active)

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

    # 1. GPID below 15 FT is excluded from assignable registry
    def test_01_gpid_below_15ft_excluded_from_registry(self):
        self.client.force_authenticate(user=self.main_officer)
        res = self.client.get('/api/v1/assignments/registry/')
        self.assertEqual(res.status_code, 200)
        gpids = [item['gpid'] for item in res.data['results']]
        self.assertNotIn(self.idol_12ft.gpid, gpids)

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

    # 8. Search cannot bypass 15 FT filtering
    def test_08_search_cannot_bypass_15ft_filtering(self):
        self.client.force_authenticate(user=self.main_officer)
        res = self.client.get(f'/api/v1/assignments/registry/?search={self.idol_12ft.gpid}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['results']), 0)

    # 9. Assignment creation rejects <15 FT
    def test_09_assignment_creation_rejects_subthreshold_15ft(self):
        self.client.force_authenticate(user=self.sho_cmr)
        res = self.client.post('/api/v1/assignments/create/', {
            'gpid': self.idol_12ft.gpid,
            'constable_id': self.pc_avail.id
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('ineligible for assignment', str(res.data))

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

    # 24. Critical negative test: subthreshold idol cannot be assigned or retrieved via registry
    def test_24_critical_negative_test_subthreshold_lookup_and_assign(self):
        self.client.force_authenticate(user=self.main_officer)

        # 1. Direct registry detail lookup rejects <15 FT
        res_lookup = self.client.get(f'/api/v1/assignments/registry/{self.idol_12ft.gpid}/')
        self.assertEqual(res_lookup.status_code, 400)
        self.assertIn('ineligible for assignment', res_lookup.data['error'])

        # 2. Assignment creation rejects <15 FT
        res_assign = self.client.post('/api/v1/assignments/create/', {
            'gpid': self.idol_12ft.gpid,
            'constable_id': self.pc_avail.id
        })
        self.assertEqual(res_assign.status_code, 400)
        self.assertIn('ineligible for assignment', str(res_assign.data))

