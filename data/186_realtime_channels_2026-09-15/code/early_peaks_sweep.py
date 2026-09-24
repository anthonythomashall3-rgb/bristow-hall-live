#!/usr/bin/env python3
"""The four early peaks, swept against 458 NBER Macrohistory series in the episode form.

THE GAP THIS ADDRESSES. Collection 171 found seven peaks with no still-publishing series covering them,
and the first four -- November 1948, July 1953, August 1957 and April 1960 -- sit before almost every
object the rule reads. Weekly claims begin in 1967. JOLTS begins in 2000. WARN notices begin in 1989.
The rule has been scored on those peaks with whatever reached them, which was little, and a rule never
tested on a quarter of the record has not been tested.

458 US monthly NBER Macrohistory series that reach 1955 or later are now held. This prices each of them
as a cause-side proposer conjoined with one of five confirmers that also reach back that far, taking
each episode of the conjoined state as one leg proposal -- the form `leg_K_state.py` established works.

WHAT A RESULT HERE IS AND IS NOT. These series are discontinued, so nothing found here can witness a
future recession, and none of it may be presented as if it could. What it can do is answer a question
the programme has never been able to answer: **does the conjunction architecture work on 1948, 1953,
1957 and 1960, or does it only work on the period it was built in?** If cause-and-confirm conjunctions
fire early and cleanly on peaks nobody was looking at when the rule was designed, that is evidence the
method generalises backwards. If they do not, the rule's record on those peaks is luck.

The scoring is the programme's standing one, unchanged: zero quiet firings, at least one call inside
[-92, -1], and the 1965-68 credit crunch scored like every other stretch. Every firing across the whole
1946-2026 span is counted, so a series that calls 1948 beautifully and also fires in 1951, 1962 and 1966
fails, as it should.
"""
import os, json, itertools, warnings, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
ROOT = next((c for c in _C if os.path.isdir(os.path.join(c, '186_realtime_channels_2026-09-15'))), _C[0])
HERE = os.path.join(ROOT, '186_realtime_channels_2026-09-15')
NBERD, DATA, OUT = os.path.join(HERE, 'data_nber'), os.path.join(HERE, 'data'), os.path.join(HERE, 'out')
NBER = [('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
        ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
        ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04'),
        ('2024-04','2024-08')]
def me(y): return pd.Timestamp(y + '-01') + pd.offsets.MonthEnd(0)
PK = [me(p) for p, _ in NBER]; TR = [me(t) for _, t in NBER]
EARLY = {'1948-11', '1953-07', '1957-08', '1960-04'}
def inside(t): return any(p <= t <= r for p, r in zip(PK, TR))
CRUNCH = (pd.Timestamp('1965-07-01'), pd.Timestamp('1968-06-30'))

def rd(folder, sid):
    p = os.path.join(folder, sid + '.csv')
    if not os.path.exists(p): return None
    q = pd.read_csv(p); c = list(q.columns)
    s = pd.Series(pd.to_numeric(q[c[1]], errors='coerce').values,
                  index=pd.to_datetime(q[c[0]], errors='coerce')).dropna().sort_index()
    return s[~s.index.duplicated(keep='last')]

# Every NBER series in this collection is monthly and was published with a lag of roughly a month;
# forty days is the programme's monthly convention and is charged to all of them alike.
LAG = 40
DIRS = {'fall6m':   lambda s: -s.pct_change(6) * 100,
        'fall12m':  lambda s: -s.pct_change(12) * 100,
        'rise6m':   lambda s: s.pct_change(6) * 100,
        'gap_high': lambda s: (1 - s / s.rolling(24, min_periods=8).max()) * 100}
# CONFIRMERS CHOSEN FOR REACH, NOT CONVENIENCE. The first version of this sweep used five confirmers of
# which only two -- industrial production and the metals price -- began before 1940. With a twenty-year
# rolling line that meant no confirmer HAD a line before 1946, so 1948, 1953 and 1957 were unreachable
# BY CONSTRUCTION. It duly returned zero for all three and put every 1960 hit at the same -20 days from
# the single confirmer that could speak. That was an artefact of the setup, not a fact about those
# recessions. These ten all have a line at every early peak, and five come from the NBER collection
# itself -- including the pre-JOLTS layoff rate, which runs from 1930.
CONFS = {
 'ip_falling':           (DATA,  'INDPRO', lambda s: -s.pct_change(6) * 100),
 'metals_price_falling': (DATA,  'WPU101', lambda s: -s.pct_change(6) * 100),
 'hours_falling':        (DATA,  'AWHMAN', lambda s: -s.diff(6)),
 'mfg_emp_falling':      (DATA,  'MANEMP', lambda s: -s.pct_change(6) * 100),
 'unrate_rising':        (DATA,  'UNRATE', lambda s: s.diff(6)),
 'layoff_rate_rising':   (NBERD, 'M0852BUSM497NNBR', lambda s: s.diff(6)),
 'separations_rising':   (NBERD, 'M0854BUSM497NNBR', lambda s: s.diff(6)),
 'accessions_falling':   (NBERD, 'M0855BUSM497NNBR', lambda s: -s.diff(6)),
 'freight_cars_falling': (NBERD, 'M03002USM544NNBR', lambda s: -s.pct_change(12) * 100),
 'business_activity_falling': (NBERD, 'M12003USM516NNBR', lambda s: -s.pct_change(6) * 100),
}
IDX = pd.date_range('1946-01-31', '2026-09-30', freq='D')
def daily(b): return b.reindex(IDX.union(b.index)).ffill().reindex(IDX).fillna(False).astype(bool)
def hold(b, d): return b.rolling(d, min_periods=1).max().astype(bool)
def over_q(x, q, win):
    ln = x.shift(1).rolling(win, min_periods=max(10, win // 2)).quantile(q / 100.0)
    return (x > ln) & ln.notna()
def episodes(fire, minexp=9):
    calls, armed, last = [], True, None
    for t, f in fire.items():
        if armed and f: calls.append(t); armed = False; last = t
        elif not armed and last is not None and (t - last).days >= minexp * 30 and not f: armed = True
    return calls
def score(calls):
    used, leads = set(), {}
    for p in PK:
        c = [t for t in calls if 0 <= (p - t).days <= 400]
        if c: t = max(c); leads[p.strftime('%Y-%m')] = (t - p).days; used.add(t)
    quiet = [t for t in calls if t not in used and not inside(t)]
    crunch = [t for t in quiet if CRUNCH[0] <= t <= CRUNCH[1]]
    inw = {k: v for k, v in leads.items() if -92 <= v <= -1}
    return len(calls), len(leads), len(inw), len(quiet), len(crunch), inw, leads

CB = {}
for cn, (fol, sid, fn) in CONFS.items():
    s = rd(fol, sid)
    if s is None or len(s) < 120: print('  confirmer missing:', sid); continue
    x = fn(s).replace([np.inf, -np.inf], np.nan).dropna(); x.index = x.index + pd.Timedelta(days=LAG)
    # The grid is deliberately coarse. The question here is an EXISTENCE question -- does any clean
    # conjunction reach 1948, 1953 or 1957 at all -- and a coarse grid answers it. The full crossing was
    # 1.4 million conjunctions, about a day and a half of computing to answer yes or no.
    for cq, cwin in itertools.product((90, 95), (120,)):
        CB[(cn, cq, cwin)] = hold(daily(over_q(x, cq, cwin)), 270)
print('confirmers:', sorted(set(k[0] for k in CB)), flush=True)

files = sorted(f[:-4] for f in os.listdir(NBERD) if f.endswith('.csv'))
print('NBER proposers: %d' % len(files), flush=True)
rows, done = [], 0
for sid in files:
    s = rd(NBERD, sid)
    if s is None or len(s) < 120: done += 1; continue
    for dname, dfn in DIRS.items():
        x = dfn(s).replace([np.inf, -np.inf], np.nan).dropna()
        if len(x) < 120: continue
        x = x.copy(); x.index = x.index + pd.Timedelta(days=LAG)
        for pq, phold, pwin in itertools.product((95, 97), (270,), (120, 240)):
            Pb = hold(daily(over_q(x, pq, pwin)), phold)
            for (cn, cq, cwin), Cb in CB.items():
                n, nh, ni, nq, nc, inw, leads = score(episodes(Pb & Cb))
                if nq == 0 and ni > 0:
                    rows.append(dict(proposer=sid, direction=dname, p_q=pq, p_win=pwin, p_hold=phold,
                                     confirmer=cn, c_q=cq, c_win=cwin, n_fire=n, n_peak=nh, n_in=ni,
                                     n_quiet=nq, n_crunch=nc,
                                     n_early_in=sum(1 for k in inw if k in EARLY),
                                     first=str(s.index.min().date()), last=str(s.index.max().date()),
                                     inwindow=json.dumps(inw), all_leads=json.dumps(leads)))
    done += 1
    if done % 60 == 0: print('  %d/%d, %d admissible' % (done, len(files), len(rows)), flush=True)
D = pd.DataFrame(rows); D.to_csv(os.path.join(OUT, 'early_peaks_sweep2.csv'), index=False)
pd.set_option('display.width', 270)
COL = ['proposer','direction','p_q','p_win','p_hold','confirmer','c_q','c_win','n_fire','n_peak','n_in','n_early_in','first','last','inwindow']
print('\nADMISSIBLE (zero quiet firings, >=1 call inside [-92,-1]): %d' % len(D))
if len(D):
    print('distinct NBER series producing an admissible leg: %d' % D.proposer.nunique())
    print('\n-- ranked by how many of the FOUR EARLY PEAKS they call inside the window --')
    print(D.sort_values(['n_early_in','n_in','n_peak'], ascending=False)[COL].head(25).to_string(index=False))
    for pk in sorted(EARLY):
        h = D[D.inwindow.str.contains(pk)]
        print('\n%s : %d admissible configurations, %d distinct series' % (pk, len(h), h.proposer.nunique()))
        if len(h): print(h.sort_values(['n_fire']).head(4)[COL].to_string(index=False))
