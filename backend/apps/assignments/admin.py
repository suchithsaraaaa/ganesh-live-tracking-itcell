from django.contrib import admin
from .models import Assignment


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'idol', 'constable', 'is_active', 'started_at', 'ended_at', 'assigned_by')
    list_filter = ('is_active', 'started_at', 'idol__zone', 'idol__police_station')
    search_fields = ('idol__gpid', 'idol__name', 'constable__username', 'constable__police_id')
    readonly_fields = ('started_at', 'created_at', 'updated_at')
