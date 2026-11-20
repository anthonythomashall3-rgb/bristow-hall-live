#!/usr/bin/env python3
"""THE BLS ALLOWANCE GUARD, TESTED WITHOUT ONE REQUEST TO THE BLS (20 Nov 2026). No AI. Standard library only.

data/105.../workspace/s2/bls_fetch.py is loaded in a fresh process per case with the BLS API replaced by a stand-in that answers like the
API (REQUEST_SUCCEEDED, or the daily-threshold refusal) and records every request it receives. Each case must hold:
  1 a test run (BLS_ROLE=test, or a pull request) never sends the production key, even when BLS_API_KEY is in its environment
  2 a test run uses BLS_API_KEY_TEST, counted as bls_v2_test
  3 the run's budget (BLS_RUN_BUDGET) stops the key and the series go down the chain (v1) - the key is not run out
  4 the ceiling over every writer's file (ops/state/bls_usage*.json, here a temporary copy) stops the key before the BLS would
  5 a refusal recorded by another writer today is honoured by a fresh runner (no request on that key)
  6 a refusal by the BLS moves to the next source and is recorded; the count of every request is written (day and hourly buckets)
  7 the budget is shared by the run's processes (BLS_RUN_FILE): a second process of the same run starts from the first one's count
Exit 1 on any failure."""
import os, sys, json, subprocess, tempfile, textwrap

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
S2 = os.path.join(ROOT, 'data', '105_bristow_hall_system_2026-09-08', 'workspace', 's2')
PROD, TEST = 'PRODKEY0000000000000000000000001', 'TESTKEY0000000000000000000000001'

STUB = textwrap.dedent(r'''
    import os, sys, json, io, urllib.request
    sys.path.insert(0, os.environ['S2'])
    LOGF = os.environ['STUB_LOG']; REFUSE = set(filter(None, os.environ.get('STUB_REFUSE', '').split(',')))
    class R(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass
    def fake(req, timeout=None):
        url = req.full_url if hasattr(req, 'full_url') else req
        if 'api.bls.gov' not in url: raise OSError('the stand-in serves the BLS API only: ' + url)
        b = json.loads(req.data.decode()); k = b.get('registrationkey', '')
        open(LOGF, 'a').write(json.dumps({'v': 2 if '/v2/' in url else 1, 'key': k, 'n': len(b['seriesid'])}) + '\n')
        if (k and k in REFUSE) or (not k and 'v1' in REFUSE):
            return R(json.dumps({'status': 'REQUEST_NOT_PROCESSED', 'message': ['Request could not be serviced, as the daily threshold for total number of requests allocated to the user with registration key %s has been reached.' % k]}).encode())
        ser = [{'seriesID': s, 'data': [{'year': '2026', 'period': 'M09', 'value': '1.0', 'footnotes': [{}]}]} for s in b['seriesid']]
        return R(json.dumps({'status': 'REQUEST_SUCCEEDED', 'Results': {'series': ser}}).encode())
    urllib.request.urlopen = fake
    import bls_fetch as B
    B._PAR = {'bls_v1': {'surveys': {'la': True, 'sm': True, 'ce': True}}}     # v1 eligible, as the parity record has it
    ids = ['LASST%02d0000000000003' % i for i in range(1, int(os.environ.get('N_SERIES', '50')) + 1)]
    for _ in range(int(os.environ.get('CALLS', '1'))):
        d, served = B.fetch(ids, 2025, 2026, chain=('bls_v2_key1', 'bls_v2_key2', 'bls_v1'), fresh=True)
    print('SERVED', json.dumps(sorted(set(served.values()))))
''')


def run(case, env_extra, files=None):
    t = tempfile.mkdtemp(prefix='blsguard_')
    st = os.path.join(t, 'ops', 'state'); os.makedirs(st)
    for name, U in (files or {}).items(): json.dump(U, open(os.path.join(st, name), 'w'))
    stub = os.path.join(t, 'stub.py'); open(stub, 'w').write(STUB)
    env = {k: v for k, v in os.environ.items() if not k.startswith(('BLS_', 'GITHUB_'))}
    env.update(S2=S2, STUB_LOG=os.path.join(t, 'requests.log'), BLS_USAGE=os.path.join(st, env_extra.pop('USAGE_NAME', 'bls_usage.json')),
               BLS_CACHE_DIR=os.path.join(t, 'cache'), BLS_RUN_ID='selftest', HOME=t)
    env.update(env_extra)
    # every writer's files are read from <ROOT>/ops/state: point the module there through a copy of its own file in the temp tree
    ws = os.path.join(t, 'data', '105_bristow_hall_system_2026-09-08', 'workspace', 's2'); os.makedirs(ws)
    src = open(os.path.join(S2, 'bls_fetch.py')).read(); open(os.path.join(ws, 'bls_fetch.py'), 'w').write(src)
    env['S2'] = ws
    out = subprocess.run([sys.executable, stub], env=env, capture_output=True, text=True, timeout=120)
    reqs = [json.loads(l) for l in open(env['STUB_LOG'])] if os.path.exists(env['STUB_LOG']) else []
    usage = json.load(open(env['BLS_USAGE'])) if os.path.exists(env['BLS_USAGE']) else {}
    served = next((json.loads(l[7:]) for l in out.stdout.splitlines() if l.startswith('SERVED ')), None)
    if out.returncode: print(case, 'process failed:', out.stderr[-800:])
    return reqs, usage, served, out.stdout + out.stderr, t


def main():
    import datetime
    from zoneinfo import ZoneInfo
    day = datetime.datetime.now(ZoneInfo('America/New_York')).date().isoformat()
    hour = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H')
    res = {}

    r, u, s, log, _ = run('1', {'BLS_ROLE': 'test', 'BLS_API_KEY': PROD, 'BLS_API_KEY_2': PROD})
    res['1 a test run never sends the production key'] = bool(r) and not any(q['key'] == PROD for q in r) and s == ['bls_v1']

    r, u, s, log, _ = run('2', {'GITHUB_EVENT_NAME': 'pull_request', 'BLS_API_KEY': PROD, 'BLS_API_KEY_TEST': TEST})
    res['2 a pull request uses the test key, counted as bls_v2_test'] = (bool(r) and all(q['key'] == TEST for q in r) and s == ['bls_v2_test']
                                                                       and u.get('requests', {}).get('bls_v2_test') == len(r) and 'bls_v2_key1' not in u.get('requests', {}))

    r, u, s, log, _ = run('3', {'BLS_API_KEY': PROD, 'BLS_RUN_BUDGET': '3', 'CALLS': '1', 'N_SERIES': '250'})
    k = [q for q in r if q['key'] == PROD]
    res['3 the run budget stops the key at 3 requests and v1 serves'] = len(k) == 3 and 'bls_v1' in (s or []) and 'BLS_RUN_BUDGET' in log

    full = {'day': day, 'requests': {'bls_v2_key1': 300}, 'alerted': {}, 'refused': {}, 'hourly': {'bls_v2_key1': {hour: 300}}}
    other = {'day': day, 'requests': {'bls_v2_key1': 150}, 'alerted': {}, 'refused': {}, 'hourly': {'bls_v2_key1': {hour: 150}}}
    r, u, s, log, _ = run('4', {'BLS_API_KEY': PROD, 'USAGE_NAME': 'bls_usage_live_tools.json'}, {'bls_usage.json': full, 'bls_usage_live_tools.json': other})
    res['4 the ceiling over every writer (300 + 150 = 450) stops the key before any request'] = not any(q['key'] == PROD for q in r) and s == ['bls_v1'] and 'BLS_DAILY_CEILING' in log

    yday = {'day': '2000-01-01', 'requests': {}, 'alerted': {}, 'refused': {}, 'hourly': {'bls_v2_key1': {hour: 449}}}
    r, u, s, log, _ = run('4b', {'BLS_API_KEY': PROD, 'N_SERIES': '100'}, {'bls_usage.json': yday})
    res['4b the last 24 hours count across the New York day change (449 + 1 reaches 450)'] = len([q for q in r if q['key'] == PROD]) == 1 and s == ['bls_v1']

    refused = {'day': day, 'requests': {'bls_v2_key1': 5}, 'alerted': {}, 'refused': {'bls_v2_key1': 'daily threshold'}, 'hourly': {}}
    r, u, s, log, _ = run('5', {'BLS_API_KEY': PROD, 'USAGE_NAME': 'bls_usage_live_tools.json'}, {'bls_usage.json': refused})
    res['5 a refusal recorded by another writer today is honoured'] = not any(q['key'] == PROD for q in r) and s == ['bls_v1']

    r, u, s, log, _ = run('6', {'BLS_API_KEY': PROD, 'STUB_REFUSE': PROD})
    res['6 a BLS refusal goes down the chain, is recorded and counted'] = (s == ['bls_v1'] and 'bls_v2_key1' in u.get('refused', {})
                                                                         and u['requests'].get('bls_v2_key1') == 1 and sum(u['hourly']['bls_v2_key1'].values()) == 1)

    r1, u1, s1, log1, t = run('7', {'BLS_API_KEY': PROD, 'BLS_RUN_BUDGET': '2', 'BLS_RUN_FILE': os.path.join(tempfile.gettempdir(), 'blsguard_run_%d.json' % os.getpid())})
    r2, u2, s2, log2, _ = run('7', {'BLS_API_KEY': PROD, 'BLS_RUN_BUDGET': '2', 'BLS_RUN_FILE': os.path.join(tempfile.gettempdir(), 'blsguard_run_%d.json' % os.getpid())})
    res['7 the budget is shared by the run\'s processes'] = len([q for q in r1 if q['key'] == PROD]) == 1 and len([q for q in r2 if q['key'] == PROD]) == 1 and s2 == ['bls_v2_key1']
    r3, u3, s3, log3, _ = run('7', {'BLS_API_KEY': PROD, 'BLS_RUN_BUDGET': '2', 'BLS_RUN_FILE': os.path.join(tempfile.gettempdir(), 'blsguard_run_%d.json' % os.getpid())})
    res['7b a third process of the same run finds the budget spent'] = not any(q['key'] == PROD for q in r3) and s3 == ['bls_v1']
    try: os.remove(os.path.join(tempfile.gettempdir(), 'blsguard_run_%d.json' % os.getpid()))
    except OSError: pass

    for k, v in res.items(): print('%-4s %s' % ('ok' if v else 'FAIL', k))
    ok = all(res.values()); print('BLS GUARD SELFTEST', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
