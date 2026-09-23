from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Assignment
from .serializers import AssignmentSerializer, CreateAssignmentSerializer, HandoverSerializer
from common.permissions import IsStationOfficerOrAbove, CanAssignFieldOfficers, filter_by_jurisdiction


class AssignmentListView(generics.ListAPIView):
    """
    List assignments with server-side jurisdiction filter.
    """
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Assignment.objects.select_related('idol', 'constable', 'assigned_by').all()
        # Filter through idol jurisdiction
        if self.request.user.role == 'CONSTABLE':
            qs = qs.filter(constable=self.request.user)
        else:
            qs = filter_by_jurisdiction(qs, self.request.user, ps_field='idol__police_station', zone_field='idol__zone', division_field='idol__division')

        is_active_param = self.request.query_params.get('is_active')
        if is_active_param is not None:
            if is_active_param.lower() in ('true', '1'):
                qs = qs.filter(is_active=True)
            elif is_active_param.lower() in ('false', '0'):
                qs = qs.filter(is_active=False)

        constable_id = self.request.query_params.get('constable_id')
        if constable_id:
            qs = qs.filter(constable_id=constable_id)

        return qs


class CreateAssignmentView(APIView):
    """
    Create a new active assignment. Accessible to Station Officers (SHO) and above.
    """
    permission_classes = [IsStationOfficerOrAbove]

    def post(self, request):
        serializer = CreateAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        idol = serializer.validated_data['idol_obj']
        constable = serializer.validated_data['constable_obj']

        assignment = Assignment.assign_constable(
            idol=idol,
            constable=constable,
            assigned_by=request.user
        )

        return Response(
            AssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED
        )


class HandoverAssignmentView(APIView):
    """
    Perform an atomic handover of an active assignment to a new constable.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            assignment = Assignment.objects.get(pk=pk, is_active=True)
        except Assignment.DoesNotExist:
            return Response(
                {'error': 'Active assignment not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Authorization: either the assigned constable themselves or station officer
        if request.user != assignment.constable and request.user.role not in ['MAIN_OFFICER', 'ACP', 'SHO']:
            return Response(
                {'error': 'You do not have permission to handover this duty.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = HandoverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_constable = serializer.validated_data['new_constable_id']
        reason = serializer.validated_data.get('reason', '')

        new_assignment = assignment.handover_to_constable(
            new_constable=new_constable,
            reason=reason,
            actor=request.user
        )

        return Response({
            'message': f"Duty successfully handed over to {new_constable.username}.",
            'previous_assignment_id': assignment.id,
            'new_assignment': AssignmentSerializer(new_assignment).data
        }, status=status.HTTP_200_OK)


class CurrentAssignmentView(APIView):
    """
    Returns active assigned idol for logged-in constable (Android APK / mobile client endpoint).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        assignment = Assignment.objects.select_related('idol').filter(
            constable=request.user,
            is_active=True
        ).first()

        if not assignment:
            return Response({'active_assignment': None})

        return Response({
            'active_assignment': {
                'assignment_id': assignment.id,
                'gpid': assignment.idol.gpid,
                'idol_id': assignment.idol.id,
                'name': assignment.idol.name,
                'association_name': assignment.idol.association_name,
                'police_station': assignment.idol.police_station,
                'zone': assignment.idol.zone,
                'procession_state': assignment.idol.procession_state,
                'started_at': assignment.started_at,
            }
        })


class EndAssignmentView(APIView):
    """
    Safely ends an active assignment without deleting historical records.
    Enforces RBAC/jurisdiction: restricted to Station Officer or above.
    Enforces active tracking session safety: if an active TrackingSession exists,
    blocks ending with 400 and clear explanation to stop the procession first.
    """
    permission_classes = [CanAssignFieldOfficers]

    def post(self, request, pk):
        try:
            assignment = Assignment.objects.select_related('idol', 'constable').get(pk=pk)
        except Assignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not assignment.is_active:
            return Response(
                {'error': 'Assignment is already ended.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Enforce server-side jurisdiction
        user = request.user
        if not (user.is_superuser or user.role == 'MAIN_OFFICER'):
            if user.role == 'ACP':
                if user.zone and assignment.idol.zone and assignment.idol.zone.lower() != user.zone.lower():
                    return Response(
                        {'error': 'You do not have jurisdiction to end assignments in this zone.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            elif user.role == 'SHO':
                if user.police_station and assignment.idol.police_station and assignment.idol.police_station.lower() != user.police_station.lower():
                    return Response(
                        {'error': 'You do not have jurisdiction to end assignments in this police station.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        # Active tracking session safety check
        from apps.tracking.models import TrackingSession, TrackingSessionStatus
        active_session = TrackingSession.objects.filter(
            assignment=assignment,
            status__in=[TrackingSessionStatus.ACTIVE, TrackingSessionStatus.STARTED]
        ).first()

        if active_session:
            return Response(
                {
                    'error': 'This officer currently has an active tracking session. Stop the procession before ending the assignment.',
                    'has_active_tracking': True,
                    'tracking_session_id': active_session.id
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')
        ended_assignment = assignment.end_assignment(actor=request.user, reason=reason)

        return Response(
            {
                'message': 'Assignment ended successfully.',
                'assignment': AssignmentSerializer(ended_assignment).data
            },
            status=status.HTTP_200_OK
        )
