#!/usr/bin/env python3
"""
Recession Signals Without Recession and the Case of 2024
Hall & Bristow, USC Marshall FBE Working Paper

reproduce.py — recomputes every statistic reported in the paper from the
deposited CSVs and prints each beside the value the manuscript states.

Usage:   python3 reproduce.py
Exit code 0 if every reported value reproduces, 1 otherwise.
"""
import sys, os, statistics
import pandas as pd, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FRED = os.path.join(HERE, '..', 'data', 'fred')
DASH = os.path.join(HERE, '..', 'data', 'dashboard')

def series(name):
    d = pd.read_csv(os.path.join(FRED, name + '.csv'))
    d.columns = ['date', 'v']
    d['date'] = pd.to_datetime(d['date'])
    d['v'] = pd.to_numeric(d['v'], errors='coerce')
    return d.set_index('date')['v'].dropna()

PASS = FAIL = 0
def report(section, claim, computed, stated, tol=1e-9):
    global PASS, FAIL
    if isinstance(stated, (str, bool, tuple)):
        ok = computed == stated
    else:
        ok = abs(computed - stated) <= tol
    PASS, FAIL = (PASS + 1, FAIL) if ok else (PASS, FAIL + 1)
    mark = 'ok  ' if ok else 'FAIL'
    print(f"  {mark} [{section}] {claim}\n         computed {computed!r}   paper states {stated!r}")

# NBER chronology, from USREC (USREC = 1 from the month after the peak through the trough)
PEAKS  = ['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11',
          '1980-01','1981-07','1990-07','2001-03','2007-12','2020-02']
TROUGHS= ['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03',
          '1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']
months = lambda a, b: (a.year - b.year) * 12 + (a.month - b.month)

u   = series('UNRATE');   sc  = series('SAHMCURRENT'); sr = series('SAHMREALTIME')
rec = series('USREC');    t10 = series('T10Y2Y');      ff = series('FEDFUNDS')
gdp = series('GDPC1');    gdi = series('A261RX1Q020SBEA')
pilt= series('W875RX1');  mts = series('CMRMTSPL');    ip = series('INDPRO')
jo  = series('JTSJOL');   lf  = series('CLF16OV');     iur = series('IURSA')
cpi = series('CPIAUCNS'); wal = series('WALCL');       pay = series('PAYEMS')
tru = series('DFEDTARU'); trl = series('DFEDTARL')
ma3 = series('CFNAIMA3'); cp  = series('RECPROUSM156N'); ham = series('JHGDPBRINDX')

print("\n" + "=" * 78)
print("SECTION 3 — the post-2022 episode")
print("=" * 78)

runs, cur = [], []
for d, v in t10.items():
    if v < 0: cur.append((d, v))
    elif cur: runs.append(cur); cur = []
if cur: runs.append(cur)
r22 = max(runs, key=len)
report('3', 'longest inversion, trading days', len(r22), 537)
report('3', 'inversion start', r22[0][0].strftime('%Y-%m-%d'), '2022-07-06')
report('3', 'inversion end', r22[-1][0].strftime('%Y-%m-%d'), '2024-08-26')
report('3', 'inversion trough', round(min(v for _, v in r22), 2), -1.08)
report('3', 'cumulative area below zero, pp-days', round(sum(v for _, v in r22)), -259)
report('3', 'largest area on record (1978-80)', round(min(sum(v for _, v in r) for r in runs)), -304)
n98 = [(d, v) for d, v in t10.items() if d.year == 1998 and v < 0]
report('3', '1998 negative trading days', len(n98), 27)
report('3', '1998 deepest reading', round(min(v for _, v in n98), 2), -0.07)

ann = lambda s: (s / s.shift(1)) ** 4 - 1
report('3', 'real GDP 2022 Q1, current vintage, %', round(float(ann(gdp)['2022-01-01']) * 100, 1), -1.0, 0.05)
report('3', 'real GDP 2022 Q2, current vintage, %', round(float(ann(gdp)['2022-04-01']) * 100, 1), 0.6, 0.05)
report('3', 'real GDI 2022 Q2, %', round(float(ann(gdi)['2022-04-01']) * 100, 1), -0.3, 0.05)
report('3', 'real GDI 2022 Q4, %', round(float(ann(gdi)['2022-10-01']) * 100, 1), -2.3, 0.05)
report('3', 'PILT, Dec 2021 to Jun 2022, %', round(100 * (float(pilt['2022-06-01']) / float(pilt['2021-12-01']) - 1), 1), -1.7, 0.05)
report('3', 'mfg and trade sales, Jan to Jun 2022, %', round(100 * (float(mts['2022-06-01']) / float(mts['2022-01-01']) - 1), 1), -2.6, 0.05)
report('3', 'industrial production, Apr 2022 to Jan 2024, %', round(100 * (float(ip['2024-01-01']) / float(ip['2022-04-01']) - 1), 1), -2.2, 0.05)
report('3', 'payrolls, first half of 2022, %', round(100 * (float(pay['2022-06-01']) / float(pay['2021-12-01']) - 1), 1), 1.7, 0.05)

report('3', 'effective funds rate, Feb 2022, %', round(float(ff['2022-02-01']), 2), 0.08)
report('3', 'effective rate rise, Mar 2022 to Aug 2023, pp', round(float(ff['2023-08-01'] - ff['2022-03-01']), 2), 5.13)
report('3', 'target range rise, upper bound, pp', round(float(tru['2023-08-01'] - tru['2022-03-01']), 2), 5.25)
report('3', 'funds rate cycle peak, %', round(float(ff['2022-01-01':'2026-07-01'].max()), 2), 5.33)
report('3', 'balance sheet peak, $tn', round(float(wal.max()) / 1e6, 2), 8.97)
report('3', 'balance sheet peak week', wal.idxmax().strftime('%Y-%m-%d'), '2022-04-13')

yoy = (cpi / cpi.shift(12) - 1) * 100
report('3', 'CPI inflation, Nov 2021, %', round(float(yoy['2021-11-01']), 1), 6.8, 0.05)
report('3', 'CPI inflation, Dec 2021, %', round(float(yoy['2021-12-01']), 1), 7.0, 0.05)
report('3', 'CPI inflation, Jun 2022, %', round(float(yoy['2022-06-01']), 1), 9.1, 0.05)

report('3', 'unemployment trough, Apr 2023, %', round(float(u['2023-04-01']), 1), 3.4)
for m, rt, cv in [('2024-07-01', 0.53, 0.50), ('2024-08-01', 0.57, 0.57), ('2024-09-01', 0.50, 0.53)]:
    report('3', f'Sahm indicator {m[:7]}, real time', round(float(sr[m]), 2), rt)
    report('3', f'Sahm indicator {m[:7]}, current vintage', round(float(sc[m]), 2), cv)
report('3', 'job openings peak, Mar 2022, thousands', int(jo.max()), 12301)
report('3', 'job openings, Aug 2024, thousands', int(jo['2024-08-01']), 7520)
report('3', 'fall in job openings, %', round(100 * (float(jo['2024-08-01']) / float(jo.max()) - 1)), -39)
vac = jo / lf * 100
report('3', 'vacancy rate, Mar 2022, %', round(float(vac['2022-03-01']), 1), 7.5)
report('3', 'vacancy rate, Aug 2024, %', round(float(vac['2024-08-01']), 1), 4.5)

print("\n" + "=" * 78)
print("SECTION 2 — the Bristow Rule and the onset lag")
print("=" * 78)

def crossing_episodes(s, thr=0.50):
    out, cur = [], []
    for d, v in s.items():
        if v >= thr: cur.append(d)
        elif cur: out.append(cur); cur = []
    if cur: out.append(cur)
    return out

def bristow(s, peak, trough):
    """End date: arg max over the crossing episode plus the twelve months after it."""
    p, t = pd.Timestamp(peak + '-01'), pd.Timestamp(trough + '-01')
    e = [x for x in crossing_episodes(s) if x[0] >= p and x[0] <= t + pd.DateOffset(months=12)]
    if not e: return None
    w = s[e[0][0]:e[0][-1] + pd.DateOffset(months=12)]
    return w.idxmax()

gaps = []
for p, t in zip(PEAKS, TROUGHS):
    d = bristow(sc, p, t)
    gaps.append(months(d, pd.Timestamp(t + '-01')))
report('2', 'postwar recessions within three months of the trough', sum(1 for g in gaps if abs(g) <= 3), 12)
report('2', 'gap of zero (coincides exactly)', sum(1 for g in gaps if g == 0), 4)
report('2', 'largest absolute gap, months', max(abs(g) for g in gaps), 3)
report('2', 'median gap, signed', float(np.median(gaps)), 1.5)
report('2', 'median gap, unsigned', float(np.median([abs(g) for g in gaps])), 2.0)
report('2', 'leads, count', sum(1 for g in gaps if g < 0), 1)

rt_gaps = [months(bristow(sr, p, t), pd.Timestamp(t + '-01'))
           for p, t in zip(PEAKS, TROUGHS) if pd.Timestamp(t + '-01') >= sr.index[0]]
report('2', 'real-time recessions covered', len(rt_gaps), 9)
report('2', 'real-time within three months', sum(1 for g in rt_gaps if abs(g) <= 3), 8)
report('2', 'real-time worst gap, months', max(abs(g) for g in rt_gaps), 4)

def onset_lags(s):
    out = []
    for p, t in zip(PEAKS, TROUGHS):
        pd_, td = pd.Timestamp(p + '-01'), pd.Timestamp(t + '-01')
        if td < s.index[0]: continue
        w = s[pd_:td + pd.DateOffset(months=6)]; x = w[w >= 0.50]
        if len(x): out.append(months(x.index[0], pd_))
    return out
lc = onset_lags(sc)
report('2', 'onset lags, current vintage, range', (min(lc), max(lc)), (1, 8))
report('2', 'onset lags, current vintage, median', statistics.median(lc), 3)
report('2', 'onset lags, current vintage, mean', round(statistics.mean(lc), 1), 3.5, 0.05)
lr = onset_lags(sr)
report('2', 'onset lags, real time, range', (min(lr), max(lr)), (2, 4))
report('2', 'onset lags, real time, median', statistics.median(lr), 4)

d3 = sc - sc.shift(3)
herald = [months(d3[pd.Timestamp(p + '-01'):pd.Timestamp(t + '-01') + pd.DateOffset(months=12)].idxmax(),
                 pd.Timestamp(t + '-01')) for p, t in zip(PEAKS, TROUGHS)]
report('2', 'second-derivative herald exact on the trough', sum(1 for g in herald if g == 0), 5)
report('2', 'herald, latest past the trough, months', max(herald), 2)
report('2', 'herald, earliest before the trough, months', min(herald), -11)

W = []
for p, t in zip(PEAKS, TROUGHS):
    td = pd.Timestamp(t + '-01')
    e = [x for x in crossing_episodes(sc) if x[0] >= pd.Timestamp(p + '-01') and x[0] <= td + pd.DateOffset(months=12)]
    W.append((td, sc[e[0][0]:e[0][-1] + pd.DateOffset(months=12)]))
lens = [len(w) for _, w in W]
report('2', 'search window length, range, months', (min(lens), max(lens)), (24, 40))
inside = [sum(1 for d in w.index if abs(months(d, t)) <= 3) for t, w in W]
report('2', 'window months inside the tolerance, maximum', max(inside), 7)
probs = [a / b for a, b in zip(inside, lens)]
report('2', 'per-window chance under a uniform null, %', round(100 * statistics.mean(probs)), 23)
joint = 1.0
for x in probs: joint *= x
report('2', 'joint chance, one in N million', round(1 / joint / 1e6), 59, 1)
worst = max(sum(1 for t, w in W if abs(months(w.idxmax(), t + pd.DateOffset(months=k))) <= 3)
            for k in (-24, -18, -12, -6, 6, 12, 18, 24))
report('2', 'displaced-trough placebo, best false score', worst, 1)

durations = [months(pd.Timestamp(TROUGHS[i] + '-01'), pd.Timestamp(PEAKS[i] + '-01')) for i in range(11)]
report('2', 'postwar durations 1948-2009, range', (min(durations), max(durations)), (6, 18))
report('2', 'postwar durations, median', float(np.median(durations)), 10.0)

print("\n" + "=" * 78)
print("SECTION 4 — the screen")
print("=" * 78)

def screen(s):
    inr = rec.reindex(s.index).fillna(0)
    flag = (s >= 0.50) & (inr == 0)
    eps, cur = [], []
    for d, f in flag.items():
        if f: cur.append(d)
        elif cur: eps.append(cur); cur = []
    if cur: eps.append(cur)
    trs = [pd.Timestamp(x + '-01') for x in TROUGHS]
    pks = [pd.Timestamp(x + '-01') for x in PEAKS]
    tails = [e for e in eps if any(0 <= months(e[0], t) <= 1 for t in trs)]
    warn  = [e for e in eps if e not in tails and any(0 <= months(p, e[-1]) <= 5 for p in pks)]
    stand = [e for e in eps if e not in tails and e not in warn]
    return int((inr == 0).sum()), int(flag.sum()), tails, warn, stand

non, cross, tails, warn, stand = screen(sc)
report('4', 'non-recession months, current vintage', non, 808)
report('4', 'of those at or above 0.50', cross, 129)
report('4', 'lagging-tail months', sum(len(e) for e in tails), 122)
report('4', 'lagging tails, count', len(tails), 12)
report('4', 'early-warning months', sum(len(e) for e in warn), 2)
report('4', 'standalone months', sum(len(e) for e in stand), 5)
report('4', 'standalone months as % of non-recession record', round(100 * sum(len(e) for e in stand) / non, 2), 0.62, 0.005)
report('4', 'standalone episodes', tuple(e[0].strftime('%Y-%m') for e in stand), ('2003-07', '2024-07'))

nonr, crossr, tailsr, warnr, standr = screen(sr)
report('4', 'non-recession months, real time', nonr, 704)
report('4', 'standalone months, real time', sum(len(e) for e in standr), 4)
report('4', 'standalone %, real time', round(100 * sum(len(e) for e in standr) / nonr, 2), 0.57, 0.005)
report('4', 'real-time standalone episodes longer than one month', sum(1 for e in standr if len(e) > 1), 1)

report('4', 'real-time 2003 July reading', round(float(sr['2003-07-01']), 2), 0.47)
report('4', '1966-67 Sahm peak', round(float(sc['1966-01-01':'1967-12-01'].max()), 2), 0.23)
report('4', '1985-86 Sahm peak', round(float(sc['1985-01-01':'1986-12-01'].max()), 2), 0.27)
report('4', '1962-63 Sahm peak', round(float(sc['1962-01-01':'1963-12-01'].max()), 2), 0.30)
report('4', '1966 spread negative in all twelve months',
       bool(((series('GS10') - series('GS1'))['1966-01-01':'1966-12-01'] < 0).all()), True)

print("\n" + "=" * 78)
print("SECTIONS 5 to 7 — the dated bar, the SOS indicator, corroboration")
print("=" * 78)

report('5', 'Bristow date for the 2024 episode', bristow(sc, '2024-04', '2024-08').strftime('%Y-%m'), '2024-08')
report('5', 'episode length, peak to trough, months', months(pd.Timestamp('2024-08-01'), pd.Timestamp('2024-04-01')), 4)
peaks_in_rec = [float(sc[pd.Timestamp(p + '-01'):pd.Timestamp(t + '-01') + pd.DateOffset(months=12)].max())
                for p, t in zip(PEAKS, TROUGHS)]
report('5', 'smallest in-recession peak', round(min(peaks_in_rec), 2), 1.50)
report('5', '2022 Sahm maximum', round(float(sc['2022-01-01':'2022-12-01'].max()), 2), 0.03)
report('5', '2023 Sahm maximum', round(float(sc['2023-01-01':'2023-12-01'].max()), 2), 0.30)
report('5', 'Sahm, Aug 2025', round(float(sc['2025-08-01']), 2), 0.13)
report('5', 'Sahm, Jul 2026', round(float(sc['2026-07-01']), 2), -0.03)
report('5', 'highest reading after Oct 2024', round(float(sc['2024-10-01':'2026-07-01'].max()), 2), 0.40)

ma26 = iur.rolling(26).mean()
sos = (ma26 - ma26.shift(1).rolling(52).min()).dropna()
plateau = sos['2023-01-01':'2023-12-31'].round(4)
plateau = plateau[plateau == 0.2000]
report('6', 'SOS plateau, weeks at exactly 0.2000', len(plateau), 12)
report('6', 'SOS plateau, first week', plateau.index.min().strftime('%Y-%m-%d'), '2023-09-02')
report('6', 'SOS plateau, last week', plateau.index.max().strftime('%Y-%m-%d'), '2023-11-18')
report('6', 'SOS never exceeds 0.20 in 2023', bool((sos['2023-01-01':'2023-12-31'] > 0.20).any()), False)

mi = pd.read_csv(os.path.join(DASH, 'michaillat_saez_recession_indicator.csv'))
mi.columns = ['date', 'm']; mi['date'] = pd.to_datetime(mi['date']); mi = mi.set_index('date')['m']
report('7', 'Michez indicator, Mar 2024', round(float(mi['2024-03-01']), 2), 0.29)
report('7', 'Michez peak, 2024', round(float(mi['2024-01-01':'2024-12-01'].max()), 2), 0.54)
report('7', 'Michez peak month', mi['2024-01-01':'2024-12-01'].idxmax().strftime('%Y-%m'), '2024-08')
report('7', 'Michez months at or above threshold from Mar 2024', int((mi['2024-03-01':'2025-05-01'] >= 0.29).sum()), 15)
report('7', 'Michez, 2022 maximum', round(float(mi['2022-01-01':'2022-12-01'].max()), 2), 0.04)
report('7', 'Michez, 2023 maximum', round(float(mi['2023-01-01':'2023-12-01'].max()), 2), 0.26)

ub = u.rolling(3).mean(); vb = (jo / lf * 100).rolling(3).mean()
vhat = (vb.shift(1).rolling(12).max() - vb)['2024-01-01':'2024-12-01']
uhat = (ub - ub.shift(1).rolling(12).min())['2024-01-01':'2024-12-01']
report('7', 'vacancy channel, 2024 minimum, pp', round(float(vhat.min()), 2), 0.71)
report('7', 'vacancy channel, Feb to Oct minimum, pp', round(float(vhat['2024-02-01':'2024-10-01'].min()), 2), 0.94)
report('7', 'unemployment sets the minimum in all twelve months', bool((uhat < vhat).all()), True)

print("\n" + "=" * 78)
print("SECTION 9 — instruments that never fired")
print("=" * 78)
report('9', 'CFNAI-MA3 low, 2022-2026', round(float(ma3['2022-01-01':'2026-07-01'].min()), 2), -0.39)
report('9', 'CFNAI-MA3 never reaches -0.70', bool((ma3['2022-01-01':'2026-07-01'] <= -0.70).any()), False)
report('9', 'Chauvet-Piger maximum, %', round(float(cp['2022-01-01':'2026-07-01'].max()), 1), 2.3, 0.05)
report('9', 'Hamilton index maximum', round(float(ham['2022-01-01':'2026-07-01'].max()), 1), 37.4, 0.05)
report('9', 'Hamilton never reaches 67', bool((ham['2022-01-01':'2026-07-01'] >= 67).any()), False)

print("\n" + "=" * 78)
print("SECTION 10 — the benchmark expansion")
print("=" * 78)
report('10', 'unemployment low, 2017-2019, %', round(float(u['2017-01-01':'2019-12-01'].min()), 1), 3.5)
pre = u[u.index < pd.Timestamp('2017-01-01')]
report('10', 'previous month at or below 3.5%', pre[pre <= 3.5].index.max().strftime('%Y-%m'), '1969-12')
report('10', 'CPI inflation, 2017-2019 average, %', round(float(yoy['2017-01-01':'2019-12-01'].mean()), 1), 2.1, 0.05)

print("\n" + "=" * 78)
print(f"REPRODUCED {PASS}    FAILED {FAIL}")
print("=" * 78 + "\n")
sys.exit(0 if FAIL == 0 else 1)
