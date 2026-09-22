from django.contrib import admin
from .models import Idol, ImportRun, ImportIssue


@admin.register(Idol)
class IdolAdmin(admin.ModelAdmin):
    list_display = ('gpid', 'ref_no', 'name', 'association_name', 'police_station', 'zone', 'procession_state', 'status')
    list_filter = ('procession_state', 'status', 'zone', 'police_station', 'immersion_date')
    search_fields = ('gpid', 'ref_no', 'name', 'association_name', 'police_station')
    readonly_fields = ('created_at', 'updated_at')


class ImportIssueInline(admin.TabularInline):
    model = ImportIssue
    extra = 0
    readonly_fields = ('row_number', 'gpid', 'ref_no', 'ps_name', 'issue_type', 'error_message')
    can_delete = False


@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'file_name', 'total_rows', 'imported_count', 'updated_count', 'skipped_count', 'duplicate_gpid_count', 'started_at')
    readonly_fields = ('started_at', 'completed_at', 'total_rows', 'imported_count', 'updated_count', 'skipped_count', 'invalid_gpid_count', 'duplicate_gpid_count', 'invalid_ps_count')
    inlines = [ImportIssueInline]
