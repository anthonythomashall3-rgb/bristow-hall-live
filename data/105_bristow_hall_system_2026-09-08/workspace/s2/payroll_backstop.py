# -*- coding: utf-8 -*-
"""E38, THE PAYROLL BACKSTOP CLOSER (v3.73, 23 September 2026, collection 333; screened in collection 323, approved by Anthony:
"for E38 backstop decision, yes!").

A closer of last resort in the union: it acts only on an episode that has stood open at least 90 days and that no other closer has
closed, on the employment situation's release day, when in that day's vintage (i) nonfarm payrolls have risen in each of the last
three months and (ii) the three-month average unemployment rate stands at least 0.3 points under its highest three-month average
since the month the episode opened. On the record it never acts first: on the ALFRED vintages it would have closed the nine
recessions since 1969 between 99 and 770 days AFTER the rule's own closes, and never in 2024 (323/out/e38_screen.json), so no close
moves. It exists for the recession the other closers might fail to close - a long labour-market recovery the weekly closer's own
confirmations do not see.

Data: the ALFRED vintage tables of PAYEMS and UNRATE (collection 27), refreshed by bhs_update.py; the latest column is today's
vintage and its name carries the day the print was published. Branch letter E.
"""
import os, csv
import pandas as pd

NG = 3; DU = 0.3; MIN_OPEN = 90

def load_vintages(path):
    """{vintage day: Series of the observations in that vintage}"""
    rows = list(csv.reader(open(path))); h = rows[0]; dates = [pd.Timestamp(r[0]) for r in rows[1:]]
    M = {}
    for j in range(1, len(h)):
        if '_' not in h[j]: continue
        vd = pd.Timestamp(h[j].split('_')[-1])
        s = pd.Series({dates[i]: float(rows[1 + i][j]) for i in range(len(dates)) if rows[1 + i][j] not in ('', '.')}).sort_index()
        if len(s): M[vd] = s
    return M

def latest_vintage(path):
    rows = list(csv.reader(open(path))); h = rows[0]
    vd = pd.Timestamp(h[-1].split('_')[-1])
    s = pd.Series({pd.Timestamp(r[0]): float(r[-1]) for r in rows[1:] if r[-1] not in ('', '.')}).sort_index()
    return vd, s

def condition(p, u, open_day):
    """the two conditions in one vintage (p: payrolls, u: the unemployment rate). Returns (holds, reading)"""
    r = dict(gains=None, u3_max=None, u3=None, turned=None, payroll_month=None)
    if p is None or u is None or len(p) < NG + 1: return False, r
    tail = p.iloc[-(NG + 1):]
    gains = sum(1 for k in range(NG) if tail.iloc[k + 1] > tail.iloc[k])
    r['gains'] = int(gains); r['payroll_month'] = p.index[-1].strftime('%Y-%m')
    om = pd.Timestamp(pd.Timestamp(open_day).year, pd.Timestamp(open_day).month, 1)
    uu = u[u.index >= om]
    if len(uu) >= 3:
        u3 = uu.rolling(3).mean().dropna()
        if len(u3):
            r['u3_max'] = round(float(u3.max()), 3); r['u3'] = round(float(u3.iloc[-1]), 3); r['turned'] = bool((u3.max() - u3.iloc[-1]) >= DU - 1e-9)
    holds = (gains == NG) and bool(r['turned'])
    return holds, r

def today_reading(al_dir, open_day, today):
    """the closer's reading on today's vintage for an open episode: fires on the vintage's day if the conditions hold and the episode
    has stood open MIN_OPEN days by then"""
    pv, p = latest_vintage(os.path.join(al_dir, 'PAYEMS_all_vintages.csv')); uv, u = latest_vintage(os.path.join(al_dir, 'UNRATE_all_vintages.csv'))
    holds, r = condition(p, u, open_day)
    day = max(pv, uv)
    open_days = (pd.Timestamp(day) - pd.Timestamp(open_day)).days
    fire = holds and open_days >= MIN_OPEN and pd.Timestamp(day) <= pd.Timestamp(today)
    r.update(vintage_day=str(day.date()), open_days=int(open_days), holds=bool(holds), fires=bool(fire), min_open_days=MIN_OPEN, gains_needed=NG, turn_needed=DU)
    return (day if fire else None), r

def first_fire_on_history(al_dir, open_day, until=None):
    """the first vintage day on which the closer would have acted for an episode opened on open_day (the screen of 323): None if never.
    `until` bounds the search (a closed episode: its close day - the closer is read only while the episode is open)."""
    P = load_vintages(os.path.join(al_dir, 'PAYEMS_all_vintages.csv')); U = load_vintages(os.path.join(al_dir, 'UNRATE_all_vintages.csv'))
    pv = sorted(P); uv = sorted(U); o = pd.Timestamp(open_day)
    def asof(M, keys, d):
        k = [x for x in keys if x <= d]; return M[k[-1]] if k else None
    for d in pv:
        if d <= o or (d - o).days < MIN_OPEN: continue
        if until is not None and d > pd.Timestamp(until): break
        holds, _ = condition(asof(P, pv, d), asof(U, uv, d), o)
        if holds: return d
    return None

if __name__ == '__main__':
    import sys, json
    AL = sys.argv[1]
    print(today_reading(AL, '2024-05-03', pd.Timestamp.today().normalize()))
