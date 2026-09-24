"""The vacancy rate as the second condition of the American call (3 September 2026, night, third pass).

Michaillat and Saez read the vacancy rate beside the unemployment rate; here it is read alone, in
Sahm's form - the three-month mean of the rate below its maximum over the previous twelve months,
in points - on Petrosky-Nadeau and Zhang's monthly series to 2000 and JOLTS after
(lab/vac/vacancy_rate_PNZ_JOLTS.csv, current vintage).  Part one: the maximum inside each of the
sixteen claims episodes, the first month at 0.5 / 0.6 / 0.8, and every crossing outside recession
windows since 1948.  Part two: the same object on JOLTS as first published (ALFRED vintages from
August 2010, the rate rebuilt as openings over payrolls plus openings) - the as-of readings around
2020 and 2022-24, and the first vintage day at each line.  Output vacancy_veto.log.
"""
import sys; sys.path.insert(0, '/home/claude/lab/slack'); sys.path.insert(0, '/home/claude/lab/rt')
import pandas as pd, numpy as np, alfred
from objects import load, sahm
from bound import PEAKS, TROUGHS, M, months

o = load(); v = o['-vacancy rate']; g = sahm(v, 3, 12)
print('the vacancy rate as the second condition (Petrosky-Nadeau-Zhang to 2000, JOLTS after; current vintage)')
EPS = [('1948-11', '1949-10'), ('1951-06', '1952-08'), ('1952-03', '1952-12'), ('1953-07', '1954-05'), ('1957-08', '1958-04'), ('1960-04', '1961-02'), ('1967-01', '1968-03'), ('1969-12', '1970-11'),
       ('1973-11', '1975-03'), ('1980-01', '1980-07'), ('1981-07', '1982-11'), ('1990-07', '1991-03'), ('2001-03', '2001-11'), ('2007-12', '2009-06'), ('2020-02', '2020-04'), ('2023-06', '2025-06')]
print('episode    max v-gap inside [start-3m, end]   first month >= 0.5 / 0.6 / 0.8 (months after start)')
for a, b in EPS:
    seg = g[M(a) - pd.DateOffset(months=3): M(b)]
    row = []
    for line in (0.5, 0.6, 0.8):
        h = seg[seg >= line]; row.append('   -' if h.empty else f'{months(h.index[0], M(a)):+4d}')
    print(f'{a}    {seg.max():5.2f}                              ' + '  '.join(row))
def alone(line):
    on = False; out = []
    for t, val in g['1948':].items():
        if val >= line and not on:
            inside = any(M(p) - pd.DateOffset(months=9) <= t <= M(q) + pd.DateOffset(months=6) for p, q in zip(PEAKS, TROUGHS)) or (M('2022-06') <= t <= M('2026-06'))
            if not inside: out.append(t.strftime('%Y-%m'))
            on = True
        elif val < line: on = False
    return out
for line in (0.5, 0.6, 0.8, 1.0): print(f'own firings outside [peak-9m, trough+6m] since 1948 at {line}: {alone(line)}')
print('\nthe vacancy rate itself, 1966-1968 and 2022-2025:'); print((-v)['1966-06':'1968-03'].round(2).tolist()); print((-v)['2022-01':'2025-06'].round(2).tolist())

print('\nREAL TIME: the vacancy gap on JOLTS as first published (ALFRED JTSJOL vintages from August 2010; the rate = openings / (payrolls + openings), payrolls current vintage)')
pay = pd.read_csv('/home/claude/lab/cps/03_payroll_employment/monthly/PAYEMS.csv'); pay.columns = ['d', 'v']; pay['d'] = pd.to_datetime(pay['d']); pay = pay.set_index('d')['v'].astype(float)
vints = alfred.vintages('JTSJOL'); print('vintages', len(vints), vints[0].date(), vints[-1].date())
rows = []
for vd in vints:
    s = alfred.asof('JTSJOL', vd)
    if s is None: continue
    rate = (s / (pay.reindex(s.index) + s) * 100).dropna()
    m3 = rate.rolling(3).mean(); gap = (m3.shift(1).rolling(12).max() - m3).dropna()
    if len(gap) == 0: continue
    rows.append((vd, gap.index[-1], round(float(gap.iloc[-1]), 2), round(float(rate.iloc[-1]), 2)))
df = pd.DataFrame(rows, columns=['vintage', 'latest_month', 'gap', 'rate']).set_index('vintage')
print('as-of readings, 2019-10 to 2020-08:'); print(df['2019-10':'2020-08'].to_string())
print('as-of readings, 2022-06 to 2024-10:'); print(df['2022-06':'2024-10'].to_string())
print('first vintage day with gap >= 0.5 / 0.6 / 0.8 in 2010-2019 (would be a false real-time crossing):', [(line, df[(df.index < '2020-01-01') & (df.gap >= line)].index.min()) for line in (0.5, 0.6, 0.8)])
print('first vintage day with gap >= 0.5 / 0.6 / 0.8 from 2020:', [(line, df[(df.index >= '2020-01-01') & (df.gap >= line)].index.min()) for line in (0.5, 0.6, 0.8)])
print('first vintage day with gap >= 0.5 / 0.6 / 0.8 from 2022:', [(line, df[(df.index >= '2022-01-01') & (df.gap >= line)].index.min()) for line in (0.5, 0.6, 0.8)])
print(f"the pre-pandemic high of the as-of gap (vintages to March 2020, before the pandemic reached the data): {df[:'2020-03-31'].gap.max():.2f} on {df[:'2020-03-31'].gap.idxmax():%Y-%m-%d}; the reading on 29 August 2023: {df.loc['2023-08-29', 'gap']:.2f}")
