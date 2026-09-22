from django.db import models
from apps.accounts.models import User


class AuditEvent(models.Model):
    """
    Audit log for sensitive operational and security events:
    - User logins
    - Assignments created / modified
    - Constable handovers
    - Report generations
    """
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_events'
    )
    action = models.CharField(max_length=100, db_index=True)
    target_model = models.CharField(max_length=50, blank=True)
    target_id = models.CharField(max_length=100, blank=True, db_index=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
        ]

    def __str__(self):
        return f"[{self.created_at}] {self.actor.username if self.actor else 'SYSTEM'} - {self.action} on {self.target_model}:{self.target_id}"
