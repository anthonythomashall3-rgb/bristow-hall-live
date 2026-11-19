# -*- coding: utf-8 -*-
"""THE STANDING SERIES CHECK (19 November 2026). No AI. Standard library + pandas.

Every series file the live rule reads is checked on its own, with no reference to what the rule made of it:
    H1  the same date twice                       (hard)
    H2  a date that cannot be read, or out of order (hard)
    H3  a period missing inside the series          (hard for monthly and weekly files)
    S1  a jump by a factor of 5 or more between neighbours (soft: a unit or scale change)
    S2  a single point far from both neighbours that then comes straight back (soft: a typing or parsing slip)
    V1  vintage tables: an observation whose newest vintage differs from its first print by a factor of 2 or more
    H4  first-print tables: a cell 5 times above or below the median of the 9 rows around it (hard: a misread number;
        this is the check that found initial claims of 2 for the week of 12 March 2022 on 19 November 2026)
A hard finding that is not in ops/series_check_known.json exits 1; everything is written to the report either way.

    python3 ops/series_check.py                    check, print the summary, write ops/state/series_check.json
    python3 ops/series_check.py --out FILE         write the report elsewhere (nothing in the repository changes)
    python3 ops/series_check.py --accept           write today's findings to ops/series_check_known.json; a later run
                                                   then fails only on a finding that is not in that file
"""
import os, sys, glob, json, math, datetime
import pandas as pd, numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = os.path.join(ROOT, 'data', '105_bristow_hall_system_2026-09-08', 'workspace')
KNOWN = os.path.join(ROOT, 'ops', 'series_check_known.json')
# the files the starter C1021 and the ender E22 read (s2/c1021.py, s2/e22.py), by pattern
FEEDS = [
    ('vintage', os.path.join(ROOT, 'data', 'onset-detector-new-2026-08-23', '27_realtime_vintages', 'alfred_all_vintages',
                             '%s_all_vintages.csv' % s)) for s in ('UNRATE', 'PAYEMS', 'UNEMPLOY', 'LNS13023621', 'JTSJOL', 'INDPRO')
] + [
    ('long', os.path.join(W, 'cache', 'c1021', '%s.csv' % s)) for s in ('FEDFUNDS', 'GS10', 'GS1', 'ICNSA', 'CCNSA', 'BAA')
] + [
    ('long', os.path.join(W, 's2', 'e22_rate_history.csv')),
    ('weekly_table', os.path.join(W, 's2', 'e22_history.csv')),
    ('weekly_table', os.path.join(W, 'cache', 'c1021', 'claims_nsa_first_prints.csv')),
    ('weekly_table', os.path.join(W, 'cache', 'national_first_prints_1985_live.csv')),
    ('weekly_table', os.path.join(ROOT, 'data', '45_dol_first_prints_2026-09', 'national_first_prints.csv')),
]


def freq_of(idx):
    d = pd.Series(idx).diff().dt.days.dropna()
    if not len(d): return None
    m = d.median()
    return 'D' if m <= 3 else 'W' if m <= 9 else 'M' if m <= 35 else 'Q' if m <= 100 else 'A'


def check_dates(idx, name, out, hard_gaps=True):
    bad = int(pd.isna(idx).sum())
    if bad: out.append(dict(file=name, check='H2', n=bad, first='', note='dates that cannot be read'))
    idx = idx[~pd.isna(idx)]
    dup = idx[idx.duplicated()]
    if len(dup): out.append(dict(file=name, check='H1', n=int(len(dup)), first=str(dup[0].date()), note='the same date twice'))
    if not idx.is_monotonic_increasing:
        out.append(dict(file=name, check='H2', n=1, first='', note='dates out of order'))
    u = pd.DatetimeIndex(sorted(set(idx))); f = freq_of(u)
    if hard_gaps and f in ('W', 'M') and len(u) > 12:
        d = pd.Series(u).diff().dt.days
        lim = 10 if f == 'W' else 35
        g = [str(u[i].date()) for i in range(1, len(u)) if d.iloc[i] > lim]
        if g: out.append(dict(file=name, check='H3', n=len(g), first=g[0], note='%s series: a period is missing before each of these dates' % ('weekly' if f == 'W' else 'monthly'), all=g[:40]))
    return f


def check_values(s, name, out, col=''):
    s = pd.to_numeric(s, errors='coerce').dropna()
    if len(s) < 24: return
    tag = name + (' [' + col + ']' if col else '')
    if (s > 0).all():
        lr = np.log(s).diff().dropna()
        j = lr[lr.abs() >= math.log(5)]
        if len(j): out.append(dict(file=tag, check='S1', n=int(len(j)), first=str(j.index[0])[:10], note='a jump by a factor of 5 or more'))
    d = s.diff()
    mad = (d - d.median()).abs().median()
    if mad and mad > 0:
        z = d / (1.4826 * mad)
        prev, nxt = z, z.shift(-1)
        sp = s[(prev.abs() > 12) & (nxt.abs() > 12) & (np.sign(prev) != np.sign(nxt)) & ((prev + nxt).abs() < 0.25 * prev.abs())]
        if len(sp): out.append(dict(file=tag, check='S2', n=int(len(sp)), first=str(sp.index[0])[:10], note='a single point far from both neighbours that comes straight back', all=[str(i)[:10] for i in sp.index[:20]]))


def run():
    out, seen = [], []
    for kind, path in FEEDS:
        name = os.path.relpath(path, ROOT)
        if not os.path.exists(path):
            seen.append(dict(file=name, kind=kind, present=False)); continue   # private files are absent outside a run
        try:
            X = pd.read_csv(path, dtype=str)
        except Exception as e:
            out.append(dict(file=name, check='H2', n=1, first='', note='cannot be read: %s' % type(e).__name__)); continue
        idx = pd.DatetimeIndex(pd.to_datetime(X.iloc[:, 0], errors='coerce', format='%Y-%m-%d')) if kind != 'weekly_table' else pd.DatetimeIndex([])
        rec = dict(file=name, kind=kind, present=True, rows=int(len(X)), first=str(idx.min())[:10] if len(idx) else '', last=str(idx.max())[:10] if len(idx) else '')
        if kind == 'vintage':
            f = check_dates(idx, name, out); rec['freq'] = f
            V = X.iloc[:, 1:].apply(pd.to_numeric, errors='coerce'); V.index = idx
            first = V.bfill(axis=1).iloc[:, 0]; last = V.ffill(axis=1).iloc[:, -1]
            check_values(last, name, out, 'newest vintage'); check_values(first, name, out, 'first prints')
            ok = (first > 0) & (last > 0); r = (last[ok] / first[ok])
            far = r[(r >= 2) | (r <= 0.5)]
            if len(far): out.append(dict(file=name, check='V1', n=int(len(far)), first=str(far.index[0])[:10], note='newest vintage against first print differs by a factor of 2 or more (a rebased index does this; anything else is a unit change)'))
            # inside one vintage the months must be complete: a hole inside the newest column
            col = V.iloc[:, -1]; a, b = col.first_valid_index(), col.last_valid_index()
            holes = col.loc[a:b].isna().sum() if a is not None else 0
            if holes: out.append(dict(file=name, check='H3', n=int(holes), first=str(col.loc[a:b][col.loc[a:b].isna()].index[0])[:10], note='empty cells inside the newest vintage'))
        elif kind == 'long':
            f = check_dates(idx, name, out); rec['freq'] = f
            s = pd.to_numeric(X.iloc[:, 1], errors='coerce'); s.index = idx
            nn = int(s.isna().sum())
            if nn: out.append(dict(file=name, check='H2', n=nn, first=str(s[s.isna()].index[0])[:10], note='values that are not numbers'))
            check_values(s, name, out)
        else:
            # a first-print table: one row a release, a week may stand in two rows; each value column is read by its own week
            rc = 'release_date' if 'release_date' in X.columns else ('iu_release' if 'iu_release' in X.columns else X.columns[0])
            rel = pd.to_datetime(X[rc], errors='coerce', format='%Y-%m-%d')
            if int(rel.isna().sum()) and rc == 'release_date': out.append(dict(file=name, check='H2', n=int(rel.isna().sum()), first='', note='release days that cannot be read'))
            rec['first'], rec['last'] = str(rel.min())[:10], str(rel.max())[:10]
            for c in X.columns:
                lc = c.lower()
                if not (lc.startswith('ic') or lc.startswith('iu')) or 'week' in lc or 'release' in lc or lc.startswith('iur'): continue
                wc = next((w for w in (('ic_week_ended', 'week_ending') if lc.startswith('ic') else ('iu_week_ended', 'week_ending')) if w in X.columns), None)
                if wc is None: continue
                v = pd.to_numeric(X[c], errors='coerce'); wk = pd.to_datetime(X[wc], errors='coerce', format='%Y-%m-%d')
                t = pd.DataFrame(dict(w=wk, v=v, r=rel)).dropna(subset=['w', 'v']).sort_values('r').drop_duplicates('w', keep='first').sort_values('w')
                if len(t) < 24: continue
                ser = pd.Series(t.v.values, index=pd.DatetimeIndex(t.w.values))
                med = ser.rolling(9, center=True, min_periods=5).median()
                far = ser[(ser < med / 5.0) | (ser > med * 5.0)]
                if len(far): out.append(dict(file=name + ' [' + c + ']', check='H4', n=int(len(far)), first=str(far.index[0])[:10], note='a cell 5 times above or below the 9 rows around it: ' + ', '.join('%s = %s' % (str(k)[:10], ('%f' % x).rstrip('0').rstrip('.')) for k, x in far.items())[:300]))
                check_values(ser, name, out, c)
        seen.append(rec)
    return seen, out


def key(f): return '%s|%s|%s|%s' % (f['file'], f['check'], f['n'], f['first'])


def main():
    seen, out = run()
    known = set(json.load(open(KNOWN)).get('known', [])) if os.path.exists(KNOWN) else set()
    for f in out: f['known'] = key(f) in known
    hard_new = [f for f in out if f['check'].startswith('H') and not f['known']]
    rep = dict(at=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), files=seen, findings=out,
               files_checked=sum(1 for s in seen if s.get('present')), files_absent=[s['file'] for s in seen if not s.get('present')],
               hard_new=len(hard_new), soft=sum(1 for f in out if not f['check'].startswith('H')))
    if '--accept' in sys.argv:
        json.dump(dict(_what='findings read and accepted on the day named; ops/series_check.py fails only on a hard finding that is not here',
                       accepted=rep['at'], known=sorted(key(f) for f in out)), open(KNOWN, 'w'), indent=1)
    dst = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(ROOT, 'ops', 'state', 'series_check.json')
    json.dump(rep, open(dst, 'w'), indent=1)
    print('series check: %d files checked, %d absent (private or not yet built), %d findings (%d hard and new)' % (rep['files_checked'], len(rep['files_absent']), len(out), len(hard_new)))
    for f in out: print('  %s %-4s n=%-4s first %-10s %s%s' % ('known' if f['known'] else 'NEW  ', f['check'], f['n'], f['first'], f['file'], ' - ' + f['note']))
    return 1 if hard_new else 0


if __name__ == '__main__':
    sys.exit(main())
