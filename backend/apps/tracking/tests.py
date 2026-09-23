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

    def test_start_tracking_exact_within_30m_allowed(self):
        # 0.00027 deg latitude ~ 30 meters
        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'latitude': 17.36187,
            'longitude': 78.4747
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'ACTIVE')

    def test_start_tracking_exact_beyond_60m_rejected(self):
        # 0.00055 deg latitude ~ 61 meters (> 50m)
        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'latitude': 17.36215,
            'longitude': 78.4747
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('START_GATE_REJECTED', res.data['error'])
        self.assertGreater(res.data['distance_meters'], 50.0)

    def test_start_tracking_high_confidence_within_30m_allowed(self):
        self.idol.geocoding_confidence = GeocodingConfidence.HIGH
        self.idol.save(update_fields=['geocoding_confidence'])

        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'latitude': 17.36187,
            'longitude': 78.4747
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'ACTIVE')

    def test_start_tracking_medium_locality_rejected(self):
        # Even if officer is physically near the approximate coordinate, locality-level cannot authorize 50m gate
        self.idol.geocoding_confidence = GeocodingConfidence.MEDIUM
        self.idol.save(update_fields=['geocoding_confidence'])

        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'latitude': 17.3616,
            'longitude': 78.4747
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('locality-level', res.data['error'])
        self.assertFalse(res.data['start_gate_eligible'])

    def test_start_tracking_unresolved_rejected(self):
        self.idol.geocoding_confidence = GeocodingConfidence.UNRESOLVED
        self.idol.latitude = None
        self.idol.longitude = None
        self.idol.save(update_fields=['geocoding_confidence', 'latitude', 'longitude'])

        res = self.client.post(reverse('tracking-start'), {
            'assignment_id': self.assignment.id,
            'latitude': 17.3616,
            'longitude': 78.4747
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn('unresolved', res.data['error'])
        self.assertFalse(res.data['start_gate_eligible'])

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
        self.assertIn('events', res.data)
        # Assignment created event exists
        event_types = [e['event_type'] for e in res.data['events']]
        self.assertIn('ASSIGNMENT_CREATED', event_types)
