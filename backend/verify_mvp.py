"""
Comprehensive MVP Verification Script for Hyderabad Police Ganesh Visarjan Live Tracking System.
Performs verification across:
1. Import Reconciliation
2. GPID Integrity
3. Assignment Integrity
4. Tracking Vertical Slice
5. Offline / Batch Sync
6. RBAC & Jurisdiction
7. PDF Operational Report
9. Security Checks
"""
import os
import sys
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.utils import timezone
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import UserRole
from apps.idols.models import Idol, ImportRun, ImportIssue, ImportIssueType
from apps.assignments.models import Assignment
from apps.tracking.models import TrackingSession, LocationPoint
from apps.reports.services import generate_idol_pdf_report

User = get_user_model()

results = {}

def log_section(title):
    print(f"\n{'='*70}\n{title}\n{'='*70}")

# ==============================================================================
# 1. IMPORT RECONCILIATION
# ==============================================================================
log_section("1. IMPORT RECONCILIATION")
try:
    total_operational_idols = Idol.objects.count()
    missing_gpid_issues = ImportIssue.objects.filter(issue_type=ImportIssueType.MISSING_GPID).count()
    duplicate_gpid_issues = ImportIssue.objects.filter(issue_type=ImportIssueType.DUPLICATE_GPID).count()

    # We take distinct row numbers from the latest run to get the exact file rows
    latest_run = ImportRun.objects.order_by('-started_at').first()
    latest_issues = ImportIssue.objects.filter(import_run=latest_run)
    latest_missing = latest_issues.filter(issue_type=ImportIssueType.MISSING_GPID).count()
    latest_dups = latest_issues.filter(issue_type=ImportIssueType.DUPLICATE_GPID).count()

    reconciled_total = total_operational_idols + latest_missing + latest_dups
    unassigned_ps_codes = Idol.objects.filter(ps_code='').count()

    print(f"Total Source Rows Read: 15,414")
    print(f"Authoritative Unique GPIDs in Operational Database: {total_operational_idols}")
    print(f"Source Rows with Missing GPID: {latest_missing}")
    print(f"Subsequent Duplicate GPID Rows in Source: {latest_dups}")
    print(f"Reconciled Sum (14,930 + 437 + 47): {reconciled_total}")
    print(f"Operational Idols with Missing PS Code: {unassigned_ps_codes}")

    assert total_operational_idols == 14930, f"Expected 14,930 unique GPIDs, got {total_operational_idols}"
    assert latest_missing == 437, f"Expected 437 missing GPIDs, got {latest_missing}"
    assert latest_dups == 47, f"Expected 47 duplicate rows, got {latest_dups}"
    assert reconciled_total == 15414, f"Sum {reconciled_total} != 15,414"
    assert unassigned_ps_codes == 0, f"Expected 0 unassigned PS codes, got {unassigned_ps_codes}"

    results['1_IMPORT_RECONCILIATION'] = 'PASS'
    print(">>> 1. IMPORT RECONCILIATION: PASS")
except Exception as e:
    results['1_IMPORT_RECONCILIATION'] = f'FAIL: {e}'
    print(f">>> 1. IMPORT RECONCILIATION: FAIL ({e})")

# ==============================================================================
# 2. GPID INTEGRITY
# ==============================================================================
log_section("2. GPID INTEGRITY")
try:
    null_gpids = Idol.objects.filter(gpid__isnull=True).count()
    empty_gpids = Idol.objects.filter(gpid='').count()
    from django.db.models import Count
    dup_counts = Idol.objects.values('gpid').annotate(c=Count('id')).filter(c__gt=1).count()

    print(f"Idols with NULL GPID: {null_gpids}")
    print(f"Idols with Empty GPID: {empty_gpids}")
    print(f"Duplicate GPIDs in Database: {dup_counts}")

    assert null_gpids == 0, "Found NULL GPIDs"
    assert empty_gpids == 0, "Found Empty GPIDs"
    assert dup_counts == 0, "Found Duplicate GPIDs in operational database"

    # Test real GPIDs search
    test_gpids = ['HYDCMRZCMNR1749', 'HYDCMRZCMNR2327', 'HYDCMRZCMNR2088']
    for test_gpid in test_gpids:
        idol = Idol.objects.filter(gpid=test_gpid).first()
        assert idol is not None, f"Could not find real GPID {test_gpid}"
        print(f"Verified Real GPID: {idol.gpid} | PS: {idol.police_station} ({idol.ps_code}) | Pandal: {idol.name}")

    # Test case-insensitive search via API
    client = APIClient()
    main_admin = User.objects.filter(role=UserRole.MAIN_OFFICER).first()
    if not main_admin:
        main_admin = User.objects.create_superuser('test_main_admin', 'main@police.gov.in', 'PoliceAdminPass2026!', role=UserRole.MAIN_OFFICER)
    client.force_authenticate(user=main_admin)

    res = client.get('/api/v1/idols/?search=hydcmrzcmnr1749')
    assert res.status_code == 200, f"Search failed with {res.status_code}"
    data = res.json()
    assert data['count'] >= 1, "Case-insensitive GPID search failed"
    assert data['results'][0]['gpid'] == 'HYDCMRZCMNR1749'

    results['2_GPID_INTEGRITY'] = 'PASS'
    print(">>> 2. GPID INTEGRITY: PASS")
except Exception as e:
    results['2_GPID_INTEGRITY'] = f'FAIL: {e}'
    print(f">>> 2. GPID INTEGRITY: FAIL ({e})")

# ==============================================================================
# 3. ASSIGNMENT INTEGRITY
# ==============================================================================
log_section("3. ASSIGNMENT INTEGRITY")
try:
    idol_a = Idol.objects.get(gpid='HYDCMRZCMNR1749')
    idol_b = Idol.objects.get(gpid='HYDCMRZCMNR2327')

    # Clean existing test assignments on these test idols
    Assignment.objects.filter(idol__in=[idol_a, idol_b]).delete()

    constable_1, _ = User.objects.get_or_create(username='test_c1_verify', defaults={'role': UserRole.CONSTABLE, 'police_id': 'PC-8801'})
    constable_2, _ = User.objects.get_or_create(username='test_c2_verify', defaults={'role': UserRole.CONSTABLE, 'police_id': 'PC-8802'})
    sho_user, _ = User.objects.get_or_create(username='test_sho_verify', defaults={'role': UserRole.SHO, 'police_station': 'Charminar'})

    # 1. Assign Constable 1 to Idol A -> Success
    assign_1 = Assignment.assign_constable(idol=idol_a, constable=constable_1, assigned_by=sho_user)
    assert assign_1.is_active is True
    print("Assigned Constable 1 to Idol A successfully.")

    # 2. Try assigning Constable 1 to Idol B while still active on Idol A -> MUST FAIL constraint
    double_assign_failed = False
    try:
        with transaction.atomic():
            Assignment.objects.create(idol=idol_b, constable=constable_1, assigned_by=sho_user, is_active=True)
    except IntegrityError:
        double_assign_failed = True
        print("Prevented double assignment for Constable 1 (DB constraint verified).")
    assert double_assign_failed, "Constraint unique_active_constable_assignment did not trigger!"

    # 3. Try assigning Constable 2 to Idol A while Constable 1 is active -> assign_constable ends old or creates atomic handover
    assign_2 = Assignment.assign_constable(idol=idol_a, constable=constable_2, assigned_by=sho_user)
    assign_1.refresh_from_db()
    assert assign_1.is_active is False, "Old assignment was not ended when new assignment created"
    assert assign_2.is_active is True, "New assignment is not active"
    print("Reassignment ended old assignment and preserved history.")

    # 4. Atomic handover with reason
    constable_3, _ = User.objects.get_or_create(username='test_c3_verify', defaults={'role': UserRole.CONSTABLE, 'police_id': 'PC-8803'})
    handover_assign = assign_2.handover_to_constable(new_constable=constable_3, actor=sho_user, reason="Shift rotation")
    assign_2.refresh_from_db()
    assert assign_2.is_active is False
    assert assign_2.handover_to == constable_3
    assert assign_2.handover_reason == "Shift rotation"
    assert handover_assign.is_active is True
    assert handover_assign.constable == constable_3
    print("Atomic handover verified with reason and chronology preserved.")

    # 5. Historical Query: Who was assigned at timestamp T?
    # Space out timestamps to test exact point-in-time lookup
    t_past_start = timezone.now() - timedelta(hours=3)
    t_past_end = timezone.now() - timedelta(hours=2)
    assign_1.started_at = t_past_start
    assign_1.ended_at = t_past_end
    assign_1.save(update_fields=['started_at', 'ended_at'])

    # Query time when assign_1 was active
    history_user = Assignment.get_constable_for_idol_at(idol_a, t_past_start + timedelta(minutes=30))
    assert history_user == constable_1, f"Expected {constable_1}, got {history_user}"
    print(f"Historical query correctly returned responsible officer: {history_user.username}")

    # 6. Unauthorized assignment attempt (Constable attempting to assign)
    constable_client = APIClient()
    constable_client.force_authenticate(user=constable_1)
    unauth_res = constable_client.post('/api/v1/assignments/create/', {'gpid': idol_b.gpid, 'constable_id': constable_2.id})
    assert unauth_res.status_code == status.HTTP_403_FORBIDDEN, f"Expected 403 Forbidden, got {unauth_res.status_code}"
    print("Unauthorized assignment attempt rejected with HTTP 403 Forbidden.")

    results['3_ASSIGNMENT_INTEGRITY'] = 'PASS'
    print(">>> 3. ASSIGNMENT INTEGRITY: PASS")
except Exception as e:
    results['3_ASSIGNMENT_INTEGRITY'] = f'FAIL: {e}'
    print(f">>> 3. ASSIGNMENT INTEGRITY: FAIL ({e})")

# ==============================================================================
# 4. TRACKING VERTICAL SLICE
# ==============================================================================
log_section("4. TRACKING VERTICAL SLICE")
try:
    idol_track = Idol.objects.get(gpid='HYDCMRZCMNR2088')
    Assignment.objects.filter(idol=idol_track).delete()

    track_constable, _ = User.objects.get_or_create(username='c_track_slice', defaults={'role': UserRole.CONSTABLE, 'police_id': 'PC-9901'})
    Assignment.assign_constable(idol=idol_track, constable=track_constable)

    client_c = APIClient()
    client_c.force_authenticate(user=track_constable)

    # A. Constable checks duty
    curr_res = client_c.get('/api/v1/assignments/current/')
    assert curr_res.status_code == 200
    active_duty = curr_res.json().get('active_assignment')
    assert active_duty is not None, "Constable should have an active assignment"
    assert active_duty['gpid'] == idol_track.gpid
    print("1. Constable authenticated and retrieved server-provided GPID:", idol_track.gpid)

    # B. Start tracking session
    start_res = client_c.post('/api/v1/tracking/start/', {'gpid': idol_track.gpid, 'device_info': 'PoliceHandset-X1'})
    assert start_res.status_code in (200, 201), f"Start tracking failed: {start_res.data}"
    session_id = start_res.json().get('session_id') or start_res.json()['id']
    print(f"2. Tracking session #{session_id} created.")

    # C. Ingest GPS point
    now = timezone.now()
    pt_res = client_c.post('/api/v1/tracking/location/', {
        'session_id': session_id,
        'latitude': 17.3616,
        'longitude': 78.4747,
        'speed': 15.5,
        'heading': 180.0,
        'accuracy': 5.0,
        'recorded_at': now.isoformat()
    })
    assert pt_res.status_code == 201
    assert pt_res.json()['status'] == 'recorded'
    print("3. GPS point recorded via API.")

    # D. Dashboard polling (Officer view)
    client_officer = APIClient()
    client_officer.force_authenticate(user=main_admin)
    dash_res = client_officer.get('/api/v1/idols/dashboard/')
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    active_marker = next((m for m in dash_data['active_markers'] if m['gpid'] == idol_track.gpid), None)
    assert active_marker is not None, "Idol did not appear on live dashboard active markers"
    assert active_marker['connection_state'] == 'LIVE'
    assert active_marker['procession_state'] == 'MOVING'
    print(f"4. Dashboard polled: GPID {idol_track.gpid} appears LIVE and MOVING.")

    # E. Historical Location Lookup
    lookup_res = client_officer.get(f"/api/v1/tracking/idols/{idol_track.gpid}/location-at/?timestamp={now.isoformat()}")
    assert lookup_res.status_code == 200
    lookup_data = lookup_res.json()
    assert lookup_data['gpid'] == idol_track.gpid
    assert abs(lookup_data['nearest_point']['time_difference_seconds']) <= 2
    assert lookup_data['constable']['police_id'] == 'PC-9901'
    print(f"5. Historical timestamp lookup verified: Delta={lookup_data['nearest_point']['time_difference_seconds']}s, Officer={lookup_data['constable']['name']}.")

    # F. Journey retrieval
    journey_res = client_officer.get(f"/api/v1/tracking/idols/{idol_track.gpid}/journey/")
    assert journey_res.status_code == 200
    journey_data = journey_res.json()
    assert journey_data['total_points'] >= 1
    print(f"6. Journey breadcrumbs retrieved: {journey_data['total_points']} points.")

    results['4_TRACKING_VERTICAL_SLICE'] = 'PASS'
    print(">>> 4. TRACKING VERTICAL SLICE: PASS")
except Exception as e:
    results['4_TRACKING_VERTICAL_SLICE'] = f'FAIL: {e}'
    print(f">>> 4. TRACKING VERTICAL SLICE: FAIL ({e})")

# ==============================================================================
# 5. OFFLINE / BATCH SYNC
# ==============================================================================
log_section("5. OFFLINE / BATCH SYNC")
try:
    t0 = timezone.now()
    batch_points = [
        {'latitude': 17.3610 + i * 0.001, 'longitude': 78.4740 + i * 0.001, 'accuracy': 4.0, 'speed': 10.0 + i, 'recorded_at': (t0 + timedelta(seconds=i*30)).isoformat()}
        for i in range(5)
    ]

    # Ingest 5 points in batch
    batch_res = client_c.post('/api/v1/tracking/location/batch/', {'session_id': session_id, 'points': batch_points}, format='json')
    assert batch_res.status_code in (200, 201), f"Batch ingest failed: {batch_res.data}"
    b_data = batch_res.json()
    assert b_data['inserted'] == 5, f"Expected 5 inserted, got {b_data}"
    print(f"Ingested 5 queued offline points: inserted={b_data['inserted']}, skipped={b_data['duplicates_skipped']}")

    # Resend same batch (simulate network retry / duplicate sync)
    retry_res = client_c.post('/api/v1/tracking/location/batch/', {'session_id': session_id, 'points': batch_points}, format='json')
    assert retry_res.status_code in (200, 201)
    r_data = retry_res.json()
    assert r_data['inserted'] == 0, f"Expected 0 new saved points on retry, got {r_data}"
    assert r_data['duplicates_skipped'] == 5, f"Expected 5 skipped duplicates, got {r_data}"
    print(f"Retry batch synchronization cleanly deduplicated: inserted={r_data['inserted']}, duplicates_skipped={r_data['duplicates_skipped']}")

    results['5_OFFLINE_BATCH_SYNC'] = 'PASS'
    print(">>> 5. OFFLINE / BATCH SYNC: PASS")
except Exception as e:
    results['5_OFFLINE_BATCH_SYNC'] = f'FAIL: {e}'
    print(f">>> 5. OFFLINE / BATCH SYNC: FAIL ({e})")

# ==============================================================================
# 6. RBAC & JURISDICTION
# ==============================================================================
log_section("6. RBAC & JURISDICTION")
try:
    acp_charminar, _ = User.objects.get_or_create(username='acp_cmrz_verify', defaults={'role': UserRole.ACP, 'zone': 'Charminar'})
    sho_charminar, _ = User.objects.get_or_create(username='sho_cmrz_verify', defaults={'role': UserRole.SHO, 'police_station': 'Charminar'})

    client_main = APIClient()
    client_main.force_authenticate(user=main_admin)

    client_acp = APIClient()
    client_acp.force_authenticate(user=acp_charminar)

    client_sho = APIClient()
    client_sho.force_authenticate(user=sho_charminar)

    # 1. Main Officer sees all idols
    main_res = client_main.get('/api/v1/idols/')
    assert main_res.json()['count'] == 14930, f"Main officer expected 14,930, got {main_res.json()['count']}"
    print(f"Main Officer city-wide count: {main_res.json()['count']} idols.")

    # 2. ACP Charminar sees only Charminar zone
    acp_res = client_acp.get('/api/v1/idols/')
    acp_count = acp_res.json()['count']
    charminar_actual = Idol.objects.filter(zone='Charminar').count()
    assert acp_count == charminar_actual, f"ACP expected {charminar_actual}, got {acp_count}"
    print(f"ACP Charminar jurisdiction count: {acp_count} idols (matches zone count).")

    # 3. SHO Charminar sees only Charminar police station
    sho_res = client_sho.get('/api/v1/idols/')
    sho_count = sho_res.json()['count']
    sho_actual = Idol.objects.filter(police_station='Charminar').count()
    assert sho_count == sho_actual, f"SHO expected {sho_actual}, got {sho_count}"
    print(f"SHO Charminar station count: {sho_count} idols (matches station count).")

    # 4. Constable cannot browse general idols list
    c_res = client_c.get('/api/v1/idols/')
    # Constable only sees idols they are assigned to
    c_count = c_res.json()['count']
    c_assigned_count = Assignment.objects.filter(constable=track_constable, is_active=True).count()
    assert c_count == c_assigned_count, f"Constable expected {c_assigned_count}, got {c_count}"
    print(f"Constable restricted to active assignment: {c_count} idol.")

    results['6_RBAC_JURISDICTION'] = 'PASS'
    print(">>> 6. RBAC & JURISDICTION: PASS")
except Exception as e:
    results['6_RBAC_JURISDICTION'] = f'FAIL: {e}'
    print(f">>> 6. RBAC & JURISDICTION: FAIL ({e})")

# ==============================================================================
# 7. PDF REPORT GENERATION
# ==============================================================================
log_section("7. PDF REPORT GENERATION")
try:
    sample_gpid = 'HYDCMRZCMNR1749'
    pdf_bytes, report_id = generate_idol_pdf_report(sample_gpid, generated_by_user=main_admin)

    assert pdf_bytes.startswith(b'%PDF'), "Generated file is not a valid PDF header"
    assert len(pdf_bytes) > 2000, f"PDF file size suspiciously small: {len(pdf_bytes)} bytes"

    # Verify report ID format and non-tamper-evident naming
    assert report_id.startswith('HYD-REP-'), f"Report ID format invalid: {report_id}"
    print(f"ReportLab PDF generated successfully for GPID {sample_gpid}:")
    print(f"  Report ID: {report_id}")
    print(f"  Size: {len(pdf_bytes)} bytes")
    print(f"  Integrity Stamp: Report ID + Generated At + Generated By (No false tamper-evident claim)")

    results['7_REPORT_GENERATION'] = 'PASS'
    print(">>> 7. PDF REPORT GENERATION: PASS")
except Exception as e:
    results['7_REPORT_GENERATION'] = f'FAIL: {e}'
    print(f">>> 7. PDF REPORT GENERATION: FAIL ({e})")

# ==============================================================================
# 9. SECURITY CHECKS
# ==============================================================================
log_section("9. SECURITY CHECKS")
try:
    # A. Check .gitignore
    with open('../.gitignore', 'r') as f:
        gitignore_content = f.read()
    assert '*.pem' in gitignore_content, "*.pem missing from .gitignore"
    assert '*.env' in gitignore_content, "*.env missing from .gitignore"
    assert '*.sqlite3' in gitignore_content, "*.sqlite3 missing from .gitignore"
    print("1. .gitignore properly protects *.pem, *.env, and databases.")

    # B. Sensitive contact numbers not returned by standard idol APIs or unprivileged users
    idol_sample = Idol.objects.filter(raw_metadata__mobile_no__isnull=False).exclude(raw_metadata__mobile_no='').first()

    # 1. Standard list view never includes contact_info
    list_res = client_main.get('/api/v1/idols/')
    first_item = list_res.json()['results'][0]
    assert 'contact_info' not in first_item, "contact_info leaked into standard list view"
    assert 'mobile_no' not in first_item, "mobile_no leaked into standard list view"

    # 2. Detail view for Constable or unprivileged role never includes contact_info
    c_detail_res = client_c.get(f'/api/v1/idols/{idol_sample.gpid}/')
    c_detail = c_detail_res.json()
    assert c_detail.get('contact_info') is None, "contact_info exposed to Constable"

    # 3. Passwords must be cryptographically hashed, never plaintext
    assert not main_admin.password.startswith('PoliceAdminPass'), "Password stored in plaintext!"
    assert main_admin.password.startswith(('pbkdf2_sha256$', 'argon2$')), "Password not properly hashed"
    print("2. Sensitive organizer contact numbers protected from standard API serializers.")
    print("3. Password cryptographic hashing verified.")

    # C. Unauthenticated access rejected
    anon_client = APIClient()
    unauth = anon_client.get('/api/v1/idols/')
    assert unauth.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    print("4. Unauthenticated requests to protected endpoints rejected with HTTP 401/403.")

    results['9_SECURITY_CHECKS'] = 'PASS'
    print(">>> 9. SECURITY CHECKS: PASS")
except Exception as e:
    results['9_SECURITY_CHECKS'] = f'FAIL: {e}'
    print(f">>> 9. SECURITY CHECKS: FAIL ({e})")

# ==============================================================================
# SUMMARY
# ==============================================================================
log_section("MVP VERIFICATION SUMMARY")
for k, v in results.items():
    print(f"{k:30}: {v}")
