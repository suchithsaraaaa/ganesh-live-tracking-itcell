from django.contrib.auth import authenticate, login, logout
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({'error': 'Username and password required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_active:
                return Response({'error': 'Account is disabled.'}, status=status.HTTP_403_FORBIDDEN)
            login(request, user)
            return Response({
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'police_id': user.police_id,
                'zone': user.zone,
                'division': user.division,
                'police_station': user.police_station,
                'must_change_password': user.must_change_password,
            })
        return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'message': 'Logged out successfully.'})


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'police_id': user.police_id,
            'zone': user.zone,
            'division': user.division,
            'police_station': user.police_station,
            'must_change_password': user.must_change_password,
        })
