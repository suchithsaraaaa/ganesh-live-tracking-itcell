from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User, UserRole
from apps.idols.models import Idol, ProcessionState, GeocodingConfidence
from apps.assignments.models import Assignment
from apps.tracking.models import TrackingSession, LocationPoint, TrackingSessionStatus


class TrackingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.constable = User.objects.create_user(
            username='pc_tracking', password='password123',
            role=UserRole.CONSTABLE, police_id='PC-999'
        )
        self.sho = User.objects.create_user(
            username='sho_tracking', password='password123',
            role=UserRole.SHO, police_station='Charminar'
        )
        self.idol = Idol.objects.create(
            gpid='HYDCMRZCMNR1749',
            name='Charminar Tracking Idol',
            police_station='Charminar',
            zone='Charminar',
            latitude=17.3616,
            longitude=78.4747,
            geocoding_confidence=GeocodingConfidence.EXACT
        )
        self.assignment = Assignment.assign_constable(
            idol=self.idol,
            constable=self.constable,
            assigned_by=self.sho
        )
        self.client.force_authenticate(user=self.constable)

    def test_start_tracking_creates_session_and_updates_state(self):
        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'device_info': 'Android Samsung S21',
            'latitude': 17.3616,
            'longitude': 78.4747
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'ACTIVE')

        self.idol.refresh_from_db()
        self.assertEqual(self.idol.procession_state, ProcessionState.TRACKING)

    def test_start_tracking_valid_assignment_and_gps_success(self):
        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'latitude': 17.36187,
            'longitude': 78.4747
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'ACTIVE')

    def test_start_tracking_mandatory_regression_unresolved_origin_and_distant_gps_success(self):
        """
        MANDATORY REGRESSION TEST:
        Officer has valid active assignment + valid GPS + GPS is several kilometres away from idol origin
        + idol origin is unresolved => SUCCESSFUL PROCESSION START
        """
        self.idol.geocoding_confidence = GeocodingConfidence.UNRESOLVED
        self.idol.latitude = None
        self.idol.longitude = None
        self.idol.save(update_fields=['geocoding_confidence', 'latitude', 'longitude'])

        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'latitude': 17.50000,
            'longitude': 78.50000
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'ACTIVE')

    def test_start_tracking_distant_gps_1_5km_away_success(self):
        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'latitude': 17.3751,
            'longitude': 78.4747
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'ACTIVE')

    def test_start_tracking_distant_gps_10km_away_success(self):
        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'latitude': 17.4516,
            'longitude': 78.4747
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'ACTIVE')

    def test_start_tracking_unresolved_idol_origin_success(self):
        self.idol.geocoding_confidence = GeocodingConfidence.UNRESOLVED
        self.idol.latitude = None
        self.idol.longitude = None
        self.idol.save(update_fields=['geocoding_confidence', 'latitude', 'longitude'])

        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'latitude': 17.3616,
            'longitude': 78.4747
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'ACTIVE')

    def test_start_tracking_missing_latitude_fails(self):
        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'longitude': 78.4747
        })
        self.assertEqual(res.status_code, 400)

    def test_start_tracking_missing_longitude_fails(self):
        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'latitude': 17.3616
        })
        self.assertEqual(res.status_code, 400)

    def test_start_tracking_invalid_latitude_fails(self):
        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'latitude': 999.0,
            'longitude': 78.4747
        })
        self.assertEqual(res.status_code, 400)

    def test_start_tracking_invalid_longitude_fails(self):
        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'latitude': 17.3616,
            'longitude': 999.0
        })
        self.assertEqual(res.status_code, 400)

    def test_start_tracking_wrong_assignment_fails(self):
        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': 999999,
            'latitude': 17.3616,
            'longitude': 78.4747
        })
        self.assertEqual(res.status_code, 400)

    def test_start_tracking_inactive_assignment_fails(self):
        self.assignment.is_active = False
        self.assignment.save(update_fields=['is_active'])

        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'latitude': 17.3616,
            'longitude': 78.4747
        })
        self.assertEqual(res.status_code, 400)

    def test_start_tracking_unauthorized_officer_fails(self):
        other_user = User.objects.create_user(
            username='other_constable',
            password='password123',
            role=UserRole.CONSTABLE
        )
        self.client.force_authenticate(user=other_user)

        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'latitude': 17.3616,
            'longitude': 78.4747
        })
        self.assertEqual(res.status_code, 403)

    def test_single_location_ingestion_and_state_transition(self):
        session = TrackingSession.objects.create(
            assignment=self.assignment,
            status=TrackingSessionStatus.ACTIVE
        )

        now = timezone.now()
        res = self.client.post(reverse('tracking-location'), {
            'session_id': session.id,
            'latitude': 17.3616,
            'longitude': 78.4747,
            'accuracy': 8.5,
            'speed': 2.4,  # > 1.0 m/s -> MOVING
            'heading': 180.0,
            'recorded_at': now.isoformat()
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'recorded')
        self.assertEqual(res.data['procession_state'], ProcessionState.MOVING)

        self.idol.refresh_from_db()
        self.assertEqual(self.idol.procession_state, ProcessionState.MOVING)

    def test_batch_location_ingestion_with_deduplication(self):
        session = TrackingSession.objects.create(
            assignment=self.assignment,
            status=TrackingSessionStatus.ACTIVE
        )

        t1 = timezone.now() - timedelta(minutes=5)
        t2 = timezone.now() - timedelta(minutes=4)

        payload = {
            'session_id': session.id,
            'points': [
                {'latitude': 17.3616, 'longitude': 78.4747, 'recorded_at': t1.isoformat(), 'speed': 1.0},
                {'latitude': 17.3620, 'longitude': 78.4750, 'recorded_at': t2.isoformat(), 'speed': 1.2},
            ]
        }
        res1 = self.client.post(reverse('tracking-location-batch'), payload, format='json')
        self.assertEqual(res1.status_code, 201)
        self.assertEqual(res1.data['inserted'], 2)

        # Retry sending the same batch (offline queue retry simulation)
        res2 = self.client.post(reverse('tracking-location-batch'), payload, format='json')
        self.assertEqual(res2.status_code, 201)
        self.assertEqual(res2.data['inserted'], 0)
        self.assertEqual(res2.data['duplicates_skipped'], 2)

    def test_timestamp_lookup_returns_nearest_point(self):
        session = TrackingSession.objects.create(
            assignment=self.assignment,
            status=TrackingSessionStatus.ACTIVE
        )
        base_time = timezone.now() - timedelta(hours=1)

        # Point at T + 0 min
        LocationPoint.objects.create(
            session=session,
            latitude=17.3600,
            longitude=78.4700,
            speed=1.5,
            recorded_at=base_time
        )
        # Point at T + 10 min
        p2 = LocationPoint.objects.create(
            session=session,
            latitude=17.3650,
            longitude=78.4750,
            speed=2.0,
            recorded_at=base_time + timedelta(minutes=10)
        )

        # Query at T + 9 min (should match Point 2 with diff of ~60s)
        query_time = (base_time + timedelta(minutes=9)).isoformat()
        res = self.client.get(reverse('tracking-location-at', kwargs={'gpid': self.idol.gpid}), {'timestamp': query_time})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['nearest_point']['id'], p2.id)
        self.assertLessEqual(res.data['nearest_point']['time_difference_seconds'], 65)
        self.assertEqual(res.data['constable']['police_id'], 'PC-999')

    def test_journey_retrieval(self):
        session = TrackingSession.objects.create(
            assignment=self.assignment,
            status=TrackingSessionStatus.ACTIVE
        )
        t = timezone.now()
        LocationPoint.objects.create(session=session, latitude=17.360, longitude=78.470, speed=1.0, recorded_at=t)
        LocationPoint.objects.create(session=session, latitude=17.362, longitude=78.472, speed=3.0, recorded_at=t + timedelta(minutes=2))

        res = self.client.get(reverse('tracking-journey', kwargs={'gpid': self.idol.gpid}))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['total_points'], 2)
        self.assertGreater(res.data['summary']['max_speed_kmh'], 10.0)

    def test_latest_location_endpoint_returns_200_and_payload(self):
        session = TrackingSession.objects.create(
            assignment=self.assignment,
            status=TrackingSessionStatus.ACTIVE
        )
        t = timezone.now()
        LocationPoint.objects.create(
            session=session,
            latitude=17.3616,
            longitude=78.4747,
            accuracy=5.0,
            speed=12.5,
            heading=180.0,
            recorded_at=t
        )
        res = self.client.get(reverse('tracking-latest', kwargs={'gpid': self.idol.gpid}))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['gpid'], self.idol.gpid)
        self.assertEqual(res.data['connection_state'], 'LIVE')
        self.assertEqual(res.data['active_session_id'], session.id)
        self.assertIsNotNone(res.data['latest_location'])
        self.assertEqual(res.data['latest_location']['latitude'], 17.3616)
        self.assertEqual(res.data['latest_location']['longitude'], 78.4747)
        self.assertEqual(res.data['constable']['police_id'], 'PC-999')


class AndroidAPKIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.pc = User.objects.create_user(
            username='pc_mobile', password='password123',
            role=UserRole.CONSTABLE, police_id='PC-777'
        )
        self.idol = Idol.objects.create(
            gpid='HYDCMRZCMNR1749',
            name='Mobile Tracking Ganesh',
            police_station='Charminar'
        )
        self.assignment = Assignment.assign_constable(idol=self.idol, constable=self.pc)

    def test_mobile_tracking_lifecycle(self):
        # 1. Create mobile tracking session
        res_sess = self.client.post('/api/tracking/session', {
            'userId': str(self.pc.id),
            'userName': self.pc.username,
            'role': 'CONSTABLE',
            'policeStationCode': 'CMNR',
            'deviceId': 'imei-998877',
            'deviceName': 'Samsung Galaxy M31'
        }, format='json')
        self.assertEqual(res_sess.status_code, 201)
        self.assertTrue(res_sess.data['success'])
        self.assertEqual(res_sess.data['activeGpid'], 'HYDCMRZCMNR1749')
        user_session_id = res_sess.data['userSessionId']

        # 2. Ingest GPS point from mobile
        res_loc = self.client.post('/api/tracking/location', {
            'userSessionId': user_session_id,
            'deviceSessionId': 'imei-998877',
            'latitude': 17.3616,
            'longitude': 78.4747,
            'accuracy': 5.0,
            'speed': 1.8,
            'heading': 90.0,
            'activeGpid': 'HYDCMRZCMNR1749',
            'capturedAt': timezone.now().isoformat()
        }, format='json')
        self.assertEqual(res_loc.status_code, 200)
        self.assertTrue(res_loc.data['success'])

        # Verify point saved to database
        self.assertEqual(LocationPoint.objects.filter(session_id=int(user_session_id)).count(), 1)
        self.idol.refresh_from_db()
        self.assertEqual(self.idol.procession_state, ProcessionState.MOVING)

        # 3. Close mobile session
        res_close = self.client.delete('/api/tracking/session', {
            'userSessionId': user_session_id,
            'deviceSessionId': 'imei-998877'
        }, format='json')
        self.assertEqual(res_close.status_code, 200)
        session = TrackingSession.objects.get(id=int(user_session_id))
        self.assertEqual(session.status, TrackingSessionStatus.STOPPED)

    def test_latest_location_returns_200_and_payload(self):
        """Regression test for LatestLocationView.get() returning proper DRF Response."""
        self.client.force_authenticate(user=self.pc)
        session = TrackingSession.objects.create(
            assignment=self.assignment,
            status=TrackingSessionStatus.ACTIVE
        )
        LocationPoint.objects.create(
            session=session,
            latitude=17.3650,
            longitude=78.4750,
            accuracy=4.2,
            speed=2.1,
            heading=90.0,
            recorded_at=timezone.now()
        )
        res = self.client.get(f'/api/v1/tracking/idols/{self.idol.gpid}/latest/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['gpid'], self.idol.gpid)
        self.assertIsNotNone(res.data['latest_location'])
        self.assertEqual(res.data['latest_location']['latitude'], 17.3650)
        self.assertEqual(res.data['constable']['police_id'], self.pc.police_id)

    def test_journey_view_includes_distance_and_events(self):
        """JourneyView computes Haversine distance and returns operational events."""
        self.client.force_authenticate(user=self.pc)
        session = TrackingSession.objects.create(
            assignment=self.assignment,
            status=TrackingSessionStatus.ACTIVE
        )
        t0 = timezone.now()
        # Point 1: Charminar (17.3616, 78.4747)
        LocationPoint.objects.create(session=session, latitude=17.3616, longitude=78.4747, recorded_at=t0)
        # Point 2: ~1 km away (17.3700, 78.4747)
        LocationPoint.objects.create(session=session, latitude=17.3700, longitude=78.4747, recorded_at=t0 + timedelta(minutes=5))

        res = self.client.get(f'/api/v1/tracking/idols/{self.idol.gpid}/journey/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['total_points'], 2)
        self.assertGreater(res.data['summary']['distance_travelled_km'], 0.5)
        # Assignment event exists
        event_types = [e['event_type'] for e in res.data['events']]
        self.assertTrue('ASSIGNMENT_CREATED' in event_types or 'PROCESSION_ASSIGNED' in event_types)

    def test_active_tracking_list_empty_when_no_active_sessions(self):
        """Mandatory Test A: When no sessions are active, GET /api/v1/tracking/active/ returns []."""
        self.client.force_authenticate(user=self.pc)
        res = self.client.get('/api/v1/tracking/active/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, [])

    def test_active_session_without_gps_is_omitted(self):
        """Mandatory Test B: Active session without GPS telemetry is omitted from live markers."""
        self.client.force_authenticate(user=self.pc)
        TrackingSession.objects.create(
            assignment=self.assignment,
            status=TrackingSessionStatus.ACTIVE
        )
        res = self.client.get('/api/v1/tracking/active/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, [])

    def test_start_tracking_persists_initial_point_and_creates_live_marker(self):
        """Mandatory Test C: Start with valid GPS creates initial LocationPoint and one live marker."""
        self.client.force_authenticate(user=self.pc)
        # Update idol to EXACT confidence at Charminar coords
        self.idol.latitude = 17.3616
        self.idol.longitude = 78.4747
        self.idol.geocoding_confidence = GeocodingConfidence.EXACT
        self.idol.save(update_fields=['latitude', 'longitude', 'geocoding_confidence'])

        res_start = self.client.post('/api/v1/tracking/start/', {
            'assignment_id': self.assignment.id,
            'latitude': 17.3616,
            'longitude': 78.4747,
            'accuracy': 5.0,
            'device_info': 'Test Device'
        })
        self.assertEqual(res_start.status_code, 201)
        session_id = res_start.data['id']

        # Verify initial point created
        self.assertTrue(LocationPoint.objects.filter(session_id=session_id).exists())

        # Verify operational event created
        from apps.tracking.models import IdolEvent, IdolEventType
        event = IdolEvent.objects.filter(tracking_session_id=session_id, event_type=IdolEventType.TRACKING_STARTED).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.latitude, 17.3616)
        self.assertEqual(event.longitude, 78.4747)

        # Verify Live Map active endpoint returns this 1 marker with tracking_session_id
        res_active = self.client.get('/api/v1/tracking/active/')
        self.assertEqual(res_active.status_code, 200)
        self.assertEqual(len(res_active.data), 1)
        m = res_active.data[0]
        self.assertEqual(m['gpid'], self.idol.gpid)
        self.assertEqual(m['tracking_session_id'], session_id)
        self.assertEqual(m['latitude'], 17.3616)
        self.assertEqual(m['longitude'], 78.4747)

    def test_new_telemetry_updates_live_marker_and_duplicate_initial_is_ignored(self):
        """Mandatory Test D & 3: New telemetry moves marker; duplicate initial GPS is skipped."""
        self.client.force_authenticate(user=self.pc)
        session = TrackingSession.objects.create(
            assignment=self.assignment,
            status=TrackingSessionStatus.ACTIVE,
            started_at=timezone.now()
        )
        t0 = session.started_at
        # Start initial point
        LocationPoint.objects.create(session=session, latitude=17.3616, longitude=78.4747, recorded_at=t0)

        # Mobile resends initial GPS within 5 seconds -> duplicate skipped
        res_dup = self.client.post('/api/v1/tracking/location/', {
            'session_id': session.id,
            'latitude': 17.3616,
            'longitude': 78.4747,
            'accuracy': 6.0,
            'recorded_at': (t0 + timedelta(seconds=2)).isoformat()
        })
        self.assertEqual(res_dup.status_code, 201)
        self.assertEqual(res_dup.data['status'], 'duplicate_ignored')
        self.assertEqual(LocationPoint.objects.filter(session=session).count(), 1)

        # New movement telemetry arrives
        t1 = t0 + timedelta(seconds=30)
        res_move = self.client.post('/api/v1/tracking/location/', {
            'session_id': session.id,
            'latitude': 17.3625,
            'longitude': 78.4755,
            'speed': 2.5,
            'heading': 45.0,
            'recorded_at': t1.isoformat()
        })
        self.assertEqual(res_move.status_code, 201)
        self.assertEqual(res_move.data['status'], 'recorded')

        # Live map returns updated position
        res_active = self.client.get('/api/v1/tracking/active/')
        self.assertEqual(len(res_active.data), 1)
        self.assertAlmostEqual(res_active.data[0]['latitude'], 17.3625)
        self.assertAlmostEqual(res_active.data[0]['longitude'], 78.4755)

    def test_stop_session_removes_marker_and_creates_event(self):
        """Mandatory Test F: Stopped session immediately disappears from active markers."""
        self.client.force_authenticate(user=self.pc)
        session = TrackingSession.objects.create(
            assignment=self.assignment,
            status=TrackingSessionStatus.ACTIVE,
            started_at=timezone.now()
        )
        LocationPoint.objects.create(session=session, latitude=17.3616, longitude=78.4747, recorded_at=session.started_at)

        # Verify visible before stop
        res1 = self.client.get('/api/v1/tracking/active/')
        self.assertEqual(len(res1.data), 1)

        # Stop session
        res_stop = self.client.post('/api/v1/tracking/stop/', {'session_id': session.id})
        self.assertEqual(res_stop.status_code, 200)

        # Verify omitted immediately after stop
        res2 = self.client.get('/api/v1/tracking/active/')
        self.assertEqual(res2.data, [])

        # Verify TRACKING_STOPPED event created
        from apps.tracking.models import IdolEvent, IdolEventType
        event = IdolEvent.objects.filter(tracking_session=session, event_type=IdolEventType.TRACKING_STOPPED).first()
        self.assertIsNotNone(event)

    def test_session_scoped_journey_isolation(self):
        """Mandatory Test G & 1: Multiple tracking sessions for the same GPID NEVER merge telemetry."""
        self.client.force_authenticate(user=self.pc)
        t_base = timezone.now() - timedelta(hours=3)

        # Session 1: Day 1 (2 points)
        s1 = TrackingSession.objects.create(
            assignment=self.assignment,
            status=TrackingSessionStatus.STOPPED,
            started_at=t_base,
            ended_at=t_base + timedelta(hours=1)
        )
        LocationPoint.objects.create(session=s1, latitude=17.3610, longitude=78.4710, recorded_at=t_base)
        LocationPoint.objects.create(session=s1, latitude=17.3620, longitude=78.4720, recorded_at=t_base + timedelta(minutes=15))

        # Session 2: Day 2 (3 points)
        t2_base = timezone.now() - timedelta(minutes=30)
        s2 = TrackingSession.objects.create(
            assignment=self.assignment,
            status=TrackingSessionStatus.ACTIVE,
            started_at=t2_base
        )
        LocationPoint.objects.create(session=s2, latitude=17.3650, longitude=78.4750, recorded_at=t2_base)
        LocationPoint.objects.create(session=s2, latitude=17.3660, longitude=78.4760, recorded_at=t2_base + timedelta(minutes=5))
        LocationPoint.objects.create(session=s2, latitude=17.3670, longitude=78.4770, recorded_at=t2_base + timedelta(minutes=10))

        # Direct session endpoint: GET /api/v1/tracking/sessions/<id>/journey/
        res_s2 = self.client.get(f'/api/v1/tracking/sessions/{s2.id}/journey/')
        self.assertEqual(res_s2.status_code, 200)
        self.assertEqual(res_s2.data['total_points'], 3)
        self.assertEqual(res_s2.data['tracking_session_id'], s2.id)

        # GPID journey endpoint with session_id scoping: GET /api/v1/tracking/idols/<gpid>/journey/?session_id=<s1.id>
        res_s1 = self.client.get(f'/api/v1/tracking/idols/{self.idol.gpid}/journey/?session_id={s1.id}')
        self.assertEqual(res_s1.status_code, 200)
        self.assertEqual(res_s1.data['total_points'], 2)
        self.assertEqual(res_s1.data['tracking_session_id'], s1.id)

    def test_ingest_procession_events_and_state_updates(self):
        """Test POST /api/v1/tracking/events/ creates IdolEvent and updates idol.procession_state."""
        self.client.force_authenticate(user=self.pc)

        # 1. REACHED_VISARJAN_SITE
        res = self.client.post('/api/v1/tracking/events/', {
            'client_event_id': 'evt-unique-101',
            'gpid': self.idol.gpid,
            'event_type': 'REACHED_VISARJAN_SITE',
            'latitude': 17.3620,
            'longitude': 78.4720,
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'recorded')
        self.assertEqual(res.data['procession_state'], 'AT_VISARJAN')

        self.idol.refresh_from_db()
        self.assertEqual(self.idol.procession_state, 'AT_VISARJAN')

        # 2. VISARJAN_DONE
        res2 = self.client.post('/api/v1/tracking/events/', {
            'client_event_id': 'evt-unique-102',
            'gpid': self.idol.gpid,
            'event_type': 'VISARJAN_DONE',
            'latitude': 17.3621,
            'longitude': 78.4721,
        })
        self.assertEqual(res2.status_code, 201)
        self.assertEqual(res2.data['procession_state'], 'IMMERSION_COMPLETED')

        self.idol.refresh_from_db()
        self.assertEqual(self.idol.procession_state, 'IMMERSION_COMPLETED')

    def test_ingest_procession_events_idempotent(self):
        """Test POST /api/v1/tracking/events/ deduplicates by client_event_id."""
        self.client.force_authenticate(user=self.pc)

        payload = {
            'client_event_id': 'evt-idempotent-999',
            'gpid': self.idol.gpid,
            'event_type': 'SENT_TO_HOLDING',
            'latitude': 17.3630,
            'longitude': 78.4730,
        }
        res1 = self.client.post('/api/v1/tracking/events/', payload)
        self.assertEqual(res1.status_code, 201)
        event_id = res1.data['event_id']

        # Send same client_event_id again
        res2 = self.client.post('/api/v1/tracking/events/', payload)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.data['status'], 'already_recorded')
        self.assertEqual(res2.data['event_id'], event_id)

