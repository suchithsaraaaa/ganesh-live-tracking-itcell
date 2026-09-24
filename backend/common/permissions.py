"""
Role-based access control and jurisdiction permissions.
"""
from rest_framework import permissions
from apps.accounts.models import UserRole


class IsMainOfficer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or request.user.role in [UserRole.MAIN_OFFICER, UserRole.SYS_ADMIN]
        )


class IsSeniorOfficerOrAbove(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or
            request.user.role in [UserRole.MAIN_OFFICER, UserRole.SYS_ADMIN, UserRole.ACP]
        )


class IsStationOfficerOrAbove(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or
            request.user.role in [UserRole.MAIN_OFFICER, UserRole.SYS_ADMIN, UserRole.ACP, UserRole.SHO]
        )


class IsConstable(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.CONSTABLE


class CanManageUsers(permissions.BasePermission):
    """
    Restricted to MAIN_OFFICER, SYS_ADMIN, superuser, or users explicitly granted manage_users capability.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return (
            request.user.is_superuser or
            request.user.role in [UserRole.MAIN_OFFICER, UserRole.SYS_ADMIN] or
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
            request.user.role in [UserRole.MAIN_OFFICER, UserRole.SYS_ADMIN, UserRole.ACP, UserRole.SHO]
        ):
            return True
        return request.user.has_capability('assign_field_officers')


def filter_by_jurisdiction(queryset, user, ps_field='police_station', zone_field='zone', division_field='division'):
    """
    Enforces server-side jurisdiction filter on querysets.
    - Superuser: city-wide access (no filter)
    - MAIN_OFFICER / SYS_ADMIN without zone: city-wide access (no filter)
    - MAIN_OFFICER / SYS_ADMIN with zone: strictly restricted to authorized zone
    - ACP: restricted to authorized zone/division
    - SHO: restricted to authorized police station
    - CONSTABLE: restricted to assigned idols only
    """
    if not user.is_authenticated:
        return queryset.none()

    if user.is_superuser:
        return queryset

    user_zone = (getattr(user, 'zone', '') or '').strip()

    # SYS_ADMIN or MAIN_OFFICER:
    # If a zone is assigned, access is strictly limited to that zone.
    # If no zone is assigned, the user is a city-wide / global administrator.
    if user.role in [UserRole.MAIN_OFFICER, UserRole.SYS_ADMIN]:
        if user_zone:
            return queryset.filter(**{f"{zone_field}__iexact": user_zone})
        return queryset

    if user.role == UserRole.ACP:
        if user_zone:
            return queryset.filter(**{f"{zone_field}__iexact": user_zone})
        if user.division:
            return queryset.filter(**{f"{division_field}__iexact": user.division})
        return queryset.none()

    if user.role == UserRole.SHO:
        if user.police_station:
            return queryset.filter(**{f"{ps_field}__iexact": user.police_station})
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

