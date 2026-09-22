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
