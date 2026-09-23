from rest_framework import serializers
from apps.idols.models import Idol, ProcessionState
from apps.tracking.models import IdolEventType


class CompletedReportRegistrySerializer(serializers.ModelSerializer):
    """
    Serializer for the official operational Reports Registry.
    Represents idols that have reached completion (Visarjan Done) or holding.
    """
    final_state = serializers.SerializerMethodField()
    final_state_display = serializers.SerializerMethodField()
    assigned_officer = serializers.SerializerMethodField()
    report_download_url = serializers.SerializerMethodField()
    completed_at = serializers.SerializerMethodField()

    class Meta:
        model = Idol
        fields = [
            'id',
            'gpid',
            'name',
            'association_name',
            'idol_height',
            'zone',
            'division',
            'police_station',
            'immersion_date',
            'procession_state',
            'final_state',
            'final_state_display',
            'assigned_officer',
            'report_download_url',
            'completed_at',
        ]

    def get_final_state(self, obj):
        # 1. Check Idol procession_state first
        if obj.procession_state == ProcessionState.IMMERSION_COMPLETED:
            return 'IMMERSION_COMPLETED'
        if obj.procession_state == ProcessionState.HOLDING:
            return 'SENT_TO_HOLDING'

        # 2. Check prefetched events
        events_map = self.context.get('events_map', {})
        event = events_map.get(obj.id)
        if event:
            if event.event_type == IdolEventType.IMMERSION_COMPLETED:
                return 'IMMERSION_COMPLETED'
            if event.event_type in [IdolEventType.SENT_TO_HOLDING, IdolEventType.HOLDING_POINT_ENTERED, IdolEventType.VISARJAN_NOT_DONE]:
                return 'SENT_TO_HOLDING'

        return obj.procession_state

    def get_final_state_display(self, obj):
        st = self.get_final_state(obj)
        if st == 'IMMERSION_COMPLETED':
            return 'Immersion Completed'
        if st == 'SENT_TO_HOLDING':
            return 'Sent to Holding'
        return st.replace('_', ' ').title()

    def get_assigned_officer(self, obj):
        assignments_map = self.context.get('assignments_map', {})
        assignment = assignments_map.get(obj.id)
        if not assignment:
            return None

        officer_name = ''
        officer_username = ''
        police_id = ''

        if assignment.constable:
            officer_name = assignment.constable.get_full_name() or assignment.constable.username
            officer_username = assignment.constable.username
            police_id = assignment.constable.police_id or ''
        else:
            officer_name = assignment.officer_name_snapshot or 'Historical Officer'
            officer_username = assignment.officer_name_snapshot or ''
            police_id = assignment.police_id_snapshot or ''

        return {
            'id': assignment.constable.id if assignment.constable else None,
            'name': officer_name,
            'username': officer_username,
            'police_id': police_id,
            'is_active': assignment.is_active,
        }

    def get_report_download_url(self, obj):
        return f"/api/v1/reports/idols/{obj.gpid}/"

    def get_completed_at(self, obj):
        events_map = self.context.get('events_map', {})
        event = events_map.get(obj.id)
        if event and event.timestamp:
            return event.timestamp.isoformat()
        return None
