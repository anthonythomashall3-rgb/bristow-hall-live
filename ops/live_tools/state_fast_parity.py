#!/usr/bin/env python3
"""PARITY OF THE STATE INPUTS FROM THE BLS API (speed program 1052). No AI. For every one of the 205 series ops/live_tools/state_fast.py
serves from the BLS API, the bytes it hands the State refresh scripts are parsed exactly as those scripts parse FRED's fredgraph file
(pd.read_csv, rows whose value is numeric, pd.to_numeric) and compared with FRED's own file parsed the same way: every date and every
value must be equal, and the series written by the scripts' to_csv must be byte-identical. A series whose BLS history starts later
than FRED's is reported (state_fast sends such a series to FRED whenever the held file starts earlier). Exit 1 on any difference."""
import os, sys, io, json, time, urllib.request
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_fast as sf


def parse(b, sid):
    n = pd.read_csv(io.BytesIO(b)); assert n.columns[1] == sid, n.columns
    n = n[pd.to_numeric(n.iloc[:, 1], errors='coerce').notna()]
    return pd.DataFrame({'date': n.iloc[:, 0].astype(str), sid: pd.to_numeric(n.iloc[:, 1])})


def main():
    t = time.time(); b = sf.bundle(); tb = time.time() - t
    if sf.REC['why']: print('BLS API answers missing (those series would go to FRED):', json.dumps(sf.REC['why'])[:800])
    if not any(b.values()):
        # 20 Nov 2026: no BLS source answered at all - this run cannot compare anything; say why instead of 205 'BLS False' lines. A test
        # run reads the BLS with its own key (BLS_API_KEY_TEST, s2/bls_fetch.py BLS_ROLE=test), never the live site's
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', '105_bristow_hall_system_2026-09-08', 'workspace', 's2'))
        import bls_fetch
        print('STATE FAST PARITY FAIL: the BLS answered none of the %d series (role %s; key %s; %s). Nothing was compared.' % (
            len(sf.BLS_OF), bls_fetch.ROLE, 'set' if bls_fetch.key_of('bls_v2_key1') else 'MISSING (BLS_API_KEY_TEST for a test run)', '; '.join(bls_fetch.LOG[-4:])[:600]))
        sys.exit(1)
    out = dict(series=0, identical=0, later_start=[], different=[], bls_seconds=round(tb, 1))
    for sid in sorted(sf.BLS_OF):
        url = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=' + sid
        f = None
        for i in range(4):
            try: f = urllib.request.urlopen(url, timeout=60).read(); break
            except Exception: time.sleep(10 * (i + 1))
        out['series'] += 1
        # production: the held file is FRED's whole series, so the BLS rows are taken from its first month (state_fast: start=held first)
        b = sf.fredgraph_from_bls(url, parse(f, sid).date.iloc[0]) if f is not None else None
        if b is None or f is None: out['different'].append(dict(sid=sid, why='BLS %s, FRED %s' % (b is not None, f is not None))); continue
        A, B = parse(f, sid), parse(b, sid)
        if B.date.iloc[0] > A.date.iloc[0]:
            A2 = A[A.date >= B.date.iloc[0]].reset_index(drop=True)
            out['later_start'].append(dict(sid=sid, fred_from=A.date.iloc[0], bls_from=B.date.iloc[0], equal_where_both=A2.to_csv(index=False) == B.to_csv(index=False)))
            if A2.to_csv(index=False) != B.to_csv(index=False): out['different'].append(dict(sid=sid, why='differs on common dates'))
            continue
        if A.to_csv(index=False, lineterminator='\n') == B.to_csv(index=False, lineterminator='\n'): out['identical'] += 1
        else:
            m = A.merge(B, on='date', how='outer', suffixes=('_fred', '_bls'), indicator=True)
            bad = m[(m['_merge'] != 'both') | (m[sid + '_fred'] != m[sid + '_bls'])]
            out['different'].append(dict(sid=sid, n=len(bad), first=bad.head(3).astype(str).values.tolist()))
    out['ok'] = not out['different']
    os.makedirs(os.environ.get('LT_OUT', '/tmp'), exist_ok=True)
    json.dump(out, open(os.path.join(os.environ.get('LT_OUT', '/tmp'), 'state_fast_parity.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'later_start'}, indent=1)[:3000])
    print('later BLS start (served from FRED when the held file starts earlier):', [(x['sid'], x['fred_from'], x['bls_from'], x['equal_where_both']) for x in out['later_start']][:60])
    print('STATE FAST PARITY', 'PASS' if out['ok'] else 'FAIL')
    sys.exit(0 if out['ok'] else 1)


if __name__ == '__main__':
    main()
