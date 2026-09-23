from django.db import models, transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.idols.models import Idol


class Assignment(models.Model):
    """
    Tracks responsibility of a Constable for an Idol.
    Preserves full assignment and handover history for auditing.
    """
    idol = models.ForeignKey(
        Idol,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    constable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignments'
    )
    # Historical identity snapshot — preserved when the officer account is deleted.
    # These fields allow the assignment record (and its linked TrackingSession/
    # LocationPoint history) to retain officer attribution even after account removal.
    officer_name_snapshot = models.CharField(max_length=255, blank=True, default='')
    police_id_snapshot = models.CharField(max_length=50, blank=True, default='')
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_assignments'
    )
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    # Handover details
    handover_reason = models.TextField(blank=True)
    handover_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_assignments'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['idol', 'is_active']),
            models.Index(fields=['constable', 'is_active']),
            models.Index(fields=['started_at', 'ended_at']),
        ]
        constraints = [
            # Invariant: A constable cannot have multiple active idol assignments
            models.UniqueConstraint(
                fields=['constable'],
                condition=models.Q(is_active=True),
                name='unique_active_constable_assignment'
            ),
            # Invariant: An idol cannot have multiple active constables assigned
            models.UniqueConstraint(
                fields=['idol'],
                condition=models.Q(is_active=True),
                name='unique_active_idol_assignment'
            ),
        ]

    def _constable_display(self):
        """Returns constable identifier, falling back to snapshot when account is deleted."""
        if self.constable_id is not None:
            return self.constable.username
        return self.officer_name_snapshot or 'Deleted Officer'

    def __str__(self):
        status = "ACTIVE" if self.is_active else "ENDED"
        return f"[{status}] {self._constable_display()} -> {self.idol.gpid}"

    @classmethod
    @transaction.atomic
    def assign_constable(cls, idol, constable, assigned_by=None):
        """
        Creates a new active assignment.
        Ensures any previous active assignment for this idol or constable is safely ended.
        """
        now = timezone.now()
        # End any existing active assignment for this idol
        cls.objects.filter(idol=idol, is_active=True).update(is_active=False, ended_at=now)
        # End any existing active assignment for this constable
        cls.objects.filter(constable=constable, is_active=True).update(is_active=False, ended_at=now)

        # Snapshot officer identity at assignment time for historical preservation.
        full_name = f"{constable.first_name} {constable.last_name}".strip() or constable.username
        assignment = cls.objects.create(
            idol=idol,
            constable=constable,
            assigned_by=assigned_by,
            started_at=now,
            is_active=True,
            officer_name_snapshot=full_name,
            police_id_snapshot=constable.police_id or '',
        )

        try:
            from apps.tracking.models import IdolEvent, IdolEventType
            IdolEvent.objects.create(
                idol=idol,
                gpid=idol.gpid,
                event_type='PROCESSION_ASSIGNED',
                timestamp=now,
                zone=idol.zone,
                actor=assigned_by,
                metadata={
                    'assignment_id': assignment.id,
                    'constable': constable.username,
                    'police_id': constable.police_id,
                    'assigned_by': assigned_by.username if assigned_by else None,
                    'zone': idol.zone,
                    'police_station': idol.police_station,
                }
            )
        except Exception:
            pass

        try:
            from apps.audit.models import AuditEvent
            AuditEvent.objects.create(
                action='PROCESSION_ASSIGNED',
                actor=assigned_by,
                target_id=str(assignment.id),
                target_model='Assignment',
                details={
                    'assignment_id': assignment.id,
                    'gpid': idol.gpid,
                    'constable': full_name,
                    'police_id': constable.police_id or '',
                    'assigned_by': assigned_by.username if assigned_by else None,
                    'zone': idol.zone,
                    'police_station': idol.police_station,
                }
            )
        except Exception:
            pass

        return assignment

    @transaction.atomic
    def handover_to_constable(self, new_constable, reason='', actor=None):
        """
        Executes an atomic handover from the current constable to a new constable.
        """
        now = timezone.now()
        # 1. Close current assignment
        self.is_active = False
        self.ended_at = now
        self.handover_reason = reason
        self.handover_to = new_constable
        self.save(update_fields=['is_active', 'ended_at', 'handover_reason', 'handover_to', 'updated_at'])

        # 2. Close any conflicting assignment the new constable might have
        Assignment.objects.filter(constable=new_constable, is_active=True).update(
            is_active=False,
            ended_at=now
        )

        # 3. Create new assignment starting at handover time
        new_assignment = Assignment.objects.create(
            idol=self.idol,
            constable=new_constable,
            assigned_by=actor,
            started_at=now,
            is_active=True
        )

        try:
            from apps.tracking.models import IdolEvent, IdolEventType
            IdolEvent.objects.create(
                idol=self.idol,
                gpid=self.idol.gpid,
                event_type=IdolEventType.ASSIGNMENT_HANDOVER,
                timestamp=now,
                zone=self.idol.zone,
                actor=actor,
                metadata={
                    'previous_constable': self._constable_display(),
                    'new_constable': new_constable.username,
                    'reason': reason
                }
            )
        except Exception:
            pass

        return new_assignment

    @transaction.atomic
    def end_assignment(self, actor=None, reason=''):
        """
        Safely ends an active assignment without deleting historical records.
        Preserves officer snapshot and logs operational & audit events.
        """
        now = timezone.now()
        self.is_active = False
        self.ended_at = now
        if reason:
            self.handover_reason = f"Ended: {reason}"
        self.save(update_fields=['is_active', 'ended_at', 'handover_reason', 'updated_at'])

        try:
            from apps.tracking.models import IdolEvent, IdolEventType
            IdolEvent.objects.create(
                idol=self.idol,
                gpid=self.idol.gpid,
                event_type=IdolEventType.ASSIGNMENT_ENDED,
                timestamp=now,
                zone=self.idol.zone,
                actor=actor,
                metadata={
                    'assignment_id': self.id,
                    'constable': self._constable_display(),
                    'police_id': self.police_id_snapshot,
                    'ended_by': actor.username if actor else 'System',
                    'reason': reason or 'Assignment ended'
                }
            )
        except Exception:
            pass

        try:
            from apps.audit.models import AuditEvent
            AuditEvent.objects.create(
                action='ASSIGNMENT_ENDED',
                actor=actor,
                target_id=str(self.id),
                target_model='Assignment',
                details={
                    'assignment_id': self.id,
                    'gpid': self.idol.gpid,
                    'constable': self._constable_display(),
                    'police_id': self.police_id_snapshot,
                    'ended_by': actor.username if actor else 'System',
                    'reason': reason
                }
            )
        except Exception:
            pass

        return self

    @classmethod
    def get_constable_for_idol_at(cls, idol, dt):
        """
        Answers: 'Who was responsible for GPID X at timestamp Y?'
        Finds assignment active at timestamp dt.
        """
        assign = cls.objects.filter(
            idol=idol,
            started_at__lte=dt
        ).filter(
            models.Q(ended_at__isnull=True) | models.Q(ended_at__gte=dt)
        ).order_by('-started_at').first()
        if assign is None:
            return None
        # Return live constable if account still exists, else return snapshot attribution.
        return assign.constable
