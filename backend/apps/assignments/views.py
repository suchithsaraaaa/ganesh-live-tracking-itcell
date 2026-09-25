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
    Enforces the authoritative 15 FT+ eligibility rule.
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

        # Optional Zone & Police Station filters
        zone = self.request.query_params.get('zone')
        if zone and zone not in ['All Zones', 'all', '']:
            from common.zones import zone_filter_q
            qs = qs.filter(zone_filter_q('idol__zone', zone.strip()))

        ps = self.request.query_params.get('police_station')
        if ps and ps not in ['All Police Stations', 'all', '']:
            from common.zones import ps_filter_q
            qs = qs.filter(ps_filter_q('idol__police_station', ps.strip()))

        # Optional height bucket filter
        hb = self.request.query_params.get('height_bucket')
        if hb and hb not in ['All Heights', 'all', 'all_heights', '']:
            hb_clean = hb.lower().strip()
            from django.db.models import Q
            if hb_clean in ['below_15', 'below-15', 'under_15', '<15', 'subthreshold']:
                qs = qs.filter(Q(idol__idol_height__lt=15) | Q(idol__idol_height__isnull=True))
            elif hb_clean in ['15_20', '15-20', 'green']:
                qs = qs.filter(idol__idol_height__gte=15, idol__idol_height__lte=20)
            elif hb_clean in ['21_25', '21-25', 'yellow']:
                qs = qs.filter(idol__idol_height__gte=21, idol__idol_height__lte=25)
            elif hb_clean in ['26_plus', '26+', 'above_25', 'red']:
                qs = qs.filter(idol__idol_height__gte=26)
            elif hb_clean in ['all_15_plus', '15_plus', '15+']:
                qs = qs.filter(idol__idol_height__gte=15)

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
    permission_classes = [CanAssignFieldOfficers]

    def post(self, request):
        serializer = CreateAssignmentSerializer(data=request.data, context={'request': request})
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
    Authorized ADMIN (MAIN_OFFICER or superuser) can force-end assignments even
    when active tracking exists, safely terminating the tracking session atomically.
    Non-admin officers (ACP/SHO) can only end assignments without active tracking sessions.
    """
    permission_classes = [CanAssignFieldOfficers]

    def post(self, request, pk):
        from django.db import transaction
        from apps.tracking.models import TrackingSession, TrackingSessionStatus

        with transaction.atomic():
            try:
                assignment = Assignment.objects.select_for_update().get(pk=pk)
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
            from common.permissions import check_user_jurisdiction_over_idol
            allowed, err_msg = check_user_jurisdiction_over_idol(user, assignment.idol)
            if not allowed:
                return Response(
                    {'error': err_msg or 'Permission denied.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Determine administrative privilege for force-ending assignments with active tracking
            is_admin = bool(
                user.is_superuser
                or user.role in ['SUPER_ADMIN', 'MAIN_OFFICER', 'SYS_ADMIN']
            )

            # Active tracking session safety check
            active_session = TrackingSession.objects.filter(
                assignment=assignment,
                status__in=[TrackingSessionStatus.ACTIVE, TrackingSessionStatus.STARTED]
            ).first()

            if active_session and not is_admin:
                return Response(
                    {
                        'error': 'Administrative privilege required to force-end an assignment with an active tracking session. Stop the procession before ending the assignment.',
                        'has_active_tracking': True,
                        'tracking_session_id': active_session.id
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            reason = request.data.get('reason', '')
            ended_assignment = assignment.end_assignment(
                actor=request.user,
                reason=reason,
                terminate_tracking=True
            )

            tracking_terminated = bool(active_session) or getattr(ended_assignment, '_tracking_terminated', False)
            msg = 'Assignment force-ended and active tracking terminated successfully.' if tracking_terminated else 'Assignment ended successfully.'
            return Response(
                {
                    'message': msg,
                    'assignment': AssignmentSerializer(ended_assignment).data,
                    'tracking_terminated': tracking_terminated,
                },
                status=status.HTTP_200_OK
            )


class AssignableIdolRegistryView(APIView):
    """
    Dedicated operational endpoint for the Officer Assignment page.
    Enforces the authoritative 15 FT+ eligibility rule, server-side jurisdiction,
    and hierarchical cascading filters with strict AND logic.
    Returns paginated GPID records with embedded active assignments and summary KPIs.
    """
    permission_classes = [CanAssignFieldOfficers]

    def get(self, request):
        from apps.idols.models import Idol
        from apps.tracking.models import TrackingSession, TrackingSessionStatus
        from apps.tracking.views import get_connection_state
        from rest_framework.pagination import PageNumberPagination
        from django.db.models import Q, Count
        from .serializers import AssignableIdolRegistrySerializer

        # Rule 1 & 29: Base population: ALL authoritative GPIDs in the registry
        qs = Idol.objects.all()

        # Rule 30: Enforce server-side jurisdiction
        qs = filter_by_jurisdiction(qs, request.user)

        # 1. Zone filter
        zone = request.query_params.get('zone')
        if zone and zone not in ['All Zones', 'all', '']:
            from common.zones import zone_filter_q
            qs = qs.filter(zone_filter_q('zone', zone.strip()))

        # 2. Police Station filter
        ps = request.query_params.get('police_station')
        if ps and ps not in ['All Police Stations', 'all', '']:
            from common.zones import ps_filter_q
            qs = qs.filter(ps_filter_q('police_station', ps.strip()))

        # 3. Visarjan Date filter (AND composition with Asia/Kolkata local date)
        visarjan_date = request.query_params.get('visarjan_date')
        if visarjan_date and visarjan_date not in ['All Dates', 'all', '']:
            vdate_clean = visarjan_date.lower().strip()
            from datetime import timedelta, datetime
            from django.utils import timezone
            today = timezone.localdate()
            if vdate_clean == 'today':
                qs = qs.filter(immersion_date=today)
            elif vdate_clean == 'tomorrow':
                qs = qs.filter(immersion_date=today + timedelta(days=1))
            else:
                try:
                    target_date = datetime.strptime(vdate_clean, '%Y-%m-%d').date()
                    qs = qs.filter(immersion_date=target_date)
                except ValueError:
                    pass

        # 4. Secondary search (respects all active filters)
        search = request.query_params.get('search')
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(gpid__icontains=search) |
                Q(name__icontains=search) |
                Q(association_name__icontains=search) |
                Q(police_station__icontains=search)
            )

        # 5. Assignment status filter (AND composition)
        assignment_status = request.query_params.get('assignment_status')
        if assignment_status and assignment_status.lower() != 'all':
            astat = assignment_status.lower().strip()
            if astat == 'assigned':
                qs = qs.filter(assignments__is_active=True).distinct()
            elif astat == 'unassigned':
                qs = qs.exclude(assignments__is_active=True)

        # Base eligible queryset: ALL eligible idols in the active scope (jurisdiction, zone, PS, date, search, status)
        base_eligible_qs = qs

        # Authoritative summary KPIs computed on this entire eligible set (does NOT zero out other height categories)
        total_eligible = base_eligible_qs.count()
        height_aggs = base_eligible_qs.aggregate(
            count_below_15=Count('id', filter=Q(idol_height__lt=15) | Q(idol_height__isnull=True)),
            count_15_20=Count('id', filter=Q(idol_height__gte=15, idol_height__lte=20)),
            count_21_25=Count('id', filter=Q(idol_height__gte=21, idol_height__lte=25)),
            count_26_plus=Count('id', filter=Q(idol_height__gte=26)),
        )
        count_below_15 = height_aggs['count_below_15'] or 0
        count_15_20 = height_aggs['count_15_20'] or 0
        count_21_25 = height_aggs['count_21_25'] or 0
        count_26_plus = height_aggs['count_26_plus'] or 0

        if assignment_status and assignment_status.lower().strip() == 'assigned':
            assigned_count = total_eligible
            unassigned_count = 0
        elif assignment_status and assignment_status.lower().strip() == 'unassigned':
            assigned_count = 0
            unassigned_count = total_eligible
        else:
            assigned_count = base_eligible_qs.filter(assignments__is_active=True).distinct().count()
            unassigned_count = max(0, total_eligible - assigned_count)

        # 6. Optional height bucket filter applied to the paginated record set
        hb = request.query_params.get('height_bucket')
        if hb and hb not in ['All Heights', 'all', 'all_heights', '']:
            hb_clean = hb.lower().strip()
            if hb_clean in ['below_15', 'below-15', 'under_15', '<15', 'subthreshold']:
                qs = qs.filter(Q(idol_height__lt=15) | Q(idol_height__isnull=True))
            elif hb_clean in ['15_20', '15-20', 'green']:
                qs = qs.filter(idol_height__gte=15, idol_height__lte=20)
            elif hb_clean in ['21_25', '21-25', 'yellow']:
                qs = qs.filter(idol_height__gte=21, idol_height__lte=25)
            elif hb_clean in ['26_plus', '26+', 'above_25', 'red']:
                qs = qs.filter(idol_height__gte=26)
            elif hb_clean in ['all_15_plus', '15_plus', '15+']:
                qs = qs.filter(idol_height__gte=15)

        # Rule 12: Operational sorting (Zone -> Police Station -> Height -> GPID)
        ordering = request.query_params.get('ordering')
        if ordering:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by('zone', 'police_station', '-idol_height', 'gpid')

        # Rule 31: Server-side pagination (default 25, max 100)
        paginator = PageNumberPagination()
        try:
            page_size = int(request.query_params.get('page_size', 25))
            paginator.page_size = max(1, min(page_size, 100))
        except ValueError:
            paginator.page_size = 25

        page_records = paginator.paginate_queryset(qs, request)

        # Batch lookup active assignments and tracking sessions for current page to prevent N+1 queries
        page_idol_ids = [idol.id for idol in page_records]
        active_assignments = {
            a.idol_id: a
            for a in Assignment.objects.filter(
                idol_id__in=page_idol_ids,
                is_active=True
            ).select_related('constable')
        }

        active_sessions = {
            s.assignment.idol_id: s
            for s in TrackingSession.objects.filter(
                assignment__idol_id__in=page_idol_ids,
                status=TrackingSessionStatus.ACTIVE
            ).select_related('assignment')
        }

        active_sessions_map = {}
        for idol_id, sess in active_sessions.items():
            latest_pt = sess.location_points.order_by('-recorded_at').first()
            active_sessions_map[idol_id] = get_connection_state(latest_pt.recorded_at if latest_pt else None)

        serializer = AssignableIdolRegistrySerializer(
            page_records,
            many=True,
            context={
                'active_assignment_map': active_assignments,
                'active_sessions_map': active_sessions_map,
                'request': request,
            }
        )

        response_data = paginator.get_paginated_response(serializer.data).data
        response_data['summary'] = {
            'total_eligible': total_eligible,
            'count_below_15': count_below_15,
            'count_15_20': count_15_20,
            'count_21_25': count_21_25,
            'count_26_plus': count_26_plus,
            'assigned': assigned_count,
            'unassigned': unassigned_count,
        }
        return Response(response_data)


class AssignableIdolDetailView(APIView):
    """
    Detailed operational view for a single GPID in the assignment console.
    Returns authoritative procession timeline events from IdolEvent.
    """
    permission_classes = [CanAssignFieldOfficers]

    def get(self, request, gpid):
        from apps.idols.models import Idol
        from apps.tracking.models import IdolEvent, TrackingSession, TrackingSessionStatus
        from apps.tracking.views import get_connection_state
        from .serializers import AssignableIdolRegistrySerializer

        try:
            idol = Idol.objects.get(gpid__iexact=gpid.strip())
        except Idol.DoesNotExist:
            return Response({'error': f'Idol with GPID {gpid} not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Rule 30: Jurisdiction verification
        if not filter_by_jurisdiction(Idol.objects.filter(id=idol.id), request.user).exists():
            return Response({'error': 'You do not have jurisdiction to view this idol.'}, status=status.HTTP_403_FORBIDDEN)

        # Active assignment
        active_assignment = Assignment.objects.filter(idol=idol, is_active=True).select_related('constable', 'assigned_by').first()

        # Telemetry / connection state
        active_session = TrackingSession.objects.filter(
            assignment__idol=idol,
            status=TrackingSessionStatus.ACTIVE
        ).order_by('-started_at').first()

        latest_pt = active_session.location_points.order_by('-recorded_at').first() if active_session else None
        conn_state = get_connection_state(latest_pt.recorded_at if latest_pt else None) if active_session else 'OFFLINE'

        # Rule 27: Procession timeline events from authoritative IdolEvent records
        raw_events = IdolEvent.objects.filter(idol=idol).order_by('timestamp').select_related('actor')
        timeline_events = []
        for ev in raw_events:
            timeline_events.append({
                'id': ev.id,
                'event_type': ev.event_type,
                'label': ev.get_event_type_display() if hasattr(ev, 'get_event_type_display') else ev.event_type,
                'timestamp': ev.timestamp.isoformat() if ev.timestamp else None,
                'zone': ev.zone,
                'actor': ev.actor.get_full_name() or ev.actor.username if ev.actor else None,
                'metadata': ev.metadata or {},
            })

        # Milestone timestamps for the lifecycle stages
        milestones = {
            'assigned': active_assignment.started_at.isoformat() if active_assignment else None,
            'reached_site': None,
            'procession_started': None,
            'reached_visarjan': None,
            'visarjan_completed': None,
            'returned_to_origin': None,
            'admin_terminated': None,
        }

        for ev in raw_events:
            et = ev.event_type.upper()
            ts = ev.timestamp.isoformat() if ev.timestamp else None
            if et in ['PROCESSION_ASSIGNED', 'ASSIGNMENT_CREATED'] and not milestones['assigned']:
                milestones['assigned'] = ts
            elif et in ['SITE_REACHED', 'HOLDING_POINT_ENTERED'] and not milestones['reached_site']:
                milestones['reached_site'] = ts
            elif et in ['TRACKING_STARTED', 'PROCESSION_STARTED'] and not milestones['procession_started']:
                milestones['procession_started'] = ts
            elif et in ['VISARJAN_REACHED'] and not milestones['reached_visarjan']:
                milestones['reached_visarjan'] = ts
            elif et in ['IMMERSION_COMPLETED'] and not milestones['visarjan_completed']:
                milestones['visarjan_completed'] = ts
            elif et == 'RETURNED_TO_ORIGIN' and not milestones['returned_to_origin']:
                milestones['returned_to_origin'] = ts
            elif et in ['PROCESSION_ADMIN_TERMINATED', 'ASSIGNMENT_FORCE_ENDED'] and not milestones['admin_terminated']:
                milestones['admin_terminated'] = ts

        # Contact info: restricted to SHO, ACP, MAIN_OFFICER
        can_view_contact = request.user.role in ['MAIN_OFFICER', 'ACP', 'SHO'] or request.user.is_superuser
        raw_meta = idol.raw_metadata or {}

        height_val = float(idol.idol_height) if idol.idol_height is not None else 0.0
        height_bucket = 'below_15' if height_val < 15.0 else ('15-20' if 15.0 <= height_val <= 20.0 else ('21-25' if 21.0 <= height_val <= 25.0 else '26+'))
        height_class = 'SUBTHRESHOLD' if height_val < 15.0 else ('GREEN' if 15.0 <= height_val <= 20.0 else ('YELLOW' if 21.0 <= height_val <= 25.0 else 'RED'))

        return Response({
            'id': idol.id,
            'gpid': idol.gpid,
            'name': idol.name or idol.association_name or 'Idol',
            'association_name': idol.association_name,
            'idol_height': height_val,
            'height_bucket': height_bucket,
            'height_classification': height_class,
            'zone': idol.zone,
            'division': idol.division,
            'police_station': idol.police_station,
            'ps_code': idol.ps_code,
            'address': idol.address or idol.instal_street or 'N/A',
            'latitude': float(idol.latitude) if idol.latitude else None,
            'longitude': float(idol.longitude) if idol.longitude else None,
            'destination': idol.river_name or idol.lake_type or 'Visarjan Site',
            'visarjan_date': idol.immersion_date.isoformat() if idol.immersion_date else None,
            'immersion_date': idol.immersion_date.isoformat() if idol.immersion_date else None,
            'procession_state': idol.procession_state,
            'connection_state': conn_state,
            'last_gps_timestamp': latest_pt.recorded_at.isoformat() if latest_pt else (idol.updated_at.isoformat() if idol.updated_at else None),
            'assignment': {
                'id': active_assignment.id,
                'status': 'ACTIVE',
                'officer_name': active_assignment._constable_display(),
                'officer_id': active_assignment.constable_id,
                'police_id': (active_assignment.constable.police_id if active_assignment.constable else active_assignment.police_id_snapshot) or '',
                'police_station': (active_assignment.constable.police_station if active_assignment.constable else '') or '',
                'phone_number': active_assignment.constable.phone_number if (active_assignment.constable and can_view_contact) else None,
                'started_at': active_assignment.started_at.isoformat() if active_assignment.started_at else None,
            } if active_assignment else None,
            'contact_info': {
                'mobile_no': raw_meta.get('mobile_no', ''),
                'email': raw_meta.get('email', ''),
            } if can_view_contact else None,
            'milestones': milestones,
            'events': timeline_events,
        })


class AssignableEligibleOfficersView(APIView):
    """
    Authoritative endpoint returning eligible ground staff (Constables)
    strictly for a specific GPID context.
    Matches:
    - role == 'CONSTABLE'
    - is_active == True
    - police_station == idol.police_station
    - zone == idol.zone
    - No active assignment
    """
    permission_classes = [CanAssignFieldOfficers]

    def get(self, request, gpid):
        from apps.idols.models import Idol
        from apps.accounts.models import User
        from apps.accounts.serializers import AssignableOfficerSerializer

        try:
            idol = Idol.objects.get(gpid__iexact=gpid.strip())
        except Idol.DoesNotExist:
            return Response({'error': f'Idol with GPID {gpid} not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Jurisdiction check
        if not filter_by_jurisdiction(Idol.objects.filter(id=idol.id), request.user).exists():
            return Response({'error': 'You do not have jurisdiction over this idol.'}, status=status.HTTP_403_FORBIDDEN)


        # Currently assigned constables across the entire system
        active_assigned_constable_ids = set(
            Assignment.objects.filter(is_active=True).values_list('constable_id', flat=True)
        )

        # Constables matching idol's police station and zone
        from common.zones import zone_filter_q, ps_filter_q
        qs = User.objects.filter(
            role='CONSTABLE',
            is_active=True,
        ).filter(
            ps_filter_q('police_station', idol.police_station.strip()),
            zone_filter_q('zone', idol.zone.strip()),
        ).exclude(
            id__in=active_assigned_constable_ids
        ).order_by('first_name', 'last_name', 'username')

        officers_data = AssignableOfficerSerializer(qs, many=True).data

        # Current active assignment for this idol, if any
        current_assignment = Assignment.objects.filter(idol=idol, is_active=True).select_related('constable').first()
        assigned_officer_data = None
        if current_assignment and current_assignment.constable:
            assigned_officer_data = {
                'id': current_assignment.constable.id,
                'username': current_assignment.constable.username,
                'full_name': current_assignment.constable.get_full_name() or current_assignment.constable.username,
                'police_id': current_assignment.constable.police_id or current_assignment.police_id_snapshot or '',
                'phone_number': current_assignment.constable.phone_number or '',
                'police_station': current_assignment.constable.police_station or '',
                'zone': current_assignment.constable.zone or '',
                'started_at': current_assignment.started_at.isoformat() if current_assignment.started_at else None,
            }

        return Response({
            'gpid': idol.gpid,
            'idol_name': idol.name or idol.association_name or 'Idol',
            'zone': idol.zone,
            'police_station': idol.police_station,
            'visarjan_date': idol.immersion_date.isoformat() if idol.immersion_date else None,
            'is_already_assigned': current_assignment is not None,
            'current_assignment': assigned_officer_data,
            'total_eligible': len(officers_data),
            'officers': officers_data,
        })


class AssignmentExportExcelView(APIView):
    """
    Generates and downloads a formatted Excel (.xlsx) file containing
    all eligible officer assignments and operational details.
    Accessible to authorized Station Officers and Administrative Officers.
    """
    permission_classes = [CanAssignFieldOfficers]

    def get(self, request):
        import io
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from django.http import HttpResponse
        from django.utils import timezone
        from django.db.models import Q
        from apps.idols.models import Idol

        # Base population: all idols in jurisdiction
        qs = Idol.objects.all()
        qs = filter_by_jurisdiction(qs, request.user)

        # Filters
        zone = request.query_params.get('zone')
        if zone and zone not in ['All Zones', 'all', '']:
            from common.zones import zone_filter_q
            qs = qs.filter(zone_filter_q('zone', zone.strip()))

        ps = request.query_params.get('police_station')
        if ps and ps not in ['All Police Stations', 'all', '']:
            from common.zones import ps_filter_q
            qs = qs.filter(ps_filter_q('police_station', ps.strip()))

        hb = request.query_params.get('height_bucket')
        if hb and hb not in ['All Heights', 'all', 'all_heights', '']:
            hb_clean = hb.lower().strip()
            if hb_clean in ['below_15', 'below-15', 'under_15', '<15', 'subthreshold']:
                qs = qs.filter(Q(idol_height__lt=15) | Q(idol_height__isnull=True))
            elif hb_clean in ['15_20', '15-20', 'green']:
                qs = qs.filter(idol_height__gte=15, idol_height__lt=21)
            elif hb_clean in ['21_25', '21-25', 'yellow']:
                qs = qs.filter(idol_height__gte=21, idol_height__lt=26)
            elif hb_clean in ['26_plus', '26+', 'above_25', 'red']:
                qs = qs.filter(idol_height__gte=26)
            elif hb_clean in ['all_15_plus', '15_plus', '15+']:
                qs = qs.filter(idol_height__gte=15)

        # Visarjan Date filter (AND composition)
        visarjan_date = request.query_params.get('visarjan_date')
        if visarjan_date and visarjan_date not in ['All Dates', 'all', '']:
            vdate_clean = visarjan_date.lower().strip()
            from datetime import date, timedelta, datetime
            today = date.today()
            if vdate_clean == 'today':
                qs = qs.filter(immersion_date=today)
            elif vdate_clean == 'tomorrow':
                qs = qs.filter(immersion_date=today + timedelta(days=1))
            else:
                try:
                    target_date = datetime.strptime(vdate_clean, '%Y-%m-%d').date()
                    qs = qs.filter(immersion_date=target_date)
                except ValueError:
                    pass

        active_assigned_ids = set(
            Assignment.objects.filter(is_active=True, idol__in=qs).values_list('idol_id', flat=True)
        )

        assignment_status = request.query_params.get('assignment_status')
        if assignment_status and assignment_status.lower() != 'all':
            astat = assignment_status.lower().strip()
            if astat == 'assigned':
                qs = qs.filter(id__in=active_assigned_ids)
            elif astat == 'unassigned':
                qs = qs.exclude(id__in=active_assigned_ids)

        search = request.query_params.get('search')
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(gpid__icontains=search) |
                Q(name__icontains=search) |
                Q(association_name__icontains=search) |
                Q(police_station__icontains=search)
            )

        qs = qs.order_by('zone', 'police_station', '-idol_height', 'gpid')

        # Prefetch active assignments
        idol_ids = list(qs.values_list('id', flat=True))
        assignments_by_idol = {
            a.idol_id: a
            for a in Assignment.objects.filter(
                idol_id__in=idol_ids,
                is_active=True
            ).select_related('constable', 'assigned_by')
        }

        # Build Excel Workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Officer Assignments"

        # Department Title Header
        ws.merge_cells("A1:O1")
        title_cell = ws["A1"]
        title_cell.value = "HYDERABAD CITY POLICE — GANESH VISARJAN MONITORING SYSTEM"
        title_cell.font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
        title_cell.fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 28

        # Metadata Subheader
        ws.merge_cells("A2:O2")
        sub_cell = ws["A2"]
        filter_meta = f"Visarjan Date: {visarjan_date}" if visarjan_date and visarjan_date not in ['all', 'All Dates'] else "All Visarjan Dates"
        sub_cell.value = f"OFFICER ASSIGNMENT & PROCESSION REGISTRY (15 FT+ IDOLS) | {filter_meta} | Exported on: {timezone.now().strftime('%d-%b-%Y %H:%M:%S IST')} | Records: {len(idol_ids)}"
        sub_cell.font = Font(name="Calibri", size=10, italic=True, color="94A3B8")
        sub_cell.fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        sub_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[2].height = 20

        # Column Headers
        headers = [
            "S.No",
            "GPID",
            "Pandal / Idol Name",
            "Height (FT)",
            "Height Category",
            "Visarjan Date",
            "Zone",
            "Police Station",
            "Assignment Status",
            "Assigned Officer",
            "Police ID",
            "Officer Station",
            "Assignment Started",
            "Procession State",
            "Address / Origin",
        ]
        ws.append([]) # row 3 is blank spacer
        ws.append(headers) # row 4
        ws.row_dimensions[4].height = 24

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="D97706", end_color="D97706", fill_type="solid")
        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=4, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border

        # Populate rows
        alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        normal_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

        row_num = 5
        can_view_contact = request.user.role in ['MAIN_OFFICER', 'ACP', 'SHO'] or request.user.is_superuser

        for idx, idol in enumerate(qs, start=1):
            assign = assignments_by_idol.get(idol.id)
            h_val = float(idol.idol_height) if idol.idol_height else 0.0
            category = "15–20 FT" if 15.0 <= h_val < 21.0 else ("21–25 FT" if 21.0 <= h_val < 26.0 else "26 FT+")

            officer_name = assign._constable_display() if assign else "—"
            police_id = (assign.constable.police_id if assign and assign.constable else (assign.police_id_snapshot if assign else "")) or "—"
            officer_ps = (assign.constable.police_station if assign and assign.constable else "") or "—"
            started_at = assign.started_at.strftime('%d-%b-%Y %H:%M') if assign and assign.started_at else "—"
            assignment_status_str = "ASSIGNED" if assign else "UNASSIGNED"
            visarjan_date_str = idol.immersion_date.strftime('%d-%b-%Y') if idol.immersion_date else "—"

            row_data = [
                idx,
                idol.gpid,
                idol.name or idol.association_name or "Ganesh Idol",
                f"{h_val:.1f}",
                category,
                visarjan_date_str,
                idol.zone,
                idol.police_station,
                assignment_status_str,
                officer_name,
                police_id,
                officer_ps,
                started_at,
                idol.get_procession_state_display() if hasattr(idol, 'get_procession_state_display') else idol.procession_state,
                idol.address or idol.instal_street or "N/A",
            ]
            ws.append(row_data)
            ws.row_dimensions[row_num].height = 20

            fill = alt_fill if idx % 2 == 0 else normal_fill
            for col_idx in range(1, len(row_data) + 1):
                cell = ws.cell(row=row_num, column=col_idx)
                cell.font = Font(name="Calibri", size=10)
                cell.fill = fill
                cell.border = thin_border
                if col_idx in [1, 2, 4, 5, 6, 9, 11, 13]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")

            row_num += 1

        # Adjust column widths
        col_widths = {
            1: 8,   # S.No
            2: 22,  # GPID
            3: 30,  # Pandal Name
            4: 12,  # Height
            5: 16,  # Height Category
            6: 16,  # Visarjan Date
            7: 18,  # Zone
            8: 22,  # Police Station
            9: 18,  # Assignment Status
            10: 25, # Assigned Officer
            11: 16, # Police ID
            12: 20, # Officer Station
            13: 20, # Started At
            14: 20, # Procession State
            15: 35, # Address
        }
        for col_idx, width in col_widths.items():
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"Hyderabad_Police_Officer_Assignments_{timezone.now().strftime('%Y%m%d_%H%M')}.xlsx"
        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
