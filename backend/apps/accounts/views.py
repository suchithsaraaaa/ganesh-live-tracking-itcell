from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from common.permissions import CanManageUsers, CanAssignFieldOfficers, IsSuperAdmin, filter_by_jurisdiction
from .models import User, UserRole, RolePermissionTemplate, CANONICAL_PERMISSIONS, ROLE_DEFAULT_PERMISSIONS
from .serializers import (
    UserSerializer,
    UserCreateUpdateSerializer,
    AssignableOfficerSerializer,
    RolePermissionTemplateSerializer,
)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({'error': 'Username and password required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            serializer = UserSerializer(user)
            return Response(serializer.data)

        existing_user = User.objects.filter(username=username).first()
        if existing_user and existing_user.check_password(password) and not existing_user.is_active:
            return Response({'error': 'Account is disabled.'}, status=status.HTTP_403_FORBIDDEN)

        return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'message': 'Logged out successfully.'})


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class UserListCreateView(APIView):
    """
    Administrative user management endpoint.
    Restricted to MAIN_OFFICER or users with manage_users capability.
    """
    permission_classes = [CanManageUsers]

    def get(self, request):
        base_qs = filter_by_jurisdiction(User.objects.all(), request.user)
        total_count = base_qs.count()
        qs = base_qs

        # 1. Zone filter
        zone = request.query_params.get('zone')
        if zone and zone != 'ALL' and zone.lower() != 'all zones':
            from common.zones import zone_filter_q
            qs = qs.filter(zone_filter_q('zone', zone.strip()))

        # 2. Police Station filter
        police_station = request.query_params.get('police_station')
        if police_station and police_station != 'ALL' and police_station.lower() != 'all police stations':
            qs = qs.filter(police_station__iexact=police_station.strip())

        # 3. Officer Level / Role filter (support both 'role' and 'officer_level')
        role = request.query_params.get('role') or request.query_params.get('officer_level')
        if role and role != 'ALL' and role.upper() in UserRole.values:
            qs = qs.filter(role=role.upper())

        # 4. Status filter (support 'status=active|inactive' and 'is_active=true|false')
        status_param = request.query_params.get('status')
        is_active = request.query_params.get('is_active')
        if status_param and status_param != 'ALL':
            if status_param.upper() in ('ACTIVE', 'TRUE', '1'):
                qs = qs.filter(is_active=True)
            elif status_param.upper() in ('INACTIVE', 'DISABLED', 'FALSE', '0'):
                qs = qs.filter(is_active=False)
        elif is_active is not None and is_active != '' and is_active != 'ALL':
            qs = qs.filter(is_active=is_active.lower() in ('true', '1'))

        # 5. Search query
        search = request.query_params.get('search')
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(police_id__icontains=search) |
                Q(police_station__icontains=search) |
                Q(zone__icontains=search) |
                Q(phone_number__icontains=search)
            )

        qs = qs.distinct().order_by('-date_joined', 'id')
        filtered_count = qs.count()

        # Optional pagination support
        page = request.query_params.get('page')
        page_size = request.query_params.get('page_size')
        if page or page_size:
            from rest_framework.pagination import PageNumberPagination
            paginator = PageNumberPagination()
            paginator.page_size = int(page_size) if page_size else 50
            page_data = paginator.paginate_queryset(qs, request)
            serializer = UserSerializer(page_data, many=True)
            resp = paginator.get_paginated_response(serializer.data)
            resp.data['total_count'] = total_count
            return resp

        serializer = UserSerializer(qs, many=True)
        return Response({
            'count': filtered_count,
            'total_count': total_count,
            'results': serializer.data
        })


    def post(self, request):
        serializer = UserCreateUpdateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            _log_account_event(request, 'USER_CREATED', user)
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(APIView):
    """
    Retrieve, update, or disable individual users.
    Restricted to MAIN_OFFICER, SYS_ADMIN, or users with manage_users capability.
    Jurisdiction is strictly enforced server-side.
    """
    permission_classes = [CanManageUsers]

    def get_object(self, pk, request_user):
        qs = filter_by_jurisdiction(User.objects.all(), request_user)
        try:
            return qs.get(pk=pk)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        user = self.get_object(pk, request.user)
        if not user:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserSerializer(user).data)

    def patch(self, request, pk):
        user = self.get_object(pk, request.user)
        if not user:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        caller_is_super = bool(request.user and request.user.role == UserRole.SUPER_ADMIN)
        if user.role == UserRole.SUPER_ADMIN and not caller_is_super:
            return Response({'error': 'Only Super Administrators can modify a Super Admin account.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = UserCreateUpdateSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            updated_user = serializer.save()
            return Response(UserSerializer(updated_user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        # Soft-disable only via this method — true hard deletion is on UserDeleteView.
        user = self.get_object(pk, request.user)
        if not user:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if user.id == request.user.id:
            return Response({'error': 'Cannot disable your own administrative account.'}, status=status.HTTP_400_BAD_REQUEST)

        caller_is_super = bool(request.user and request.user.role == UserRole.SUPER_ADMIN)
        if user.role == UserRole.SUPER_ADMIN:
            if not caller_is_super:
                return Response({'error': 'Only Super Administrators can disable a Super Admin account.'}, status=status.HTTP_403_FORBIDDEN)
            active_super_count = User.objects.filter(role=UserRole.SUPER_ADMIN, is_active=True).exclude(pk=user.pk).count()
            if active_super_count < 1:
                return Response({'error': 'Cannot disable the last active Super Administrator. At least one active Super Admin must exist.'}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = False
        user.save(update_fields=['is_active'])
        _log_account_event(request, 'USER_DISABLED', user)
        return Response({'message': f'User {user.username} has been disabled.'})


class UserToggleActiveView(APIView):
    """
    Quick toggle for user active/inactive state.
    Jurisdiction is strictly enforced server-side.
    """
    permission_classes = [CanManageUsers]

    def post(self, request, pk):
        qs = filter_by_jurisdiction(User.objects.all(), request.user)
        try:
            user = qs.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if user.id == request.user.id and user.is_active:
            return Response({'error': 'Cannot disable your own administrative account.'}, status=status.HTTP_400_BAD_REQUEST)

        caller_is_super = bool(request.user and request.user.role == UserRole.SUPER_ADMIN)
        if user.role == UserRole.SUPER_ADMIN:
            if not caller_is_super:
                return Response({'error': 'Only Super Administrators can modify a Super Admin account.'}, status=status.HTTP_403_FORBIDDEN)
            if user.is_active:
                active_super_count = User.objects.filter(role=UserRole.SUPER_ADMIN, is_active=True).exclude(pk=user.pk).count()
                if active_super_count < 1:
                    return Response({'error': 'Cannot disable the last active Super Administrator. At least one active Super Admin must exist.'}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        action = 'USER_ENABLED' if user.is_active else 'USER_DISABLED'
        _log_account_event(request, action, user)
        return Response({
            'id': user.id,
            'username': user.username,
            'is_active': user.is_active,
            'message': f"User {user.username} is now {'active' if user.is_active else 'disabled'}."
        })


class AssignableOfficerDirectoryView(APIView):
    """
    Returns field officers (constables) available for idol assignment.
    Respects jurisdiction:
    - MAIN_OFFICER / SYS_ADMIN without zone (or superuser): city-wide
    - MAIN_OFFICER / SYS_ADMIN with zone: within assigned zone
    - ACP: within ACP's zone/division
    - SHO: within SHO's police station
    Excludes phone numbers to protect officer privacy.
    """
    permission_classes = [CanAssignFieldOfficers]

    def get(self, request):
        caller = request.user
        qs = User.objects.filter(role=UserRole.CONSTABLE, is_active=True).order_by('police_station', 'username')

        user_zone = (caller.zone or '').strip()

        # Jurisdiction filter
        if caller.role == UserRole.SHO:
            if caller.police_station:
                from common.zones import ps_filter_q
                qs = qs.filter(ps_filter_q('police_station', caller.police_station))
            else:
                qs = qs.none()
        elif caller.role == UserRole.ACP:
            if user_zone:
                from common.zones import zone_filter_q
                qs = qs.filter(zone_filter_q('zone', user_zone))
            elif caller.division:
                qs = qs.filter(division__iexact=caller.division)
            else:
                qs = qs.none()
        elif caller.role == UserRole.SYS_ADMIN and not caller.is_superuser:
            if user_zone:
                from common.zones import zone_filter_q
                qs = qs.filter(zone_filter_q('zone', user_zone))
            else:
                qs = qs.none()
        elif caller.role == UserRole.MAIN_OFFICER and not caller.is_superuser:
            if user_zone:
                from common.zones import zone_filter_q
                qs = qs.filter(zone_filter_q('zone', user_zone))

        # Optional zone filter if authorized
        requested_zone = request.query_params.get('zone')
        if requested_zone:
            from common.zones import are_same_zone, zone_filter_q
            if not caller.is_superuser and user_zone and not are_same_zone(user_zone, requested_zone):
                return Response({'error': 'Cannot view officers outside your zone jurisdiction.'}, status=status.HTTP_403_FORBIDDEN)
            qs = qs.filter(zone_filter_q('zone', requested_zone))

        # Optional station filter if authorized
        requested_ps = request.query_params.get('police_station')
        if requested_ps:
            from common.zones import are_same_ps, ps_filter_q
            if caller.role == UserRole.SHO and not are_same_ps(caller.police_station, requested_ps):
                return Response({'error': 'Cannot view officers outside your police station jurisdiction.'}, status=status.HTTP_403_FORBIDDEN)
            qs = qs.filter(ps_filter_q('police_station', requested_ps))

        search = request.query_params.get('search')
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(police_id__icontains=search)
            )

        # Batch lookup active assignments for these constables
        from apps.assignments.models import Assignment
        active_assignments = {
            a.constable_id: a.idol.gpid
            for a in Assignment.objects.filter(
                constable__in=qs,
                is_active=True
            ).select_related('idol')
        }

        available_only = request.query_params.get('available_only', '').lower() in ['true', '1']

        officers = []
        for user in qs:
            assigned_gpid = active_assignments.get(user.id)
            user.currently_assigned = assigned_gpid is not None
            user.assigned_gpid = assigned_gpid
            if available_only and user.currently_assigned:
                continue
            officers.append(user)

        serializer = AssignableOfficerSerializer(officers, many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _log_account_event(request, action: str, target_user: User, extra_details: dict = None) -> None:
    """Record an administrative account lifecycle event in the audit trail."""
    try:
        from apps.audit.models import AuditEvent
        ip = (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.META.get('REMOTE_ADDR')
        ) if request else None
        actor = request.user if request and request.user.is_authenticated else None
        full_name = f"{target_user.first_name} {target_user.last_name}".strip() or target_user.username
        details = {
            'username': target_user.username,
            'full_name': full_name,
            'police_id': target_user.police_id or '',
            'role': target_user.role,
            'police_station': target_user.police_station or '',
        }
        if extra_details:
            details.update(extra_details)
        AuditEvent.objects.create(
            actor=actor,
            action=action,
            target_model='User',
            target_id=str(target_user.id),
            details=details,
            ip_address=ip,
        )
    except Exception:
        # Audit failure must never block the primary operation.
        pass


class UserDeleteView(APIView):
    """
    Permanently deletes a user account.

    Preflight invariants enforced atomically:
    1. Caller must have manage_users capability.
    2. Target user must exist (404 otherwise).
    3. Caller cannot delete their own account (400).
    4. Target must not have an active idol assignment (400 — reassign first).
    5. Deletion is wrapped in a transaction; any ProtectedError rolls back
       the whole operation and returns 409.

    Historical data safety:
    - Assignment.constable uses SET_NULL, so Assignment rows are preserved.
    - Assignment.officer_name_snapshot and police_id_snapshot retain identity.
    - TrackingSession → LocationPoint rows are preserved through the Assignment.
    - IdolEvent.actor uses SET_NULL — procession events are preserved.
    - AuditEvent.actor uses SET_NULL — audit trail is preserved.
    - A final USER_DELETED audit record is written before the account is removed.
    """
    permission_classes = [CanManageUsers]

    def delete(self, request, pk):
        # --- 1. Target existence check (with strict server-side jurisdiction scoping) ---
        qs = filter_by_jurisdiction(User.objects.all(), request.user)
        try:
            user = qs.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # --- 2. Self-deletion guard ---
        if user.id == request.user.id:
            return Response(
                {'error': 'You cannot delete your own account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        caller_is_super = bool(request.user and request.user.role == UserRole.SUPER_ADMIN)

        # --- 3. Super Admin & Hierarchy Deletion Guards ---
        if user.role == UserRole.SUPER_ADMIN:
            if not caller_is_super:
                return Response({'error': 'Only Super Administrators can delete a Super Admin account.'}, status=status.HTTP_403_FORBIDDEN)
            active_super_count = User.objects.filter(role=UserRole.SUPER_ADMIN, is_active=True).exclude(pk=user.pk).count()
            if active_super_count < 1:
                return Response({'error': 'Cannot delete the last active Super Administrator. At least one active Super Admin must exist.'}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.role == UserRole.SYS_ADMIN and not caller_is_super:
            if user.role in [UserRole.SUPER_ADMIN, UserRole.MAIN_OFFICER]:
                return Response({'error': f"System Administrators cannot delete '{user.role}' accounts."}, status=status.HTTP_403_FORBIDDEN)

        # --- 4. Active assignment block ---
        from apps.assignments.models import Assignment
        if Assignment.objects.filter(constable=user, is_active=True).exists():
            return Response(
                {
                    'error': (
                        'This officer has an active GPID assignment. '
                        'Reassign or end the assignment before deleting this account.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- 5. Capture identity snapshot for audit record BEFORE deletion ---
        full_name = f"{user.first_name} {user.last_name}".strip() or user.username
        audit_details = {
            'username': user.username,
            'full_name': full_name,
            'police_id': user.police_id or '',
            'role': user.role,
            'police_station': user.police_station or '',
            'deleted_by': request.user.username,
        }

        # --- 6. Atomic hard deletion with ProtectedError guard ---
        try:
            with transaction.atomic():
                from apps.audit.models import AuditEvent
                ip = (
                    request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                    or request.META.get('REMOTE_ADDR')
                ) or None
                AuditEvent.objects.create(
                    actor=request.user,
                    action='USER_DELETED',
                    target_model='User',
                    target_id=str(user.id),
                    details=audit_details,
                    ip_address=ip,
                )
                user.delete()
        except Exception as exc:
            return Response(
                {
                    'error': (
                        'Account deletion failed due to protected historical records. '
                        'The account and all associated operational history have been preserved. '
                        f'Detail: {type(exc).__name__}'
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response({'message': f"User account '{full_name}' ({audit_details['username']}) deleted successfully."})


class RoleTemplateListView(APIView):
    """
    List role templates and default capabilities.
    Strictly restricted to SUPER_ADMIN.
    Non-superadmin accounts receive HTTP 403 Forbidden.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        templates_by_role = {t.role: t for t in RolePermissionTemplate.objects.all()}
        results = []
        for role_code, role_label in UserRole.choices:
            template = templates_by_role.get(role_code)
            if template:
                serializer = RolePermissionTemplateSerializer(template)
                results.append(serializer.data)
            else:
                user_count = User.objects.filter(role=role_code).count()
                results.append({
                    'id': None,
                    'role': role_code,
                    'role_display': role_label,
                    'description': '',
                    'permissions': ROLE_DEFAULT_PERMISSIONS.get(role_code, []),
                    'user_count': user_count,
                    'updated_at': None,
                    'updated_by_name': '',
                })

        return Response({
            'results': results,
            'canonical_permissions': CANONICAL_PERMISSIONS,
        })


class RoleTemplateDetailView(APIView):
    """
    Retrieve or update role default permissions template.
    Strictly restricted to SUPER_ADMIN for all HTTP methods (GET, PUT, PATCH).
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request, role):
        role_upper = role.upper()
        if role_upper not in UserRole.values:
            return Response({'error': f"Invalid operational role '{role}'."}, status=status.HTTP_404_NOT_FOUND)

        template = RolePermissionTemplate.objects.filter(role=role_upper).first()
        if not template:
            template = RolePermissionTemplate(
                role=role_upper,
                permissions=ROLE_DEFAULT_PERMISSIONS.get(role_upper, [])
            )
        serializer = RolePermissionTemplateSerializer(template)
        return Response(serializer.data)

    def put(self, request, role):
        return self._update_template(request, role)

    def patch(self, request, role):
        return self._update_template(request, role)

    def _update_template(self, request, role):
        role_upper = role.upper()
        if role_upper not in UserRole.values:
            return Response({'error': f"Invalid operational role '{role}'."}, status=status.HTTP_404_NOT_FOUND)

        raw_permissions = request.data.get('permissions')
        if hasattr(request.data, 'getlist') and not isinstance(raw_permissions, list):
            getlist_val = request.data.getlist('permissions')
            if getlist_val:
                raw_permissions = getlist_val

        if raw_permissions is None or not isinstance(raw_permissions, list):
            return Response({'error': 'Permissions must be provided as a list of strings.'}, status=status.HTTP_400_BAD_REQUEST)

        invalid_perms = [p for p in raw_permissions if p not in CANONICAL_PERMISSIONS]
        if invalid_perms:
            return Response(
                {'error': f"Invalid permission codename(s): {', '.join(invalid_perms)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        template, _ = RolePermissionTemplate.objects.get_or_create(
            role=role_upper,
            defaults={'permissions': ROLE_DEFAULT_PERMISSIONS.get(role_upper, [])}
        )

        old_perms = set(template.permissions or [])
        new_perms = set(raw_permissions)

        added = sorted(list(new_perms - old_perms))
        removed = sorted(list(old_perms - new_perms))

        template.permissions = sorted(list(new_perms))
        if 'description' in request.data:
            template.description = str(request.data['description']).strip()
        template.updated_by = request.user
        template.save()

        affected_count = User.objects.filter(role=role_upper).count()

        # Audit logging: ROLE_TEMPLATE_UPDATED
        try:
            from apps.audit.models import AuditEvent
            ip = (
                request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                or request.META.get('REMOTE_ADDR')
            ) or None
            AuditEvent.objects.create(
                actor=request.user,
                action='ROLE_TEMPLATE_UPDATED',
                target_model='RolePermissionTemplate',
                target_id=role_upper,
                details={
                    'role': role_upper,
                    'added': added,
                    'removed': removed,
                    'permissions': template.permissions,
                    'affected_users_count': affected_count,
                },
                ip_address=ip,
            )
        except Exception:
            pass

        serializer = RolePermissionTemplateSerializer(template)
        resp_data = serializer.data
        resp_data['added'] = added
        resp_data['removed'] = removed
        resp_data['affected_users_count'] = affected_count
        resp_data['message'] = f"Default permissions for {template.get_role_display()} updated successfully."
        return Response(resp_data)

