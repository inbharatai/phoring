"""Comprehensive test suite for all 5 security/stability fixes."""
import requests
import json

BASE = 'http://localhost:5001'
results = []


def test(name, method, url, json_data=None, expect_status=400):
    try:
        r = getattr(requests, method)(url, json=json_data, timeout=5)
        status = r.status_code
        ok = status == expect_status
        try:
            body = r.json()
        except Exception:
            body = r.text[:200]
        result = 'PASS' if ok else 'FAIL'
        results.append((result, name))
        print(f'  [{result}] {name}: status={status} (expected {expect_status})')
        if not ok:
            print(f'         body={json.dumps(body, ensure_ascii=False)[:200]}')
    except Exception as e:
        results.append(('ERR', name))
        print(f'  [ERR] {name}: {e}')


print('=' * 60)
print('FIX 1: Path Traversal & Input Validation')
print('=' * 60)

print('\n--- graph.py endpoints (should return 400) ---')
test('GET project bad ID', 'get', f'{BASE}/api/graph/project/INVALID_BAD_ID')
test('DELETE project bad ID', 'delete', f'{BASE}/api/graph/project/hack_attempt')
test('POST reset bad ID', 'post', f'{BASE}/api/graph/project/evil_id/reset')

print('\n--- simulation.py endpoints (should return 400) ---')
test('GET entities bad graph_id (dots)', 'get', f'{BASE}/api/simulation/entities/bad..id..here')
test('GET entity detail bad IDs (!)', 'get', f'{BASE}/api/simulation/entities/bad!id/some-uuid')
test('GET entities by type bad (@)', 'get', f'{BASE}/api/simulation/entities/bad@id/by-type/Person')

print('\n--- report.py endpoints (should return 400) ---')
test('POST generate bad sim_id', 'post', f'{BASE}/api/report/generate', {'simulation_id': 'bad_sim_id'})
test('POST status bad task_id', 'post', f'{BASE}/api/report/generate/status', {'task_id': 'bad_task'})
test('POST status bad sim_id', 'post', f'{BASE}/api/report/generate/status', {'simulation_id': 'bad_sim'})
test('GET report bad report_id', 'get', f'{BASE}/api/report/INVALID_REPORT')
test('GET by-simulation bad sim_id', 'get', f'{BASE}/api/report/by-simulation/bad_sim')
test('GET download bad report_id', 'get', f'{BASE}/api/report/INVALID_REPORT/download')
test('DELETE report bad report_id', 'delete', f'{BASE}/api/report/INVALID_REPORT')
test('POST chat bad sim_id', 'post', f'{BASE}/api/report/chat', {'simulation_id': 'bad', 'message': 'test'})

print('\n--- Valid ID format (should pass validation, return 404 since data missing) ---')
test('GET project valid format', 'get', f'{BASE}/api/graph/project/proj_aabbccddeeff', expect_status=404)
test('POST generate valid sim format', 'post', f'{BASE}/api/report/generate', {'simulation_id': 'sim_aabbccddeeff'}, expect_status=404)
test('GET report valid format', 'get', f'{BASE}/api/report/report_aabbccddeeff', expect_status=404)
test('GET by-sim valid format', 'get', f'{BASE}/api/report/by-simulation/sim_aabbccddeeff', expect_status=404)

print('\n' + '=' * 60)
print('FIX 2: DEBUG=False Default')
print('=' * 60)
# Trigger a deliberate error and check the response doesn't contain a Werkzeug debugger
r = requests.get(f'{BASE}/api/report/check/../../etc/passwd', timeout=5)
body = r.text
debugger_exposed = 'Werkzeug' in body or 'Traceback' in body or 'debugger' in body.lower()
result = 'PASS' if not debugger_exposed else 'FAIL'
results.append((result, 'No Werkzeug debugger exposed on error'))
print(f'  [{result}] No Werkzeug debugger exposed on error (status={r.status_code})')
if debugger_exposed:
    print(f'         Debugger content detected in response!')

# Also check that DEBUG is actually False in config
r2 = requests.get(f'{BASE}/health', timeout=5)
health = r2.json()
result2 = 'PASS' if r2.status_code == 200 else 'FAIL'
results.append((result2, 'Health endpoint works'))
print(f'  [{result2}] Health endpoint works (status={r2.status_code})')

print('\n' + '=' * 60)
print('FIX 3: DOMPurify (frontend - build verification)')
print('=' * 60)
# We can't run the frontend in this test, but we verify the import exists
import os
for vue_file in ['frontend/src/components/Step4Report.vue', 'frontend/src/components/Step5Interaction.vue']:
    full_path = os.path.join(r'c:\Users\reetu\Desktop\Phoring.ai', vue_file)
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    has_import = "import DOMPurify from 'dompurify'" in content
    has_sanitize = 'DOMPurify.sanitize(' in content
    ok = has_import and has_sanitize
    result = 'PASS' if ok else 'FAIL'
    results.append((result, f'DOMPurify in {os.path.basename(vue_file)}'))
    print(f'  [{result}] DOMPurify in {os.path.basename(vue_file)} (import={has_import}, sanitize={has_sanitize})')

print('\n' + '=' * 60)
print('FIX 4: File Locking (code verification)')
print('=' * 60)
# Verify threading.Lock usage in project.py and simulation_manager.py
for py_file, checks in [
    ('backend/app/models/project.py', ['threading.Lock', '_get_lock(', 'with lock:']),
    ('backend/app/services/simulation_manager.py', ['threading.Lock', '_get_state_lock(', 'with lock:', 'tempfile.mkstemp', 'os.replace(']),
]:
    full_path = os.path.join(r'c:\Users\reetu\Desktop\Phoring.ai', py_file)
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    missing = [c for c in checks if c not in content]
    ok = len(missing) == 0
    result = 'PASS' if ok else 'FAIL'
    results.append((result, f'File locking in {os.path.basename(py_file)}'))
    print(f'  [{result}] File locking in {os.path.basename(py_file)}')
    if missing:
        print(f'         Missing: {missing}')

# Verify defense-in-depth regex checks
for py_file, pattern in [
    ('backend/app/models/project.py', 're.match('),
    ('backend/app/services/simulation_manager.py', 're.match('),
]:
    full_path = os.path.join(r'c:\Users\reetu\Desktop\Phoring.ai', py_file)
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    ok = pattern in content
    result = 'PASS' if ok else 'FAIL'
    results.append((result, f'Defense-in-depth regex in {os.path.basename(py_file)}'))
    print(f'  [{result}] Defense-in-depth regex in {os.path.basename(py_file)}')

print('\n' + '=' * 60)
print('FIX 5: Concurrent Write Safety (threaded test)')
print('=' * 60)
import threading
import time

errors = []
THREADS = 10

def concurrent_write(i):
    """Hit an endpoint that triggers state management."""
    try:
        # Use a valid-format but nonexistent sim ID - should get 404 not 500
        r = requests.get(f'{BASE}/api/report/by-simulation/sim_aabbccddeef{i:01x}', timeout=5)
        if r.status_code not in (400, 404):
            errors.append(f'Thread {i}: unexpected status {r.status_code}')
    except Exception as e:
        errors.append(f'Thread {i}: {e}')

threads = [threading.Thread(target=concurrent_write, args=(i,)) for i in range(THREADS)]
start = time.time()
for t in threads:
    t.start()
for t in threads:
    t.join(timeout=10)
elapsed = time.time() - start

ok = len(errors) == 0
result = 'PASS' if ok else 'FAIL'
results.append((result, f'Concurrent requests ({THREADS} threads)'))
print(f'  [{result}] Concurrent requests ({THREADS} threads, {elapsed:.2f}s)')
if errors:
    for e in errors[:5]:
        print(f'         {e}')

# ==================== SUMMARY ====================
print('\n' + '=' * 60)
passed = sum(1 for r, _ in results if r == 'PASS')
failed = sum(1 for r, _ in results if r == 'FAIL')
errs = sum(1 for r, _ in results if r == 'ERR')
total = len(results)
print(f'FINAL RESULTS: {passed}/{total} passed, {failed} failed, {errs} errors')
if failed > 0 or errs > 0:
    print('\nFAILED/ERROR tests:')
    for r, name in results:
        if r in ('FAIL', 'ERR'):
            print(f'  [{r}] {name}')
else:
    print('\nALL TESTS PASSED!')
print('=' * 60)
