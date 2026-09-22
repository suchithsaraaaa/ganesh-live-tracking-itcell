from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Police Hierarchy & Jurisdiction', {
            'fields': ('role', 'police_id', 'phone_number', 'zone', 'division', 'police_station', 'must_change_password')
        }),
    )
    list_display = ('username', 'police_id', 'role', 'police_station', 'zone', 'is_active')
    list_filter = ('role', 'zone', 'division', 'police_station', 'is_active')
    search_fields = ('username', 'police_id', 'first_name', 'last_name', 'police_station')
