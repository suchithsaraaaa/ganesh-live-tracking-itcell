from django.contrib.auth import authenticate, login, logout
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
        user = self.get_object(pk)
        if not user:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Do not allow deleting self
        if user.id == request.user.id:
            return Response({'error': 'Cannot disable your own administrative account.'}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = False
        user.save(update_fields=['is_active'])
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

        officers = []
        for user in qs:
            assigned_gpid = active_assignments.get(user.id)
            user.currently_assigned = assigned_gpid is not None
            user.assigned_gpid = assigned_gpid
            officers.append(user)

        serializer = AssignableOfficerSerializer(officers, many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })
