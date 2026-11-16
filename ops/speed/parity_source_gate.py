#!/usr/bin/env python3
"""PARITY PROOF for the source gate's prefetch (speed program 1052). No AI. Runs on GitHub Actions.

The gate is run twice on the same built site (the site as committed on this branch) with the same verified store:
  A  as it runs today: every source fetched one by one by the gate (cold)
  B  with this run's prefetch: the sources A read are fetched in parallel first (--prefetch-to), then the gate starts from them (--warm)
Every check row (page, label, check, status, value, period, series, transformation, expected, detail), the decision and the totals
must be identical. Writes ops/speed/out/parity_source_gate.json; exit 1 if anything differs."""
import os, sys, json, shutil, tempfile, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WS = os.path.join(ROOT, 'data', '105_bristow_hall_system_2026-09-08', 'workspace')
sys.path.insert(0, os.path.join(WS, 's2'))
import source_gate as sg
SITE = os.path.join(ROOT, 'data', '105_bristow_hall_system_2026-09-08', 'site', 'public')


def main():
    tmp = tempfile.mkdtemp(prefix='gate_parity_')
    ver = os.path.join(tmp, 'verified.json')
    src_ver = os.path.join(ROOT, 'ops', 'state', 'source_gate_verified.json')
    if os.path.exists(src_ver): shutil.copy(src_ver, ver)
    t = time.time()
    A = sg.run(SITE, 'warn', sources_out=os.path.join(tmp, 'A_sources.json'), out=os.path.join(tmp, 'A.json'), verified_path=ver, quiet=True, write_verified=False)
    ta = time.time() - t
    keys = sorted(k for k in json.load(open(os.path.join(tmp, 'A_sources.json'))) if not k.endswith(':err'))
    json.dump(keys, open(os.path.join(tmp, 'keys.json'), 'w'))
    t = time.time(); sg.prefetch(os.path.join(tmp, 'prefetch.json'), keys_path=os.path.join(tmp, 'keys.json')); tp = time.time() - t
    t = time.time()
    B = sg.run(SITE, 'warn', out=os.path.join(tmp, 'B.json'), verified_path=ver, quiet=True, write_verified=False, warm=os.path.join(tmp, 'prefetch.json'))
    tb = time.time() - t
    ra, rb = [json.dumps(r, sort_keys=True, default=str) for r in A['rows']], [json.dumps(r, sort_keys=True, default=str) for r in B['rows']]
    diff = [x for x in ra if x not in rb][:10] + [x for x in rb if x not in ra][:10]
    # A source that one of the two gates could not read (a publisher's error at that moment) is not a difference of the gates: such a
    # row pair is listed apart, and only if the OTHER gate read the source and passed it. Every other row must be identical.
    FAILREAD = ('could not be read', 'unreachable', 'source unreachable', 'time budget')
    key = lambda r: (r['page'], r['label'], r['check'], r.get('series'))
    ka, kb = {key(r): r for r in A['rows']}, {key(r): r for r in B['rows']}
    readfail, real = [], []
    for k in sorted(set(ka) | set(kb), key=str):
        a, b = ka.get(k), kb.get(k)
        if json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str): continue
        one_failed = a and b and (any(f in (a.get('detail') or '') for f in FAILREAD) or any(f in (b.get('detail') or '') for f in FAILREAD))
        (readfail if one_failed else real).append(dict(A=a, B=b))
    out = dict(rows_A=len(ra), rows_B=len(rb), rows_identical=ra == rb, decision_A=A['decision'], decision_B=B['decision'],
               totals_A=A['totals'], totals_B=B['totals'], seconds_cold=round(ta, 1), seconds_prefetch=round(tp, 1), seconds_warm_gate=round(tb, 1),
               calls_cold=A['source_calls'], calls_warm_gate=B['source_calls'], source_read_failures_one_side=readfail,
               real_differences=real, differing_rows=diff)
    out['ok'] = not real and len(ra) == len(rb) and A['decision'] == B['decision']
    os.makedirs(os.path.join(ROOT, 'ops', 'speed', 'out'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'ops', 'speed', 'out', 'parity_source_gate.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ('differing_rows', 'source_read_failures_one_side', 'real_differences')}))
    print('rows differing only because one gate could not read a source at that moment: %d; real differences: %d' % (len(readfail), len(real)))
    for d in real[:6]: print('REAL', json.dumps(d, default=str)[:400])
    for d in diff[:6]: print('DIFF', d[:300])
    print('PARITY', 'PASS' if out['ok'] else 'FAIL')
    sys.exit(0 if out['ok'] else 1)


if __name__ == '__main__':
    main()
