#!/usr/bin/env python3
"""Tidy the Philadelphia Fed RTDSM vintage matrices into long format and first-print series.

Input : raw/rtdsm/files/<slug>/<slug>{MvMd,QvMd,MvQd,QvQd}.xlsx  (rows = observation dates, columns =
        vintages named <VAR><yy>M<m> or <VAR><yy>Q<q>)
Output: tidy/rtdsm/<VAR>_<kind>_long.csv.gz   variable, obs, vintage, asof, value
        tidy/rtdsm/<VAR>_<kind>_firstprint.csv obs, first_vintage, first_asof, first_value,
                                             first_pct_chg_within_vintage, latest_value
        tidy/rtdsm/rtdsm_vintage_summary.csv   one row per file

'asof' is the date the vintage stands for. Per the RTDSM documentation (gen_doc_nonNIPA.pdf) a monthly
vintage holds data available by the 15th of that month, and a quarterly vintage data available by the 15th
of the middle month of the quarter; releases after the 15th fall into the next vintage. So asof = the 15th.
A true release-day timestamp needs the release calendar (for CES/CPS: raw/rtdsm/files/*/
Release_-Dates-Employment_Situation-BLS.xls, from 1966).

first_pct_chg_within_vintage: percent change of the first-printed value over the previous observation AS
PRINTED IN THE SAME VINTAGE. Use it rather than differencing first_value across rows: index bases change
between vintages (e.g. IP 1957-59=100 -> 1967=100 -> ... ), so first_value is not one consistent series.
"""
import os, re, gzip, csv, glob
import pandas as pd

W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/new_candidates'
SRC = os.path.join(W, 'raw', 'rtdsm', 'files'); OUT = os.path.join(W, 'tidy', 'rtdsm')
os.makedirs(OUT, exist_ok=True)

def asof(label):
    m = re.match(r'^(\d{2})([MQ])(\d{1,2})$', label)
    yy, f, n = int(m.group(1)), m.group(2), int(m.group(3))
    y = 1900 + yy if yy >= 60 else 2000 + yy
    mon = n if f == 'M' else 3 * n - 1
    return '%04d-%02d-15' % (y, mon), '%04d%s%d' % (y, f, n)

def obs_key(s):
    s = str(s).strip()
    m = re.match(r'^(\d{4}):(\d{2})$', s)
    if m: return '%s-%s-01' % m.groups()
    m = re.match(r'^(\d{4}):Q(\d)$', s)
    if m: return '%s-%02d-01' % (m.group(1), 3 * int(m.group(2)) - 2)
    return None

summ = []
for f in sorted(glob.glob(os.path.join(SRC, '*', '*.xlsx'))):
    kind = re.search(r'(MvMd|QvMd|MvQd|QvQd)\.xlsx$', f)
    if not kind: continue
    kind = kind.group(1)
    x = pd.read_excel(f, sheet_name=0)
    x = x.rename(columns={x.columns[0]: 'DATE'})
    x['obs'] = x['DATE'].map(obs_key)
    x = x[x['obs'].notna()]
    vcols = [c for c in x.columns if c not in ('DATE', 'obs')]
    var = os.path.basename(f)[:-len(kind) - 5].upper()     # file slug, e.g. m1QvMd.xlsx -> M1
    assert all(c.upper().startswith(var) for c in vcols), (f, vcols[:3])
    vcols_u = {c: c.upper() for c in vcols}
    meta = {c: asof(vcols_u[c][len(var):]) for c in vcols}
    vals = x[vcols].apply(pd.to_numeric, errors='coerce')
    vals.index = x['obs'].values
    # long
    lp = os.path.join(OUT, '%s_%s_long.csv.gz' % (var, kind))
    n = 0
    if os.path.exists(lp) and os.environ.get('REUSE_LONG'):     # long file already written by a previous run
        n = int(vals.notna().sum().sum())
    else:
        with gzip.open(lp, 'wt', newline='') as g:
            w = csv.writer(g); w.writerow(['variable', 'obs', 'vintage', 'asof', 'value'])
            for c in vcols:
                s = vals[c].dropna()
                a, lab = meta[c]
                for o, v in s.items():
                    w.writerow([var, o, lab, a, repr(float(v))]); n += 1
    # first print + within-vintage pct change
    rows = []
    for o in vals.index:
        r = vals.loc[o]
        nz = r[r.notna()]
        if nz.empty: continue
        c0 = nz.index[0]
        v0 = float(nz.iloc[0])
        col = vals[c0]
        i = list(vals.index).index(o)
        prev = col.iloc[i - 1] if i > 0 else float('nan')
        pc = 100.0 * (v0 / prev - 1.0) if pd.notna(prev) and prev != 0 else ''
        rows.append([o, meta[c0][1], meta[c0][0], v0, pc, float(nz.iloc[-1])])
    fp = pd.DataFrame(rows, columns=['obs', 'first_vintage', 'first_asof', 'first_value',
                                     'first_pct_chg_within_vintage', 'latest_value'])
    # genuine first print = first appeared within 130 days (monthly obs) / 200 days (quarterly obs) of the
    # observation date; anything later entered the file as back-filled history (first vintage or a later
    # historical extension), which a real-time reader must treat as history, not as news
    fp['lag_days'] = (pd.to_datetime(fp['first_asof']) - pd.to_datetime(fp['obs'])).dt.days
    # vintage columns that hold any data (e.g. CPI columns before 1994 are empty in cpiQvMd.xlsx)
    nonempty = [c for c in vcols if vals[c].notna().any()]
    v0lab = meta[nonempty[0]][1]
    v0last = vals[nonempty[0]].dropna().index.max()
    # everything in the first non-empty vintage except its newest observation was already history then
    fp['is_backfill'] = (fp['lag_days'] > (130 if kind.endswith('Md') else 200)) | \
                        ((fp['first_vintage'] == v0lab) & (fp['obs'] < v0last))
    fp.to_csv(os.path.join(OUT, '%s_%s_firstprint.csv' % (var, kind)), index=False)
    # the first vintage in a file back-fills history: flag observations whose "first print" is the file's
    # first vintage, since those are deep history, not genuine first releases
    genuine = fp[~fp['is_backfill']]
    summ.append(dict(variable=var, kind=kind, file=os.path.relpath(f, W), n_vintages=len(nonempty),
                     first_vintage=v0lab, last_vintage=meta[nonempty[-1]][1],
                     first_obs=vals.dropna(how='all').index.min(), last_obs=vals.dropna(how='all').index.max(),
                     n_long_rows=n, first_genuine_firstprint_obs=genuine['obs'].min() if len(genuine) else '',
                     n_genuine_firstprints=len(genuine)))
    print(var, kind, len(vcols), n, flush=True)
pd.DataFrame(summ).to_csv(os.path.join(OUT, 'rtdsm_vintage_summary.csv'), index=False)
