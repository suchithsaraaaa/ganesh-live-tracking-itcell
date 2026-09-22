from rest_framework import generics, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from .models import Idol, ProcessionState
from .serializers import IdolListSerializer, IdolDetailSerializer
from common.permissions import filter_by_jurisdiction
from apps.tracking.models import TrackingSession, LocationPoint, TrackingSessionStatus
from apps.tracking.views import get_connection_state


class DashboardStatsView(APIView):
    """
    High-level operational overview cards and active tracking markers.
    Enforces server-side jurisdiction.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = filter_by_jurisdiction(Idol.objects.all(), request.user)

        # Apply optional zone / PS filter
        zone = request.query_params.get('zone')
        if zone:
            qs = qs.filter(zone__iexact=zone)
        ps = request.query_params.get('police_station')
        if ps:
            qs = qs.filter(police_station__iexact=ps)

        # Operational KPIs
        total_idols = qs.count()
        counts_by_state = dict(
            qs.values_list('procession_state').annotate(c=Count('id'))
        )

        tracking_active = qs.filter(
            procession_state__in=[ProcessionState.TRACKING, ProcessionState.MOVING, ProcessionState.HOLDING]
        ).count()
        moving = counts_by_state.get(ProcessionState.MOVING, 0)
        holding = counts_by_state.get(ProcessionState.HOLDING, 0)
        at_visarjan = counts_by_state.get(ProcessionState.AT_VISARJAN, 0)
        immersion_completed = counts_by_state.get(ProcessionState.IMMERSION_COMPLETED, 0)
        not_started = counts_by_state.get(ProcessionState.NOT_STARTED, 0)

        unassigned_count = qs.filter(assignments__is_active=True).count()
        unassigned = total_idols - unassigned_count

        # Query active tracking sessions for map markers
        active_sessions = TrackingSession.objects.filter(
            assignment__idol__in=qs,
            status=TrackingSessionStatus.ACTIVE
        ).select_related('assignment__idol', 'assignment__constable')

        active_markers = []
        offline_or_degraded = 0

        for sess in active_sessions:
            idol = sess.assignment.idol
            constable = sess.assignment.constable
            latest_pt = sess.location_points.order_by('-recorded_at').first()

            conn_state = get_connection_state(latest_pt.recorded_at if latest_pt else None)
            if conn_state in ['DEGRADED', 'OFFLINE']:
                offline_or_degraded += 1

            if latest_pt:
                active_markers.append({
                    'id': idol.id,
                    'gpid': idol.gpid,
                    'idol_name': idol.name or idol.association_name or 'Idol',
                    'association_name': idol.association_name,
                    'zone': idol.zone,
                    'division': idol.division,
                    'police_station': idol.police_station,
                    'ps_code': idol.ps_code,
                    'procession_state': idol.procession_state,
                    'connection_state': conn_state,
                    'latitude': latest_pt.latitude,
                    'longitude': latest_pt.longitude,
                    'speed': latest_pt.speed,
                    'heading': latest_pt.heading,
                    'accuracy': latest_pt.accuracy,
                    'last_gps_timestamp': latest_pt.recorded_at,
                    'assigned_constable': {
                        'id': constable.id,
                        'name': constable.get_full_name() or constable.username,
                        'police_id': constable.police_id,
                        'phone_number': constable.phone_number
                    }
                })

        return Response({
            'kpis': {
                'total_idols': total_idols,
                'tracking_active': tracking_active,
                'moving': moving,
                'holding': holding,
                'at_visarjan': at_visarjan,
                'immersion_completed': immersion_completed,
                'not_started': not_started,
                'unassigned': max(0, unassigned),
                'offline_or_degraded': offline_or_degraded,
            },
            'active_markers_count': len(active_markers),
            'active_markers': active_markers
        })



class IdolListView(generics.ListAPIView):
    """
    List idols with server-side jurisdiction enforcement, search, and filtering.
    """
    serializer_class = IdolListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = [
        'gpid',
        'name',
        'association_name',
        'police_station',
        'zone',
        'division',
        'ref_no'
    ]

    def get_queryset(self):
        qs = Idol.objects.all()
        # Enforce server-side jurisdiction filter
        qs = filter_by_jurisdiction(qs, self.request.user)

        # Apply optional query params
        zone = self.request.query_params.get('zone')
        if zone:
            qs = qs.filter(zone__iexact=zone)

        division = self.request.query_params.get('division')
        if division:
            qs = qs.filter(division__iexact=division)

        ps = self.request.query_params.get('police_station')
        if ps:
            qs = qs.filter(police_station__iexact=ps)

        procession_state = self.request.query_params.get('procession_state')
        if procession_state:
            qs = qs.filter(procession_state=procession_state)

        return qs


class IdolDetailView(generics.RetrieveAPIView):
    """
    Retrieve single idol details with jurisdiction authorization.
    Lookup by GPID (authoritative) or database ID.
    """
    serializer_class = IdolDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        lookup = self.kwargs.get('lookup')
        qs = filter_by_jurisdiction(Idol.objects.all(), self.request.user)
        if lookup.isdigit():
            return generics.get_object_or_404(qs, id=int(lookup))
        return generics.get_object_or_404(qs, gpid__iexact=lookup)
