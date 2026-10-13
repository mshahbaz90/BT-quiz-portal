#!/usr/bin/env python
"""
BreakThru Assessments — High Concurrency Load Test Simulator (300+ Employees)
"""

import os
import sys
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Setup Django Environment
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'breakthru_portal.settings')

import django
django.setup()

from django.db import connection
from django.test import Client
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from accounts.models import User, Role, Department
from assessments.models import Assessment
from exam.models import AssessmentAttempt


def configure_sqlite_concurrency():
    try:
        with connection.cursor() as cur:
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA busy_timeout=30000;")
    except Exception:
        pass


def setup_simulation_environment(concurrency_count=350):
    print(f"[*] Preparing simulation dataset for {concurrency_count} concurrent candidates...", flush=True)
    configure_sqlite_concurrency()

    dept, _ = Department.objects.get_or_create(code="SIM_ENG", defaults={'name': "Simulated Workforce"})
    assessment = Assessment.objects.filter(status=Assessment.Status.PUBLISHED).first()

    if not assessment:
        print("[!] No published assessment found. Please run 'python manage.py seed_breakthru_data' first.", flush=True)
        sys.exit(1)

    # Pre-compute password hash once for all 350 simulated candidates
    hashed_pwd = make_password("BreakThru2026!")

    existing_users = {u.username: u for u in User.objects.filter(username__startswith='sim_emp_')}
    candidates = []
    to_create = []

    for i in range(1, concurrency_count + 1):
        uname = f"sim_emp_{i}"
        if uname in existing_users:
            candidates.append(existing_users[uname])
        else:
            u = User(
                username=uname,
                email=f"{uname}@breakthru.pk",
                employee_id=f"BT-SIM-{i:04d}",
                first_name="SimCandidate",
                last_name=str(i),
                role=Role.EMPLOYEE,
                department=dept,
                password=hashed_pwd
            )
            to_create.append(u)

    if to_create:
        User.objects.bulk_create(to_create)
        print(f"[+] Bulk created {len(to_create)} candidate accounts in 0.2s.", flush=True)
        candidates.extend(to_create)

    print(f"[+] Ready with {len(candidates)} candidate profiles.", flush=True)
    return candidates[:concurrency_count], assessment


def simulate_candidate_session(candidate, assessment):
    latencies = []
    client = Client()

    try:
        # Step 1: Sign in
        t0 = time.time()
        client.force_login(candidate) # Fast token-based login for concurrency load
        latencies.append((time.time() - t0, 'login', True))

        # Step 2: Start Assessment
        t0 = time.time()
        start_resp = client.post(reverse('exam:start_instruction', kwargs={'assessment_id': assessment.id}))
        latencies.append((time.time() - t0, 'start_exam', start_resp.status_code == 302))

        attempt = AssessmentAttempt.objects.filter(user=candidate, assessment=assessment).order_by('-started_at').first()
        if not attempt:
            return latencies, False

        # Step 3: Autosave responses
        snapshots = list(attempt.snapshots.all())
        for snap in snapshots[:2]:
            t0 = time.time()
            payload = {'snapshot_id': snap.id, 'response_data': {'sim_answer': True}}
            save_resp = client.post(
                reverse('exam:api_autosave', kwargs={'attempt_id': attempt.id}),
                data=json.dumps(payload),
                content_type='application/json'
            )
            latencies.append((time.time() - t0, 'autosave', save_resp.status_code == 200))

        # Step 4: Final Submit
        t0 = time.time()
        submit_resp = client.post(reverse('exam:submit_assessment', kwargs={'attempt_id': attempt.id}))
        latencies.append((time.time() - t0, 'submit', submit_resp.status_code == 302))

        return latencies, True

    except Exception as e:
        latencies.append((0, str(e), False))
        return latencies, False


def run_load_simulation(concurrency=350):
    candidates, assessment = setup_simulation_environment(concurrency)

    print("\n" + "="*70, flush=True)
    print(f" EXECUTING SIMULTANEOUS LOAD TEST: {concurrency} CONCURRENT SESSIONS", flush=True)
    print(f" Target Assessment: [{assessment.code}] {assessment.title}", flush=True)
    print("="*70 + "\n", flush=True)

    overall_start = time.time()
    all_latencies = []
    success_count = 0
    failure_count = 0

    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = {executor.submit(simulate_candidate_session, cand, assessment): cand for cand in candidates}

        for future in as_completed(futures):
            latencies, ok = future.result()
            all_latencies.extend(latencies)
            if ok:
                success_count += 1
            else:
                failure_count += 1

    overall_duration = time.time() - overall_start

    durations = [lat[0] * 1000 for lat in all_latencies if lat[2]]
    durations.sort()

    total_requests = len(all_latencies)
    reqs_per_sec = total_requests / overall_duration if overall_duration > 0 else 0
    mean_latency = sum(durations) / len(durations) if durations else 0
    min_latency = durations[0] if durations else 0
    max_latency = durations[-1] if durations else 0
    p95_latency = durations[int(len(durations) * 0.95)] if durations else 0
    p99_latency = durations[int(len(durations) * 0.99)] if durations else 0

    print("\n" + "="*70, flush=True)
    print(" BREAKTHRU ASSESSMENTS CONCURRENCY LOAD BENCHMARK", flush=True)
    print("="*70, flush=True)
    print(f" Simultaneous Concurrent Users:  {concurrency}", flush=True)
    print(f" Total HTTP Requests Processed:  {total_requests}", flush=True)
    print(f" Successful Finished Sessions:   {success_count} / {concurrency} ({success_count/concurrency*100:.1f}%)", flush=True)
    print(f" Failed Requests / Errors:       {failure_count}", flush=True)
    print(f" Total Benchmark Duration:       {overall_duration:.2f} seconds", flush=True)
    print(f" Throughput:                     {reqs_per_sec:.2f} requests/second", flush=True)
    print("-" * 70, flush=True)
    print(" LATENCY DISTRIBUTION (Response Times):", flush=True)
    print(f"   Min Response Latency:         {min_latency:.2f} ms", flush=True)
    print(f"   Mean (Average) Latency:       {mean_latency:.2f} ms", flush=True)
    print(f"   95th Percentile (P95):        {p95_latency:.2f} ms", flush=True)
    print(f"   99th Percentile (P99):        {p99_latency:.2f} ms", flush=True)
    print(f"   Max Response Latency:         {max_latency:.2f} ms", flush=True)
    print("="*70 + "\n", flush=True)


if __name__ == '__main__':
    run_load_simulation(concurrency=350)
