"""
Race Condition & Concurrency Invariant Test Suite.
HYDERABAD POLICE GANESH VISARJAN TRACKING SYSTEM

Executes concurrent operational race condition tests:
1. Double-assignment prevention (Same officer assigned to 2 idols concurrently)
2. Double-assignment prevention (2 officers assigned to same idol concurrently)
3. Admin force-end under concurrent high-frequency GPS telemetry
4. Immediate reassignment of officer to a new idol post-termination
5. Verification that telemetry & historical session are preserved without corruption
"""
import asyncio
import aiohttp
import time
import sys
from datetime import datetime, timezone

async def test_race_conditions(base_url, admin_user, admin_pass):
    print("\n" + "=" * 80)
    print("  EXECUTING RACE CONDITION & CONCURRENCY INVARIANT TEST SUITE")
    print(f"  Target: {base_url}")
    print("=" * 80)

    async with aiohttp.ClientSession() as session:
        # 1. Login admin
        login_url = f"{base_url}/api/v1/auth/login/"
        async with session.post(login_url, json={'username': admin_user, 'password': admin_pass}) as resp:
            assert resp.status == 200, f"Admin login failed: {resp.status}"
            cookies = {k: v.value for k, v in resp.cookies.items()}
            csrf = cookies.get('csrftoken', '')
            auth_headers = {'X-CSRFToken': csrf, 'Referer': base_url}
            print("[+] Admin authenticated successfully.")

    async with aiohttp.ClientSession(cookies=cookies, headers=auth_headers) as session:
        # Fetch idols and constables for testing
        async with session.get(f"{base_url}/api/v1/assignments/?page=1") as resp:
            assert resp.status == 200
            data = await resp.json()
            existing_assignments = data.get('results', [])

        print(f"[+] Loaded existing assignments: {len(existing_assignments)}")

        # -------------------------------------------------------------------------
        # TEST 1: Double-assignment race: Officer A -> GPID 1 AND Officer A -> GPID 2
        # -------------------------------------------------------------------------
        print("\n[*] TEST 1: Double-Assignment Prevention (Same officer, 2 different idols simultaneously)...")
        # Find 2 unassigned test idols and 1 free constable
        async with session.get(f"{base_url}/api/v1/auth/users/?role=CONSTABLE&page_size=10") as resp:
            c_data = await resp.json()
            test_officer = c_data['results'][0]['id']

        # Pick two idols
        async with session.get(f"{base_url}/api/v1/idols/?page_size=10") as resp:
            i_data = await resp.json()
            idol_1 = i_data['results'][0]['gpid']
            idol_2 = i_data['results'][1]['gpid']

        # Attempt simultaneous POST to /api/v1/assignments/create/
        assign_url = f"{base_url}/api/v1/assignments/create/"
        req1 = session.post(assign_url, json={'gpid': idol_1, 'constable_id': test_officer})
        req2 = session.post(assign_url, json={'gpid': idol_2, 'constable_id': test_officer})

        res1, res2 = await asyncio.gather(req1, req2, return_exceptions=True)
        s1 = res1.status if hasattr(res1, 'status') else 500
        s2 = res2.status if hasattr(res2, 'status') else 500
        
        statuses = [s1, s2]
        success_count = sum(1 for s in statuses if s in [200, 201])
        rejected_count = sum(1 for s in statuses if s in [400, 409])
        print(f"    Statuses: [{s1}, {s2}] -> Success: {success_count}, Rejected: {rejected_count}")
        assert success_count <= 1, f"CRITICAL INVARIANT VIOLATION: Officer was assigned to multiple idols simultaneously! ({statuses})"
        print("[+] PASS: Invariant preserved: Exactly one (or zero) assignment succeeded. Double-assignment prevented.")

        # -------------------------------------------------------------------------
        # TEST 2: Double-assignment race: GPID 1 -> Officer A AND GPID 1 -> Officer B
        # -------------------------------------------------------------------------
        print("\n[*] TEST 2: Double-Assignment Prevention (Two officers, same idol simultaneously)...")
        officer_a = c_data['results'][1]['id']
        officer_b = c_data['results'][2]['id']
        target_idol = i_data['results'][2]['gpid']

        reqA = session.post(assign_url, json={'gpid': target_idol, 'constable_id': officer_a})
        reqB = session.post(assign_url, json={'gpid': target_idol, 'constable_id': officer_b})

        resA, resB = await asyncio.gather(reqA, reqB, return_exceptions=True)
        sA = resA.status if hasattr(resA, 'status') else 500
        sB = resB.status if hasattr(resB, 'status') else 500
        statuses_2 = [sA, sB]
        success_count_2 = sum(1 for s in statuses_2 if s in [200, 201])
        print(f"    Statuses: [{sA}, {sB}] -> Success: {success_count_2}")
        assert success_count_2 <= 1, f"CRITICAL INVARIANT VIOLATION: Multiple officers assigned to same idol! ({statuses_2})"
        print("[+] PASS: Invariant preserved: Same idol cannot have multiple active assignments.")

        # -------------------------------------------------------------------------
        # TEST 3: Admin Force-End under concurrent GPS Telemetry
        # -------------------------------------------------------------------------
        print("\n[*] TEST 3: Admin Force-End under concurrent GPS telemetry...")
        # Get active tracking sessions
        async with session.get(f"{base_url}/api/v1/tracking/active/") as resp:
            active_list = await resp.json()
            assert len(active_list) > 0, "Need at least 1 active tracking session for force-end test"
            target_marker = active_list[0]
            target_gpid = target_marker['gpid']
            target_session_id = target_marker['tracking_session_id']

        # Find active assignment ID
        async with session.get(f"{base_url}/api/v1/assignments/?gpid={target_gpid}") as a_resp:
            a_data = await a_resp.json()
            active_assignments = [a for a in a_data.get('results', []) if a.get('is_active')]
            assert len(active_assignments) > 0, f"No active assignment found for {target_gpid}"
            target_assignment_id = active_assignments[0]['id']
            print(f"    Selected GPID {target_gpid} | Assignment #{target_assignment_id} | Session #{target_session_id}")

        # Concurrently send telemetry pings while triggering admin force-end
        telemetry_url = f"{base_url}/api/v1/tracking/location/"
        force_end_url = f"{base_url}/api/v1/assignments/{target_assignment_id}/end/"
        
        async def send_burst_telemetry():
            results = []
            for k in range(5):
                payload = {
                    'session_id': target_session_id,
                    'latitude': 17.3850 + k * 0.0001,
                    'longitude': 78.4867 + k * 0.0001,
                    'accuracy': 5.0,
                    'speed': 2.0,
                    'heading': 90.0,
                    'recorded_at': datetime.now(timezone.utc).isoformat(),
                }
                try:
                    async with session.post(telemetry_url, json=payload, timeout=5) as r:
                        results.append(r.status)
                except Exception:
                    results.append(500)
                await asyncio.sleep(0.05)
            return results

        async def trigger_force_end():
            await asyncio.sleep(0.08)  # fire during telemetry burst
            try:
                async with session.post(force_end_url, json={'reason': 'Race Condition Load Test'}) as r:
                    res_json = await r.json() if r.status < 500 else await r.text()
                    return r.status, res_json
            except Exception as e:
                return 500, str(e)

        telemetry_future = asyncio.create_task(send_burst_telemetry())
        force_end_future = asyncio.create_task(trigger_force_end())

        telemetry_res, force_end_res = await asyncio.gather(telemetry_future, force_end_future)
        fe_status, fe_data = force_end_res
        print(f"    Telemetry burst statuses: {telemetry_res}")
        print(f"    Force-end status: {fe_status} -> {fe_data}")
        assert fe_status in [200, 201], f"Force-end failed: {fe_status} {fe_data}"

        # -------------------------------------------------------------------------
        # TEST 4: Verification of Force-End Invariants
        # -------------------------------------------------------------------------
        print("\n[*] TEST 4: Verifying Force-End Post-Conditions...")
        # 1. Assignment is inactive
        assert fe_data['assignment']['is_active'] is False, "Assignment is still marked active!"
        constable_id = fe_data['assignment']['constable']
        async with session.get(f"{base_url}/api/v1/assignments/?constable_id={constable_id}&is_active=true") as resp:
            a_data = await resp.json()
            active_for_officer = a_data.get('results', [])
            assert len(active_for_officer) == 0, "Officer still has active assignments!"
            print(f"    [+] Assignment #{target_assignment_id} successfully marked inactive; Officer #{constable_id} is free.")

        # 2. Tracking session is terminated, NOT deleted
        async with session.get(f"{base_url}/api/v1/tracking/active/") as resp:
            active_now = await resp.json()
            still_active = [m for m in active_now if m['gpid'] == target_gpid]
            assert len(still_active) == 0, "Idol is still in active tracking markers list!"
            print("    [+] Idol cleanly removed from active tracking map markers.")

        # 3. Journey breadcrumbs remain intact in database
        async with session.get(f"{base_url}/api/v1/tracking/idols/{target_gpid}/journey/?session_id={target_session_id}") as resp:
            j_data = await resp.json()
            points_count = len(j_data.get('points', []))
            assert points_count > 0, "Telemetry points were deleted or corrupted!"
            print(f"    [+] Historical telemetry breadcrumbs intact ({points_count} points preserved).")

        # 4. Immediate re-assignment of freed officer is possible
        print(f"\n[*] TEST 5: Immediate Reassignment of Freed Officer #{constable_id}...")
        async with session.post(assign_url, json={'gpid': target_gpid, 'constable_id': constable_id}) as resp:
            reassign_status = resp.status
            reassign_data = await resp.json()
            assert reassign_status in [200, 201], f"Re-assignment failed: {reassign_status} {reassign_data}"
            print(f"    [+] GPID {target_gpid} immediately reassigned to freed Officer #{constable_id} (Status: {reassign_status}).")

    print("\n" + "=" * 80)
    print("  ALL CONCURRENCY & RACE CONDITION INVARIANTS VERIFIED (100% PASS)")
    print("=" * 80)

if __name__ == '__main__':
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001"
    asyncio.run(test_race_conditions(base_url, "loadtest_admin", "Police@Test2026!"))
