#!/usr/bin/env python3
"""1032-A198 (PREREG-1032-a198; Anthony 14 Nov 2026 06:59 PT: 'Go but don't do dc since it's our own construction').
BH STATE CHRONOLOGY V4: each of the 50 states dated exactly as the nation is (register v3.2), on the Philadelphia Fed state coincident index.
Deviation of the log index from an HP trend (lambda 133,107.94); Bry-Boschan windows OECD (5, 5, 15) plus floor windows (2, 2, 6) that overlap no OECD window
and fall 1.0 point or more - the national builder's own functions. Grade = mean of the labour dimension (state unemployment rate) and the output dimension
(the index by quarter through the national output_dimension); the nation's third dimension, industrial production, has no monthly state measure.
Status in the national order: open and under 1.0 = open_unsettled; closed and under 1.0 = fails_DD; grade 2.0 or more = recession; a non-recession window
ending fewer than its min-phase months before a recession window's peak = runup; grade under 0.05 = no_damage; otherwise disturbance.
Periods = recession + disturbance. A202: the class is read from the grade rounded to two places, as the national builder does (two periods at 2.00 were disturbances before). Provisional = open or trough under 24 months old. Line = running grade inside each period, zero between periods (A206, Anthony 14 Nov 2026 17:23 PT: no plateaus; as the national page, whose damage shows only while an episode is open). No AI."""
import os, sys, json, numpy as np, pandas as pd
C = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(C, 'out'); DI = os.path.expanduser('~/Projects/Disturbance Indicator Data')
sys.path.insert(0, os.path.join(DI, '10_chronology_site/code')); import disturbance_chronology as dc, damage_dimensions_live_v376 as dd
import state_payroll_activity_1207 as spa   # 1207: the class rule reads payrolls as well as the State index
CUT = 2.0; NODMG = 0.05
X = pd.read_excel(os.path.join(C, 'data/philly/coincident-revised.xls'), sheet_name='Indexes'); X = X.set_index(pd.to_datetime(X.iloc[:, 0])).iloc[:, 1:].astype(float)
STS = [c for c in X.columns if len(c) == 2 and c != 'US']; assert len(STS) == 50 and 'DC' not in STS
last = X.index[-1]; mdiff = lambda a, b: (a.year - b.year) * 12 + a.month - b.month; rows = []; LINE = {}; URL = {}
# 1167 (24 Nov 2026; Anthony: one grading rule for every contraction, and the State grade on three dimensions as the nation's): production =
# the State production index (jobs in manufacturing, mining and utilities times national output per job, benchmarked to BEA's real output
# of the three industries; collection 1167, PREREG-1167-limit-3, adopted), read by the national production function; every window graded
# on the fall of the State index itself where it fell 1.0 percent or more, otherwise on its fall against trend; grade = damage; 2.00 = recession.
SPI = pd.read_csv(os.path.join(C, 'data/spi/spi_state_monthly_benchmarked_1167.csv'), index_col=0, parse_dates=True)
ACT_MIN = 1.0
def graded(y, p, te, last, w=None, lo=None, hi=None):
    # 1201 (27 Nov 2026): the fall of activity is the LARGEST fall inside the window, from a high in [p - 6 months, te] to the lowest level after it (to te + 6 months). The rule of 1167 took the single highest level of the whole span; where activity ended a long window above where it began, that high lay at the end and the fall read 0 (Arkansas 1980: the index fell 1.17 percent and read 0.0). National register: no class, date or grade changes. States: 9 periods become recessions.
    s = y[(y.index >= p - pd.DateOffset(months=6)) & (y.index <= min(te + pd.DateOffset(months=6), last))]; dd_ = 1 - s / s.where(s.index <= te).cummax().ffill()
    tl = dd_.idxmax(); pl = s[:tl].idxmax(); fl = float(100 * dd_.max())
    if fl >= ACT_MIN: return pl, tl, 'activity', fl, 'index', None
    # 1207 (PREREG-1207, 27 Nov 2026): where the State index fell under ACT_MIN percent, payrolls (three-month average) are read the same way; a fall of spa.PAY_MIN percent or more grades the window on the months payrolls fell
    pf = spa.fall(w, p, te, last, lo, hi) if w is not None else None
    if pf is not None and pf[2] >= spa.PAY_MIN: return pf[0], pf[1], 'activity', fl, 'payrolls', pf[2]
    return p, te, 'trend', fl, None, (pf[2] if pf is not None else None)
def parts(UR, base, Gq, p, m, Pm=None):
    ex = (UR[(UR.index >= p) & (UR.index <= m)] - base).clip(lower=0); L = dd.labour_score(float(ex.max()), float(ex.sum())) if len(ex) else 0.0
    q = dd.production_dimension(Pm, p, m) if Pm is not None and len(Pm[(Pm.index >= p - pd.DateOffset(months=12)) & (Pm.index <= m)]) >= 2 else None
    return L, dd.output_dimension(Gq, p, m), (float(ex.max()) if len(ex) else 0.0), q
def grade3(L, o, q): return (L + o['score'] + q['score']) / 3 if q is not None else (L + o['score']) / 2
for st in STS:
    y = X[st].dropna(); ly = np.log(y); dev = 100 * (ly - dc.hp(ly, dc.LAMBDA)); w5, _ = dc.windows(dev, 5, 5, 15); w2, _ = dc.windows(dev, 2, 2, 6)
    fall = lambda p, t: float(dev[p] - (dev[t] if t is not None else dev[p:].min())); cand = [(p, t, 5) for p, t in w5]
    for p, t in w2:
        if not any(dc.overlaps(p, t, q, (s if s is not None else last)) for q, s, k in cand if k == 5) and fall(p, t) >= dc.DD_MIN: cand.append((p, t, 2))
    # 1201 (27 Nov 2026): one-month windows. A State whose index peaked in March 2020 and troughed in April fell in ONE month, which the
    # floor rule (phase of 2 months) cannot hold: South Dakota had no 2020 period at all (index down 23 percent, unemployment 2.4 to 8.8).
    # A window of one month (1, 1, 3) that overlaps no window already held and falls 1.0 point or more is a candidate like a floor window.
    # Replayed on the data of 27 Nov 2026 it adds three periods and changes none: SD Mar-Apr 2020 (recession), LA Aug-Sep 2021 (disturbance,
    # Hurricane Ida), AK May 1979-Sep 1980 (disturbance, before the record's first month).
    w1, _ = dc.windows(dev, 1, 1, 3)
    for p, t in w1:
        if t is not None and not any(dc.overlaps(p, t, q, (s if s is not None else last)) for q, s, k in cand) and fall(p, t) >= dc.DD_MIN: cand.append((p, t, 1))
    u = pd.read_csv(os.path.join(DI, '03_data/state/fred_state_ur', f'{st}UR.csv')); UR = pd.Series(u.iloc[:, 1].astype(float).values, index=pd.to_datetime(u.iloc[:, 0])).dropna()
    Gq = y.resample('QS').mean(); URL[st] = UR.index[-1].strftime('%Y-%m'); R = []
    W = spa.series(st, os.path.join(DI, '03_data/state/fred_state_payrolls'), os.path.join(C, 'data/fred_nsa')); cs = sorted(cand, key=lambda r: r[0])   # 1207
    for i, (p, t, mp) in enumerate(cs):
        te = t if t is not None else last; lo = (cs[i - 1][1] if cs[i - 1][1] is not None else last) if i else None; hi = cs[i + 1][0] if i + 1 < len(cs) else None
        gp, gt, on, act, ab, pfl = graded(y, p, te, last, W, lo, hi); pre = UR[(UR.index < gp) & (UR.index >= gp - pd.DateOffset(months=12))]; assert len(pre) >= 11, (st, gp)   # 1167: the labour base before the graded months; as the national builder otherwise
        Pm = SPI[st].dropna() if st in SPI else None
        base = float(pre.min()); L, o, rise, q = parts(UR, base, Gq, gp, gt, Pm); g = grade3(L, o, q); f = fall(p, t)
        R.append(dict(st=st, p=p, t=t, te=te, mp=mp, f=f, base=base, L=L, O=o['score'], P=(q['score'] if q is not None else None), pt=o['pt'], ppt=(q['pt'] if q is not None else None), rise=rise, g=g, gp=gp, gt=gt, on=on, act=act, ab=ab, pfl=pfl, Pm=Pm))
    for r in R: r['status'] = 'open_unsettled' if (r['t'] is None and r['f'] < dc.DD_MIN) else ('fails_DD' if r['f'] < dc.DD_MIN else ('recession' if (round(r['g'], 2) >= CUT and r['on'] == 'activity') else ''))   # 1167 class rule: a recession needs the activity index itself to fall ACT_MIN percent or more
    rp = [r['p'] for r in R if r['status'] == 'recession']
    for r in R:
        if r['status']: continue
        r['status'] = 'runup' if any(q > r['te'] and mdiff(q, r['te']) < r['mp'] for q in rp) else ('no_damage' if r['g'] < NODMG else 'disturbance')
    per = [r for r in R if r['status'] in ('recession', 'disturbance')]; ln = {}
    for i, r in enumerate(per):
        v = None; nxt = per[i + 1]['p'] if i + 1 < len(per) else last + pd.DateOffset(months=1)
        for m in pd.date_range(r['p'], nxt - pd.DateOffset(months=1), freq='MS'):
            if m <= r['te']:   # 1167: the running grade over the graded months (0 before they begin, the period's grade after they end)
                if m < r['gp']: v = 0.0
                elif m == r['te']: v = round(r['g'], 2)   # the trough month reads the period's grade (its graded months may run up to 6 months past the trough)
                else: L, o, _, q = parts(UR, r['base'], Gq, r['gp'], min(m, r['gt']), r['Pm']); v = round(grade3(L, o, q), 2)
            ln[m.strftime('%Y-%m')] = v if m <= r['te'] else 0.0
            if m == r['te']: r['line_at_end'] = v
        r['line_high'] = max(ln[m.strftime('%Y-%m')] for m in pd.date_range(r['p'], r['te'], freq='MS'))
    LINE[st] = sorted(ln.items())
    for r in R:
        rows.append({'st': st, 'peak': r['p'].strftime('%Y-%m'), 'trough': r['t'].strftime('%Y-%m') if r['t'] is not None else None, 'open': r['t'] is None, 'months': mdiff(r['te'], r['p']),
                     'dating': 'OECD 5/15' if r['mp'] == 5 else ('floor 2/6' if r['mp'] == 2 else 'one month 1/3'), 'status': r['status'], 'class': r['status'] if r['status'] in ('recession', 'disturbance') else '',
                     'dev_fall_pp': round(r['f'], 2), 'ur_rise_pp': round(r['rise'], 2), 'index_fall_pct': round(r['pt'], 2), 'L': round(r['L'], 2), 'O': round(r['O'], 2),
                     'P': (round(r['P'], 2) if r['P'] is not None else None), 'production_fall_pct': (round(r['ppt'], 2) if r['ppt'] is not None else None),
                     'graded_on': r['on'], 'graded_from': r['gp'].strftime('%Y-%m'), 'graded_to': r['gt'].strftime('%Y-%m'), 'activity_fall_pct': round(r['act'], 2), 'activity_fall_on': r['ab'], 'payroll_fall_pct': (round(r['pfl'], 2) if r['pfl'] is not None else None), 'grade': round(r['g'], 2),
                     'line_at_end': r.get('line_at_end'), 'line_high': r.get('line_high'), 'provisional': bool(r['t'] is None or mdiff(last, r['t']) < dc.PROVISIONAL_MONTHS)})
T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, 'BH-STATE-CHRONOLOGY-V4-1032.csv'), index=False); P = T[T['class'] != ''].copy()
json.dump({'through': last.strftime('%Y-%m'), 'unemployment_through': URL, 'states': {st: {'line': LINE[st]} for st in STS}}, open(os.path.join(OUT, 'damage_line_v4_a198_1032.json'), 'w'))
N = pd.read_csv(os.path.join(DI, '10_chronology_site/out_v3_2_damage_cut/chronology.csv')); idx = pd.period_range('1979-07', last.strftime('%Y-%m'), freq='M'); rec = pd.Series(0.0, index=idx); anyb = pd.Series(0.0, index=idx)
for st, g in P.groupby('st'):
    r1 = pd.Series(0, index=idx); r2 = pd.Series(0, index=idx)
    for r in g.itertuples():
        m = (idx > pd.Period(r.peak, 'M')) & (idx <= (pd.Period(r.trough, 'M') if isinstance(r.trough, str) else idx[-1])); r2[m] = 1
        if r.status == 'recession': r1[m] = 1
    rec += r1; anyb += r2
rec /= len(STS); anyb /= len(STS); nr = pd.Series(0, index=idx); nd = pd.Series(0, index=idx); eps = []
for r in N.itertuples():
    cls = 'recession' if r.status == 'recession' else ('disturbance' if r.status.startswith('disturbance') else None)
    if cls is None: continue
    p = pd.Period(r.peak, 'M'); t = pd.Period(r.trough, 'M') if isinstance(r.trough, str) else idx[-1]
    if t < idx[0]: continue
    m = (idx > p) & (idx <= t); (nr if cls == 'recession' else nd)[m] = 1
    eps.append({'window': f"{r.peak} to {r.trough if isinstance(r.trough, str) else 'open'}", 'class': cls, 'national_grade': float(r.grade), 'peak_share_of_states_in_recession': round(float(rec[m].max()), 2), 'peak_share_of_states_in_a_period': round(float(anyb[m].max()), 2)})
quiet = (nr == 0) & (nd == 0); E = pd.DataFrame(eps); K = P[~P.open]; A7 = json.load(open(os.path.join(OUT, 'trial_state_growth_cycles_a197_1032.json')))
sh = {'national_recession_months': round(float(anyb[nr == 1].mean()), 3), 'national_disturbance_months': round(float(anyb[nd == 1].mean()), 3), 'quiet_months': round(float(anyb[quiet].mean()), 3)}
c1 = round(float(rec.corr(nr)), 3); d3 = float((K.line_at_end - K.grade).abs().max())
out = {'states': len(STS), 'windows': int(len(T)), 'by_status': {k: int(v) for k, v in T.status.value_counts().items()}, 'periods': int(len(P)), 'periods_per_state_median': float(P.groupby('st').size().median()),
       'periods_per_state_min_max': [int(P.groupby('st').size().min()), int(P.groupby('st').size().max())], 'open_periods': {k: int(v) for k, v in P[P.open].status.value_counts().items()},
       'open_recessions': sorted(P[P.open & (P.status == 'recession')].st), 'open_disturbances': sorted(P[P.open & (P.status == 'disturbance')].st), 'provisional_periods': int(P.provisional.sum()),
       'correlation_share_of_states_in_recession_with_national_recession_months': {'v4': c1, 'trial_A197': A7['correlation_share_of_states_in_recession_with_national_recession_months']},
       'correlation_share_of_states_in_a_period_with_nation_in_a_period': round(float(anyb.corr(((nr + nd) > 0).astype(int))), 3),
       'rank_correlation_national_grade_with_peak_share_in_recession_by_episode': round(float(E.national_grade.corr(E.peak_share_of_states_in_recession, method='spearman')), 3),
       'mean_share_of_states_in_recession': {'national_recession_months': round(float(rec[nr == 1].mean()), 3), 'national_disturbance_months': round(float(rec[nd == 1].mean()), 3), 'quiet_months': round(float(rec[quiet].mean()), 3)},
       'mean_share_of_states_in_a_period': sh, 'line_high_above_cut_in_a_disturbance': int(((P.status == 'disturbance') & (P.line_high >= CUT)).sum()), 'line_not_at_its_high_at_the_end': int((P.line_high > P.line_at_end + 0.005).sum()),
       'predictions': {'P1_corr_0.70_or_more': bool(c1 >= 0.70), 'P2_disturbance_minus_quiet_0.20_or_more': bool(sh['national_disturbance_months'] - sh['quiet_months'] >= 0.20), 'P3_line_equals_grade_at_trough': bool(d3 <= 0.01), 'P3_largest_difference': round(d3, 4), 'P4_no_period_under_0.05': bool((P.grade >= NODMG).all())},
       'episodes': eps}
json.dump(out, open(os.path.join(OUT, 'state_chronology_v4_a198_1032.json'), 'w'), indent=1); print(json.dumps(out, indent=1))
