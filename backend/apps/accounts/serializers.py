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
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
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

    def validate_password(self, value):
        if not value or not str(value).strip():
            return None
        if len(str(value).strip()) < 6:
            raise serializers.ValidationError("Password must be at least 6 characters.")
        return str(value).strip()

    def validate(self, attrs):
        from apps.geography.models import PoliceStationBoundary

        request = self.context.get('request')
        caller = request.user if request and request.user.is_authenticated else None
        caller_zone = (getattr(caller, 'zone', '') or '').strip() if caller else ''
        is_global_admin = bool(
            caller and (
                caller.is_superuser or
                (caller.role == UserRole.MAIN_OFFICER and not caller_zone)
            )
        )

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

        # -----------------------------------------------------------------
        # Scope Enforcement for Zone-Scoped Administrators (SYS_ADMIN / MAIN_OFFICER with zone)
        # -----------------------------------------------------------------
        if caller and not is_global_admin and caller_zone:
            # 1. Self-protection: caller cannot alter their own role or zone jurisdiction
            if self.instance and self.instance.id == caller.id:
                if 'zone' in attrs and (attrs['zone'] or '').strip().lower() != caller_zone.lower():
                    errors['zone'] = ['Cannot modify your own assigned zone jurisdiction.']
                if 'role' in attrs and attrs['role'] != self.instance.role:
                    errors['role'] = ['Cannot modify your own administrative role.']

            # 2. Target user zone boundary:
            if not self.instance:
                # Creating new user: target zone MUST match caller's zone
                if 'zone' in attrs and (attrs['zone'] or '').strip():
                    if attrs['zone'].strip().lower() != caller_zone.lower():
                        errors['zone'] = [f"Cannot create accounts outside your assigned zone ('{caller_zone}')."]
                    else:
                        attrs['zone'] = caller_zone
                else:
                    attrs['zone'] = caller_zone
                zone = caller_zone

                # Scope escape prevention: A zoned administrator cannot create a global / unzoned admin
                if role in [UserRole.MAIN_OFFICER, UserRole.SYS_ADMIN]:
                    attrs['zone'] = caller_zone
                    zone = caller_zone
            else:
                # Updating existing user: cannot transfer across zones or remove zone
                if 'zone' in attrs:
                    new_zone = (attrs['zone'] or '').strip()
                    if new_zone and new_zone.lower() != caller_zone.lower():
                        errors['zone'] = [f"Cannot transfer accounts to another zone ('{new_zone}')."]
                    elif not new_zone:
                        errors['zone'] = ['Cannot remove zone jurisdiction from user account.']
                    else:
                        attrs['zone'] = caller_zone

            # 3. Police Station scope validation: police station must belong to caller's zone
            if police_station and PoliceStationBoundary.objects.exists():
                ps_obj = PoliceStationBoundary.objects.filter(ps_name__iexact=police_station).first()
                if ps_obj and ps_obj.zone.strip().lower() != caller_zone.lower():
                    errors['police_station'] = [
                        f"Selected police station '{ps_obj.ps_name}' belongs to '{ps_obj.zone}', "
                        f"outside your assigned zone '{caller_zone}'."
                    ]

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
        if password and str(password).strip():
            user.set_password(str(password).strip())
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password and str(password).strip():
            instance.set_password(str(password).strip())
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

