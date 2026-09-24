import os
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from common.permissions import filter_by_jurisdiction

import math
from .models import TrackingSession, LocationPoint, TrackingSessionStatus, IdolEvent, IdolEventType
from .serializers import (
    TrackingSessionSerializer,
    StartTrackingSerializer,
    LocationPointSerializer,
    IngestLocationSerializer,
    BatchIngestLocationSerializer,
    ProcessionEventSerializer,
)
from apps.accounts.models import User
from apps.idols.models import Idol, ProcessionState, GeocodingConfidence


def haversine_distance_meters(lat1, lon1, lat2, lon2):
    """
    Computes great-circle distance between two coordinates in meters.
    """
    R = 6371000.0  # Earth radius in meters
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def calculate_sequential_distance_km(points):
    """
    Computes total travel distance from sequential GPS coordinates using Haversine formula.
    Filters micro-jitter (< 5 meters).
    """
    if len(points) < 2:
        return 0.0

    R = 6371.0  # Earth radius in km
    total_km = 0.0
    for i in range(1, len(points)):
        lat1, lon1 = points[i - 1].latitude, points[i - 1].longitude
        lat2, lon2 = points[i].latitude, points[i].longitude
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        segment = R * c
        if segment >= 0.005:  # ignore < 5m GPS noise
            total_km += segment

    return round(total_km, 2)


def get_connection_state(last_recorded_at):
    """
    Computes telemetry freshness state without conflating network loss with procession state.
    """
    if not last_recorded_at:
        return 'OFFLINE'
    delta = (timezone.now() - last_recorded_at).total_seconds()
    if delta < 120:  # < 2 minutes
        return 'LIVE'
    elif delta < 600:  # 2 - 10 minutes
        return 'DEGRADED'
    return 'OFFLINE'  # > 10 minutes


class StartTrackingView(APIView):
    """
    Starts GPS tracking session for an active assignment.
    Transitions Idol procession state to TRACKING.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StartTrackingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignment = serializer.validated_data['assignment_obj']
        device_info = serializer.validated_data.get('device_info', '')

        # Authorization: constable assigned to this duty or station officer
        if request.user != assignment.constable and request.user.role not in ['MAIN_OFFICER', 'ACP', 'SHO']:
            return Response(
                {'error': 'You do not have permission to start tracking for this idol.'},
                status=status.HTTP_403_FORBIDDEN
            )

        officer_lat = serializer.validated_data['latitude']
        officer_lon = serializer.validated_data['longitude']

        with transaction.atomic():
            now = timezone.now()
            # Stop any previously active tracking session for this assignment
            TrackingSession.objects.filter(
                assignment=assignment,
                status=TrackingSessionStatus.ACTIVE
            ).update(status=TrackingSessionStatus.STOPPED, ended_at=now)

            session = TrackingSession.objects.create(
                assignment=assignment,
                device_info=device_info,
                status=TrackingSessionStatus.ACTIVE,
                started_at=now
            )

            # Persist initial start GPS as first LocationPoint immediately
            # Guarantees live marker appears instantly on Live Map
            start_lat = float(officer_lat) if officer_lat is not None else None
            start_lon = float(officer_lon) if officer_lon is not None else None
            if start_lat is not None and start_lon is not None:
                LocationPoint.objects.create(
                    session=session,
                    latitude=start_lat,
                    longitude=start_lon,
                    accuracy=serializer.validated_data.get('accuracy'),
                    speed=0.0,
                    heading=0.0,
                    recorded_at=now
                )

            # Update Idol procession state if not already started
            idol = assignment.idol
            if idol.procession_state == ProcessionState.NOT_STARTED:
                idol.procession_state = ProcessionState.TRACKING
                idol.save(update_fields=['procession_state', 'updated_at'])

            # Log durable operational event
            constable_name = assignment.constable.username if assignment.constable else (assignment.officer_name_snapshot or 'Assigned Officer')
            IdolEvent.objects.create(
                idol=idol,
                gpid=idol.gpid,
                event_type=IdolEventType.TRACKING_STARTED,
                timestamp=now,
                latitude=start_lat,
                longitude=start_lon,
                zone=idol.zone,
                actor=request.user,
                tracking_session=session,
                metadata={
                    'device_info': device_info,
                    'constable': constable_name,
                    'source': 'Ground Staff Device'
                }
            )

        return Response(TrackingSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class IngestLocationView(APIView):
    """
    Receives single real-time GPS breadcrumb from constable device.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = IngestLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        session = get_object_or_404(TrackingSession, id=data['session_id'], status=TrackingSessionStatus.ACTIVE)

        # Check for duplicate of initial start GPS point (only within first 15 seconds of session start)
        if session.started_at and abs((data['recorded_at'] - session.started_at).total_seconds()) <= 15:
            initial_point = LocationPoint.objects.filter(session=session).order_by('recorded_at').first()
            if initial_point and abs(data['latitude'] - initial_point.latitude) < 0.0001 and abs(data['longitude'] - initial_point.longitude) < 0.0001:
                if data.get('accuracy') is not None and not initial_point.accuracy:
                    initial_point.accuracy = data.get('accuracy')
                    initial_point.save(update_fields=['accuracy'])
                return Response({
                    'status': 'duplicate_ignored',
                    'point_id': initial_point.id,
                    'gpid': session.assignment.idol.gpid,
                    'connection_state': 'LIVE',
                    'procession_state': session.assignment.idol.procession_state
                }, status=status.HTTP_201_CREATED)

        # Ingest or update if duplicate timestamp
        point, created = LocationPoint.objects.get_or_create(
            session=session,
            recorded_at=data['recorded_at'],
            defaults={
                'latitude': data['latitude'],
                'longitude': data['longitude'],
                'accuracy': data.get('accuracy'),
                'speed': data.get('speed'),
                'heading': data.get('heading'),
            }
        )

        # Update procession movement state based on telemetry speed
        speed = data.get('speed')
        idol = session.assignment.idol
        if speed is not None:
            if speed > 1.0 and idol.procession_state in [ProcessionState.NOT_STARTED, ProcessionState.TRACKING, ProcessionState.HOLDING]:
                idol.procession_state = ProcessionState.MOVING
                idol.save(update_fields=['procession_state', 'updated_at'])
            elif speed <= 0.3 and idol.procession_state == ProcessionState.MOVING:
                idol.procession_state = ProcessionState.HOLDING
                idol.save(update_fields=['procession_state', 'updated_at'])

        return Response({
            'status': 'recorded' if created else 'duplicate_ignored',
            'point_id': point.id,
            'gpid': idol.gpid,
            'connection_state': 'LIVE',
            'procession_state': idol.procession_state
        }, status=status.HTTP_201_CREATED)


class BatchIngestLocationView(APIView):
    """
    Receives an offline queue of GPS points recorded during network disconnection.
    Ensures safe idempotency and prevents duplicate telemetry.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BatchIngestLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = serializer.validated_data['session_id']
        points_data = serializer.validated_data['points']
        session = get_object_or_404(TrackingSession, id=session_id)

        existing_timestamps = set(
            LocationPoint.objects.filter(session=session).values_list('recorded_at', flat=True)
        )
        initial_point = LocationPoint.objects.filter(session=session).order_by('recorded_at').first()

        points_to_create = []
        for p in points_data:
            rec_at_str = p.get('recorded_at')
            if not rec_at_str:
                continue
            try:
                rec_at = pd_to_dt = timezone.datetime.fromisoformat(rec_at_str.replace('Z', '+00:00'))
            except Exception:
                continue

            if rec_at in existing_timestamps:
                continue  # Skip already recorded point

            lat = float(p.get('latitude', 0))
            lon = float(p.get('longitude', 0))
            if lat == 0 and lon == 0:
                continue

            # Skip if this point duplicates the initial start point created at session start
            if initial_point and session.started_at and abs((rec_at - session.started_at).total_seconds()) <= 15:
                if abs(lat - initial_point.latitude) < 0.0001 and abs(lon - initial_point.longitude) < 0.0001:
                    continue

            points_to_create.append(LocationPoint(
                session=session,
                latitude=lat,
                longitude=lon,
                accuracy=p.get('accuracy'),
                speed=p.get('speed'),
                heading=p.get('heading'),
                recorded_at=rec_at
            ))
            existing_timestamps.add(rec_at)


        if points_to_create:
            with transaction.atomic():
                LocationPoint.objects.bulk_create(points_to_create, ignore_conflicts=True)

        return Response({
            'status': 'success',
            'received': len(points_data),
            'inserted': len(points_to_create),
            'duplicates_skipped': len(points_data) - len(points_to_create)
        }, status=status.HTTP_201_CREATED)


class StopTrackingView(APIView):
    """
    Stops GPS tracking session.
    Optionally marks idol status as AT_VISARJAN or IMMERSION_COMPLETED.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get('session_id')
        gpid = request.data.get('gpid')
        final_state = request.data.get('final_state')  # AT_VISARJAN or IMMERSION_COMPLETED

        if session_id:
            session = get_object_or_404(TrackingSession, id=session_id)
        elif gpid:
            session = TrackingSession.objects.filter(
                assignment__idol__gpid__iexact=gpid,
                status=TrackingSessionStatus.ACTIVE
            ).order_by('-started_at').first()
            if not session:
                return Response(
                    {'error': f'No active tracking session found for GPID {gpid}.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            return Response({'error': 'session_id or gpid required.'}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        with transaction.atomic():
            session.stop_session()

            idol = session.assignment.idol
            if final_state in [ProcessionState.AT_VISARJAN, ProcessionState.IMMERSION_COMPLETED]:
                idol.procession_state = final_state
                idol.save(update_fields=['procession_state', 'updated_at'])

            latest_pt = session.location_points.order_by('-recorded_at').first()
            stop_lat = latest_pt.latitude if latest_pt else None
            stop_lon = latest_pt.longitude if latest_pt else None

            # Log operational event
            IdolEvent.objects.create(
                idol=idol,
                gpid=idol.gpid,
                event_type=IdolEventType.TRACKING_STOPPED,
                timestamp=now,
                latitude=stop_lat,
                longitude=stop_lon,
                zone=idol.zone,
                actor=request.user,
                tracking_session=session,
                metadata={
                    'final_state': final_state or idol.procession_state,
                    'stopped_by': request.user.username,
                    'source': 'Ground Staff Device'
                }
            )

            if final_state == ProcessionState.AT_VISARJAN:
                IdolEvent.objects.create(
                    idol=idol,
                    gpid=idol.gpid,
                    event_type=IdolEventType.VISARJAN_REACHED,
                    timestamp=now,
                    latitude=stop_lat,
                    longitude=stop_lon,
                    zone=idol.zone,
                    actor=request.user,
                    tracking_session=session
                )
            elif final_state == ProcessionState.IMMERSION_COMPLETED:
                IdolEvent.objects.create(
                    idol=idol,
                    gpid=idol.gpid,
                    event_type=IdolEventType.IMMERSION_COMPLETED,
                    timestamp=now,
                    latitude=stop_lat,
                    longitude=stop_lon,
                    zone=idol.zone,
                    actor=request.user,
                    tracking_session=session
                )

        return Response({
            'status': 'stopped',
            'session_id': session.id,
            'gpid': idol.gpid,
            'procession_state': idol.procession_state
        })


class TimestampLookupView(APIView):
    """
    Operational requirement: Officer selects GPID, Date, and Time.
    Backend queries indexed database and returns nearest historical GPS point.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, gpid):
        timestamp_str = request.query_params.get('timestamp')
        if not timestamp_str:
            return Response({'error': 'timestamp parameter is required (ISO format).'}, status=status.HTTP_400_BAD_REQUEST)

        idol = get_object_or_404(filter_by_jurisdiction(Idol.objects.all(), request.user), gpid__iexact=gpid)

        norm_ts = timestamp_str.replace(' ', '+')
        from django.utils.dateparse import parse_datetime
        target_dt = parse_datetime(norm_ts)
        if not target_dt:
            try:
                target_dt = datetime.fromisoformat(norm_ts.replace('Z', '+00:00'))
            except Exception as e:
                return Response({'error': f'Invalid timestamp format: {e}'}, status=status.HTTP_400_BAD_REQUEST)
        if timezone.is_naive(target_dt):
            target_dt = timezone.make_aware(target_dt)

        # Query LocationPoints associated with this idol's tracking sessions
        # Find points before and after target_dt using index
        point_before = LocationPoint.objects.filter(
            session__assignment__idol=idol,
            recorded_at__lte=target_dt
        ).order_by('-recorded_at').first()

        point_after = LocationPoint.objects.filter(
            session__assignment__idol=idol,
            recorded_at__gte=target_dt
        ).order_by('recorded_at').first()

        nearest_point = None
        min_diff = None

        if point_before and point_after:
            diff_before = abs((target_dt - point_before.recorded_at).total_seconds())
            diff_after = abs((point_after.recorded_at - target_dt).total_seconds())
            if diff_before <= diff_after:
                nearest_point = point_before
                min_diff = diff_before
            else:
                nearest_point = point_after
                min_diff = diff_after
        elif point_before:
            nearest_point = point_before
            min_diff = abs((target_dt - point_before.recorded_at).total_seconds())
        elif point_after:
            nearest_point = point_after
            min_diff = abs((point_after.recorded_at - target_dt).total_seconds())

        if not nearest_point:
            return Response({
                'message': f'No GPS tracking points recorded for GPID {gpid}.',
                'gpid': gpid,
                'nearest_point': None
            }, status=status.HTTP_404_NOT_FOUND)

        constable = nearest_point.session.assignment.constable

        return Response({
            'gpid': idol.gpid,
            'idol_name': idol.name,
            'target_timestamp': target_dt,
            'nearest_point': {
                'id': nearest_point.id,
                'latitude': nearest_point.latitude,
                'longitude': nearest_point.longitude,
                'accuracy': nearest_point.accuracy,
                'speed': nearest_point.speed,
                'heading': nearest_point.heading,
                'recorded_at': nearest_point.recorded_at,
                'time_difference_seconds': round(min_diff, 1),
            },
            'session_id': nearest_point.session.id,
            'constable': {
                'id': constable.id,
                'username': constable.username,
                'name': constable.get_full_name() or constable.username,
                'police_id': constable.police_id,
            }
        })


def build_session_journey_response(session, idol):
    """
    Builds a complete session-scoped journey payload.
    Guarantees that telemetry from other sessions for the same GPID is never mixed.
    """
    points = LocationPoint.objects.filter(session=session).order_by('recorded_at')

    if not points.exists():
        return Response({
            'gpid': idol.gpid,
            'tracking_session_id': session.id,
            'idol_name': idol.name,
            'police_station': idol.police_station,
            'zone': idol.zone,
            'procession_state': idol.procession_state,
            'connection_state': 'OFFLINE',
            'total_points': 0,
            'points': [],
            'summary': {
                'start_time': None,
                'end_time': None,
                'max_speed_kmh': 0,
                'distance_travelled_km': 0.0,
            },
            'events': []
        })

    points_list = []
    max_speed = 0.0
    for p in points:
        spd = p.speed or 0.0
        if spd > max_speed:
            max_speed = spd
        points_list.append({
            'latitude': p.latitude,
            'longitude': p.longitude,
            'speed': p.speed,
            'heading': p.heading,
            'accuracy': p.accuracy,
            'recorded_at': p.recorded_at.isoformat() if p.recorded_at else None,
        })

    start_time = points_list[0]['recorded_at']
    end_time = points_list[-1]['recorded_at']

    # Last point connection freshness
    last_pt = points.last()
    connection_state = get_connection_state(last_pt.recorded_at if last_pt else None)

    # Calculate actual sequential travelled distance (Haversine)
    distance_km = calculate_sequential_distance_km(points)

    # Retrieve operational event timeline scoped to this tracking session
    raw_events = IdolEvent.objects.filter(
        Q(tracking_session=session) | Q(idol=idol, tracking_session__isnull=True)
    ).order_by('timestamp').select_related('actor')

    events_list = [{
        'id': ev.id,
        'event_type': ev.event_type,
        'label': ev.get_event_type_display(),
        'timestamp': ev.timestamp.isoformat() if ev.timestamp else None,
        'latitude': ev.latitude,
        'longitude': ev.longitude,
        'zone': ev.zone,
        'actor': ev.actor.get_full_name() or ev.actor.username if ev.actor else None,
        'metadata': ev.metadata
    } for ev in raw_events]

    return Response({
        'gpid': idol.gpid,
        'tracking_session_id': session.id,
        'idol_name': idol.name,
        'police_station': idol.police_station,
        'zone': idol.zone,
        'procession_state': idol.procession_state,
        'connection_state': connection_state,
        'total_points': len(points_list),
        'summary': {
            'start_time': start_time,
            'end_time': end_time,
            'max_speed_kmh': round(max_speed * 3.6, 2),  # m/s to km/h
            'distance_travelled_km': distance_km,
        },
        'points': points_list,
        'events': events_list
    })


class JourneyView(APIView):
    """
    Returns complete chronological GPS breadcrumbs and procession stats for a GPID.
    Explicitly supports session_id scoping so multiple sessions for one GPID are NEVER merged.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, gpid):
        idol = get_object_or_404(filter_by_jurisdiction(Idol.objects.all(), request.user), gpid__iexact=gpid)
        session_id = request.query_params.get('session_id')

        if session_id and str(session_id).isdigit():
            session = get_object_or_404(TrackingSession, id=int(session_id), assignment__idol=idol)
        else:
            # Active session priority, or latest session
            session = TrackingSession.objects.filter(
                assignment__idol=idol,
                status=TrackingSessionStatus.ACTIVE
            ).order_by('-started_at').first()
            if not session:
                session = TrackingSession.objects.filter(
                    assignment__idol=idol
                ).order_by('-started_at').first()

        if not session:
            return Response({
                'gpid': idol.gpid,
                'tracking_session_id': None,
                'idol_name': idol.name,
                'total_points': 0,
                'points': [],
                'summary': {
                    'start_time': None,
                    'end_time': None,
                    'max_speed_kmh': 0,
                    'distance_travelled_km': 0,
                },
                'events': []
            })

        return build_session_journey_response(session, idol)


class SessionJourneyView(APIView):
    """
    Direct session-scoped journey endpoint: GET /api/v1/tracking/sessions/<int:session_id>/journey/
    Guarantees that telemetry from previous sessions is never mixed.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        scoped_sessions = filter_by_jurisdiction(
            TrackingSession.objects.all(),
            request.user,
            ps_field='assignment__idol__police_station',
            zone_field='assignment__idol__zone',
            division_field='assignment__idol__division'
        )
        session = get_object_or_404(scoped_sessions, id=session_id)
        return build_session_journey_response(session, session.assignment.idol)


class ActiveTrackingListView(APIView):
    """
    Returns ONLY currently active tracking sessions with their valid latest GPS positions.
    If zero active sessions exist: returns [].
    If session has no GPS telemetry: omitted.
    If session is stopped: omitted.
    Strictly zero registry / centroid fallback points.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = TrackingSession.objects.filter(
            status=TrackingSessionStatus.ACTIVE
        ).select_related(
            'assignment__idol',
            'assignment__constable'
        )

        # Enforce server-side jurisdiction
        qs = filter_by_jurisdiction(
            qs,
            request.user,
            ps_field='assignment__idol__police_station',
            zone_field='assignment__idol__zone',
            division_field='assignment__idol__division'
        )

        # Unified active procession filters
        zone = request.query_params.get('zone')
        if zone and zone != 'All Zones':
            qs = qs.filter(assignment__idol__zone__iexact=zone)

        ps = request.query_params.get('police_station')
        if ps:
            qs = qs.filter(assignment__idol__police_station__iexact=ps)

        height_bucket = request.query_params.get('height_bucket')
        if height_bucket and height_bucket != 'ALL':
            hb = height_bucket.lower().strip()
            if hb in ['15_20', '15-20', 'green']:
                qs = qs.filter(assignment__idol__idol_height__gte=15, assignment__idol__idol_height__lt=21)
            elif hb in ['21_25', '21-25', 'yellow']:
                qs = qs.filter(assignment__idol__idol_height__gte=21, assignment__idol__idol_height__lt=26)
            elif hb in ['above_25', '26_plus', '26+', 'red']:
                qs = qs.filter(assignment__idol__idol_height__gte=26)

        search = request.query_params.get('search')
        if search:
            s = search.strip()
            qs = qs.filter(
                Q(assignment__idol__gpid__icontains=s) |
                Q(assignment__idol__name__icontains=s) |
                Q(assignment__idol__association_name__icontains=s)
            )

        active_sessions = list(qs.order_by('-started_at'))
        if not active_sessions:
            return Response([])

        session_ids = [s.id for s in active_sessions]
        # Query latest LocationPoint for each active session (efficient single query)
        from django.db import connection
        if connection.vendor == 'postgresql':
            latest_points = {
                pt.session_id: pt
                for pt in LocationPoint.objects.filter(session_id__in=session_ids)
                                             .order_by('session_id', '-recorded_at')
                                             .distinct('session_id')
            }
        else:
            latest_points = {}
            for pt in LocationPoint.objects.filter(session_id__in=session_ids).order_by('-recorded_at'):
                if pt.session_id not in latest_points:
                    latest_points[pt.session_id] = pt

        can_view_contact = request.user.role in ['MAIN_OFFICER', 'ACP', 'SHO']

        from apps.idols.views import get_height_classification

        markers = []
        for sess in active_sessions:
            latest_pt = latest_points.get(sess.id)
            if not latest_pt or latest_pt.latitude is None or latest_pt.longitude is None:
                # Omit if no valid latest GPS position
                continue

            idol = sess.assignment.idol
            constable = sess.assignment.constable
            conn_state = get_connection_state(latest_pt.recorded_at)
            height_val = float(idol.idol_height) if idol.idol_height is not None else None

            markers.append({
                'id': idol.id,
                'tracking_session_id': sess.id,
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
                'latitude': float(latest_pt.latitude),
                'longitude': float(latest_pt.longitude),
                'speed': float(latest_pt.speed) if latest_pt.speed is not None else None,
                'heading': float(latest_pt.heading) if latest_pt.heading is not None else None,
                'accuracy': float(latest_pt.accuracy) if latest_pt.accuracy is not None else None,
                'last_gps_timestamp': latest_pt.recorded_at.isoformat() if latest_pt.recorded_at else None,
                'session_started_at': sess.started_at.isoformat() if sess.started_at else None,
                'idol_height': height_val,
                'height_classification': get_height_classification(height_val),
                'origin_location': idol.address or idol.instal_street or idol.instal_village or 'N/A',
                'destination': idol.river_name or idol.lake_type or 'Visarjan Site',
                'owner_name': idol.name or idol.association_name or 'N/A',
                'assigned_constable': {
                    'id': constable.id,
                    'name': constable.get_full_name() or constable.username,
                    'police_id': constable.police_id,
                    'phone_number': constable.phone_number if can_view_contact else None
                } if constable else (
                    {
                        'id': None,
                        'name': sess.assignment.officer_name_snapshot or 'Assigned Officer',
                        'police_id': sess.assignment.police_id_snapshot,
                        'phone_number': None
                    } if sess.assignment else None
                )
            })

        return Response(markers)


class LatestLocationView(APIView):
    """
    Returns the latest known location and telemetry status for an idol.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, gpid):
        idol = get_object_or_404(filter_by_jurisdiction(Idol.objects.all(), request.user), gpid__iexact=gpid)
        latest_point = LocationPoint.objects.filter(
            session__assignment__idol=idol
        ).order_by('-recorded_at').first()

        active_session = TrackingSession.objects.filter(
            assignment__idol=idol,
            status=TrackingSessionStatus.ACTIVE
        ).first()

        last_recorded = latest_point.recorded_at if latest_point else None
        connection_state = get_connection_state(last_recorded)

        assigned_constable = None
        if active_session:
            c = active_session.constable
            assigned_constable = {
                'id': c.id,
                'name': c.get_full_name() or c.username,
                'police_id': c.police_id
            }

        return Response({
            'gpid': idol.gpid,
            'name': idol.name,
            'police_station': idol.police_station,
            'zone': idol.zone,
            'procession_state': idol.procession_state,
            'connection_state': connection_state,
            'active_session_id': active_session.id if active_session else None,
            'constable': assigned_constable,
            'latest_location': {
                'latitude': latest_point.latitude,
                'longitude': latest_point.longitude,
                'accuracy': latest_point.accuracy,
                'speed': latest_point.speed,
                'heading': latest_point.heading,
                'recorded_at': latest_point.recorded_at.isoformat(),
            } if latest_point else None
        })


class MobileSessionView(APIView):
    """
    Direct endpoint for Android APK (live_tracking_service.dart):
    POST /api/tracking/session
    PATCH /api/tracking/session
    DELETE /api/tracking/session
    """
    permission_classes = []  # Allow token or user payload identification

    def post(self, request):
        user_id = request.data.get('userId')
        user_name = request.data.get('userName')
        device_id = request.data.get('deviceId', 'device-default')
        device_name = request.data.get('deviceName', 'Android Device')

        # Find user
        user = None
        if user_id and str(user_id).isdigit():
            user = User.objects.filter(id=int(user_id)).first()
        if not user and user_name:
            user = User.objects.filter(username=user_name).first()
        if not user:
            # Fallback to first available constable in the database
            user = User.objects.filter(role='CONSTABLE').first()
            if not user:
                if not getattr(settings, 'DEBUG', False):
                    return Response(
                        {'error': 'Constable user not found or unassigned.'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                # Development / testing only: auto-provision demo user with unusable password
                demo_password = os.environ.get('DEMO_CONSTABLE_PASSWORD')
                user = User.objects.create_user(
                    username=user_name or 'pc_default',
                    role='CONSTABLE'
                )
                if demo_password:
                    user.set_password(demo_password)
                else:
                    user.set_unusable_password()
                user.save()

        # Lookup active assignment for this constable
        from apps.assignments.models import Assignment
        assignment = Assignment.objects.filter(constable=user, is_active=True).first()

        if not assignment:
            # Check if an idol is available in user's PS to assign
            idol = Idol.objects.first()
            if idol:
                assignment = Assignment.assign_constable(idol=idol, constable=user)

        active_gpid = assignment.idol.gpid if assignment else 'HYD-UNASSIGNED'

        # Create or update active tracking session
        TrackingSession.objects.filter(
            assignment=assignment,
            status=TrackingSessionStatus.ACTIVE
        ).update(status=TrackingSessionStatus.STOPPED, ended_at=timezone.now())

        session = TrackingSession.objects.create(
            assignment=assignment,
            device_info=f"{device_name} ({device_id})",
            status=TrackingSessionStatus.ACTIVE
        )

        if assignment and assignment.idol.procession_state == ProcessionState.NOT_STARTED:
            assignment.idol.procession_state = ProcessionState.TRACKING
            assignment.idol.save(update_fields=['procession_state', 'updated_at'])

        return Response({
            'success': True,
            'userSessionId': str(session.id),
            'deviceSessionId': str(device_id),
            'activeGpid': active_gpid
        }, status=status.HTTP_201_CREATED)

    def patch(self, request):
        session_id = request.data.get('userSessionId')
        tracking_status = request.data.get('trackingStatus')
        if session_id and str(session_id).isdigit():
            TrackingSession.objects.filter(id=int(session_id)).update(updated_at=timezone.now())
        return Response({'success': True})

    def delete(self, request):
        session_id = request.data.get('userSessionId')
        if session_id and str(session_id).isdigit():
            TrackingSession.objects.filter(id=int(session_id)).update(
                status=TrackingSessionStatus.STOPPED,
                ended_at=timezone.now()
            )
        return Response({'success': True})


class MobileLocationView(APIView):
    """
    Direct endpoint for Android APK (live_tracking_service.dart):
    POST /api/tracking/location
    """
    permission_classes = []

    def post(self, request):
        session_id = request.data.get('userSessionId')
        lat = request.data.get('latitude')
        lon = request.data.get('longitude')
        accuracy = request.data.get('accuracy')
        speed = request.data.get('speed')
        heading = request.data.get('heading')
        captured_at_str = request.data.get('capturedAt')
        active_gpid = request.data.get('activeGpid')

        if not lat or not lon:
            return Response({'success': False, 'error': 'Missing coordinates'}, status=status.HTTP_400_BAD_REQUEST)

        session = None
        if session_id and str(session_id).isdigit():
            session = TrackingSession.objects.filter(id=int(session_id)).first()

        if not session and active_gpid:
            session = TrackingSession.objects.filter(
                assignment__idol__gpid__iexact=active_gpid,
                status=TrackingSessionStatus.ACTIVE
            ).first()

        if not session:
            # Find any active session or create one for the gpid
            idol = Idol.objects.filter(gpid__iexact=active_gpid).first() if active_gpid else Idol.objects.first()
            if idol:
                assignment = idol.assignments.filter(is_active=True).first()
                if not assignment:
                    user = User.objects.filter(role='CONSTABLE').first()
                    assignment = Assignment.assign_constable(idol=idol, constable=user)
                session = TrackingSession.objects.create(assignment=assignment, status=TrackingSessionStatus.ACTIVE)

        if not session:
            return Response({'success': False, 'error': 'No session found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            if captured_at_str:
                captured_at = timezone.datetime.fromisoformat(captured_at_str.replace('Z', '+00:00'))
            else:
                captured_at = timezone.now()
        except Exception:
            captured_at = timezone.now()

        LocationPoint.objects.create(
            session=session,
            latitude=float(lat),
            longitude=float(lon),
            accuracy=float(accuracy) if accuracy is not None else None,
            speed=float(speed) if speed is not None else None,
            heading=float(heading) if heading is not None else None,
            recorded_at=captured_at
        )

        # Update idol state if speed indicates movement
        if speed is not None and float(speed) > 1.0:
            idol = session.assignment.idol
            if idol.procession_state in [ProcessionState.NOT_STARTED, ProcessionState.TRACKING, ProcessionState.HOLDING]:
                idol.procession_state = ProcessionState.MOVING
                idol.save(update_fields=['procession_state', 'updated_at'])

        return Response({'success': True})


class ProcessionEventIngestView(APIView):
    """
    Ingests operational procession lifecycle events from ground staff devices
    (e.g., REACHED_SITE, PROCESSION_STARTED, REACHED_VISARJAN_SITE, VISARJAN_DONE,
    VISARJAN_NOT_DONE, SENT_TO_HOLDING, RETURNED_TO_ORIGIN).
    Deduplicates idempotently via client_event_id and updates authoritative Idol state.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProcessionEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        gpid = data['gpid']
        client_event_id = data.get('client_event_id')
        event_type_raw = data['event_type'].upper()
        lat = data.get('latitude')
        lon = data.get('longitude')
        occurred_at = data.get('occurred_at') or timezone.now()

        idol = get_object_or_404(Idol, gpid__iexact=gpid)

        # Idempotency check: if client_event_id was already processed, return existing
        if client_event_id:
            existing_event = IdolEvent.objects.filter(
                idol=idol,
                metadata__client_event_id=client_event_id
            ).first()
            if existing_event:
                return Response({
                    'status': 'already_recorded',
                    'event_id': existing_event.id,
                    'client_event_id': client_event_id,
                    'gpid': idol.gpid,
                    'event_type': existing_event.event_type,
                    'state': event_type_raw,
                    'procession_state': idol.procession_state,
                }, status=status.HTTP_200_OK)

        # Resolve tracking session
        session = None
        session_id_str = data.get('tracking_session_id')
        if session_id_str and session_id_str.isdigit():
            session = TrackingSession.objects.filter(id=int(session_id_str)).first()
        if not session:
            session = TrackingSession.objects.filter(
                assignment__idol=idol,
                status=TrackingSessionStatus.ACTIVE
            ).order_by('-started_at').first()

        # Map event type to IdolEventType and ProcessionState
        type_mapping = {
            'REACHED_SITE': (IdolEventType.REACHED_SITE, None),
            'AT_IDOL': (IdolEventType.REACHED_SITE, None),
            'PROCESSION_STARTED': (IdolEventType.TRACKING_STARTED, ProcessionState.TRACKING),
            'REACHED_VISARJAN_SITE': (IdolEventType.VISARJAN_REACHED, ProcessionState.AT_VISARJAN),
            'REACHED_VISARJAN_AREA': (IdolEventType.VISARJAN_REACHED, ProcessionState.AT_VISARJAN),
            'VISARJAN_DONE': (IdolEventType.IMMERSION_COMPLETED, ProcessionState.IMMERSION_COMPLETED),
            'VISARJAN_NOT_DONE': (IdolEventType.VISARJAN_NOT_DONE, ProcessionState.HOLDING),
            'SENT_TO_HOLDING': (IdolEventType.HOLDING_POINT_ENTERED, ProcessionState.HOLDING),
            'HOLDING': (IdolEventType.HOLDING_POINT_ENTERED, ProcessionState.HOLDING),
            'RETURNED_TO_ORIGIN': (IdolEventType.RETURNED_TO_ORIGIN, ProcessionState.NOT_STARTED),
            'RETURNED_TO_PANDAL': (IdolEventType.RETURNED_TO_ORIGIN, ProcessionState.NOT_STARTED),
        }

        mapped_type, new_state = type_mapping.get(event_type_raw, (event_type_raw, None))

        with transaction.atomic():
            if new_state:
                idol.procession_state = new_state
                idol.save(update_fields=['procession_state', 'updated_at'])

            event = IdolEvent.objects.create(
                idol=idol,
                gpid=idol.gpid,
                event_type=mapped_type,
                timestamp=occurred_at,
                latitude=lat,
                longitude=lon,
                zone=idol.zone,
                actor=request.user if request.user.is_authenticated else None,
                tracking_session=session,
                metadata={
                    'client_event_id': client_event_id,
                    'raw_event_type': event_type_raw,
                    'submitted_by': request.user.username if request.user.is_authenticated else 'unknown',
                    'source': 'Android Field Tracker',
                }
            )

        return Response({
            'status': 'recorded',
            'event_id': event.id,
            'client_event_id': client_event_id,
            'gpid': idol.gpid,
            'event_type': mapped_type,
            'state': event_type_raw,
            'procession_state': idol.procession_state,
        }, status=status.HTTP_201_CREATED)
