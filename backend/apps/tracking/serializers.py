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
    latitude = serializers.DecimalField(max_digits=12, decimal_places=8, required=True, allow_null=False)
    longitude = serializers.DecimalField(max_digits=12, decimal_places=8, required=True, allow_null=False)

    def validate_latitude(self, value):
        if value is None:
            raise serializers.ValidationError('Latitude is required.')
        if value < -90 or value > 90:
            raise serializers.ValidationError('Latitude must be between -90.0 and 90.0.')
        return value

    def validate_longitude(self, value):
        if value is None:
            raise serializers.ValidationError('Longitude is required.')
        if value < -180 or value > 180:
            raise serializers.ValidationError('Longitude must be between -180.0 and 180.0.')
        return value

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

        if assignment_id and gpid:
            if data['assignment_obj'].idol.gpid.upper() != gpid.upper():
                raise serializers.ValidationError(f'GPID {gpid} does not match assignment {assignment_id}.')

        if data.get('latitude') is None or data.get('longitude') is None:
            raise serializers.ValidationError('Valid GPS coordinates (latitude and longitude) are required to start procession tracking.')

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


class ProcessionEventSerializer(serializers.Serializer):
    client_event_id = serializers.CharField(max_length=128, required=False, allow_blank=True, default='')
    gpid = serializers.CharField(max_length=64, required=True)
    assignment_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default='')
    tracking_session_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default='')
    event_type = serializers.CharField(max_length=50, required=True)
    latitude = serializers.FloatField(required=False, allow_null=True, default=None)
    longitude = serializers.FloatField(required=False, allow_null=True, default=None)
    occurred_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
