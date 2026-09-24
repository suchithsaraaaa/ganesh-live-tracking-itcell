"""
Isolated Test Database Seeding Script.
HYDERABAD POLICE GANESH VISARJAN TRACKING SYSTEM

Populates ganesh_tracking_isolated_loadtest with:
- 1 Main Officer (admin)
- 20 ACP / SHO officers
- 400 Constables
- 500 Test Idols
- 300 Active Assignments
- 300 Active Tracking Sessions

STRICT SAFETY GUARANTEE:
Validates that the active database is NOT the production database ('ganesh_tracking')
before executing any write operations.
"""
import os
import sys
import django
from django.utils import timezone

# Setup Django environment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.db import connection, transaction
from apps.accounts.models import User, UserRole
from apps.idols.models import Idol, ProcessionState, GeocodingConfidence
from apps.assignments.models import Assignment
from apps.tracking.models import TrackingSession, TrackingSessionStatus, LocationPoint

from django.contrib.auth.hashers import make_password

def verify_safety():
    db_name = connection.settings_dict['NAME']
    print(f"[*] Target database: {db_name}")
    if db_name in ['ganesh_tracking', 'prod', 'production']:
        raise RuntimeError(
            f"CRITICAL SAFETY VIOLATION: Refusing to seed load test data into production database '{db_name}'!"
        )
    print("[+] Database safety verified. Proceeding with isolated seed.")

def seed():
    verify_safety()
    with transaction.atomic():
        print("[*] Pre-computing valid PBKDF2 password hash...")
        hashed_pwd = make_password('Police@Test2026!')

        print("[*] Creating administrative officers...")
        admin, _ = User.objects.get_or_create(
            username='loadtest_admin',
            defaults={
                'role': UserRole.MAIN_OFFICER,
                'email': 'loadtest_admin@police.gov.in',
                'police_id': 'TS-HQ-0001',
                'phone_number': '9999900000',
                'password': hashed_pwd,
            }
        )
        if admin.password != hashed_pwd:
            admin.password = hashed_pwd
            admin.save()

        # 20 Station Officers (SHO)
        station_names = [
            'Charminar', 'Afzalgunj', 'Mirchowk', 'Goshamahal', 'Mangalhat',
            'Begum Bazar', 'Shah Ali Banda', 'Hussaini Alam', 'Kamalapuri', 'Bahadurpura',
            'Abids', 'Sultan Bazar', 'Nampally', 'Chaderghat', 'Malakpet',
            'Asif Nagar', 'Habeeb Nagar', 'Golconda', 'Langer Houz', 'Kulsumpura'
        ]
        shos = []
        for i, s_name in enumerate(station_names):
            sho, _ = User.objects.get_or_create(
                username=f'loadtest_sho_{i+1:02d}',
                defaults={
                    'role': UserRole.SHO,
                    'police_station': s_name,
                    'zone': 'Central Zone' if i < 10 else 'South Zone',
                    'police_id': f'TS-SHO-{i+1:03d}',
                    'phone_number': f'999991{i+1:04d}',
                    'password': hashed_pwd,
                }
            )
            if sho.password != hashed_pwd:
                sho.password = hashed_pwd
                sho.save()
            shos.append(sho)

        print("[*] Creating 400 Constable accounts...")
        constables = []
        for i in range(1, 401):
            ps = station_names[(i - 1) % len(station_names)]
            c, _ = User.objects.get_or_create(
                username=f'loadtest_pc_{i:03d}',
                defaults={
                    'role': UserRole.CONSTABLE,
                    'police_station': ps,
                    'zone': 'Central Zone' if (i % 2 == 0) else 'South Zone',
                    'police_id': f'TS-PC-{i:04d}',
                    'phone_number': f'99998{i:05d}',
                    'password': hashed_pwd,
                }
            )
            if c.password != hashed_pwd:
                c.password = hashed_pwd
                c.save()
            constables.append(c)

        print("[*] Creating 500 Test Idols with valid geocoded coordinates...")
        # Base coordinates centered in Hyderabad (17.36 to 17.42, 78.44 to 78.50)
        base_lat = 17.3850
        base_lon = 78.4867
        idols = []
        for i in range(1, 501):
            ps = station_names[(i - 1) % len(station_names)]
            # Disperse around PS
            lat = base_lat + ((i % 25) - 12) * 0.003
            lon = base_lon + ((i // 25) - 10) * 0.003
            height = 15.0 + (i % 15)  # 15 to 29 ft
            gpid = f"HYD-LOAD-{ps[:4].upper()}-{i:04d}"
            
            idol, _ = Idol.objects.get_or_create(
                gpid=gpid,
                defaults={
                    'name': f"Test Idol {gpid}",
                    'association_name': f"Test Utsav Samithi {i}",
                    'zone': 'Central Zone' if (i % 2 == 0) else 'South Zone',
                    'police_station': ps,
                    'idol_height': height,
                    'procession_state': ProcessionState.NOT_STARTED,
                    'latitude': lat,
                    'longitude': lon,
                    'geocoding_confidence': GeocodingConfidence.EXACT,
                    'address': f"Pandal Site #{i}, {ps}, Hyderabad",
                    'immersion_date': timezone.localdate(),
                }
            )
            idols.append(idol)

        print("[*] Assigning 300 constables to 300 idols and starting tracking sessions...")
        active_sessions = []
        for i in range(300):
            c = constables[i]
            idol = idols[i]
            
            # Create active assignment
            assignment = Assignment.objects.filter(idol=idol, is_active=True).first()
            if not assignment:
                assignment = Assignment.objects.create(
                    idol=idol,
                    constable=c,
                    assigned_by=admin,
                    is_active=True,
                    officer_name_snapshot=c.get_full_name() or c.username,
                    police_id_snapshot=c.police_id,
                )

            # Update idol state
            idol.procession_state = ProcessionState.MOVING if i % 2 == 0 else ProcessionState.TRACKING
            idol.save(update_fields=['procession_state'])

            # Create active tracking session
            session = TrackingSession.objects.filter(assignment=assignment, status=TrackingSessionStatus.ACTIVE).first()
            if not session:
                session = TrackingSession.objects.create(
                    assignment=assignment,
                    device_info=f"LoadTest-Android-{i+1:03d}",
                    status=TrackingSessionStatus.ACTIVE,
                    started_at=timezone.now() - timezone.timedelta(minutes=30),
                )
            
            # Initial location point
            if not session.location_points.exists():
                LocationPoint.objects.create(
                    session=session,
                    latitude=float(idol.latitude),
                    longitude=float(idol.longitude),
                    accuracy=10.0,
                    speed=2.5,
                    heading=90.0,
                    recorded_at=timezone.now() - timezone.timedelta(minutes=1),
                )
            active_sessions.append(session)

        print(f"[+] Successfully seeded:")
        print(f"    - Officers: {len(shos) + 1}")
        print(f"    - Constables: {len(constables)}")
        print(f"    - Idols: {len(idols)}")
        print(f"    - Active Assignments: 300")
        print(f"    - Active Tracking Sessions: {len(active_sessions)}")

if __name__ == '__main__':
    seed()
