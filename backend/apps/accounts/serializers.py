from rest_framework import serializers
from .models import User, UserRole, CANONICAL_PERMISSIONS


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
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
            'role_display',
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


class RolePermissionTemplateSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    user_count = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = None  # Loaded lazily or via model reference
        fields = [
            'id',
            'role',
            'role_display',
            'description',
            'permissions',
            'user_count',
            'updated_at',
            'updated_by_name',
        ]
        read_only_fields = ['id', 'role_display', 'user_count', 'updated_at', 'updated_by_name']

    def __init__(self, *args, **kwargs):
        from .models import RolePermissionTemplate
        self.Meta.model = RolePermissionTemplate
        super().__init__(*args, **kwargs)

    def get_user_count(self, obj) -> int:
        return User.objects.filter(role=obj.role).count()

    def get_updated_by_name(self, obj) -> str:
        if obj.updated_by:
            return obj.updated_by.get_full_name() or obj.updated_by.username
        return ''

    def validate_permissions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Permissions must be a list of strings.")
        invalid = [p for p in value if p not in CANONICAL_PERMISSIONS]
        if invalid:
            raise serializers.ValidationError(f"Invalid permission codenames: {', '.join(invalid)}")
        return value


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
        caller_is_super = bool(caller and caller.role == UserRole.SUPER_ADMIN)
        caller_zone = (getattr(caller, 'zone', '') or '').strip() if caller else ''
        is_global_admin = bool(
            caller and (
                caller.role == UserRole.SUPER_ADMIN or
                (caller.role == UserRole.MAIN_OFFICER and not caller_zone) or
                (caller.is_superuser and not caller_zone)
            )
        )

        # Determine effective target role
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
        # 1. SUPER_ADMIN Role & Account Protection Guards
        # -----------------------------------------------------------------
        # Only SUPER_ADMIN (or superuser) can assign SUPER_ADMIN role
        if role == UserRole.SUPER_ADMIN and not caller_is_super:
            errors['role'] = ['Only Super Administrators can create or assign the Super Admin role.']

        # Only SUPER_ADMIN (or superuser) can modify an existing SUPER_ADMIN account
        if self.instance and self.instance.role == UserRole.SUPER_ADMIN and not caller_is_super:
            errors['detail'] = ['Only Super Administrators can modify a Super Admin account.']

        # Demotion guard: Cannot demote the last active Super Admin
        if self.instance and self.instance.role == UserRole.SUPER_ADMIN and role != UserRole.SUPER_ADMIN:
            active_super_count = User.objects.filter(role=UserRole.SUPER_ADMIN, is_active=True).exclude(pk=self.instance.pk).count()
            if active_super_count < 1:
                errors['role'] = ['Cannot demote the last active Super Administrator. At least one active Super Admin must exist.']

        # Deactivation guard: Cannot disable the last active Super Admin
        if self.instance and self.instance.role == UserRole.SUPER_ADMIN and attrs.get('is_active') is False:
            active_super_count = User.objects.filter(role=UserRole.SUPER_ADMIN, is_active=True).exclude(pk=self.instance.pk).count()
            if active_super_count < 1:
                errors['is_active'] = ['Cannot disable the last active Super Administrator. At least one active Super Admin must exist.']

        # Self-modification guard for caller: caller cannot alter their own role
        if self.instance and caller and self.instance.id == caller.id:
            if 'role' in attrs and attrs['role'] != self.instance.role:
                errors['role'] = ['Cannot modify your own administrative role.']

        # -----------------------------------------------------------------
        # 2. SYS_ADMIN Hierarchy & Scope Guards
        # -----------------------------------------------------------------
        if caller and caller.role == UserRole.SYS_ADMIN and not caller_is_super:
            if role in [UserRole.SUPER_ADMIN, UserRole.MAIN_OFFICER]:
                errors['role'] = [f"System Administrators cannot assign or manage '{role}' accounts."]

        # -----------------------------------------------------------------
        # 3. Custom Permissions Privilege Escalation Guard
        # -----------------------------------------------------------------
        if 'custom_permissions' in attrs and attrs['custom_permissions']:
            if not caller_is_super:
                for sensitive_perm in ['manage_role_templates', 'manage_roles']:
                    if sensitive_perm in attrs['custom_permissions']:
                        errors['custom_permissions'] = [
                            f"Permission '{sensitive_perm}' can only be granted by a Super Administrator."
                        ]
                        break
                if caller and 'custom_permissions' not in errors:
                    caller_perms = set(caller.get_effective_permissions())
                    unauthorized = [p for p in attrs['custom_permissions'] if p not in caller_perms]
                    if unauthorized:
                        errors['custom_permissions'] = [
                            f"Cannot grant capabilities exceeding your own authority: {', '.join(unauthorized)}"
                        ]

        # -----------------------------------------------------------------
        # 4. Scope Enforcement for Zone-Scoped Administrators (SYS_ADMIN / Zoned MAIN_OFFICER)
        # -----------------------------------------------------------------
        if caller and not is_global_admin and caller_zone:
            # Self-protection: caller cannot alter their own assigned zone
            if self.instance and self.instance.id == caller.id:
                if 'zone' in attrs and (attrs['zone'] or '').strip().lower() != caller_zone.lower():
                    errors['zone'] = ['Cannot modify your own assigned zone jurisdiction.']

            # Target user zone boundary:
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

            # Police Station scope validation: police station must belong to caller's zone
            if police_station and PoliceStationBoundary.objects.exists():
                ps_obj = PoliceStationBoundary.objects.filter(ps_name__iexact=police_station).first()
                if ps_obj and ps_obj.zone.strip().lower() != caller_zone.lower():
                    errors['police_station'] = [
                        f"Selected police station '{ps_obj.ps_name}' belongs to '{ps_obj.zone}', "
                        f"outside your assigned zone '{caller_zone}'."
                    ]

        # Station / Zone validations by role
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
        request = self.context.get('request')
        password = validated_data.pop('password', None)

        old_role = instance.role
        old_custom = list(instance.custom_permissions or [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Handle password update
        password_changed = False
        if password and str(password).strip():
            instance.set_password(str(password).strip())
            password_changed = True

        instance.save()

        new_role = instance.role
        new_custom = list(instance.custom_permissions or [])

        from apps.accounts.views import _log_account_event
        if password_changed:
            _log_account_event(request, 'PASSWORD_RESET', instance)

        if new_role != old_role:
            _log_account_event(
                request,
                'ROLE_CHANGED',
                instance,
                extra_details={'previous_role': old_role, 'new_role': new_role}
            )
            if new_role == UserRole.SUPER_ADMIN:
                _log_account_event(
                    request,
                    'SUPER_ADMIN_GRANTED',
                    instance,
                    extra_details={'previous_role': old_role, 'new_role': new_role}
                )

        if new_custom != old_custom:
            added = [p for p in new_custom if p not in old_custom]
            removed = [p for p in old_custom if p not in new_custom]
            if added:
                _log_account_event(
                    request,
                    'PERMISSION_OVERRIDE_GRANTED',
                    instance,
                    extra_details={'added_permissions': added, 'current_permissions': new_custom}
                )
            if removed:
                _log_account_event(
                    request,
                    'PERMISSION_OVERRIDE_REVOKED',
                    instance,
                    extra_details={'removed_permissions': removed, 'current_permissions': new_custom}
                )

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

