from rest_framework import serializers
from .models import TrackingSession, LocationPoint
from apps.assignments.models import Assignment


class TrackingSessionSerializer(serializers.ModelSerializer):
    gpid = serializers.CharField(source='assignment.idol.gpid', read_only=True)
    idol_name = serializers.CharField(source='assignment.idol.name', read_only=True)
    constable_name = serializers.CharField(source='assignment.constable.get_full_name', read_only=True)
    constable_username = serializers.CharField(source='assignment.constable.username', read_only=True)
    police_station = serializers.CharField(source='assignment.idol.police_station', read_only=True)

    class Meta:
        model = TrackingSession
        fields = [
            'id',
            'assignment',
            'gpid',
            'idol_name',
            'police_station',
            'constable_name',
            'constable_username',
            'device_info',
            'started_at',
            'ended_at',
            'status',
            'created_at',
        ]
        read_only_fields = ['started_at', 'ended_at', 'status']


class StartTrackingSerializer(serializers.Serializer):
    assignment_id = serializers.IntegerField(required=False)
    gpid = serializers.CharField(required=False)
    device_info = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        assignment_id = data.get('assignment_id')
        gpid = data.get('gpid')

        if not assignment_id and not gpid:
            raise serializers.ValidationError('Either assignment_id or gpid is required.')

        if assignment_id:
            try:
                data['assignment_obj'] = Assignment.objects.select_related('idol', 'constable').get(id=assignment_id, is_active=True)
            except Assignment.DoesNotExist:
                raise serializers.ValidationError(f'Active assignment {assignment_id} not found.')
        elif gpid:
            try:
                data['assignment_obj'] = Assignment.objects.select_related('idol', 'constable').get(idol__gpid__iexact=gpid, is_active=True)
            except Assignment.DoesNotExist:
                raise serializers.ValidationError(f'No active assignment found for GPID {gpid}.')

        return data


class LocationPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationPoint
        fields = [
            'id',
            'session',
            'latitude',
            'longitude',
            'accuracy',
            'speed',
            'heading',
            'recorded_at',
            'received_at',
        ]
        read_only_fields = ['received_at']


class IngestLocationSerializer(serializers.Serializer):
    session_id = serializers.IntegerField(required=True)
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)
    accuracy = serializers.FloatField(required=False, default=None)
    speed = serializers.FloatField(required=False, default=None)
    heading = serializers.FloatField(required=False, default=None)
    recorded_at = serializers.DateTimeField(required=True)


class BatchIngestLocationSerializer(serializers.Serializer):
    session_id = serializers.IntegerField(required=True)
    points = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )
