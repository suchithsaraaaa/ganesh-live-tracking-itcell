from rest_framework import serializers
from .models import Assignment
from apps.accounts.models import User, UserRole
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
            idol = Idol.objects.get(gpid__iexact=gpid)
            data['idol_obj'] = idol
        except Idol.DoesNotExist:
            raise serializers.ValidationError({'gpid': f'Idol with GPID {gpid} does not exist.'})

        try:
            constable = User.objects.get(id=constable_id)
            data['constable_obj'] = constable
        except User.DoesNotExist:
            raise serializers.ValidationError({'constable_id': f'User with ID {constable_id} does not exist.'})

        # Rule 16: Eligible Officer Rules
        if not constable.is_active:
            raise serializers.ValidationError({
                'constable_id': f"Officer {constable.username} is disabled and cannot be assigned."
            })

        if constable.role != UserRole.CONSTABLE:
            raise serializers.ValidationError({
                'constable_id': f"User {constable.username} does not have the Constable / Ground Staff role."
            })

        # Rule 18: One active assignment per GPID
        if Assignment.objects.filter(idol=idol, is_active=True).exists():
            raise serializers.ValidationError({
                'gpid': f"GPID {idol.gpid} already has an active officer assignment."
            })

        # Rule 19: One active assignment per constable
        if Assignment.objects.filter(constable=constable, is_active=True).exists():
            raise serializers.ValidationError({
                'constable_id': f"Officer {constable.username} already has an active GPID assignment."
            })

        # Station and Zone match between Idol and Constable
        if not constable.police_station or constable.police_station.lower() != idol.police_station.lower():
            raise serializers.ValidationError({
                'constable_id': f"Officer's police station ('{constable.police_station or 'None'}') does not match idol's police station ('{idol.police_station}')."
            })
        if not constable.zone or constable.zone.lower() != idol.zone.lower():
            raise serializers.ValidationError({
                'constable_id': f"Officer's zone ('{constable.zone or 'None'}') does not match idol's zone ('{idol.zone}')."
            })

        # Rule 30: Caller jurisdiction verification
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            caller = request.user
            caller_zone = (caller.zone or '').strip()
            is_global_admin = bool(caller.is_superuser or caller.role == UserRole.SUPER_ADMIN or (caller.role == UserRole.MAIN_OFFICER and not caller_zone))
            if not is_global_admin:
                if caller.role == UserRole.SYS_ADMIN:
                    if not caller_zone:
                        raise serializers.ValidationError({'error': 'Your System Administrator account has no assigned zone.'})
                    if idol.zone and idol.zone.lower() != caller_zone.lower():
                        raise serializers.ValidationError({'gpid': f"Idol is in '{idol.zone}', outside your assigned zone ('{caller_zone}')."})
                    if constable.zone and constable.zone.lower() != caller_zone.lower():
                        raise serializers.ValidationError({'constable_id': f"Officer is in '{constable.zone}', outside your assigned zone ('{caller_zone}')."})
                elif caller.role in [UserRole.MAIN_OFFICER, UserRole.ACP]:
                    if caller_zone and idol.zone and idol.zone.lower() != caller_zone.lower():
                        raise serializers.ValidationError({'error': 'Idol is outside your authorized zone jurisdiction.'})
                elif caller.role == UserRole.SHO:
                    if caller.police_station and idol.police_station and idol.police_station.lower() != caller.police_station.lower():
                        raise serializers.ValidationError({'error': 'Idol is outside your police station jurisdiction.'})
                    if caller.police_station and constable.police_station and constable.police_station.lower() != caller.police_station.lower():
                        raise serializers.ValidationError({'constable_id': 'Cannot assign officer from outside your police station.'})

        return data


class HandoverSerializer(serializers.Serializer):
    new_constable_id = serializers.IntegerField(required=True)
    reason = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_new_constable_id(self, value):
        try:
            return User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(f'User with ID {value} does not exist.')


class AssignableIdolRegistrySerializer(serializers.ModelSerializer):
    """
    Lean operational serializer for the GPID Registry table.
    Enforces height bucket categorization and embeds current active assignment.
    """
    idol_height = serializers.FloatField(read_only=True)
    height = serializers.FloatField(source='idol_height', read_only=True)
    height_bucket = serializers.SerializerMethodField()
    height_classification = serializers.SerializerMethodField()
    assignment = serializers.SerializerMethodField()
    tracking_state = serializers.SerializerMethodField()
    visarjan_date = serializers.DateField(source='immersion_date', read_only=True)
    immersion_date = serializers.DateField(read_only=True)

    class Meta:
        model = Idol
        fields = [
            'id',
            'gpid',
            'name',
            'association_name',
            'idol_height',
            'height',
            'height_bucket',
            'height_classification',
            'zone',
            'division',
            'police_station',
            'ps_code',
            'address',
            'latitude',
            'longitude',
            'geocoding_confidence',
            'resolved_address',
            'immersion_date',
            'visarjan_date',
            'procession_state',
            'tracking_state',
            'assignment',
        ]

    def get_height_bucket(self, obj):
        if obj.idol_height is None:
            return 'below_15'
        h = float(obj.idol_height)
        if h < 15.0:
            return 'below_15'
        elif 15.0 <= h < 21.0:
            return '15-20'
        elif 21.0 <= h < 26.0:
            return '21-25'
        elif h >= 26.0:
            return '26+'
        return 'below_15'

    def get_height_classification(self, obj):
        if obj.idol_height is None:
            return 'UNKNOWN'
        h = float(obj.idol_height)
        if 15.0 <= h < 21.0:
            return 'GREEN'
        elif 21.0 <= h < 26.0:
            return 'YELLOW'
        elif h >= 26.0:
            return 'RED'
        return 'SUBTHRESHOLD'

    def get_assignment(self, obj):
        active_map = self.context.get('active_assignment_map')
        if active_map is not None:
            assign = active_map.get(obj.id)
        else:
            assign = obj.assignments.filter(is_active=True).select_related('constable').first()

        if not assign:
            return None

        officer = assign.constable
        return {
            'id': assign.id,
            'status': 'ACTIVE',
            'officer_name': assign._constable_display(),
            'officer_id': assign.constable_id,
            'police_id': (officer.police_id if officer else assign.police_id_snapshot) or '',
            'police_station': (officer.police_station if officer else '') or '',
            'started_at': assign.started_at,
        }

    def get_tracking_state(self, obj):
        tracking_map = self.context.get('active_sessions_map')
        if tracking_map is not None:
            return tracking_map.get(obj.id, 'OFFLINE')
        return 'OFFLINE'
