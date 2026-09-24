# -*- coding: utf-8 -*-
"""THE JOLTS -> INDEED BRIDGE (v3.73, 23 September 2026, collection 333; the rule-4 test in collection 330).

The hub's vacancy object is JOLTS job openings over the labour force, first prints, and the gap of its four-month mean below the
highest of the prior four means; the openers ask whether that gap stood at 0.25 in two of the prior twelve months. When the Bureau
does not publish JOLTS (the autumn 2025 shutdown held two months), the object stops a month or two short and the condition goes
stale. This bridge carries it: for at most two missing months the openings are the last printed openings scaled by the Indeed
Hiring Lab's total job postings index (seasonally adjusted, the monthly mean of the daily index; published on GitHub, keyless,
about twelve days behind). Collection 330 measured the bridge on 70 months since August 2020: one month carried, mean error 0.05
points of the gap (the line is 0.25), agreement at the line 91 per cent; two months, 0.09 and 84 per cent; three months, 0.12 and
80 per cent - so the bridge stops at two, and a third missing month reads dark. The substitute months are flagged in the state and
on the data page and vanish the day the print lands; the labour force of a bridged month, if the jobs report is dark too, is the
last printed labour force, carried.

Inert otherwise: when every scheduled JOLTS month has printed the build reads exactly the files it read before. A drill
(BHS_JOLTS_DARK_MONTHS=n) cuts the last n printed months and bridges them, to show what the hub would have read.
"""
import os, json, datetime
import pandas as pd

INDEED_URL = 'https://raw.githubusercontent.com/hiring-lab/data/master/US/aggregate_job_postings_US.csv'
INDEED = os.path.join('cache', 'indeed_us_postings.csv')
JOLTS = os.path.join('cache', 'alfred_first_JTSJOL.csv'); CLF = os.path.join('cache', 'alfred_first_CLF16OV.csv'); RELCAL = os.path.join('cache', 'relcal_JTSJOL.csv')
SCHED = os.path.join('cache', 'release_schedule.csv'); DAYS = os.path.join('cache', 'vacancy_bridge_days.json')
MAX_MONTHS = 2; GRACE_DAYS = 3; INDEED_LAG_DAYS = 12

def indeed_monthly(path=INDEED):
    d = pd.read_csv(path, parse_dates=['date']); d = d[d['variable'] == 'total postings']
    s = pd.Series(pd.to_numeric(d['indeed_job_postings_index_SA'], errors='coerce').values, index=d['date']).dropna().sort_index()
    m = s.resample('MS').mean(); last_day = s.index.max()
    complete = m[m.index + pd.offsets.MonthEnd(0) <= last_day]   # a month counts only once its last day is in the file
    return complete, last_day

def expected_release(month):
    """the day the Bureau scheduled the month's JOLTS release (cache/release_schedule.csv); else the usual lag, five weeks after the month"""
    try:
        c = pd.read_csv(SCHED); c = c[c['series'] == 'JTSJOL']; c['reference_month'] = pd.to_datetime(c['reference_month'])
        r = c[c['reference_month'] == month]
        if len(r): return pd.Timestamp(r['release_date'].iloc[0])
    except Exception: pass
    return month + pd.offsets.MonthEnd(0) + pd.Timedelta(days=35)

def _al_dir():
    for root in (os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')):
        d = os.path.join(root, 'onset-detector-new-2026-08-23', '27_realtime_vintages', 'alfred_all_vintages')
        if os.path.isdir(d): return d
    return None
VINT_NAME = 'JTSJOL_all_vintages.csv'
def R_all_first_release(month):
    R = pd.read_csv(RELCAL, index_col=0, parse_dates=['first_release']); R.index = pd.to_datetime(R.index)
    return pd.Timestamp(R.loc[month, 'first_release']) if month in R.index else None
def vintage_table_bridged(rows, cut_from=None):
    """the ALFRED vintage table of JOLTS openings with the bridged months added as vintages of their own days (and, in a drill, the real
    vintages from cut_from on removed). Returns the bridged file's path."""
    import csv
    src = os.path.join(_al_dir(), VINT_NAME); tab = list(csv.reader(open(src))); h = tab[0]; body = tab[1:]
    dates = [r[0] for r in body]; cols = list(range(1, len(h)))
    if cut_from is not None:
        cols = [j for j in cols if '_' in h[j] and pd.Timestamp(h[j].split('_')[-1]) < cut_from]
    if not cols: raise RuntimeError('no JOLTS vintage left before the cut')
    last = cols[-1]
    out_h = [h[0]] + [h[j] for j in cols]; out_rows = [[r[0]] + [r[j] for j in cols] for r in body]
    idx = {d: i for i, d in enumerate(dates)}
    carried = {}
    for m, v, day in rows:
        carried[m.strftime('%Y-%m-%d')] = v
        col = 'JTSJOL_' + day.strftime('%Y%m%d'); out_h.append(col)
        for r in out_rows:
            base = r[len(out_h) - 2] if len(r) >= len(out_h) - 1 else ''
            r.append(base)
        for md, mv in carried.items():
            if md not in idx:
                dates.append(md); idx[md] = len(out_rows); out_rows.append([md] + [''] * (len(out_h) - 1))
            out_rows[idx[md]][-1] = ('%.1f' % mv)
    out_rows.sort(key=lambda r: r[0])
    dst = os.path.join('cache', 'JTSJOL_all_vintages_bridged.csv')
    with open(dst, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(out_h); w.writerows(out_rows)
    return dst
def bridge(today, dark_months=None):
    """decide, and write the bridged files. Returns the info dict (active, months, paths)."""
    today = pd.Timestamp(today).normalize()
    J = pd.read_csv(JOLTS, index_col=0, parse_dates=True); J.index = pd.to_datetime(J.index)
    C = pd.read_csv(CLF, index_col=0, parse_dates=True); C.index = pd.to_datetime(C.index)
    R = pd.read_csv(RELCAL, index_col=0, parse_dates=['first_release']); R.index = pd.to_datetime(R.index)
    info = dict(active=False, drill=bool(dark_months), months=[], dark=False, last_print=str(J.index.max().date()), note='')
    if dark_months:
        cut = J.index.sort_values()[-int(dark_months):]
        J = J[J.index < cut.min()]; R = R[R.index < cut.min()]   # the labour force is not cut: a JOLTS-only dark spell
        missing = list(cut)
    else:
        missing = []; m = J.index.max() + pd.DateOffset(months=1)
        while expected_release(m) + pd.Timedelta(days=GRACE_DAYS) < today and len(missing) < MAX_MONTHS + 1:
            missing.append(m); m = m + pd.DateOffset(months=1)
    if not missing:
        info['note'] = 'every scheduled JOLTS month has printed; the bridge is idle'; return info
    if len(missing) > MAX_MONTHS:
        info.update(dark=True, months=[str(x.date()) for x in missing], note='%d JOLTS months missing: more than the bridge carries (%d); the vacancy channel reads dark' % (len(missing), MAX_MONTHS)); return info
    if not os.path.exists(INDEED):
        info.update(note='JOLTS months missing (%s) but no Indeed file in hand; the channel reads stale' % [str(x.date()) for x in missing]); return info
    Im, last_day = indeed_monthly()
    last_m = J.index.max()
    if last_m not in Im.index:
        info.update(note='the Indeed index does not cover the last printed JOLTS month %s; the bridge cannot scale' % last_m.date()); return info
    try: days = json.load(open(DAYS))
    except Exception: days = {}
    rows = []
    for m in missing:
        if m not in Im.index:
            info['note'] = 'the Indeed month %s is not yet complete (index through %s)' % (m.strftime('%Y-%m'), last_day.date()); break
        sub = float(J['first'].loc[last_m]) * float(Im[m]) / float(Im[last_m])
        if dark_months: day = m + pd.offsets.MonthEnd(0) + pd.Timedelta(days=INDEED_LAG_DAYS)
        else:
            key = m.strftime('%Y-%m'); day = pd.Timestamp(days.get(key) or today); days[key] = str(day.date())
        rows.append((m, round(sub, 1), day))
    if not rows: return info
    if not dark_months:
        try: json.dump(days, open(DAYS, 'w'), indent=1)
        except Exception: pass
    JB = J.copy()
    for m, v, day in rows: JB.loc[m, 'first'] = v; JB.loc[m, 'release'] = str(day.date())
    JB = JB.sort_index(); JB.index.name = 'date'
    RB = R.copy()
    for m, v, day in rows: RB.loc[m, 'first_release'] = day; RB.loc[m, 'first_print'] = v
    RB = RB.sort_index()
    CB = C.copy(); carried = []
    for m, v, day in rows:
        if m not in CB.index:
            CB.loc[m, 'first'] = float(C['first'].iloc[-1]); CB.loc[m, 'release'] = str(day.date()); carried.append(m.strftime('%Y-%m'))
    CB = CB.sort_index(); CB.index.name = 'date'
    pj = os.path.join('cache', 'alfred_first_JTSJOL_bridged.csv'); pr = os.path.join('cache', 'relcal_JTSJOL_bridged.csv'); pc = os.path.join('cache', 'alfred_first_CLF16OV_bridged.csv')
    JB.to_csv(pj); RB.to_csv(pr); CB.to_csv(pc)
    # the vintage table the as-of vacancy object reads (s2/asof_objects.py: every vintage as it stood on its day): in a drill the
    # vintages that carried the cut months never appeared; each bridged month adds a vintage on its own day, carrying the substitutes so far
    pv = vintage_table_bridged(rows, cut_from=(R_all_first_release(missing[0]) if dark_months else None))
    info.update(active=True, months=[m.strftime('%Y-%m') for m, v, day in rows], substitutes=[(m.strftime('%Y-%m'), v, str(day.date())) for m, v, day in rows],
                labour_force_carried=carried, indeed_through=str(last_day.date()), paths=dict(jolts=pj, relcal=pr, clf=pc, vintages=pv),
                note='JOLTS bridged by the Indeed postings index for %s (last print %s)' % (', '.join(m.strftime('%Y-%m') for m, v, day in rows), last_m.strftime('%Y-%m')))
    return info

if __name__ == '__main__':
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    print(json.dumps(bridge(datetime.date.today(), dark_months=n), indent=1, default=str))
