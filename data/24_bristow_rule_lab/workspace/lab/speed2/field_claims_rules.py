"""The field's other claims rules, read on this route's data (3 September 2026, night, fifth pass; Rule 16).

The detector sweep of this night (lab/research/detector_sweep_2026-09-03.md) found two claims-based one-call
rules outside the field survey of 22 August: Hester's (Hussman Funds, November 2025) - "In every case that the
4-week average of jobless claims has climbed by 90,000 from a 52-week low, there's been a recession ... only one
false positive (in a February 1977 report ...)" - and the Budget Lab's (Yale, 10 August 2026) - the 12-week
trailing average of claimants as a share of covered employment, more than 0.25 points above its 52-week minimum.
Here both are read on the Department's national weekly file: the current seasonally adjusted series from 1967
(Hester's is a level rule in thousands, so it is read on the levels as published today) and, for Hester's rule,
on the route's real-time seasonal adjustment from 1969; the Budget Lab's on the insured unemployment rate
(FRED IURSA, 1971-) as the nearest public form of claimants over covered employment.  Each rule: episodes
(first week the gap crosses the line after at least 26 weeks below it), the days from the peak month's end for
each of the thirteen since 1967, and every other episode.  Publication: the Thursday after the week (5 days).
Output field_claims_rules.log.
"""
import numpy as np, pandas as pd
W = '/home/claude/lab/weekly'
N = pd.read_csv(f'{W}/DOL_national_weekly_claims_1967.csv', index_col=0, parse_dates=True)
R = pd.read_csv(f'{W}/DOL_national_weekly_claims_sa_rt.csv', index_col=0, parse_dates=True)
iur = pd.read_csv('/home/claude/archive/data/fred/IURSA.csv'); iur.columns = ['d', 'v']; iur = iur.set_index(pd.to_datetime(iur['d']))['v'].astype(float)
PEAKS = ['1969-12', '1973-11', '1980-01', '1981-07', '1990-07', '2001-03', '2007-12', '2020-02', '2023-07']
TROUGHS = ['1970-11', '1975-03', '1980-07', '1982-11', '1991-03', '2001-11', '2009-06', '2020-04', '2024-08']
M = lambda s: pd.Timestamp(s + '-01')

def episodes(g, line, quiet=26, pub=5):
    out = []; below = 0
    for t, v in g.dropna().items():
        if v >= line:
            if below >= quiet: out.append(t + pd.Timedelta(days=pub))
            below = 0
        else: below += 1
    return out

def score(eps, label):
    rows = []; used = set()
    for p, q in zip(PEAKS, TROUGHS):
        c = [e for e in eps if M(p) - pd.DateOffset(months=6) <= e <= M(q) + pd.offsets.MonthEnd(0)]
        if c: used.add(c[0]); rows.append(f'{p}:{(c[0] - (M(p) + pd.offsets.MonthEnd(0))).days:+d}d')
        else: rows.append(f'{p}:none')
    other = [e.strftime('%Y-%m-%d') for e in eps if e not in used]
    lags = [int(r.split(':')[1][:-1]) for r in rows if 'none' not in r]
    print(f'{label}\n   peaks: ' + ' '.join(rows) + f'\n   reached {len(lags)}/{len(PEAKS)}, median {np.median(lags):.0f} d, within a month {sum(l <= 30 for l in lags)};  other episodes ({len(other)}): {other}')

print("HESTER (Hussman Funds, November 2025): 4-week average of initial claims 90,000 above its 52-week low")
g = N['ic_sa'].rolling(4).mean(); g = g - g.rolling(52, min_periods=26).min()
score(episodes(g['1968':], 90000), '  on the current seasonally adjusted file (levels as published today)')
gr = R['ic_sa_rt'].rolling(4).mean(); gr = gr - gr.rolling(52, min_periods=26).min()
score(episodes(gr['1970':], 90000), "  on the route's real-time seasonal adjustment (1969-)")
for line in (60000, 75000, 90000, 120000):
    score(episodes(g['1968':], line), f'  current file, line {line:,}')
print('\n  the same in the route\'s units: 8-week mean of log initial claims above its 52-week low (leg I arms at 40 log points; the ceiling of the 1970 pause set the floor)')
gl = (np.log(N['ic_sa']) * 100).rolling(4).mean(); gl = gl - gl.rolling(52, min_periods=26).min()
for line in (25, 30, 40):
    score(episodes(gl['1968':], line), f'  4-week mean of the log, line {line} log points')

print("\nBUDGET LAB (Yale, 10 August 2026): 12-week trailing average of claimants over covered employment, 0.25 points above its 52-week minimum - read on the insured unemployment rate (FRED IURSA, 1971-)")
b = iur.rolling(12).mean(); b = b - b.rolling(52, min_periods=26).min()
PEAKS = PEAKS[1:]; TROUGHS = TROUGHS[1:]
for line in (0.2, 0.25, 0.3):
    score(episodes(b['1972':], line), f'  line {line}')
print('\n  Richmond Fed SOS for comparison (26-week mean of the insured rate 0.2 above its 52-week minimum)')
s = iur.rolling(26).mean(); s = s - s.rolling(52, min_periods=26).min()
score(episodes(s['1972':], 0.2), '  SOS 0.2')
print('\n  2023-24 on each: the maximum of the gap between June 2023 and December 2024 -',
      f"Hester {g['2023-06':'2024-12'].max():,.0f}; Budget Lab {b['2023-06':'2024-12'].max():.3f}; SOS {s['2023-06':'2024-12'].max():.3f}")
