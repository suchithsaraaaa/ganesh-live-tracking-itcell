"""
Role-based access control and jurisdiction permissions.
"""
from rest_framework import permissions
from apps.accounts.models import UserRole


class IsMainOfficer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_superuser or request.user.role == UserRole.MAIN_OFFICER)


class IsSeniorOfficerOrAbove(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or
            request.user.role in [UserRole.MAIN_OFFICER, UserRole.ACP]
        )


class IsStationOfficerOrAbove(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or
            request.user.role in [UserRole.MAIN_OFFICER, UserRole.ACP, UserRole.SHO]
        )


class IsConstable(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.CONSTABLE


class CanManageUsers(permissions.BasePermission):
    """
    Restricted to MAIN_OFFICER or superuser or users explicitly granted manage_users capability.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return (
            request.user.is_superuser or
            request.user.role == UserRole.MAIN_OFFICER or
            request.user.has_capability('manage_users')
        )


class CanAssignFieldOfficers(permissions.BasePermission):
    """
    Restricted to station officers or above, superusers, or users with assign_field_officers capability.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.role in [UserRole.MAIN_OFFICER, UserRole.ACP, UserRole.SHO]:
            return True
        return request.user.has_capability('assign_field_officers')


def filter_by_jurisdiction(queryset, user, ps_field='police_station', zone_field='zone', division_field='division'):
    """
    Enforces server-side jurisdiction filter on querysets.
    - MAIN_OFFICER: city-wide access (no filter)
    - ACP: restricted to authorized zone/division
    - SHO: restricted to authorized police station
    - CONSTABLE: restricted to assigned idols only
    """
    if not user.is_authenticated:
        return queryset.none()

    if user.role == UserRole.MAIN_OFFICER or user.is_superuser:
        return queryset

    if user.role == UserRole.ACP:
        if user.zone:
            return queryset.filter(**{f"{zone_field}__iexact": user.zone})
        if user.division:
            return queryset.filter(**{f"{division_field}__iexact": user.division})
        return queryset.none()

    if user.role == UserRole.SHO:
        if user.police_station:
            return queryset.filter(**{f"{ps_field}__iexact": user.police_station})
        return queryset.none()

    if user.role == UserRole.CONSTABLE:
        if getattr(queryset, 'model', None) and queryset.model.__name__ == 'User':
            return queryset.filter(id=user.id)
        # Constable only sees idols currently assigned to them
        from apps.assignments.models import Assignment
        assigned_idol_ids = Assignment.objects.filter(
            constable=user,
            is_active=True
        ).values_list('idol_id', flat=True)
        return queryset.filter(id__in=assigned_idol_ids)

    return queryset.none()

