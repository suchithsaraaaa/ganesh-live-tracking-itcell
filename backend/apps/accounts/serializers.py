from rest_framework import serializers
from .models import User, UserRole, CANONICAL_PERMISSIONS


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'name',
            'first_name',
            'last_name',
            'role',
            'police_id',
            'zone',
            'division',
            'police_station',
            'is_active',
            'permissions',
            'custom_permissions',
            'date_joined',
            'last_login',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']

    def get_name(self, obj) -> str:
        return obj.get_full_name() or obj.username

    def get_permissions(self, obj) -> list[str]:
        return obj.get_effective_permissions()


class UserCreateUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    custom_permissions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'password',
            'first_name',
            'last_name',
            'role',
            'police_id',
            'zone',
            'division',
            'police_station',
            'is_active',
            'custom_permissions',
        ]

    def validate_custom_permissions(self, value):
        if value:
            invalid = [p for p in value if p not in CANONICAL_PERMISSIONS]
            if invalid:
                raise serializers.ValidationError(
                    f"Unknown or unauthorized permission codename(s): {', '.join(invalid)}"
                )
        return value

    def validate(self, attrs):
        from apps.geography.models import PoliceStationBoundary

        # Determine effective role
        role = attrs.get('role', self.instance.role if self.instance else UserRole.CONSTABLE)
        
        # Determine effective zone and police_station
        zone = attrs.get('zone', self.instance.zone if self.instance else '')
        if zone:
            zone = zone.strip()
        police_station = attrs.get('police_station', self.instance.police_station if self.instance else '')
        if police_station:
            police_station = police_station.strip()

        errors = {}

        if role == UserRole.CONSTABLE:
            if not zone:
                errors['zone'] = ['Zone is required for Constable / Ground Staff accounts.']
            if not police_station:
                errors['police_station'] = ['Police Station is required for Constable / Ground Staff accounts.']

            if zone and police_station and PoliceStationBoundary.objects.exists():
                ps_obj = PoliceStationBoundary.objects.filter(ps_name__iexact=police_station).first()
                if not ps_obj:
                    errors['police_station'] = [f"Police station '{police_station}' is not a recognized authoritative station."]
                elif ps_obj.zone.lower() != zone.lower():
                    errors['police_station'] = [f"Selected police station '{ps_obj.ps_name}' does not belong to '{zone}' (belongs to '{ps_obj.zone}')."]
                else:
                    attrs['zone'] = ps_obj.zone
                    attrs['police_station'] = ps_obj.ps_name
                    if ps_obj.division and not attrs.get('division'):
                        attrs['division'] = ps_obj.division

        elif role == UserRole.SHO:
            if not police_station:
                errors['police_station'] = ['Police Station is required for SHO accounts.']
            elif PoliceStationBoundary.objects.exists():
                ps_obj = PoliceStationBoundary.objects.filter(ps_name__iexact=police_station).first()
                if not ps_obj:
                    errors['police_station'] = [f"Police station '{police_station}' is not a recognized authoritative station."]
                else:
                    attrs['police_station'] = ps_obj.ps_name
                    if not zone:
                        attrs['zone'] = ps_obj.zone
                    elif ps_obj.zone.lower() != zone.lower():
                        errors['police_station'] = [f"Selected police station '{ps_obj.ps_name}' does not belong to '{zone}'."]

        elif role == UserRole.ACP:
            division = attrs.get('division', self.instance.division if self.instance else '')
            if not zone and not division:
                errors['zone'] = ['Zone or Division is required for ACP accounts.']

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class AssignableOfficerSerializer(serializers.ModelSerializer):
    """
    Officer directory serializer for assignment UI.
    Adheres strictly to zero phone_number exposure.
    """
    name = serializers.SerializerMethodField()
    currently_assigned = serializers.BooleanField(read_only=True)
    assigned_gpid = serializers.CharField(read_only=True, allow_null=True)
    availability = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'name',
            'username',
            'police_id',
            'role',
            'zone',
            'police_station',
            'is_active',
            'currently_assigned',
            'assigned_gpid',
            'availability',
        ]

    def get_name(self, obj) -> str:
        return obj.get_full_name() or obj.username

    def get_availability(self, obj) -> str:
        return 'ASSIGNED' if getattr(obj, 'currently_assigned', False) else 'AVAILABLE'

