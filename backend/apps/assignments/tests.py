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
            zone='Charminar'
        )
        self.idol_2 = Idol.objects.create(
            gpid='HYDCMRZCMNR0113',
            name='Charminar Idol 2',
            police_station='Charminar',
            zone='Charminar'
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
            geocoding_confidence='EXACT'
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
