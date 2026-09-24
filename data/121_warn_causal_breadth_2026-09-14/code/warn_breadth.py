"""WARN BREADTH, PRICED CAUSALLY - THE BUILD COLLECTION 117 LEFT UNDONE.

The WARN Act of 1988 makes an employer give the state sixty days' written notice before a mass layoff.
The notice therefore exists before the job ends BECAUSE THE LAW SAYS IT MUST, which makes it the only
labour datum in the country that is ahead of the event by construction rather than by correlation.

Collection 117 gathered 40,619 dated notices from 25 states and found that no single state works: a
state's notice flow is lumpy, one plant closure moves it, and its line is either unreachable or always
breached. It also found that the obvious breadth measure is degenerate - if each state's line is priced
as its maximum over every quiet week of the WHOLE record, then no state can be lit in a quiet week by
construction, breadth's own quiet ceiling is zero, and one lit state trips it. That is hindsight, not a
rule.

This prices every line the way the rule prices all its others: from an expanding window that ends
before the week being read, so nothing is ever set by data the reader did not yet have.

  - a notice is public seven days after it is filed;
  - a state's reading in week w is the count of notices it received in the trailing THIRTEEN weeks,
    using only notices public by w;
  - a state is LIT in week w if that count exceeds every count it produced in any QUIET week strictly
    before w, after a burn-in of three years of its own history;
  - quiet means outside a window from nine months before a peak to eighteen months after a trough;
  - breadth in week w is the share of REPORTING states that are lit, where a state reports once it has
    passed its burn-in, so the panel grows as states join - the evolving menu, which is what Anthony
    asked for on 14 September: a series enters on the day it began;
  - the rule fires when breadth exceeds every breadth reached in any quiet week strictly before w.

Nothing here is fitted. Every line is an expanding maximum over the past.
"""
import os, json, glob, csv, sys
import numpy as np, pandas as pd
W = os.path.expanduser('~/Projects/Onset Detector Data/117_warn_notices_2026-09-14/data/warn_notices')
if not os.path.isdir(W):
    W = os.path.expanduser('~/mnt/Onset Detector Data/117_warn_notices_2026-09-14/data/warn_notices')
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/out'
os.makedirs(OUT, exist_ok=True)
IDX = json.load(open(f'{W}/_INDEX.json'))

PEAKS   = ['1990-07','2001-03','2007-12','2020-02','2024-04']
TROUGHS = ['1991-03','2001-11','2009-06','2020-04','2024-08']
DEADLINE = {'1990-07':'1990-07-24','2001-03':'2001-03-24','2007-12':'2007-12-24',
            '2020-02':'2020-02-22','2024-04':'2024-04-23'}
RULE_CALL = {'1990-07':'1990-07-26','2001-03':'2001-03-29','2007-12':'2007-12-24',
             '2020-02':'2020-03-12','2024-04':'2024-05-03'}
M = lambda s: pd.Timestamp(s + '-01'); END = lambda s: M(s) + pd.offsets.MonthEnd(0)
PUBLIC_LAG = pd.Timedelta(days=7)
WINDOW = int(sys.argv[1]) if len(sys.argv) > 1 else 13     # weeks
PCTL = float(sys.argv[2]) if len(sys.argv) > 2 else 100.0  # the percentile of prior quiet that lights a state
MINREP = int(sys.argv[3]) if len(sys.argv) > 3 else 8      # states that must report before breadth is read at all

# Breadth's own line saturates on a small panel. Until 2005 only Oregon and Illinois report, so breadth
# can only be nothing, a half or one; it reaches one in some quiet week within a few years, its expanding
# quiet maximum becomes one, and after that nothing can ever exceed it. The measure is therefore not read
# until MINREP states report, and its line is priced only over the weeks where it is read. That buys
# honesty at the cost of coverage: with eight states the series begins in 2008, so WARN breadth cannot
# see 1990 or 2001 at all, and says so rather than pretending to.
BURN = 156                                                 # weeks of a state's own history

# Lighting a state only at a new all-time quiet HIGH makes breadth almost binary on a small panel:
# with two states reporting until 2005 it can only be 0, a half or one, its own expanding quiet
# maximum reaches a half within a few years, and after that nothing can exceed it. A percentile of
# the state's prior quiet distribution keeps the same causal discipline - nothing is read that was
# not already in the past - while letting breadth vary continuously, which is what a breadth measure
# needs in order to have a line at all.

weeks = pd.date_range('1989-01-07', '2026-09-05', freq='W-SAT')
quiet = pd.Series(True, index=weeks)
for pk, tr in zip(PEAKS, TROUGHS):
    quiet[(weeks >= M(pk) - pd.DateOffset(months=9)) & (weeks <= M(tr) + pd.DateOffset(months=18))] = False

counts = {}
for rec in IDX:
    st, col = rec['state'], rec['col']
    fs = glob.glob(f'{W}/{st.lower()}.csv') or glob.glob(f'{W}/{st.upper()}.csv')
    if not fs: print('no file for', st); continue
    # Texas's file has rows with more fields than its header, which the C parser refuses; the python
    # engine with on_bad_lines='skip' reads it. Texas is 7,303 notices from 1999 and four recessions,
    # so losing it to a parser default would have cost the panel its second-longest state.
    df = None
    for kw in (dict(low_memory=False), dict(engine='python', on_bad_lines='skip'),
               dict(engine='python', on_bad_lines='skip', sep=None)):
        try:
            df = pd.read_csv(fs[0], **kw)
            if col in df.columns or any(c.strip().lower()==col.strip().lower() for c in df.columns): break
        except Exception:
            df = None
    if df is None:
        print('unreadable', st); continue
    if col not in df.columns:
        cand = [c for c in df.columns if c.strip().lower() == col.strip().lower()]
        if not cand: print('no column', st, col); continue
        col = cand[0]
    import warnings as _w; _w.filterwarnings('ignore')
    d = pd.to_datetime(df[col], errors='coerce', format='mixed').dropna()
    d = d[(d >= '1988-01-01') & (d <= '2026-09-30')]
    if len(d) < 50: print('too few', st, len(d)); continue
    pubd = d + PUBLIC_LAG
    # A state that has no notices before 2008 must be ABSENT before 2008, not reporting zero. The
    # first version reindexed every state onto the full 1989-2026 week index and filled with zero,
    # which made all twenty-three states look present from 1992 and diluted breadth by counting
    # states that had not yet begun to publish. The series is masked to nothing before that state's
    # own first notice.
    s = pd.Series(1, index=pd.DatetimeIndex(pubd)).resample('W-SAT').sum().reindex(weeks).fillna(0)
    s[weeks < pubd.min()] = np.nan
    counts[st] = s.rolling(WINDOW, min_periods=WINDOW).sum()
    print(f'{st}: {len(d)} notices, {d.min().date()} to {d.max().date()}', flush=True)

print(f'\n{len(counts)} states in the panel, window {WINDOW} weeks', flush=True)
lit = pd.DataFrame(index=weeks); reporting = pd.DataFrame(index=weeks)
for st, s in counts.items():
    first = s.first_valid_index()
    if first is None: continue
    start = first + pd.Timedelta(weeks=BURN)
    if start > weeks[-1]: continue
    q = s.where(quiet)
    if PCTL >= 100:
        thr = q.expanding().max().shift(1)
    else:
        thr = q.expanding(min_periods=52).quantile(PCTL / 100.0).shift(1)
    lit[st] = pd.Series(((s > thr) & thr.notna()).values & (weeks >= start), index=weeks)
    reporting[st] = pd.Series((weeks >= start), index=weeks)
n_rep = reporting.sum(axis=1)
breadth = (lit.sum(axis=1) / n_rep.replace(0, np.nan))
res = pd.DataFrame(dict(reporting=n_rep, lit=lit.sum(axis=1), breadth=breadth))
res.to_csv(f'{OUT}/warn_breadth_{WINDOW}w.csv')

breadth = breadth.where(n_rep >= MINREP)
bq = breadth.where(quiet)
line = bq.expanding(min_periods=52).max().shift(1)
fire = (breadth > line) & line.notna()
# THE LIVE READING (14 September 2026, for v3.36). The site shows every object against its line, so
# the leg has to publish the same pair the other legs publish: the breadth of the week and the line it
# is read against, which is the highest breadth reached in any quiet week strictly before that week.
pd.DataFrame(dict(reporting=n_rep, lit=lit.sum(axis=1), breadth=breadth, line=line,
                  ratio=(breadth / line.replace(0, np.nan)))).dropna(subset=['breadth']).to_csv(
    f'{OUT}/warn_live_{WINDOW}w_{int(PCTL)}.csv', index_label='date')

first_read = breadth.first_valid_index()
print('breadth first read:', first_read, ' (panel reaches', MINREP, 'states)')
print('weeks with a reading:', int(breadth.notna().sum()), ' first:', breadth.first_valid_index())
for yr in (1992, 1995, 2000, 2005, 2008, 2012, 2020, 2024):
    k = n_rep[n_rep.index.year == yr]
    if len(k): print(f'   states reporting in {yr}: {int(k.iloc[0])}')
print('\nfalse alarms (quiet weeks that fire):')
fa = [d for d in weeks[fire & quiet]]
eps, last = [], None
for d in fa:
    if last is None or (d - last).days > 183: eps.append(str(d.date()))
    last = d
print(f'  {len(eps)} episodes: {eps[:10]}')
print('\nrecessions:')
rows = []
for pk, tr in zip(PEAKS, TROUGHS):
    seg = fire[(weeks >= M(pk) - pd.DateOffset(months=6)) & (weeks <= M(tr))]
    hit = seg[seg]
    first = hit.index[0] if len(hit) else None
    rows.append(dict(peak=pk, fired=str(first.date()) if first is not None else '',
                     lead_days=(first - END(pk)).days if first is not None else None,
                     beat_deadline=bool(first is not None and first <= pd.Timestamp(DEADLINE[pk])),
                     vs_rule_days=(first - pd.Timestamp(RULE_CALL[pk])).days if first is not None else None,
                     reporting=int(n_rep.get(first, 0)) if first is not None else None))
print(pd.DataFrame(rows).to_string(index=False))
