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
        on_delete=models.CASCADE,
        related_name='assignments'
    )
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

    def __str__(self):
        status = "ACTIVE" if self.is_active else "ENDED"
        return f"[{status}] {self.constable.username} -> {self.idol.gpid}"

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

        return cls.objects.create(
            idol=idol,
            constable=constable,
            assigned_by=assigned_by,
            started_at=now,
            is_active=True
        )

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

        return new_assignment

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
        return assign.constable if assign else None
