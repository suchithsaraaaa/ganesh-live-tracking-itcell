from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    MAIN_OFFICER = 'MAIN_OFFICER', 'Main Officer / System Admin'
    ACP = 'ACP', 'ACP / Senior Officer'
    SHO = 'SHO', 'Station House Officer'
    CONSTABLE = 'CONSTABLE', 'Constable / Ground Staff'


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CONSTABLE,
        db_index=True
    )
    police_id = models.CharField(max_length=50, blank=True, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True)
    zone = models.CharField(max_length=100, blank=True, db_index=True)
    division = models.CharField(max_length=100, blank=True, db_index=True)
    police_station = models.CharField(max_length=100, blank=True, db_index=True)
    must_change_password = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()}) - {self.police_station or 'City Wide'}"
