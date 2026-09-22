import os
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import TrackingSession, LocationPoint, TrackingSessionStatus
from .serializers import (
    TrackingSessionSerializer,
    StartTrackingSerializer,
    LocationPointSerializer,
    IngestLocationSerializer,
    BatchIngestLocationSerializer,
)
from apps.accounts.models import User
from apps.idols.models import Idol, ProcessionState


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

        with transaction.atomic():
            # Stop any previously active tracking session for this assignment
            TrackingSession.objects.filter(
                assignment=assignment,
                status=TrackingSessionStatus.ACTIVE
            ).update(status=TrackingSessionStatus.STOPPED, ended_at=timezone.now())

            session = TrackingSession.objects.create(
                assignment=assignment,
                device_info=device_info,
                status=TrackingSessionStatus.ACTIVE
            )

            # Update Idol procession state if not already started
            idol = assignment.idol
            if idol.procession_state == ProcessionState.NOT_STARTED:
                idol.procession_state = ProcessionState.TRACKING
                idol.save(update_fields=['procession_state', 'updated_at'])

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
            session = get_object_or_404(
                TrackingSession,
                assignment__idol__gpid__iexact=gpid,
                status=TrackingSessionStatus.ACTIVE
            )
        else:
            return Response({'error': 'session_id or gpid required.'}, status=status.HTTP_400_BAD_REQUEST)

        session.stop_session()

        idol = session.assignment.idol
        if final_state in [ProcessionState.AT_VISARJAN, ProcessionState.IMMERSION_COMPLETED]:
            idol.procession_state = final_state
            idol.save(update_fields=['procession_state', 'updated_at'])

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

        idol = get_object_or_404(Idol, gpid__iexact=gpid)

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


class JourneyView(APIView):
    """
    Returns complete chronological GPS breadcrumbs and procession stats for a GPID.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, gpid):
        idol = get_object_or_404(Idol, gpid__iexact=gpid)

        points = LocationPoint.objects.filter(
            session__assignment__idol=idol
        ).order_by('recorded_at')

        if not points.exists():
            return Response({
                'gpid': idol.gpid,
                'idol_name': idol.name,
                'total_points': 0,
                'points': [],
                'summary': {
                    'start_time': None,
                    'end_time': None,
                    'max_speed_kmh': 0,
                }
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
                'recorded_at': p.recorded_at,
            })

        start_time = points_list[0]['recorded_at']
        end_time = points_list[-1]['recorded_at']

        # Last point connection freshness
        last_recorded = points_list[-1]['recorded_at']
        connection_state = get_connection_state(last_recorded)

        return Response({
            'gpid': idol.gpid,
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
            },
            'points': points_list
        })


class LatestLocationView(APIView):
    """
    Returns the latest known location and telemetry status for an idol.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, gpid):
        idol = get_object_or_404(Idol, gpid__iexact=gpid)
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
