from rest_framework import serializers
from .models import Assignment
from apps.accounts.models import User
from apps.idols.models import Idol


class AssignmentSerializer(serializers.ModelSerializer):
    constable_name = serializers.SerializerMethodField()
    constable_username = serializers.SerializerMethodField()
    constable_police_id = serializers.SerializerMethodField()
    idol_gpid = serializers.CharField(source='idol.gpid', read_only=True)
    idol_name = serializers.CharField(source='idol.name', read_only=True)
    police_station = serializers.CharField(source='idol.police_station', read_only=True)

    class Meta:
        model = Assignment
        fields = [
            'id',
            'idol',
            'idol_gpid',
            'idol_name',
            'police_station',
            'constable',
            'constable_name',
            'constable_username',
            'constable_police_id',
            'assigned_by',
            'started_at',
            'ended_at',
            'is_active',
            'handover_reason',
            'handover_to',
            'created_at',
        ]
        read_only_fields = ['started_at', 'ended_at', 'is_active', 'handover_to', 'assigned_by']

    def get_constable_name(self, obj):
        if obj.constable:
            return obj.constable.get_full_name() or obj.constable.username
        return obj.officer_name_snapshot or 'Historical Officer'

    def get_constable_username(self, obj):
        if obj.constable:
            return obj.constable.username
        return obj.officer_name_snapshot or 'Historical Officer'

    def get_constable_police_id(self, obj):
        if obj.constable:
            return obj.constable.police_id or ''
        return obj.police_id_snapshot or ''


class CreateAssignmentSerializer(serializers.Serializer):
    gpid = serializers.CharField(required=True)
    constable_id = serializers.IntegerField(required=True)

    def validate(self, data):
        gpid = data.get('gpid')
        constable_id = data.get('constable_id')
        try:
            data['idol_obj'] = Idol.objects.get(gpid__iexact=gpid)
        except Idol.DoesNotExist:
            raise serializers.ValidationError({'gpid': f'Idol with GPID {gpid} does not exist.'})

        try:
            data['constable_obj'] = User.objects.get(id=constable_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({'constable_id': f'User with ID {constable_id} does not exist.'})

        return data


class HandoverSerializer(serializers.Serializer):
    new_constable_id = serializers.IntegerField(required=True)
    reason = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_new_constable_id(self, value):
        try:
            return User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(f'User with ID {value} does not exist.')
