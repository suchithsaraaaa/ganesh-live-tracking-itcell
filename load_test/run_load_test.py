"""
High-Concurrency HTTP Load Testing Runner.
HYDERABAD POLICE GANESH VISARJAN TRACKING SYSTEM

Executes concurrent, multi-user HTTP-level load tests across Stages 0 - 5:
- Stage 0: 10 web users + 10 tracking sessions (Baseline)
- Stage 1: 100 web users + 50 tracking sessions
- Stage 2: 200 web users + 100 tracking sessions
- Stage 3: 300 web users + 200 tracking sessions
- Stage 4: 400 web users + 300 tracking sessions (TARGET)
- Stage 5: 500 web users + 300 tracking sessions (STRESS / SATURATION)

Features:
- Pure asynchronous I/O (aiohttp)
- Realistic weighted traffic mix (40% dashboard, 20% live map, 15% assignments, 10% users, 10% reports, 5% auth)
- High-frequency GPS telemetry breadcrumb ingestion (every 3 seconds per device)
- Telemetry idempotency testing (duplicate breadcrumb rejection)
- Real-time percentiles: p50, p90, p95, p99, max
- Detailed output format conforming to MEASURED test evidence rules.
"""
import asyncio
import aiohttp
import time
import random
import json
import argparse
import sys
from datetime import datetime, timezone

# Stage definitions
STAGE_CONFIGS = {
    0: {'users': 10,  'sessions': 10,  'duration': 60,  'name': 'Stage 0 — Baseline (10 users, 10 sessions)'},
    1: {'users': 100, 'sessions': 50,  'duration': 120, 'name': 'Stage 1 — Ramp-up (100 users, 50 sessions)'},
    2: {'users': 200, 'sessions': 100, 'duration': 120, 'name': 'Stage 2 — Intermediate (200 users, 100 sessions)'},
    3: {'users': 300, 'sessions': 200, 'duration': 180, 'name': 'Stage 3 — Pre-Target (300 users, 200 sessions)'},
    4: {'users': 400, 'sessions': 300, 'duration': 240, 'name': 'Stage 4 — Acceptance Target (400 users, 300 sessions)'},
    5: {'users': 500, 'sessions': 300, 'duration': 180, 'name': 'Stage 5 — Stress / Saturation (500 users, 300 sessions)'},
}

class MetricsCollector:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.start_time = None
        self.end_time = None
        self.latencies = {}  # endpoint -> list of ms
        self.status_codes = {}
        self.telemetry_sent = 0
        self.telemetry_success = 0
        self.telemetry_duplicates = 0
        self.telemetry_failed = 0
        self.errors = []

    def start(self):
        self.start_time = time.time()

    def stop(self):
        self.end_time = time.time()

    async def record_request(self, endpoint, status, duration_ms, is_telemetry=False, is_dup=False):
        async with self.lock:
            if endpoint not in self.latencies:
                self.latencies[endpoint] = []
            self.latencies[endpoint].append(duration_ms)
            
            self.status_codes[status] = self.status_codes.get(status, 0) + 1
            
            if is_telemetry:
                self.telemetry_sent += 1
                if 200 <= status < 300:
                    if is_dup:
                        self.telemetry_duplicates += 1
                    else:
                        self.telemetry_success += 1
                else:
                    self.telemetry_failed += 1

    def calculate_percentiles(self, vals):
        if not vals:
            return {'count': 0, 'avg': 0, 'p50': 0, 'p90': 0, 'p95': 0, 'p99': 0, 'max': 0}
        s = sorted(vals)
        n = len(s)
        return {
            'count': n,
            'avg': round(sum(s) / n, 2),
            'min': round(s[0], 2),
            'p50': round(s[int(n * 0.50)], 2),
            'p90': round(s[int(n * 0.90)], 2),
            'p95': round(s[min(int(n * 0.95), n - 1)], 2),
            'p99': round(s[min(int(n * 0.99), n - 1)], 2),
            'max': round(s[-1], 2),
        }

    def report(self):
        total_duration = (self.end_time - self.start_time) if self.end_time else 1
        all_latencies = []
        for l in self.latencies.values():
            all_latencies.extend(l)
        
        total_reqs = len(all_latencies)
        rps = round(total_reqs / total_duration, 2)
        overall = self.calculate_percentiles(all_latencies)
        
        success_count = sum(c for code, c in self.status_codes.items() if 200 <= code < 300)
        err_4xx = sum(c for code, c in self.status_codes.items() if 400 <= code < 500)
        err_5xx = sum(c for code, c in self.status_codes.items() if 500 <= code < 600)
        error_rate = round(((err_4xx + err_5xx) / total_reqs * 100), 2) if total_reqs else 0.0

        endpoint_reports = {}
        for ep, lats in self.latencies.items():
            endpoint_reports[ep] = self.calculate_percentiles(lats)

        return {
            'duration_sec': round(total_duration, 2),
            'total_requests': total_reqs,
            'requests_per_sec': rps,
            'success_count': success_count,
            'error_4xx': err_4xx,
            'error_5xx': err_5xx,
            'error_rate_pct': error_rate,
            'overall_latency': overall,
            'endpoints': endpoint_reports,
            'telemetry': {
                'sent': self.telemetry_sent,
                'accepted': self.telemetry_success,
                'duplicates_ignored': self.telemetry_duplicates,
                'failed': self.telemetry_failed,
            },
            'status_codes': self.status_codes
        }

async def authenticate_user(session, base_url, username, password):
    url = f"{base_url}/api/v1/auth/login/"
    payload = {'username': username, 'password': password}
    try:
        t0 = time.time()
        async with session.post(url, json=payload, timeout=15) as resp:
            dur = (time.time() - t0) * 1000
            if resp.status == 200:
                data = await resp.json()
                # Django session auth uses sessionid cookie or token
                token = data.get('token') or data.get('access')
                return token, dur
            return None, dur
    except Exception as e:
        return None, 15000

async def simulate_web_user(user_id, base_url, metrics, stop_event, auth_headers):
    """
    Simulates an authenticated web user:
    - 40%: Dashboard / operational monitoring
    - 20%: Live tracking active markers
    - 15%: Officer assignment management
    - 10%: User management
    - 10%: Reports registry
    - 5%: Auth check (/me/)
    """
    endpoints_pool = [
        ('dashboard', '/api/v1/idols/dashboard/', 40),
        ('active_tracking', '/api/v1/tracking/active/', 20),
        ('assignments', '/api/v1/assignments/', 15),
        ('users', '/api/v1/users/', 10),
        ('reports', '/api/v1/reports/', 10),
        ('auth_me', '/api/v1/auth/me/', 5),
    ]
    # Build weighted selection list
    weighted = []
    for name, path, weight in endpoints_pool:
        weighted.extend([(name, path)] * weight)

    async with aiohttp.ClientSession(headers=auth_headers) as session:
        while not stop_event.is_set():
            name, path = random.choice(weighted)
            url = f"{base_url}{path}"
            
            # Add realistic filter variants for dashboard and assignments
            if name == 'dashboard':
                filter_choice = random.choice(['all', 'zone', 'height', 'immr'])
                if filter_choice == 'zone':
                    url += "?zone=Central+Zone"
                elif filter_choice == 'height':
                    url += "?height_bucket=21_25"
                elif filter_choice == 'immr':
                    url += "?immersions_today=true"
            elif name == 'assignments':
                if random.random() < 0.5:
                    url += "?page=1"

            t0 = time.time()
            status = 0
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    status = resp.status
                    await resp.read()
            except asyncio.TimeoutError:
                status = 504
            except Exception:
                status = 502
            dur = (time.time() - t0) * 1000
            
            await metrics.record_request(path, status, dur)
            # Realistic officer pacing: 1 to 3 seconds think time between user clicks
            await asyncio.sleep(random.uniform(1.0, 3.0))

async def simulate_mobile_device(device_idx, base_url, metrics, stop_event, auth_headers, session_id):
    """
    Simulates a ground staff mobile device:
    - Sends GPS telemetry breadcrumbs every 3 seconds to /api/v1/tracking/location/
    - Real-time coordinates along a corridor in Hyderabad
    - Periodic duplicate transmission (every 10 pings) to verify backend idempotency
    """
    base_lat = 17.3850 + (device_idx % 20) * 0.002
    base_lon = 78.4867 + (device_idx // 20) * 0.002
    step = 0

    url = f"{base_url}/api/v1/tracking/location/"
    async with aiohttp.ClientSession(headers=auth_headers) as session:
        while not stop_event.is_set():
            step += 1
            # Move slightly north-east along procession corridor
            cur_lat = round(base_lat + step * 0.0001, 6)
            cur_lon = round(base_lon + step * 0.0001, 6)
            timestamp_iso = datetime.now(timezone.utc).isoformat()

            payload = {
                'session_id': session_id,
                'latitude': cur_lat,
                'longitude': cur_lon,
                'accuracy': round(random.uniform(4.0, 15.0), 1),
                'speed': round(random.uniform(0.5, 3.5), 2),
                'heading': round(random.uniform(45.0, 90.0), 1),
                'recorded_at': timestamp_iso,
            }

            t0 = time.time()
            status = 0
            is_dup = False
            try:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    status = resp.status
                    resp_json = await resp.json() if resp.status < 500 else {}
                    if resp_json.get('status') == 'duplicate_ignored':
                        is_dup = True
            except asyncio.TimeoutError:
                status = 504
            except Exception:
                status = 502
            dur = (time.time() - t0) * 1000
            await metrics.record_request('/api/v1/tracking/location/', status, dur, is_telemetry=True, is_dup=is_dup)

            # Test Idempotency: Every 10 pings, resend the exact same coordinates and timestamp
            if step % 10 == 0:
                t0 = time.time()
                try:
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        status = resp.status
                        resp_json = await resp.json() if resp.status < 500 else {}
                        is_dup = resp_json.get('status') == 'duplicate_ignored'
                except Exception:
                    status = 502
                dur = (time.time() - t0) * 1000
                await metrics.record_request('/api/v1/tracking/location/', status, dur, is_telemetry=True, is_dup=is_dup)

            # Android app interval is 3.0 seconds
            await asyncio.sleep(3.0)

async def run_stage(stage_num, base_url, admin_user, admin_pass):
    cfg = STAGE_CONFIGS[stage_num]
    num_users = cfg['users']
    num_sessions = cfg['sessions']
    duration = cfg['duration']

    print("\n" + "=" * 80)
    print(f"  RUNNING LOAD TEST: {cfg['name']}")
    print(f"  Target: {num_users} Concurrent Web Users | {num_sessions} Active Telemetry Sessions")
    print(f"  Duration: {duration} seconds | Base URL: {base_url}")
    print("=" * 80)

    # 1. Authenticate admin / get auth cookie or token
    print("[*] Pre-authenticating test sessions...")
    auth_headers = {}
    async with aiohttp.ClientSession() as setup_session:
        # Test login latency
        token, login_ms = await authenticate_user(setup_session, base_url, admin_user, admin_pass)
        print(f"[+] Admin authentication response time: {login_ms:.2f} ms")
        if token:
            auth_headers['Authorization'] = f"Bearer {token}"

        # Fetch active tracking sessions from isolated environment
        try:
            async with setup_session.get(f"{base_url}/api/v1/tracking/active/", headers=auth_headers) as resp:
                if resp.status == 200:
                    markers = await resp.json()
                    available_session_ids = [
                        m['tracking_session_id'] for m in markers if m.get('tracking_session_id')
                    ]
                    print(f"[+] Discovered {len(available_session_ids)} active tracking sessions in environment.")
                else:
                    available_session_ids = list(range(1, num_sessions + 1))
        except Exception as e:
            available_session_ids = list(range(1, num_sessions + 1))

    # Pad session IDs if needed
    if len(available_session_ids) < num_sessions:
        for i in range(1, num_sessions + 1):
            if i not in available_session_ids:
                available_session_ids.append(i)

    metrics = MetricsCollector()
    stop_event = asyncio.Event()
    metrics.start()

    tasks = []
    # Spawn Web Users
    print(f"[*] Spawning {num_users} concurrent authenticated web users...")
    for uid in range(num_users):
        t = asyncio.create_task(simulate_web_user(uid, base_url, metrics, stop_event, auth_headers))
        tasks.append(t)

    # Spawn Mobile GPS Devices
    print(f"[*] Spawning {num_sessions} active GPS tracking mobile devices (3s telemetry interval)...")
    for s_idx in range(num_sessions):
        sess_id = available_session_ids[s_idx % len(available_session_ids)]
        t = asyncio.create_task(simulate_mobile_device(s_idx, base_url, metrics, stop_event, auth_headers, sess_id))
        tasks.append(t)

    print(f"[+] All {len(tasks)} concurrent tasks running. Monitoring for {duration} seconds...")
    # Monitor loop
    start_time = time.time()
    while time.time() - start_time < duration:
        await asyncio.sleep(10)
        elapsed = int(time.time() - start_time)
        res = metrics.report()
        print(f"    [{elapsed:>3}s / {duration}s] Req: {res['total_requests']:>6} | "
              f"RPS: {res['requests_per_sec']:>6.1f} | "
              f"p95: {res['overall_latency']['p95']:>6.1f}ms | "
              f"Errors: {res['error_rate_pct']:>4.1f}% | "
              f"GPS: {res['telemetry']['sent']} sent ({res['telemetry']['duplicates_ignored']} dups)")

    print("[*] Test window finished. Signaling tasks to stop...")
    stop_event.set()
    await asyncio.gather(*tasks, return_exceptions=True)
    metrics.stop()

    summary = metrics.report()
    summary_file = f"load_test_stage_{stage_num}_results.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 80)
    print(f"  STAGE {stage_num} COMPLETED RESULTS SUMMARY")
    print("=" * 80)
    print(f"  Duration:           {summary['duration_sec']} s")
    print(f"  Total Requests:     {summary['total_requests']}")
    print(f"  Throughput (RPS):   {summary['requests_per_sec']} req/s")
    print(f"  Successful (2xx):   {summary['success_count']}")
    print(f"  Client Error (4xx): {summary['error_4xx']}")
    print(f"  Server Error (5xx): {summary['error_5xx']}")
    print(f"  Error Rate:         {summary['error_rate_pct']} %")
    print(f"  Overall Latency:")
    print(f"    - Avg:            {summary['overall_latency']['avg']} ms")
    print(f"    - p50 (Median):   {summary['overall_latency']['p50']} ms")
    print(f"    - p90:            {summary['overall_latency']['p90']} ms")
    print(f"    - p95:            {summary['overall_latency']['p95']} ms")
    print(f"    - p99:            {summary['overall_latency']['p99']} ms")
    print(f"    - Max:            {summary['overall_latency']['max']} ms")
    print(f"  Telemetry Ingestion:")
    print(f"    - Breadcrumbs:    {summary['telemetry']['sent']}")
    print(f"    - Accepted:       {summary['telemetry']['accepted']}")
    print(f"    - Duplicates Ok:  {summary['telemetry']['duplicates_ignored']}")
    print(f"    - Failed:         {summary['telemetry']['failed']}")
    print("\n  Per-Endpoint Latency Breakdown:")
    for ep, stat in summary['endpoints'].items():
        print(f"    {ep:<32} Req: {stat['count']:<6} | p50: {stat['p50']:>6.1f}ms | p95: {stat['p95']:>6.1f}ms | Max: {stat['max']:>7.1f}ms")
    print("=" * 80)
    return summary

def main():
    parser = argparse.ArgumentParser(description="Concurrent HTTP Load Test Runner")
    parser.add_argument('--stage', type=int, default=0, choices=[0, 1, 2, 3, 4, 5], help="Stage number (0 to 5)")
    parser.add_argument('--base-url', type=str, default="http://127.0.0.1:8000", help="Base URL of target API")
    parser.add_argument('--user', type=str, default="loadtest_admin", help="Admin username")
    parser.add_argument('--password', type=str, default="Police@Test2026!", help="Admin password")
    args = parser.parse_args()

    asyncio.run(run_stage(args.stage, args.base_url, args.user, args.password))

if __name__ == '__main__':
    main()
