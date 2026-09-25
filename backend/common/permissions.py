"""
Role-based access control and jurisdiction permissions.
"""
from rest_framework import permissions
from apps.accounts.models import UserRole


class IsSuperAdmin(permissions.BasePermission):
    """Allows access strictly to users with the SUPER_ADMIN operational role."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.SUPER_ADMIN
        )


class IsMainOfficer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or request.user.role in [UserRole.SUPER_ADMIN, UserRole.MAIN_OFFICER, UserRole.SYS_ADMIN]
        )


class IsSeniorOfficerOrAbove(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or
            request.user.role in [UserRole.SUPER_ADMIN, UserRole.MAIN_OFFICER, UserRole.SYS_ADMIN, UserRole.ACP]
        )


class IsStationOfficerOrAbove(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or
            request.user.role in [UserRole.SUPER_ADMIN, UserRole.MAIN_OFFICER, UserRole.SYS_ADMIN, UserRole.ACP, UserRole.SHO]
        )


class IsConstable(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.CONSTABLE


class CanManageUsers(permissions.BasePermission):
    """
    Restricted to SUPER_ADMIN, MAIN_OFFICER, SYS_ADMIN, superuser, or users explicitly granted manage_users capability.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return (
            request.user.is_superuser or
            request.user.role in [UserRole.SUPER_ADMIN, UserRole.MAIN_OFFICER, UserRole.SYS_ADMIN] or
            request.user.has_capability('manage_users')
        )


class CanAssignFieldOfficers(permissions.BasePermission):
    """
    Restricted to station officers or above, superusers, or users with assign_field_officers capability.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if (
            request.user.is_superuser or
            request.user.role in [UserRole.SUPER_ADMIN, UserRole.MAIN_OFFICER, UserRole.SYS_ADMIN, UserRole.ACP, UserRole.SHO]
        ):
            return True
        return request.user.has_capability('assign_field_officers')


def filter_by_jurisdiction(queryset, user, ps_field='police_station', zone_field='zone', division_field='division'):
    """
    Enforces server-side jurisdiction filter on querysets.
    - Superuser / SUPER_ADMIN: global city-wide access (no filter)
    - MAIN_OFFICER / SYS_ADMIN without zone: city-wide access (no filter)
    - MAIN_OFFICER / SYS_ADMIN with zone: strictly restricted to authorized zone
    - ACP: restricted to authorized zone/division
    - SHO: restricted to authorized police station
    - CONSTABLE: restricted to assigned idols only
    """
    if not user.is_authenticated:
        return queryset.none()

    if user.is_superuser or user.role == UserRole.SUPER_ADMIN:
        return queryset

    user_zone = (getattr(user, 'zone', '') or '').strip()

    # SYS_ADMIN: strictly a Zonal System Admin.
    # Must only receive data for their assigned zone.
    # If no zone is assigned, DO NOT silently treat as city-wide — enforce safest restriction (none).
    if user.role == UserRole.SYS_ADMIN:
        if user_zone:
            from common.zones import zone_filter_q
            return queryset.filter(zone_filter_q(zone_field, user_zone))
        return queryset.none()

    # MAIN_OFFICER: City-wide operational officer (or zone-scoped if assigned to a zone).
    if user.role == UserRole.MAIN_OFFICER:
        if user_zone and user_zone.lower() not in ['all', 'all zones', 'city-wide', 'city wide', 'citywide']:
            from common.zones import zone_filter_q
            return queryset.filter(zone_filter_q(zone_field, user_zone))
        return queryset

    if user.role == UserRole.ACP:
        if user_zone:
            from common.zones import zone_filter_q
            return queryset.filter(zone_filter_q(zone_field, user_zone))
        if user.division:
            return queryset.filter(**{f"{division_field}__iexact": user.division})
        return queryset.none()

    if user.role == UserRole.SHO:
        if user.police_station:
            from common.zones import ps_filter_q
            return queryset.filter(ps_filter_q(ps_field, user.police_station))
        return queryset.none()

    if user.role == UserRole.CONSTABLE:
        if getattr(queryset, 'model', None):
            model_name = queryset.model.__name__
            if model_name == 'User':
                return queryset.filter(id=user.id)
            if model_name == 'TrackingSession':
                return queryset.filter(assignment__constable=user, assignment__is_active=True)
            if model_name == 'Assignment':
                return queryset.filter(constable=user, is_active=True)
        # Constable only sees idols currently assigned to them
        from apps.assignments.models import Assignment
        assigned_idol_ids = Assignment.objects.filter(
            constable=user,
            is_active=True
        ).values_list('idol_id', flat=True)
        return queryset.filter(id__in=assigned_idol_ids)

    return queryset.none()


def check_user_jurisdiction_over_idol(user, idol) -> tuple[bool, str]:
    """
    Authoritative server-side jurisdiction check for a specific user and idol.
    Returns (True, "") if permitted, or (False, error_message) if denied.
    Consistent across Assignment creation, Registry, Eligible Officers, and End Assignment.

    Rules:
    - Unauthenticated: False
    - Superuser / SUPER_ADMIN: global city-wide access
    - MAIN_OFFICER: global city-wide access (or zone-scoped if assigned to a specific zone)
    - SYS_ADMIN: strictly Zonal System Admin (must have zone and match idol's zone)
    - ACP: restricted to authorized zone (or division)
    - SHO: restricted to authorized police station (and matching zone if user.zone is set)
    - CONSTABLE: not permitted for management / end assignment
    """
    if not user or not user.is_authenticated:
        return False, "Authentication credentials were not provided."

    if user.is_superuser or user.role == UserRole.SUPER_ADMIN:
        return True, ""

    from common.zones import are_same_zone, are_same_ps

    user_zone = (getattr(user, 'zone', '') or '').strip()
    idol_zone = (getattr(idol, 'zone', '') or '').strip()
    user_ps = (getattr(user, 'police_station', '') or '').strip()
    idol_ps = (getattr(idol, 'police_station', '') or '').strip()

    if user.role == UserRole.MAIN_OFFICER:
        if user_zone and user_zone.lower() not in ['all', 'all zones', 'city-wide', 'city wide', 'citywide']:
            if not are_same_zone(user_zone, idol_zone):
                return False, "Idol is outside your authorized zone jurisdiction."
        return True, ""

    if user.role == UserRole.SYS_ADMIN:
        if not user_zone:
            return False, "Your System Administrator account has no assigned zone."
        if not are_same_zone(user_zone, idol_zone):
            return False, f"Idol is in '{idol_zone or 'None'}', outside your assigned zone ('{user_zone}')."
        return True, ""

    if user.role == UserRole.ACP:
        if user_zone:
            if not are_same_zone(user_zone, idol_zone):
                return False, "Idol is outside your authorized zone jurisdiction."
            return True, ""
        user_div = (getattr(user, 'division', '') or '').strip()
        idol_div = (getattr(idol, 'division', '') or '').strip()
        if user_div:
            if user_div.lower() != idol_div.lower():
                return False, "Idol is outside your authorized division jurisdiction."
            return True, ""
        return False, "Officer has no assigned zone or division."

    if user.role == UserRole.SHO:
        if not user_ps:
            return False, "Your account has no assigned police station."
        if not are_same_ps(user_ps, idol_ps):
            return False, "Idol is outside your police station jurisdiction."
        # If user also has a zone set, verify it matches canonically
        if user_zone and idol_zone and not are_same_zone(user_zone, idol_zone):
            return False, "Idol is outside your authorized zone jurisdiction."
        return True, ""

    if user.role == UserRole.CONSTABLE:
        return False, "Constables are not permitted to manage assignments."

    return False, "Permission denied."


