from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from common.permissions import CanManageUsers, CanAssignFieldOfficers
from .models import User, UserRole
from .serializers import (
    UserSerializer,
    UserCreateUpdateSerializer,
    AssignableOfficerSerializer
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
        qs = User.objects.all().order_by('-date_joined')

        role = request.query_params.get('role')
        if role and role.upper() in UserRole.values:
            qs = qs.filter(role=role.upper())

        is_active = request.query_params.get('is_active')
        if is_active is not None and is_active != '':
            qs = qs.filter(is_active=is_active.lower() in ('true', '1'))

        police_station = request.query_params.get('police_station')
        if police_station:
            qs = qs.filter(police_station__iexact=police_station)

        search = request.query_params.get('search')
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(police_id__icontains=search)
            )

        serializer = UserSerializer(qs, many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })

    def post(self, request):
        serializer = UserCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            _log_account_event(request, 'USER_CREATED', user)
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(APIView):
    """
    Retrieve, update, or disable individual users.
    Restricted to MAIN_OFFICER or users with manage_users capability.
    """
    permission_classes = [CanManageUsers]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserSerializer(user).data)

    def patch(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserCreateUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            updated_user = serializer.save()
            return Response(UserSerializer(updated_user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        # Soft-disable only via this method — true hard deletion is on UserDeleteView.
        user = self.get_object(pk)
        if not user:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if user.id == request.user.id:
            return Response({'error': 'Cannot disable your own administrative account.'}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = False
        user.save(update_fields=['is_active'])
        _log_account_event(request, 'USER_DISABLED', user)
        return Response({'message': f'User {user.username} has been disabled.'})


class UserToggleActiveView(APIView):
    """
    Quick toggle for user active/inactive state.
    """
    permission_classes = [CanManageUsers]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if user.id == request.user.id and user.is_active:
            return Response({'error': 'Cannot disable your own administrative account.'}, status=status.HTTP_400_BAD_REQUEST)

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
    - MAIN_OFFICER: city-wide
    - ACP: within ACP's zone/division
    - SHO: within SHO's police station
    Excludes phone numbers to protect officer privacy.
    """
    permission_classes = [CanAssignFieldOfficers]

    def get(self, request):
        caller = request.user
        qs = User.objects.filter(role=UserRole.CONSTABLE, is_active=True).order_by('police_station', 'username')

        # Jurisdiction filter
        if caller.role == UserRole.SHO:
            if caller.police_station:
                qs = qs.filter(police_station__iexact=caller.police_station)
            else:
                qs = qs.none()
        elif caller.role == UserRole.ACP:
            if caller.zone:
                qs = qs.filter(zone__iexact=caller.zone)
            elif caller.division:
                qs = qs.filter(division__iexact=caller.division)
            else:
                qs = qs.none()

        # Optional station filter if authorized
        requested_ps = request.query_params.get('police_station')
        if requested_ps:
            if caller.role == UserRole.SHO and caller.police_station.lower() != requested_ps.lower():
                return Response({'error': 'Cannot view officers outside your police station jurisdiction.'}, status=status.HTTP_403_FORBIDDEN)
            qs = qs.filter(police_station__iexact=requested_ps)

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

def _log_account_event(request, action: str, target_user: User) -> None:
    """Record an administrative account lifecycle event in the audit trail."""
    try:
        from apps.audit.models import AuditEvent
        ip = (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.META.get('REMOTE_ADDR')
        ) or None
        full_name = f"{target_user.first_name} {target_user.last_name}".strip() or target_user.username
        AuditEvent.objects.create(
            actor=request.user if request.user.is_authenticated else None,
            action=action,
            target_model='User',
            target_id=str(target_user.id),
            details={
                'username': target_user.username,
                'full_name': full_name,
                'police_id': target_user.police_id or '',
                'role': target_user.role,
                'police_station': target_user.police_station or '',
            },
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
        # --- 1. Target existence check ---
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # --- 2. Self-deletion guard ---
        if user.id == request.user.id:
            return Response(
                {'error': 'You cannot delete your own account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- 3. Active assignment block ---
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

        # --- 4. Capture identity snapshot for audit record BEFORE deletion ---
        full_name = f"{user.first_name} {user.last_name}".strip() or user.username
        audit_details = {
            'username': user.username,
            'full_name': full_name,
            'police_id': user.police_id or '',
            'role': user.role,
            'police_station': user.police_station or '',
            'deleted_by': request.user.username,
        }

        # --- 5. Atomic hard deletion with ProtectedError guard ---
        try:
            with transaction.atomic():
                # Write the audit record inside the transaction so a rollback
                # removes it too — we do NOT want a USER_DELETED entry when
                # deletion fails.
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
            # Catches ProtectedError, IntegrityError, or any other DB-level
            # protection. The transaction is rolled back; user record is intact.
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

