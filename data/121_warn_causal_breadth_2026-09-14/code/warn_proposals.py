"""WARN BREADTH AS A LEG THE WALK CAN CHOOSE, NOT A LINE I PICKED.

Collection 121 found a setting - 26-week window, states lit at their causal 90th percentile, panel of
six - that beats the 2007 and 2024 deadlines, and a Sahm gate that removes nineteen of twenty quiet
firings. But those numbers were read off the whole record, which is the fitting this programme refuses.
To be admissible the leg's lines must be chosen BY THE WALK, from a menu, at each annual cut, on the
record ratified by that date - exactly as every other line in the rule is chosen.

So this writes out the leg's proposals for EVERY setting in the menu, and the walk searches over them.
Each proposal is a (published, dated) pair: the Saturday the week ended plus three days for the release,
and the month the breadth reading belongs to.

The arming condition is fixed in advance rather than searched, and is not a new object: it is the rule's
own Sahm gap, at 0.12, a third of the hub's own line of 0.3667. It is not fitted - every quiet firing in
the whole record sits at a Sahm gap of exactly zero, so any positive value does the same work.
"""
import os, json, glob, csv, itertools
import numpy as np, pandas as pd
W = os.path.expanduser('~/Projects/Onset Detector Data/117_warn_notices_2026-09-14/data/warn_notices')
if not os.path.isdir(W): W = os.path.expanduser('~/mnt/Onset Detector Data/117_warn_notices_2026-09-14/data/warn_notices')
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/out'
IDX = json.load(open(f'{W}/_INDEX.json'))
PEAKS   = ['1990-07','2001-03','2007-12','2020-02','2024-04']
TROUGHS = ['1991-03','2001-11','2009-06','2020-04','2024-08']
M = lambda s: pd.Timestamp(s + '-01')
weeks = pd.date_range('1989-01-07', pd.Timestamp.today().normalize(), freq='W-SAT')   # through the latest Saturday (auto-updating from 16 September 2026; was fixed at 2026-09-05)
quiet = pd.Series(True, index=weeks)
for pk, tr in zip(PEAKS, TROUGHS):
    quiet[(weeks >= M(pk) - pd.DateOffset(months=9)) & (weeks <= M(tr) + pd.DateOffset(months=18))] = False
import warnings; warnings.filterwarnings('ignore')

# ---- the arming condition: the rule's own Sahm gap, charged its publication lag ----
import urllib.request, urllib.parse, json as _json
ENV = os.path.expanduser('~/Projects/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env')
if not os.path.exists(ENV):
    ENV = os.path.expanduser('~/mnt/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env')
KEY = [l.split('=', 1)[1].strip().strip('"').strip("'") for l in open(ENV) if l.startswith('FRED_API_KEY=')][0]
_q = urllib.parse.urlencode({'series_id': 'UNRATE', 'api_key': KEY, 'file_type': 'json'})
import time as _time
for _try in range(4):   # 17 September 2026: FRED answers 429 or an edge block while the standing collector draws on the key; wait and retry
    try:
        with urllib.request.urlopen(f'https://api.stlouisfed.org/fred/series/observations?{_q}', timeout=120) as _r:
            _o = _json.loads(_r.read())['observations']
        break
    except Exception as _e:
        if _try == 3: raise
        _time.sleep(30 * (_try + 1))
_u = pd.Series({pd.Timestamp(x['date']): float(x['value']) for x in _o if x['value'] != '.'}).sort_index()
_m3 = _u.rolling(3).mean()
SAHM = _m3 - _m3.rolling(12).min()
ARM = 0.12
def armed(d):
    # month m's employment report is published in the first week of m+1, so on date d the latest
    # month available is the one ending at least a month earlier
    prior = SAHM[SAHM.index <= d - pd.DateOffset(months=1)]
    return len(prior) > 0 and float(prior.iloc[-1]) >= ARM
raw = {}
for rec in IDX:
    st, col = rec['state'], rec['col']
    fs = glob.glob(f'{W}/{st.lower()}.csv') or glob.glob(f'{W}/{st.upper()}.csv')
    if not fs: continue
    df = None
    for kw in (dict(low_memory=False), dict(engine='python', on_bad_lines='skip')):
        try:
            df = pd.read_csv(fs[0], **kw)
            if any(c.strip().lower() == col.strip().lower() for c in df.columns): break
        except Exception: df = None
    if df is None: continue
    cand = [c for c in df.columns if c.strip().lower() == col.strip().lower()]
    if not cand: continue
    d = pd.to_datetime(df[cand[0]], errors='coerce', format='mixed').dropna()
    d = d[(d >= '1988-01-01') & (d <= pd.Timestamp.today().normalize() + pd.Timedelta(days=7))]   # through today (auto-updating from 17 September 2026; was fixed at 2026-09-30)
    if len(d) < 50: continue
    raw[st] = d + pd.Timedelta(days=7)          # public seven days after filing
print(len(raw), 'states')
rows = []
for WINDOW, PCTL, MINREP in itertools.product((13, 26), (85, 90, 95), (6,)):
    counts = {}
    for st, pubd in raw.items():
        s = pd.Series(1, index=pd.DatetimeIndex(pubd)).resample('W-SAT').sum().reindex(weeks).fillna(0)
        s[weeks < pubd.min()] = np.nan
        counts[st] = s.rolling(WINDOW, min_periods=WINDOW).sum()
    lit = pd.DataFrame(index=weeks); rep = pd.DataFrame(index=weeks)
    for st, s in counts.items():
        first = s.first_valid_index()
        if first is None: continue
        start = first + pd.Timedelta(weeks=156)
        if start > weeks[-1]: continue
        q = s.where(quiet)
        thr = q.expanding(min_periods=52).quantile(PCTL / 100.0).shift(1)
        lit[st] = pd.Series(((s > thr) & thr.notna()).values & (weeks >= start), index=weeks)
        rep[st] = pd.Series((weeks >= start), index=weeks)
    n = rep.sum(axis=1)
    br = (lit.sum(axis=1) / n.replace(0, np.nan)).where(n >= MINREP)
    line = br.where(quiet).expanding(min_periods=52).max().shift(1)
    fire = (br > line) & line.notna()
    n_raw = n_gated = 0
    for d in weeks[fire.fillna(False)]:
        n_raw += 1
        if not armed(d): continue
        n_gated += 1
        rows.append(dict(warnw=WINDOW, warnp=PCTL, published=str((d + pd.Timedelta(days=3)).date()),
                         dated=str(pd.Timestamp(d.year, d.month, 1).date())))
    print(f'  window {WINDOW}, percentile {PCTL}: {n_raw} firings, {n_gated} survive the Sahm gate', flush=True)
with open(f'{OUT}/warn_leg_proposals.csv.tmp', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['warnw', 'warnp', 'published', 'dated']); w.writeheader(); w.writerows(rows)
os.replace(f'{OUT}/warn_leg_proposals.csv.tmp', f'{OUT}/warn_leg_proposals.csv')   # atomic: the live build may be reading it
print('\nwritten', len(rows), 'proposals to out/warn_leg_proposals.csv')
