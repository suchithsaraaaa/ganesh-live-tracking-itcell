from datetime import datetime
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework import generics, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Idol, ProcessionState
from .serializers import IdolListSerializer, IdolDetailSerializer
from common.permissions import filter_by_jurisdiction
from apps.tracking.models import TrackingSession, LocationPoint, TrackingSessionStatus
from apps.tracking.views import get_connection_state


def get_height_classification(height):
    """
    Classifies idol height into operational bands:
    - GREEN: 15 <= height < 21 ft (15–20 ft band)
    - YELLOW: 21 <= height < 26 ft (21–25 ft band)
    - RED: height >= 26 ft (26+ ft band)
    - SUBTHRESHOLD: height < 15 ft (non-operational)
    """
    if height is None:
        return 'UNKNOWN'
    try:
        h = float(height)
    except (ValueError, TypeError):
        return 'UNKNOWN'

    if 15.0 <= h < 21.0:
        return 'GREEN'
    elif 21.0 <= h < 26.0:
        return 'YELLOW'
    elif h >= 26.0:
        return 'RED'
    return 'SUBTHRESHOLD'


def apply_idol_filters(qs, params, user=None, is_dashboard=False):
    """
    Applies unified operational filters to an Idol queryset:
    - Main Dashboard (is_dashboard=True):
      * Population rule: immersion_date = timezone.localdate() (Asia/Kolkata) across ALL heights.
      * No mandatory 15+ ft threshold.
      * Height filter is purely optional.
    - Non-dashboard views (is_dashboard=False):
      * Default rule: idol_height >= 15 (only bypassed for MAIN_OFFICER diagnostics).
    - Height buckets: below_15, 15_20, 21_25, above_25
    - Generic min_height / max_height
    - Immersions Today / exact immersion_date / immr_date alias
    - Zone, Division, Police Station, Procession State
    All conditions compose using AND logic.
    """
    from datetime import timedelta
    today = timezone.localdate()

    if is_dashboard:
        # 1. Main Dashboard population rule: TODAY'S Visarjan across ALL heights (Asia/Kolkata)
        immr_date = (params.get('immersion_date') or params.get('immr_date') or '').strip().lower()
        if immr_date in ['all', 'all_dates', 'all dates']:
            pass
        elif immr_date == 'tomorrow':
            qs = qs.filter(immersion_date=today + timedelta(days=1))
        elif immr_date and immr_date != 'today':
            try:
                target_date = datetime.strptime(immr_date, '%Y-%m-%d').date()
                qs = qs.filter(immersion_date=target_date)
            except ValueError:
                qs = qs.filter(immersion_date=today)
        else:
            # Default for Main Dashboard: today's Visarjan date in Asia/Kolkata
            qs = qs.filter(immersion_date=today)
    else:
        # 1. Operational 15+ ft threshold enforcement for non-dashboard views
        include_subthreshold = params.get('include_subthreshold', '').lower() in ['true', '1', 'yes']
        if not (include_subthreshold and user and getattr(user, 'role', None) == 'MAIN_OFFICER'):
            qs = qs.filter(idol_height__gte=15)

        # Date filtering for non-dashboard
        immersions_today = params.get('immersions_today', '').lower() in ['true', '1', 'yes']
        immr_date = params.get('immersion_date') or params.get('immr_date')
        if immersions_today or immr_date == 'today':
            qs = qs.filter(immersion_date=today)
        elif immr_date:
            try:
                target_date = datetime.strptime(immr_date.strip(), '%Y-%m-%d').date()
                qs = qs.filter(immersion_date=target_date)
            except ValueError:
                pass

    # 2. Height bucket filtering (applicable to both dashboard and non-dashboard)
    height_bucket = params.get('height_bucket')
    if height_bucket and height_bucket.upper() != 'ALL':
        hb = height_bucket.lower().strip()
        if hb in ['below_15', 'below-15', 'under_15', '<15', 'subthreshold']:
            qs = qs.filter(Q(idol_height__lt=15) | Q(idol_height__isnull=True))
        elif hb in ['15_20', '15-20', 'green']:
            qs = qs.filter(idol_height__gte=15, idol_height__lt=21)
        elif hb in ['21_25', '21-25', 'yellow']:
            qs = qs.filter(idol_height__gte=21, idol_height__lt=26)
        elif hb in ['above_25', '26_plus', '26+', 'red']:
            qs = qs.filter(idol_height__gte=26)

    # 3. Generic min / max height
    min_h = params.get('min_height')
    if min_h:
        try:
            qs = qs.filter(idol_height__gte=float(min_h))
        except ValueError:
            pass

    max_h = params.get('max_height')
    if max_h:
        try:
            qs = qs.filter(idol_height__lte=float(max_h))
        except ValueError:
            pass

    # 4. Jurisdiction / Location filters
    zone = params.get('zone')
    if zone and zone != 'All Zones':
        qs = qs.filter(zone__iexact=zone)

    division = params.get('division')
    if division:
        qs = qs.filter(division__iexact=division)

    ps = params.get('police_station')
    if ps:
        qs = qs.filter(police_station__iexact=ps)

    # 5. Procession state filter
    procession_state = params.get('procession_state')
    if procession_state and procession_state != 'ALL':
        qs = qs.filter(procession_state=procession_state)

    return qs


class DashboardStatsView(APIView):
    """
    High-level operational overview cards and active tracking markers.
    Main Dashboard population: TODAY'S VISARJAN GPIDs across ALL HEIGHTS.
    Enforces server-side jurisdiction and One GPID = One Map Marker.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = filter_by_jurisdiction(Idol.objects.all(), request.user)
        qs = apply_idol_filters(qs, request.query_params, request.user, is_dashboard=True)

        # Operational KPIs (all evaluated on today's complete population)
        total_idols = qs.count()
        today = timezone.localdate()
        immersions_today_count = qs.filter(immersion_date=today).count()

        counts_by_state = dict(
            qs.values_list('procession_state').annotate(c=Count('id'))
        )

        tracking_active = (
            counts_by_state.get(ProcessionState.TRACKING, 0) +
            counts_by_state.get(ProcessionState.MOVING, 0) +
            counts_by_state.get(ProcessionState.HOLDING, 0)
        )
        moving = counts_by_state.get(ProcessionState.MOVING, 0)
        holding = counts_by_state.get(ProcessionState.HOLDING, 0)
        at_visarjan = counts_by_state.get(ProcessionState.AT_VISARJAN, 0)
        immersion_completed = counts_by_state.get(ProcessionState.IMMERSION_COMPLETED, 0)
        not_started = counts_by_state.get(ProcessionState.NOT_STARTED, 0)

        # Distinct assigned count (prevents duplicate joins)
        assigned_count = qs.filter(assignments__is_active=True).distinct().count()
        unassigned = max(0, total_idols - assigned_count)

        # Height distribution counts for current eligible query in a single query
        height_aggs = qs.aggregate(
            h_below_15=Count('id', filter=Q(idol_height__lt=15) | Q(idol_height__isnull=True)),
            h_15_20=Count('id', filter=Q(idol_height__gte=15, idol_height__lt=21)),
            h_21_25=Count('id', filter=Q(idol_height__gte=21, idol_height__lt=26)),
            h_26_plus=Count('id', filter=Q(idol_height__gte=26)),
        )
        h_below_15 = height_aggs['h_below_15'] or 0
        h_15_20 = height_aggs['h_15_20'] or 0
        h_21_25 = height_aggs['h_21_25'] or 0
        h_26_plus = height_aggs['h_26_plus'] or 0

        # Authoritative Zone-wise breakdown across today's complete GPID population
        zone_aggregates = list(
            qs.values('zone').annotate(
                total=Count('id'),
                active=Count('id', filter=Q(procession_state=ProcessionState.MOVING)),
                holding=Count('id', filter=Q(procession_state=ProcessionState.HOLDING)),
                immersed=Count('id', filter=Q(procession_state=ProcessionState.IMMERSION_COMPLETED)),
            ).order_by('-total')
        )

        from apps.assignments.models import Assignment
        active_assignments_by_idol = {
            a.idol_id: a.constable
            for a in Assignment.objects.filter(idol__in=qs, is_active=True).select_related('constable')
        }

        # Query active tracking sessions for map markers (priority live telemetry)
        active_sessions = list(TrackingSession.objects.filter(
            assignment__idol__in=qs,
            status=TrackingSessionStatus.ACTIVE
        ).select_related('assignment__idol', 'assignment__constable').order_by('-started_at'))

        # Batch-fetch latest location points for all active sessions to eliminate N+1 queries
        active_session_ids = [s.id for s in active_sessions]
        latest_pts_by_session = {}
        if active_session_ids:
            try:
                # PostgreSQL high-performance indexed query
                for lp in LocationPoint.objects.filter(session_id__in=active_session_ids).order_by('session_id', '-recorded_at').distinct('session_id'):
                    latest_pts_by_session[lp.session_id] = lp
            except Exception:
                # SQLite fallback during local development / testing
                for lp in LocationPoint.objects.filter(session_id__in=active_session_ids).order_by('recorded_at'):
                    latest_pts_by_session[lp.session_id] = lp

        active_markers = []
        seen_gpids = set()
        offline_or_degraded = 0

        can_view_contact = request.user.role in ['MAIN_OFFICER', 'ACP', 'SHO']

        # 1. Process active tracking sessions (live telemetry priority)
        for sess in active_sessions:
            idol = sess.assignment.idol
            if idol.gpid in seen_gpids:
                continue
            seen_gpids.add(idol.gpid)

            constable = sess.assignment.constable
            latest_pt = latest_pts_by_session.get(sess.id)

            conn_state = get_connection_state(latest_pt.recorded_at if latest_pt else None)
            if conn_state in ['DEGRADED', 'OFFLINE']:
                offline_or_degraded += 1

            if latest_pt:
                height_val = float(idol.idol_height) if idol.idol_height is not None else None
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
                    'is_origin_marker': False,
                    'latitude': latest_pt.latitude,
                    'longitude': latest_pt.longitude,
                    'speed': latest_pt.speed,
                    'heading': latest_pt.heading,
                    'accuracy': latest_pt.accuracy,
                    'last_gps_timestamp': latest_pt.recorded_at,
                    'idol_height': height_val,
                    'height_classification': get_height_classification(height_val),
                    'immersion_date': str(idol.immersion_date) if idol.immersion_date else None,
                    'origin_location': idol.address or idol.instal_street or idol.instal_village or 'N/A',
                    'geocoding_confidence': idol.geocoding_confidence,
                    'geocoding_result_type': idol.geocoding_result_type,
                    'resolved_address': idol.resolved_address,
                    'start_gate_eligible': idol.geocoding_confidence in ['EXACT', 'HIGH'],
                    'destination': idol.river_name or idol.lake_type or 'Visarjan Site',
                    'owner_name': idol.name or idol.association_name or 'N/A',
                    'assigned_constable': {
                        'id': constable.id,
                        'name': constable.get_full_name() or constable.username,
                        'police_id': constable.police_id,
                        'phone_number': constable.phone_number if can_view_contact else None
                    }
                })
            elif idol.latitude is not None and idol.longitude is not None:
                height_val = float(idol.idol_height) if idol.idol_height is not None else None
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
                    'connection_state': 'OFFLINE',
                    'is_origin_marker': True,
                    'latitude': float(idol.latitude),
                    'longitude': float(idol.longitude),
                    'speed': None,
                    'heading': None,
                    'accuracy': None,
                    'last_gps_timestamp': idol.updated_at,
                    'idol_height': height_val,
                    'height_classification': get_height_classification(height_val),
                    'immersion_date': str(idol.immersion_date) if idol.immersion_date else None,
                    'origin_location': idol.address or idol.instal_street or idol.instal_village or 'N/A',
                    'geocoding_confidence': idol.geocoding_confidence,
                    'geocoding_result_type': idol.geocoding_result_type,
                    'resolved_address': idol.resolved_address,
                    'start_gate_eligible': idol.geocoding_confidence in ['EXACT', 'HIGH'],
                    'destination': idol.river_name or idol.lake_type or 'Visarjan Site',
                    'owner_name': idol.name or idol.association_name or 'N/A',
                    'assigned_constable': {
                        'id': constable.id,
                        'name': constable.get_full_name() or constable.username,
                        'police_id': constable.police_id,
                        'phone_number': constable.phone_number if can_view_contact else None
                    }
                })

        # 2. Add all other eligible idols with valid geocoded origin coordinates (Rule 17)
        for idol in qs.filter(latitude__isnull=False, longitude__isnull=False):
            if idol.gpid in seen_gpids:
                continue
            seen_gpids.add(idol.gpid)

            constable = active_assignments_by_idol.get(idol.id)
            height_val = float(idol.idol_height) if idol.idol_height is not None else None

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
                'connection_state': 'OFFLINE',
                'is_origin_marker': True,
                'latitude': float(idol.latitude),
                'longitude': float(idol.longitude),
                'speed': None,
                'heading': None,
                'accuracy': None,
                'last_gps_timestamp': idol.updated_at,
                'idol_height': height_val,
                'height_classification': get_height_classification(height_val),
                'immersion_date': str(idol.immersion_date) if idol.immersion_date else None,
                'origin_location': idol.address or idol.instal_street or idol.instal_village or 'N/A',
                'geocoding_confidence': idol.geocoding_confidence,
                'geocoding_result_type': idol.geocoding_result_type,
                'resolved_address': idol.resolved_address,
                'start_gate_eligible': idol.geocoding_confidence in ['EXACT', 'HIGH'],
                'destination': idol.river_name or idol.lake_type or 'Visarjan Site',
                'owner_name': idol.name or idol.association_name or 'N/A',
                'assigned_constable': {
                    'id': constable.id,
                    'name': constable.get_full_name() or constable.username,
                    'police_id': constable.police_id,
                    'phone_number': constable.phone_number if can_view_contact else None
                } if constable else None
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
                'unassigned': unassigned,
                'offline_or_degraded': offline_or_degraded,
                'immersions_today': immersions_today_count,
                'h_below_15': h_below_15,
                'h_15_20': h_15_20,
                'h_21_25': h_21_25,
                'h_26_plus': h_26_plus,
                'zone_stats': zone_aggregates,
            },
            'zone_stats': zone_aggregates,
            'active_markers_count': len(active_markers),
            'active_markers': active_markers
        })


class IdolListView(generics.ListAPIView):
    """
    List idols with server-side jurisdiction enforcement, search, and filtering.
    Defaults strictly to operational idols (>= 15 ft).
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
        # Enforce operational threshold and composition filters
        qs = apply_idol_filters(qs, self.request.query_params, self.request.user)
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
