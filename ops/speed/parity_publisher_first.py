#!/usr/bin/env python3
"""PARITY PROOF for s2/publisher_first.py (speed program 1052). No AI. Runs on GitHub Actions (FRED blocks the Mac's address).

For each series the rule reads at release time (PAYEMS, UNRATE, UNEMPLOY, LNS13023621, JTSJOL, INDPRO) its ALFRED vintage table is
put back to the state it had the moment before its newest vintage was appended (that column dropped, and the rows only it carried),
then the newest vintage is written again three ways:
  A  the FRED path: FRED's vintage of that day (realtime_start = realtime_end = the day), written by write_column - must give the
     committed file byte for byte (this proves write_column is bhs_update.py's _append_vintages)
  B  the publisher path: the publisher's series read now (BLS API v2 whole history / the Fed's G.17 file), written by append()
     - must give the committed file byte for byte (valid while no release has come since the newest vintage)
  C  the cross-check: verify() on B's file must find FRED's vintage equal and mark it verified; on a file whose publisher read
     was altered in one month it must find the difference and put FRED's vintage back (the file then equals the committed one).
Writes ops/speed/out/parity_publisher_first.json; exit 1 if any check fails."""
import os, sys, json, hashlib, tempfile, urllib.request, urllib.parse
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WS = os.path.join(ROOT, 'data', '105_bristow_hall_system_2026-09-08', 'workspace')
sys.path.insert(0, os.path.join(WS, 's2'))
import publisher_first as pf
AL = os.path.join(ROOT, 'data', 'onset-detector-new-2026-08-23', '27_realtime_vintages', 'alfred_all_vintages')
KEY = os.environ['FRED_API_KEY']


def fred_json(path, **q):
    q.update(api_key=KEY, file_type='json')
    with urllib.request.urlopen('https://api.stlouisfed.org/fred/' + path + '?' + urllib.parse.urlencode(q), timeout=60) as r:
        return json.load(r)


def fred_vintage(s, day):   # bhs_update.py: fred(s,realtime_start=d,realtime_end=d,observation_start='1919-01-01').dropna()
    d = fred_json('series/observations', series_id=s, realtime_start=day, realtime_end=day, observation_start='1919-01-01')
    x = pd.Series({o['date']: (float('nan') if o['value'] == '.' else float(o['value'])) for o in d['observations']})
    x.index = pd.to_datetime(x.index); return x.sort_index().dropna()


def vintage_dates(s, start):
    return fred_json('series/vintagedates', series_id=s, realtime_start=start, realtime_end='9999-12-31').get('vintage_dates', [])


def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def pre_state(src, dst):
    tab = pd.read_csv(src, index_col=0); tab.index = pd.to_datetime(tab.index)
    last = tab[tab.columns[-1]]; tab = tab.drop(columns=[tab.columns[-1]])
    tab = tab[~(tab.isna().all(axis=1) & last.notna())]     # the rows only the newest vintage carried (a row empty in every vintage stays)
    tab.index.name = 'date'; tab.to_csv(dst, na_rep='')


def main():
    out = {'series': {}, 'ok': True}
    tmp = tempfile.mkdtemp(prefix='pf_parity_')
    pub = pf.publisher(list(pf.PF), full=True)
    for s in pf.PF:
        src = os.path.join(AL, '%s_all_vintages.csv' % s); r = {'committed_sha256': sha(src)}
        col = pd.read_csv(src, index_col=0, nrows=1).columns[-1]; day = '%s-%s-%s' % (col[-8:-4], col[-4:-2], col[-2:])
        r['newest_vintage'] = col
        for k in ('A', 'B', 'C'): os.makedirs(os.path.join(tmp, k), exist_ok=True)
        pa, pb, pc = (os.path.join(tmp, k, os.path.basename(src)) for k in ('A', 'B', 'C'))
        # A: the FRED path
        pre_state(src, pa); fv = fred_vintage(s, day); pf.write_column(pa, s, day, fv)
        r['A_fred_path_sha256'] = sha(pa); r['A_equal'] = r['A_fred_path_sha256'] == r['committed_sha256']
        # B: the publisher path (append() with the publisher's whole series; its state file kept in tmp)
        pre_state(src, pb); pf.STATE = os.path.join(tmp, 'stateB_%s.json' % s)
        got = pf.append(os.path.join(tmp, 'B'), day=day, series=[s], force_day=True, pub={s: pub[s]})
        r['B_column'] = got.get(s); r['B_publisher_path_sha256'] = sha(pb); r['B_equal'] = r['B_publisher_path_sha256'] == r['committed_sha256']
        p = pub[s].dropna(); ix = p.index.union(fv.index); a, b = p.reindex(ix), fv.reindex(ix)
        r['publisher_months'], r['fred_months'] = int(len(p)), int(len(fv))
        r['months_differing'] = [str(d.date()) for d in ix if not ((pd.isna(a[d]) and pd.isna(b[d])) or a[d] == b[d])][:20]
        # C: the FRED cross-check on B, then on a publisher read altered in its newest month
        bad = pf.verify(os.path.join(tmp, 'B'), fred_vintage, vintage_dates, say=lambda *x: None)
        r['C_verified'] = bool(r['B_column']) and json.load(open(pf.STATE))['columns'][r['B_column']]['status'] == 'verified' and not bad
        r['B_after_verify_equal'] = sha(pb) == r['committed_sha256']
        pre_state(src, pc); pf.STATE = os.path.join(tmp, 'stateC_%s.json' % s)
        t = p.copy(); t.iloc[-1] = t.iloc[-1] + 1.0
        pf.append(os.path.join(tmp, 'C'), day=day, series=[s], force_day=True, pub={s: t})
        badc = pf.verify(os.path.join(tmp, 'C'), fred_vintage, vintage_dates, say=lambda *x: None)
        r['C_tamper_caught'] = len(badc) == 1 and sha(pc) == r['committed_sha256']
        r['ok'] = all(r[k] for k in ('A_equal', 'B_equal', 'C_verified', 'B_after_verify_equal', 'C_tamper_caught'))
        out['ok'] &= r['ok']; out['series'][s] = r
        print('%-12s %-22s A(FRED path)=%s B(publisher)=%s C(verified)=%s C(tamper caught, FRED put back)=%s | months publisher %d FRED %d, differing %s'
              % (s, col, r['A_equal'], r['B_equal'], r['C_verified'], r['C_tamper_caught'], r['publisher_months'], r['fred_months'], r['months_differing'][:3]))
    os.makedirs(os.path.join(ROOT, 'ops', 'speed', 'out'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'ops', 'speed', 'out', 'parity_publisher_first.json'), 'w'), indent=1)
    print('PARITY', 'PASS' if out['ok'] else 'FAIL')
    sys.exit(0 if out['ok'] else 1)


if __name__ == '__main__':
    main()
