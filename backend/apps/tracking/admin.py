from django.contrib import admin
from .models import TrackingSession, LocationPoint


class LocationPointInline(admin.TabularInline):
    model = LocationPoint
    extra = 0
    readonly_fields = ('latitude', 'longitude', 'accuracy', 'speed', 'heading', 'recorded_at', 'received_at')
    can_delete = False


@admin.register(TrackingSession)
class TrackingSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'assignment', 'status', 'started_at', 'ended_at', 'device_info')
    list_filter = ('status', 'started_at')
    search_fields = ('assignment__idol__gpid', 'assignment__constable__username')
    inlines = [LocationPointInline]


@admin.register(LocationPoint)
class LocationPointAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'latitude', 'longitude', 'accuracy', 'speed', 'recorded_at', 'received_at')
    list_filter = ('recorded_at', 'received_at')
    search_fields = ('session__assignment__idol__gpid',)
