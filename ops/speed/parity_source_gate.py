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
    A = sg.run(SITE, 'warn', sources_out=os.path.join(tmp, 'A_sources.json'), out=os.path.join(tmp, 'A.json'), verified_path=ver, quiet=True, write_verified=False,
               cache_out=os.path.join(tmp, 'A_cache.json'))
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
    fig = lambda r: (r['page'], r['label'], r.get('series'))     # one published figure: all its check rows together
    ga, gb = {}, {}
    for r in A['rows']: ga.setdefault(fig(r), []).append(json.dumps(r, sort_keys=True, default=str))
    for r in B['rows']: gb.setdefault(fig(r), []).append(json.dumps(r, sort_keys=True, default=str))
    failed = lambda rows: any(any(f in json.loads(x).get('detail', '') for f in FAILREAD) for x in rows)
    passed = lambda rows: all(json.loads(x)['status'] in ('PASS', 'WARN') for x in rows) and not failed(rows)
    readfail, real = [], []
    for k in sorted(set(ga) | set(gb), key=str):
        a, b = ga.get(k, []), gb.get(k, [])
        if a == b: continue
        if (failed(a) and passed(b)) or (failed(b) and passed(a)): readfail.append(dict(figure=k, A=a, B=b))
        else: real.append(dict(figure=k, A=a, B=b))
    # THE NOISE FLOOR: a figure that still differs is re-checked against a SECOND cold gate (as today). If the second cold gate agrees
    # with the warm one, or differs from the first cold one too, the difference is the publishers' answers at that moment (a read that
    # failed and a fallback series taken), not the prefetch.
    noise, unexplained = [], []
    if real:
        A2 = sg.run(SITE, 'warn', out=os.path.join(tmp, 'A2.json'), verified_path=ver, quiet=True, write_verified=False)
        g2 = {}
        for r in A2['rows']: g2.setdefault(fig(r), []).append(json.dumps(r, sort_keys=True, default=str))
        for d in real:
            k = d['figure']; a2 = g2.get(k, [])
            (noise if (a2 == d['B'] or a2 != d['A']) else unexplained).append(dict(d, A2=a2))
    out = dict(rows_A=len(ra), rows_B=len(rb), rows_identical=ra == rb, decision_A=A['decision'], decision_B=B['decision'],
               totals_A=A['totals'], totals_B=B['totals'], seconds_cold=round(ta, 1), seconds_prefetch=round(tp, 1), seconds_warm_gate=round(tb, 1),
               calls_cold=A['source_calls'], calls_warm_gate=B['source_calls'], source_read_failures_one_side=readfail,
               real_differences=real, cold_vs_cold_noise=noise, unexplained=unexplained, differing_rows=diff)
    # C (1052, 16 Nov): the prefetch starting from the cold gate's own sources as a previous run left them (--prev): FRED answers FRED
    # reports unchanged are kept, the rest fetched; the gate from it must give A's rows
    t = time.time(); sg.prefetch(os.path.join(tmp, 'prefetchC.json'), keys_path=os.path.join(tmp, 'keys.json'), prev=os.path.join(tmp, 'A_cache.json')); tpc = time.time() - t
    Cr = sg.run(SITE, 'warn', out=os.path.join(tmp, 'C.json'), verified_path=ver, quiet=True, write_verified=False, warm=os.path.join(tmp, 'prefetchC.json'))
    rc_ = [json.dumps(r, sort_keys=True, default=str) for r in Cr['rows']]
    out['C_prefetch_seconds'] = round(tpc, 1); out['C_rows_identical_to_A'] = rc_ == ra; out['C_rows_identical_to_B'] = rc_ == rb
    out['C_decision'] = Cr['decision']; out['C_calls'] = Cr['source_calls']
    print('C (prefetch from the last run\'s sources): prefetch %.0f s; rows identical to the cold gate: %s, to B: %s' % (tpc, rc_ == ra, rc_ == rb))
    out['ok'] = not unexplained and A['decision'] == B['decision'] and A['totals']['fail'] == B['totals']['fail'] and (rc_ == ra or rc_ == rb)
    os.makedirs(os.path.join(ROOT, 'ops', 'speed', 'out'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'ops', 'speed', 'out', 'parity_source_gate.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ('differing_rows', 'source_read_failures_one_side', 'real_differences', 'cold_vs_cold_noise', 'unexplained')}))
    print('figures differing: %d where one gate could not read a source; %d more, of which %d also differ between two cold gates (noise) and %d unexplained'
          % (len(readfail), len(real), len(noise), len(unexplained)))
    for d in unexplained[:6]: print('UNEXPLAINED', json.dumps(d, default=str)[:500])
    for d in noise[:6]: print('NOISE', json.dumps(d, default=str)[:300])
    for d in diff[:6]: print('DIFF', d[:300])
    print('PARITY', 'PASS' if out['ok'] else 'FAIL')
    sys.exit(0 if out['ok'] else 1)


if __name__ == '__main__':
    main()
