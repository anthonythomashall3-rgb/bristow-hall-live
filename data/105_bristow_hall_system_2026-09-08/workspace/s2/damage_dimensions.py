# -*- coding: utf-8 -*-
"""THE DAMAGE GRADE IN THREE DIMENSIONS (v3.73, 23 September 2026, collection 333; the test in 327/code/damage_consensus_grade.py;
Anthony: "is there a way to meet the consensus? find it!!!").

The recession line's height is its damage on the scale of ten, the Great Depression at 10. From v3.57 the grade was the labour
dimension alone: the geometric mean of the unemployment rate's deepest excess over its pre-recession low (points) and of that excess
summed week by week (point-months), on a logarithmic scale. v3.73 keeps that arithmetic and applies it to two more dimensions:

  output      real GDP inside the episode - the peak-to-trough fall (per cent) and the cumulative loss below the peak (per cent x quarters);
  production  industrial production inside the episode - the peak-to-trough fall (per cent) and the cumulative loss (per cent x months).

Each dimension: score = 10 * ln(1 + sqrt(depth x cumulative)) / ln(1 + sqrt(depth_1929-33 x cumulative_1929-33)). The grade is the
arithmetic mean of the three dimensions. Against the ex-post consensus of collection 196 (six measures, thirteen episodes since 1948,
each candidate ranked by height) it orders 75 of 78 pairs as the consensus does (Spearman 0.978); the labour dimension alone orders 72
(0.938). The three pairs it misses are pairs the consensus itself has nearly tied. No weight was fitted: the three dimensions carry
equal weight, and inside each dimension depth and duration carry equal weight, exactly as the labour grade always did.

Windows. The episode is the rule's own: the call month to the close month (the open episode: to today). Output: the quarters from the
one before the call's quarter to the close's quarter; the peak anywhere in that span, the trough after it. Production: the months from
twelve before the call month to the close month; the peak anywhere in that span, the trough after it and not before the call month.
The Depression on the same arithmetic: GDP 26.3 per cent and 298.5 per cent x quarters (collection 196, annual real GDP 1929-33 x 4);
industrial production 53.6 per cent and 1413 per cent x months (INDPRO, August 1929 to March 1933, computed in 327).

Vintages, the fifth form's rule (17 September 2026: "the nowcast for current times, the data we already have for past times"): every
quarter and month that has printed is read as published today; the open recession's unprinted quarter is bridged by the Atlanta Fed's
GDPNow (the latest nowcast, an annual rate, applied to the last printed level for one quarter); an unprinted month of production is not
guessed - production counts the months that have printed. A closed recession's grade is therefore revised only by the agencies' own
revisions of its months and quarters, as the labour grade already is.

Data: the ALFRED vintage tables in collection 27 (GDPC1, GDPNOW, INDPRO), refreshed by bhs_update.py; the last column is today's
vintage. Nothing here reads anything the site's build did not already hold on the disk.
"""
import os, csv, math
import numpy as np, pandas as pd

DEP = dict(u_depth=21.7, u_pm=528.3, gdp_pt=26.3, gdp_cum=298.5, ip_pt=53.6, ip_cum=1413.0)

def score2(depth, cum, dep_depth, dep_cum):
    """the dimension's score of ten: log of the geometric mean of depth and cumulative loss, the Depression at 10"""
    x = (max(float(depth), 0.0) * max(float(cum), 0.0)) ** 0.5
    return 10.0 * math.log1p(x) / math.log1p((dep_depth * dep_cum) ** 0.5)

def grade(labour, output, production):
    """the grade: the arithmetic mean of the three dimensions (None for a dimension not yet readable counts as zero, flagged by the caller)"""
    return (float(labour or 0.0) + float(output or 0.0) + float(production or 0.0)) / 3.0

def _last_column(path):
    rows = list(csv.reader(open(path))); h = rows[0]
    vd = h[-1].split('_')[-1]
    s = pd.Series({pd.Timestamp(r[0]): float(r[-1]) for r in rows[1:] if r[-1] not in ('', '.')}).sort_index()
    return s, pd.Timestamp(vd)

def load_current(alfred_dir):
    """today's vintage of real GDP, of GDPNow (its latest quarter and annual rate) and of industrial production"""
    G, gv = _last_column(os.path.join(alfred_dir, 'GDPC1_all_vintages.csv'))
    I, iv = _last_column(os.path.join(alfred_dir, 'INDPRO_all_vintages.csv'))
    try:
        N, nv = _last_column(os.path.join(alfred_dir, 'GDPNOW_all_vintages.csv'))
        now = dict(quarter=N.index[-1], rate=float(N.iloc[-1]), vintage=nv)
    except Exception:
        now = None
    return dict(gdp=G, gdp_vintage=gv, ip=I, ip_vintage=iv, nowcast=now)

def qstart(t):
    t = pd.Timestamp(t); return pd.Timestamp(t.year, 3 * ((t.month - 1) // 3) + 1, 1)

def pt_and_cum(seg, not_before=None):
    """peak anywhere in seg, trough after it (and not before `not_before`): the fall per cent and the cumulative shortfall (per cent x periods)"""
    best = 0.0; cum = 0.0
    for qi, v in seg.items():
        later = seg[seg.index > qi]
        if not_before is not None: later = later[later.index >= not_before]
        if len(later):
            f = (v - later.min()) / v * 100.0
            if f > best: best = f; cum = float(((v - later) / v * 100.0).clip(lower=0).sum())
    return best, cum

def output_dimension(G, call, through, nowcast=None, today=None):
    """real GDP inside the episode from the quarter before the call's quarter to `through`'s quarter. A quarter inside the span that has
    not printed is bridged by the nowcast when it is the nowcast's own quarter; further unprinted quarters are not guessed."""
    q0 = qstart(call) - pd.DateOffset(months=3); q1 = qstart(through)
    seg = G[(G.index >= q0) & (G.index <= q1)].copy(); used_now = False
    if nowcast is not None and len(seg) and q1 > seg.index.max():
        nq = qstart(nowcast['quarter'])
        if nq == seg.index.max() + pd.DateOffset(months=3) and nq <= q1:
            seg[nq] = float(seg.iloc[-1]) * (1.0 + nowcast['rate'] / 100.0) ** 0.25; seg = seg.sort_index(); used_now = True
    if len(seg) < 2: return dict(pt=0.0, cum=0.0, score=0.0, quarters=int(len(seg)), nowcast=used_now, through=(str(seg.index.max().date()) if len(seg) else None))
    pt, cum = pt_and_cum(seg)
    return dict(pt=round(float(pt), 4), cum=round(float(cum), 4), score=round(float(score2(pt, cum, DEP["gdp_pt"], DEP["gdp_cum"])), 4), quarters=int(len(seg)), nowcast=used_now, through=str(seg.index.max().date()))

def production_dimension(I, call, through):
    """industrial production from twelve months before the call month to `through`'s month; the trough not before the call month"""
    m_call = pd.Timestamp(pd.Timestamp(call).year, pd.Timestamp(call).month, 1); m1 = pd.Timestamp(pd.Timestamp(through).year, pd.Timestamp(through).month, 1)
    seg = I[(I.index >= m_call - pd.DateOffset(months=12)) & (I.index <= m1)]
    if len(seg) < 2: return dict(pt=0.0, cum=0.0, score=0.0, months=int(len(seg)), through=(str(seg.index.max().date()) if len(seg) else None))
    pt, cum = pt_and_cum(seg, not_before=m_call)
    return dict(pt=round(float(pt), 4), cum=round(float(cum), 4), score=round(float(score2(pt, cum, DEP["ip_pt"], DEP["ip_cum"])), 4), months=int(len(seg)), through=str(seg.index.max().date()))

def labour_score(depth, pm):
    return score2(depth, pm, DEP['u_depth'], DEP['u_pm'])

def episode_path(cur, call, close, week_pubs, open_episode=False):
    """the two dimensions week by week: for each (week_ending, published) of the labour path, the output and production dimensions
    read through the week's own quarter and month, and on the close day through the close month (a closed recession: as published today;
    the open one: the nowcast for the unprinted quarter, printed months only for production). Returns a DataFrame indexed by the publication day."""
    rows = []; n = len(week_pubs)
    for i, (t, p) in enumerate(week_pubs):
        # each week reads through its own month and quarter; the close day's row reads through the close month, the record's window
        thr = pd.Timestamp(t) if close is None else (pd.Timestamp(close) if i == n - 1 else min(pd.Timestamp(t), pd.Timestamp(close)))
        o = output_dimension(cur['gdp'], call, thr, nowcast=(cur['nowcast'] if open_episode else None))
        q = production_dimension(cur['ip'], call, thr)
        rows.append(dict(published=pd.Timestamp(p), week_ending=pd.Timestamp(t), output=o['score'], production=q['score'], gdp_pt=o['pt'], gdp_cum=o['cum'], gdp_nowcast=o['nowcast'], ip_pt=q['pt'], ip_cum=q['cum']))
    df = pd.DataFrame(rows)
    if not len(df): return df
    # one row per publication day (24 September 2026, E66): a catch-up release publishes several weeks on one day (seven on 20 November 2025;
    # the early first prints carry a week's first revision on the next issue's day), and a duplicated index made the caller's float() fail.
    # The row kept is the latest week published that day, the one read through the latest data.
    df = df.sort_values(['published', 'week_ending'], kind='stable').drop_duplicates('published', keep='last')
    return df.set_index('published').sort_index()

if __name__ == '__main__':
    import sys, json
    AL = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/Projects/Onset Detector Data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages')
    cur = load_current(AL)
    for call, close in [('2007-12-24', '2009-06-18'), ('2020-03-12', '2020-05-07'), ('2024-05-03', '2024-09-26')]:
        print(call, output_dimension(cur['gdp'], call, close), production_dimension(cur['ip'], call, close))
