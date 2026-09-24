from rest_framework import serializers
from .models import User, UserRole, CANONICAL_PERMISSIONS


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    jurisdiction_display = serializers.SerializerMethodField()
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
            'jurisdiction_display',
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

    def get_role_display(self, obj) -> str:
        if obj.role == UserRole.SYS_ADMIN:
            return 'Zonal System Admin' if obj.zone else 'System Admin (Unassigned Zone)'
        if obj.role == UserRole.SUPER_ADMIN:
            return 'Super Administrator'
        if obj.role == UserRole.MAIN_OFFICER:
            return 'Main Officer'
        return obj.get_role_display()

    def get_jurisdiction_display(self, obj) -> str:
        if obj.role == UserRole.SUPER_ADMIN:
            return 'City Wide'
        if obj.role == UserRole.MAIN_OFFICER:
            return obj.zone if obj.zone else 'City Wide'
        if obj.police_station:
            return obj.police_station
        if obj.zone:
            return obj.zone
        if obj.division:
            return obj.division
        return 'Unassigned'

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

        # -----------------------------------------------------------------
        # 1. Self-Modification Guards (BUG 2)
        # -----------------------------------------------------------------
        is_self_edit = bool(self.instance and caller and self.instance.id == caller.id)
        if is_self_edit:
            if 'role' in attrs and attrs['role'] != self.instance.role:
                errors['role'] = ['You cannot change your own operational role.']
            if 'zone' in attrs and (attrs['zone'] or '').strip().lower() != (self.instance.zone or '').strip().lower():
                errors['zone'] = ['You cannot change your own assigned jurisdiction.']
            if 'custom_permissions' in attrs and not caller_is_super:
                if set(attrs['custom_permissions']) != set(self.instance.custom_permissions or []):
                    errors['custom_permissions'] = ['You cannot modify your own granular permissions.']

        # -----------------------------------------------------------------
        # 2. Role Change & Creation Hierarchy Guards (BUG 2 & BUG 3)
        # -----------------------------------------------------------------
        is_role_change = bool(self.instance and 'role' in attrs and attrs['role'] != self.instance.role)
        is_user_creation = bool(not self.instance)

        if is_role_change and not is_self_edit:
            if caller_is_super:
                pass  # Super Admin can change roles
            elif caller and caller.role == UserRole.MAIN_OFFICER:
                if role == UserRole.SUPER_ADMIN:
                    errors['role'] = ['Only Super Administrators can assign the Super Admin role.']
            elif caller and caller.role == UserRole.SYS_ADMIN:
                # SYS_ADMIN can ONLY change roles for users in their own zone to CONSTABLE or SHO
                if role not in [UserRole.CONSTABLE, UserRole.SHO]:
                    errors['role'] = [f"System Administrators can only assign Constable or SHO roles, not '{role}'."]
                if self.instance.role in [UserRole.SUPER_ADMIN, UserRole.MAIN_OFFICER, UserRole.SYS_ADMIN]:
                    errors['role'] = [f"System Administrators cannot modify the role of '{self.instance.role}' accounts."]
            else:
                errors['role'] = ['You are not authorized to change operational roles.']

        if is_user_creation:
            if caller and caller.role == UserRole.SYS_ADMIN:
                if role not in [UserRole.CONSTABLE, UserRole.SHO]:
                    errors['role'] = [f"System Administrators can only create Constable or SHO accounts, not '{role}'."]
            elif caller and caller.role not in [UserRole.SUPER_ADMIN, UserRole.MAIN_OFFICER] and not caller_is_super:
                errors['role'] = ['You are not authorized to create officer accounts.']

        # -----------------------------------------------------------------
        # 3. Custom Permissions Privilege Escalation Guard
        # -----------------------------------------------------------------
        if 'custom_permissions' in attrs and attrs['custom_permissions'] and not is_self_edit:
            if not caller_is_super:
                for sensitive_perm in ['manage_role_templates', 'manage_roles', 'global_settings', 'manage_geography']:
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
        if caller and (caller.role == UserRole.SYS_ADMIN or (caller.role == UserRole.MAIN_OFFICER and caller_zone)):
            if caller.role == UserRole.SYS_ADMIN and not caller_zone:
                errors['detail'] = ['Your System Administrator account has no assigned zone. Contact Super Admin.']

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
            elif not is_self_edit:
                # Updating another user: cannot transfer across zones or remove zone
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

