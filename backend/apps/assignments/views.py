from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Assignment
from .serializers import AssignmentSerializer, CreateAssignmentSerializer, HandoverSerializer
from common.permissions import IsStationOfficerOrAbove, filter_by_jurisdiction


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
            return qs.filter(constable=self.request.user)
        return filter_by_jurisdiction(qs, self.request.user, ps_field='idol__police_station', zone_field='idol__zone', division_field='idol__division')


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
