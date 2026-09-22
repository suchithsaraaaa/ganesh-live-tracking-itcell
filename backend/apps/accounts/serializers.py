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

    class Meta:
        model = User
        fields = [
            'id',
            'name',
            'username',
            'police_id',
            'role',
            'police_station',
            'is_active',
            'currently_assigned',
            'assigned_gpid',
        ]

    def get_name(self, obj) -> str:
        return obj.get_full_name() or obj.username
