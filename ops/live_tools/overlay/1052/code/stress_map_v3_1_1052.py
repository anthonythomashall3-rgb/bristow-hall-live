#!/usr/bin/env python3
"""1052 NATIONAL STRESS MAP V3.1 STATE LAYER (PREREG-1052 v3, Amendment 1 of 15 Nov 05:15 PT: C2 WITHDRAWN, the pre-1979 layer is v1's; P5 scored on colour).
Generated from stress_map_v3_1052.py by code/make_v3_1_from_v3_1052.py. Below, the v3 docstring as it stood (its C2 paragraph no longer applies):
V3 STATE LAYER = the v1 script with exactly the two State-layer changes of doc/PREREG-1052-national-stress-map-v3-four-design-changes-for-coh-2026-11-15.md:
 C1: inside a State chronology recession period every month is at least red (colour value capped at -3; deep red at grade 4.0 or more); disturbances at least orange (as v1).
 C2: before 1979-07 the State index is a two-input coincident index built like the Philadelphia Fed's (Stock-Watson single dynamic factor: AR(2) factor, AR(2) idiosyncratic
     errors) from payroll job growth and the change in the insured unemployment rate (sign reversed), one model per State, parameters estimated on 1947-1978 only and then
     run (smoothed) over every month held; the factor's growth is scaled to the mean and SD of payroll growth over 1947-1978 and cumulated to a level. Same windows and grade
     functions as v4 (run_v4 unchanged); labour input unchanged (k x insured rate).
 Everything else, the v1 tests included, is the v1 code unchanged. Outputs: out/stress_map_v3_state_month.csv, out/STRESS-MAP-V3-STATE-TESTS-1052.txt,
 out/stress_map_v3_tests_state_1052.json, web/stress-map/state_layer_v3.html (read by stress_map_v2_1052.py --v3).
--- v1 docstring follows ---
1052 NATIONAL STRESS MAP V1 (doc/PREREG-1052-national-stress-map-v1-state-damage-and-growth-by--2026-11-15.md, with Amendment 1).
One colour value per State-month, 1947-01 to the latest month of the State chronology v4.
 - 1979-07 on: the State chronology v4 exactly (1032 out/BH-STATE-CHRONOLOGY-V4-1032.csv periods, out/damage_line_v4_a198_1032.json line);
   the deviation for the green side is the v4 deviation (log Philadelphia Fed coincident index less its HP trend), recomputed with the
   national functions exactly as the v4 script does.
 - before 1979-07: layer L0 = the v4 code path (copied verbatim below as run_v4, checked to reproduce the v4 files) with its two inputs swapped:
   index = BLS State nonfarm payrolls NSA (954 data/state_nan), seasonally adjusted here (below); labour = k x the State insured unemployment
   rate (DOL continued weeks claimed / 4.33 / payroll jobs x 100, FH_state_claims_nsa_log, natural logs exponentiated; payrolls are in thousands,
   so jobs = payroll x 1000), seasonally adjusted the same way. k fitted once on 1979-07..1996-12 (median over v4 recession periods wholly inside
   that span of the ratio: v4 unemployment-rate rise / insured-rate rise, both measured by the v4 rule: excess over the lowest value of the
   12 months before the peak, highest excess from peak to trough).
 Seasonal adjustment (stated, fixed before running): log series x; trend = centred 2x12 moving average (the 954 smoother); ratio r = x - trend;
 seasonal factor for a calendar month = centred 7-year moving mean of r for that calendar month (at least 3 years; carried to the ends);
 factors re-centred so each 12 consecutive months sum to zero (their own 2x12 average removed); adjusted x = x - factor.
 Colour (Amendment 1, fixed cut points): colour value s on one axis, yellow = 0.
   inside a period (recession or disturbance; months peak..trough, the extent of the v4 line): grade g = the running grade (the line):
     g < 0.05 -> s = -1 (orange: period open, no damage yet); 0.05..1.0 -> -1..-2; 1.0..2.0 -> -2..-3 (2.0 = full red); 2.0..4.0 -> -3..-4 (deep red); >4 -> -4.
   no period open: s = deviation / the State's quiet-record SD (SD of the deviation over the layer's months outside every period), clipped to [-1, +2]:
     -1 orange, 0 yellow, +1 light green, +2 deep green.
   Reporting bands: red = in a period with g >= 2.0 (deep red: g >= 4.0); orange = in a period with g < 2.0, or no period and s <= -0.5;
   yellow -0.5 < s < 0.5; light green 0.5 <= s < 1.5; green s >= 1.5; grey = no payroll data yet (L0 only).
 No AI: every number below is computed here."""
import os, sys, json, math, numpy as np, pandas as pd
C = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(C, 'out'); WEB = os.path.join(C, 'web', 'stress-map')
ROOT = os.path.dirname(C); DI = os.path.expanduser('~/Projects/Disturbance Indicator Data')
V4D = os.path.join(ROOT, '1032_state_recession_indicator_all_states_dc_2026-11-09')
sys.path.insert(0, os.path.join(DI, '10_chronology_site/code')); import disturbance_chronology as dc, damage_dimensions_live_v376 as dd
CUT = 2.0; NODMG = 0.05; SEAM = pd.Timestamp('1979-07-01'); START = pd.Timestamp('1947-01-01')
mdiff = lambda a, b: (a.year - b.year) * 12 + a.month - b.month
ym = lambda t: t.strftime('%Y-%m')

# ---------------- the v4 code path (state_chronology_v4_growth_cycle_a198_1032.py lines 17-46, verbatim except: inputs are arguments, `last` is the series' last month,
# and a short pre-peak base (fewer than 11 months, only where the insured rate has not yet begun) is allowed and flagged instead of asserted) -------------
def run_v4(st, y, UR, last, allow_short=False, Pm=None, one_month=False):
    # 1167 (24 Nov 2026; Anthony: one grading rule; the State grade on three dimensions): each window is graded on the fall of its own
    # index (the highest level from 6 months before the peak to the trough, to the lowest level after it, up to 6 months past the trough)
    # where it fell 1.0 percent or more, otherwise on its fall against trend; Pm = the place's production index (the State production
    # index of collection 1167; None for a county), read by the national production function; grade = the mean of the dimensions held.
    ly = np.log(y); dev = 100 * (ly - dc.hp(ly, dc.LAMBDA)); w5, _ = dc.windows(dev, 5, 5, 15); w2, _ = dc.windows(dev, 2, 2, 6)
    fall = lambda p, t: float(dev[p] - (dev[t] if t is not None else dev[p:].min())); cand = [(p, t, 5) for p, t in w5]
    for p, t in w2:
        if not any(dc.overlaps(p, t, q, (s if s is not None else last)) for q, s, k in cand if k == 5) and fall(p, t) >= dc.DD_MIN: cand.append((p, t, 2))
    # 1201 (27 Nov 2026): one-month windows, as in the State chronology builder (overlay/1032), so the map's State layer stays that file. A State whose index peaked in March 2020 and troughed in April fell in ONE month, which the
    # floor rule (phase of 2 months) cannot hold: South Dakota had no 2020 period at all (index down 23 percent, unemployment 2.4 to 8.8).
    # A window of one month (1, 1, 3) that overlaps no window already held and falls 1.0 point or more is a candidate like a floor window.
    # Replayed on the data of 27 Nov 2026 it adds three periods and changes none: SD Mar-Apr 2020 (recession), LA Aug-Sep 2021 (disturbance,
    # Hurricane Ida), AK May 1979-Sep 1980 (disturbance, before the record's first month).
    w1 = dc.windows(dev, 1, 1, 3)[0] if one_month else []   # only the State chronology layer (1979-07 on); the older layer is left as it was
    for p, t in w1:
        if t is not None and not any(dc.overlaps(p, t, q, (s if s is not None else last)) for q, s, k in cand) and fall(p, t) >= dc.DD_MIN: cand.append((p, t, 1))
    Gq = y.resample('QS').mean(); R = []
    def graded(p, te):
        a = y[(y.index >= p - pd.DateOffset(months=6)) & (y.index <= te)]; pl = a.idxmax()
        b = y[(y.index >= pl) & (y.index <= min(te + pd.DateOffset(months=6), last))]; tl = b.idxmin(); fl = float(100 * (1 - b.min() / a.max()))
        return (pl, tl, 'activity', fl) if fl >= 1.0 else (p, te, 'trend', fl)
    def parts(UR, base, Gq, p, m):
        ex = (UR[(UR.index >= p) & (UR.index <= m)] - base).clip(lower=0); L = dd.labour_score(float(ex.max()), float(ex.sum())) if len(ex) else 0.0
        q = dd.production_dimension(Pm, p, m) if Pm is not None and len(Pm[(Pm.index >= p - pd.DateOffset(months=12)) & (Pm.index <= m)]) >= 2 else None
        return L, dd.output_dimension(Gq, p, m), (float(ex.max()) if len(ex) else 0.0), q
    g3 = lambda L, o, q: (L + o['score'] + q['score']) / 3 if q is not None else (L + o['score']) / 2
    for p, t, mp in sorted(cand, key=lambda r: r[0]):
        te = t if t is not None else last; gp, gt, on, act = graded(p, te)
        pre = UR[(UR.index < gp) & (UR.index >= gp - pd.DateOffset(months=12))]; short = len(pre) < 11
        if short:
            assert allow_short, (st, gp)
            if len(pre) == 0: pre = UR[UR.index <= UR.index[0] + pd.DateOffset(months=11)]   # peak before the insured rate begins: its first 12 months
        base = float(pre.min()); L, o, rise, q = parts(UR, base, Gq, gp, gt); g = g3(L, o, q); f = fall(p, t)
        R.append(dict(st=st, p=p, t=t, te=te, mp=mp, f=f, base=base, L=L, O=o['score'], pt=o['pt'], rise=rise, g=g, short_base=short, gp=gp, gt=gt, on=on))
    for r in R: r['status'] = 'open_unsettled' if (r['t'] is None and r['f'] < dc.DD_MIN) else ('fails_DD' if r['f'] < dc.DD_MIN else ('recession' if (round(r['g'], 2) >= CUT and r['on'] == 'activity') else ''))   # 1167 class rule: a recession needs the activity index itself to fall ACT_MIN percent or more
    rp = [r['p'] for r in R if r['status'] == 'recession']
    for r in R:
        if r['status']: continue
        r['status'] = 'runup' if any(q > r['te'] and mdiff(q, r['te']) < r['mp'] for q in rp) else ('no_damage' if r['g'] < NODMG else 'disturbance')
    per = [r for r in R if r['status'] in ('recession', 'disturbance')]; ln = {}
    for i, r in enumerate(per):
        v = None; nxt = per[i + 1]['p'] if i + 1 < len(per) else last + pd.DateOffset(months=1)
        for m in pd.date_range(r['p'], nxt - pd.DateOffset(months=1), freq='MS'):
            if m <= r['te']:
                if m < r['gp']: v = 0.0
                elif m == r['te']: v = round(r['g'], 2)
                else: L, o, _, q = parts(UR, r['base'], Gq, r['gp'], min(m, r['gt'])); v = round(g3(L, o, q), 2)
            ln[m.strftime('%Y-%m')] = v if m <= r['te'] else 0.0
            if m == r['te']: r['line_at_end'] = v
        r['line_high'] = max(ln[m.strftime('%Y-%m')] for m in pd.date_range(r['p'], r['te'], freq='MS'))
    for r in R: r['provisional'] = bool(r['t'] is None or mdiff(last, r['t']) < dc.PROVISIONAL_MONTHS)
    return R, ln, dev

def sa_log(x):
    x = x.astype(float); T = x.rolling(12, center=True).mean().rolling(2).mean().shift(-1); r = x - T
    S = pd.Series(np.nan, index=x.index)
    for mo in range(1, 13):
        k = x.index.month == mo; s = r[k].rolling(7, center=True, min_periods=3).mean(); S[k] = s.ffill().bfill().values
    S = S - S.rolling(12, center=True).mean().rolling(2).mean().shift(-1).ffill().bfill()
    return x - S

# ---------------- v4 (1979 on): the files as published, and a re-run of the code path on its own inputs to prove run_v4 is the v4 code -------------
_S1167 = pd.read_csv(os.path.join(V4D, 'data/spi/spi_state_monthly_benchmarked_1167.csv'), index_col=0, parse_dates=True); SPI1167 = {c: _S1167[c].dropna() for c in _S1167.columns}   # 1167: the State production index
V4T = pd.read_csv(os.path.join(V4D, 'out/BH-STATE-CHRONOLOGY-V4-1032.csv')); V4J = json.load(open(os.path.join(V4D, 'out/damage_line_v4_a198_1032.json')))
X = pd.read_excel(os.path.join(V4D, 'data/philly/coincident-revised.xls'), sheet_name='Indexes'); X = X.set_index(pd.to_datetime(X.iloc[:, 0])).iloc[:, 1:].astype(float)
STS = [c for c in X.columns if len(c) == 2 and c != 'US']; assert len(STS) == 50 and 'DC' not in STS
LAST = pd.Timestamp(V4J['through'] + '-01'); assert X.index[-1] == LAST
V4UR = {}   # 19 Nov 2026 (1150): the labour input of each State-month is kept for the page's factors panel
V4 = {}; repro = {'states_line_identical': 0, 'states_windows_identical': 0, 'differences': []}
for st in STS:
    y = X[st].dropna(); u = pd.read_csv(os.path.join(DI, '03_data/state/fred_state_ur', f'{st}UR.csv')); UR = pd.Series(u.iloc[:, 1].astype(float).values, index=pd.to_datetime(u.iloc[:, 0])).dropna()
    R, ln, dev = run_v4(st, y, UR, LAST, Pm=SPI1167.get(st), one_month=True); V4[st] = dict(R=R, ln=ln, dev=dev); V4UR[st] = UR   # 1167: production dimension
    pub = dict(V4J['states'][st]['line']); mine = ln
    if pub == mine: repro['states_line_identical'] += 1
    else: repro['differences'].append((st, 'line', sum(1 for k in set(pub) | set(mine) if pub.get(k) != mine.get(k))))
    a = V4T[V4T.st == st][['peak', 'trough', 'status', 'grade']].fillna('').values.tolist()
    b = [[ym(r['p']), ym(r['t']) if r['t'] is not None else '', r['status'], round(r['g'], 2)] for r in R]
    if a == b: repro['states_windows_identical'] += 1
    else: repro['differences'].append((st, 'windows', len(a), len(b)))
# v4 periods as published (these, not the re-run, colour the map)
def periods_from_table(T):
    P = {}
    for r in T[T.status.isin(['recession', 'disturbance'])].itertuples():
        P.setdefault(r.st, []).append(dict(p=pd.Timestamp(r.peak + '-01'), t=(pd.Timestamp(r.trough + '-01') if isinstance(r.trough, str) else None), status=r.status, grade=float(r.grade), provisional=bool(r.provisional)))
    return P
def damage_start(P, ln):
    """19 Nov 2026 (Anthony: the map starts each period where the State page does): a period's first month is the first month from its peak
    to its trough whose line is 0.05 or more (the State page's Start column: the month after max(peak, first damage month - 1)); the month after
    the peak when no month has damage yet. The peak as dated is kept in p0 (the base for every measurement)."""
    for q in P:
        q['p0'] = q['p']; te = q['t'] if q['t'] is not None else q['p'] + pd.DateOffset(years=200)
        on = sorted(pd.Timestamp(k + '-01') for k, v in ln.items() if (v or 0) >= NODMG and q['p'] <= pd.Timestamp(k + '-01') <= te)
        q['p'] = max(q['p'], on[0] - pd.DateOffset(months=1)) + pd.DateOffset(months=1) if on else q['p'] + pd.DateOffset(months=1)
        if q['t'] is not None and q['p'] > q['t']: q['p'] = q['t']
    return P
V4P = periods_from_table(V4T)
for _st in V4P: damage_start(V4P[_st], dict(V4J['states'][_st]['line']))

# ---------------- L0 inputs -------------
sys.path.insert(0, os.path.join(C, 'code')); import payroll_prints_1161   # 1161
NAN = os.path.join(ROOT, '954_state_chronology_1939_bry_boschan_2026-10-31/data/state_nan')
FH = pd.read_csv(os.path.join(ROOT, '24_bristow_rule_lab/workspace/lab/fh/FH_state_claims_nsa_log.csv'), index_col=0, parse_dates=True)
CL_LAST = FH.index[-1]
PAY = {}; IUR = {}; PAYSTART = {}
for st in STS:
    s = pd.read_csv(os.path.join(NAN, f'{st}NAN.csv'), index_col=0, parse_dates=True).iloc[:, 0]; s = pd.to_numeric(s, errors='coerce').dropna()
    s = payroll_prints_1161.extend(st, s)   # 1161: months printed before the State's BLS series begins (Minnesota 1947-1949)
    assert (s.index == pd.date_range(s.index[0], s.index[-1], freq='MS')).all(), st
    PAYSTART[st] = s.index[0]; s = s[s.index <= CL_LAST]                       # L0 runs to the claims' last month (the labour input ends there)
    PAY[st] = np.exp(sa_log(np.log(s)))
    cw = np.exp(FH[f'{st} | continued weeks claimed']).dropna()                # natural logs of the monthly count of continued weeks claimed
    j = cw.index.intersection(s.index); iu = cw[j] / 4.33 / (s[j] * 1000.0) * 100.0   # payrolls are in thousands of jobs
    IUR[st] = np.exp(sa_log(np.log(iu)))
# C2 (two-input pre-1979 index) WITHDRAWN by Amendment 1: L0 runs on the payrolls index, as v1.
# ---------------- k: fitted once on 1979-07..1996-12 -------------
KR = []
for st in STS:
    for r in V4T[(V4T.st == st) & (V4T.status == 'recession')].itertuples():
        if not isinstance(r.trough, str): continue
        p = pd.Timestamp(r.peak + '-01'); t = pd.Timestamp(r.trough + '-01')
        if p < SEAM or t > pd.Timestamp('1996-12-01'): continue
        I = IUR[st]; pre = I[(I.index < p) & (I.index >= p - pd.DateOffset(months=12))]; ex = (I[(I.index >= p) & (I.index <= t)] - float(pre.min())).clip(lower=0)
        ir = float(ex.max())
        if ir > 0: KR.append(dict(st=st, peak=r.peak, trough=r.trough, ur_rise=float(r.ur_rise_pp), iur_rise=round(ir, 4), ratio=float(r.ur_rise_pp) / ir))
K = float(np.median([x['ratio'] for x in KR])); print('k =', round(K, 4), 'from', len(KR), 'v4 recession periods')
# ---------------- L0 run -------------
L0 = {}; short_n = 0
for st in STS:
    R, ln, dev = run_v4(st, PAY[st], K * IUR[st], PAY[st].index[-1], allow_short=True, Pm=SPI1167.get(st)); L0[st] = dict(R=R, ln=ln, dev=dev)   # v3.1: v1's L0 (C2 withdrawn); 1167: production where the index runs (1975 on)
    short_n += sum(1 for r in R if r['short_base'] and r['status'] in ('recession', 'disturbance') and r['te'] >= START)
L0P = {st: [dict(p=r['p'], t=r['t'], te=r['te'], status=r['status'], grade=round(r['g'], 2), provisional=r['provisional'], line_at_end=r.get('line_at_end'), line_high=r.get('line_high'))
            for r in L0[st]['R'] if r['status'] in ('recession', 'disturbance')] for st in STS}
for _st in STS: damage_start(L0P[_st], L0[_st]['ln'])

# ---------------- the map: one row per State-month -------------
MONTHS = pd.date_range(START, LAST, freq='MS')
def colour_value(inp, g, dsd):
    if inp:
        if g < NODMG: return -1.0
        if g <= 1.0: return -1.0 - (g - NODMG) / (1.0 - NODMG)
        if g <= 2.0: return -2.0 - (g - 1.0)
        return max(-4.0, -3.0 - (g - 2.0) / 2.0)
    return float(min(2.0, max(-1.0, dsd)))
def band(status, g, s):
    if status == 'no_data': return 'grey'
    if status == 'recession': return 'deep red' if g >= 4.0 else 'red'   # C1
    if status == 'disturbance': return 'deep red' if g >= 4.0 else ('red' if g >= CUT else 'orange')
    return 'orange' if s <= -0.5 else ('yellow' if s < 0.5 else ('light green' if s < 1.5 else 'green'))
ANCH = [(-4, (103, 0, 13)), (-3, (204, 24, 30)), (-2, (241, 105, 19)), (-1, (253, 174, 97)), (0, (255, 230, 90)), (1, (166, 217, 106)), (2, (26, 120, 60))]
def hexof(s):
    s = round(s / 0.05) * 0.05
    for (a, ca), (b, cb) in zip(ANCH, ANCH[1:]):
        if a - 1e-9 <= s <= b + 1e-9:
            w = (s - a) / (b - a); return '#%02x%02x%02x' % tuple(int(round(x + (y - x) * w)) for x, y in zip(ca, cb))
PAL = [hexof(-4 + 0.05 * i) for i in range(121)]
def in_period(P, m, last):
    for q in P:
        te = q['t'] if q['t'] is not None else last
        if q['p'] <= m <= te: return q
    return None
QSD = {}
for st in STS:
    for lay, D, P, last in (('L0', L0[st], L0P[st], PAY[st].index[-1]), ('v4', V4[st], V4P.get(st, []), LAST)):
        dv = D['dev']; q = pd.Series([in_period(P, m, last) is None for m in dv.index], index=dv.index); QSD[(st, lay)] = float(dv[q].std())
rows = []
for st in STS:
    for m in MONTHS:
        k = ym(m)
        if m < SEAM:
            lay = 'L0'
            if m < PAYSTART[st]:
                rows.append(dict(st=st, month=k, layer='L0', period_status='no_data', period_peak='', period_trough='', provisional='', grade='', deviation_pp='', deviation_sd='', colour_value='', band='grey', colour_hex='#d5d9de')); continue
            P = L0P[st]; ln = L0[st]['ln']; dv = L0[st]['dev']; last = PAY[st].index[-1]; _li = K * IUR[st]
        else:
            lay = 'v4'; P = V4P.get(st, []); ln = dict(V4J['states'][st]['line']); dv = V4[st]['dev']; last = LAST; _li = V4UR[st]
        q = in_period(P, m, last); g = float(ln.get(k, 0.0)) if q is not None else 0.0
        d = float(dv[m]); dsd = d / QSD[(st, lay)]; s = colour_value(q is not None, g, dsd); stt = q['status'] if q is not None else 'none'
        if stt == 'recession': s = min(s, -3.0)   # C1: every recession month at least red
        rows.append(dict(st=st, month=k, layer=lay, period_status=stt, period_peak=ym(q['p']) if q else '', period_trough=(ym(q['t']) if q and q['t'] is not None else ('open' if q else '')),
                         provisional=(bool(q['provisional']) if q else ''), grade=round(g, 2), deviation_pp=round(d, 3), deviation_sd=round(dsd, 3), colour_value=round(s, 3), band=band(stt, g, s), colour_hex=hexof(s),
                         labour_input=(round(float(_li[m]), 2) if m in _li.index and np.isfinite(_li[m]) else '')))
M = pd.DataFrame(rows); os.makedirs(OUT, exist_ok=True); M.to_csv(os.path.join(OUT, 'stress_map_v3_1_state_month.csv'), index=False)
M['m'] = pd.to_datetime(M.month + '-01'); M['inp'] = M.period_status.isin(['recession', 'disturbance']); M['rec'] = M.period_status == 'recession'; M['has'] = M.period_status != 'no_data'
M['g'] = pd.to_numeric(M.grade, errors='coerce')
BY = M.groupby('m')
SH = pd.DataFrame({b: BY.apply(lambda x, b=b: float((x.band == b).sum()) / float(x.has.sum())) for b in ['deep red', 'red', 'orange', 'yellow', 'light green', 'green']}); SH['grey_states'] = BY.apply(lambda x: int((~x.has).sum()))
SH['red_or_deeper'] = SH['red'] + SH['deep red']

# ---------------- tests P1-P7 and the national page's two checks -------------
NR = pd.read_csv(os.path.join(DI, '10_chronology_site/out_v3_2_damage_cut/chronology.csv'))
NREC = [(pd.Timestamp(r.peak + '-01'), pd.Timestamp(r.trough + '-01') if isinstance(r.trough, str) else None) for r in NR.itertuples() if r.status == 'recession']
NDIS = [(pd.Timestamp(r.peak + '-01'), pd.Timestamp(r.trough + '-01') if isinstance(r.trough, str) else None) for r in NR.itertuples() if str(r.status).startswith('disturbance')]
T = []; RES = {}
def rep(name, ok, txt): RES[name] = bool(ok); T.append(f"{name}: {'PASS' if ok else 'FAIL'}  {txt}")
# P1
ov = pd.date_range('1979-07-01', '1996-12-01', freq='MS'); al = n = 0
for st in STS:
    for m in ov:
        a = in_period(L0P[st], m, PAY[st].index[-1]) is not None; b = in_period(V4P.get(st, []), m, LAST) is not None; al += a == b; n += 1
p1 = al / n
fl = sum(in_period(L0P[st], m, PAY[st].index[-1]) is not None for st in STS for m in ov) / n; fv = sum(in_period(V4P.get(st, []), m, LAST) is not None for st in STS for m in ov) / n
rep('P1', p1 >= 0.80, f"share of State-months 1979-07..1996-12 classified alike (in a period or not) by L0 and v4 = {p1:.3f} ({al} of {n}); bar 0.80. "
    f"(Share of these State-months in a period: L0 {fl:.3f}, v4 {fv:.3f}; agreement expected by chance from those shares {fl * fv + (1 - fl) * (1 - fv):.3f})")
# P2
L0IN = {st: pd.Series([in_period(L0P[st], m, PAY[st].index[-1]) for m in MONTHS], index=MONTHS) for st in STS}
w = pd.date_range('1948-01-01', '1978-12-01', freq='MS')
has = pd.Series([sum(1 for st in STS if m >= PAYSTART[st]) for m in w], index=w)
shr = pd.Series([sum(1 for st in STS if m >= PAYSTART[st] and L0IN[st][m] is not None and L0IN[st][m]['status'] == 'recession') for m in w], index=w) / has
nr = pd.Series([int(any(p < m <= (t if t is not None else LAST) for p, t in NREC)) for m in w], index=w)
p2 = float(shr.corr(nr)); rep('P2', p2 >= 0.70, f"correlation 1948-01..1978-12 of the share of States in an L0 recession period with national recession months (register v3.2, months after peak through trough) = {p2:.3f}; bar 0.70")
# P3
txt = []; ok3 = True
for p, t in NREC:
    if p.year < 1948 or t is None or t > pd.Timestamp('1975-12-01'): continue
    hs = [st for st in STS if t >= PAYSTART[st]]; s = sum(1 for st in hs if L0IN[st][t] is not None) / len(hs); s50 = sum(1 for st in hs if L0IN[st][t] is not None) / 50
    ok3 &= s >= 0.40; txt.append(f"{ym(p)}..{ym(t)}: {s:.2f} of {len(hs)} States with data in a period at the trough month ({s50:.2f} of all 50)")
rep('P3', ok3, '; '.join(txt) + '; bar 0.40 each')
# P4
V = M[M.m >= SEAM]
LINES = {st: dict(V4J['states'][st]['line']) for st in STS}
diff = (V.g - pd.Series([LINES[a].get(b, 0.0) for a, b in zip(V.st, V.month)], index=V.index)).abs()[V.inp]   # 19 Nov 2026: scored on the months inside a period (a period starts where the State page starts it)
out4 = float(V.g[~V.inp].abs().max())
pin = V.inp.values == np.array([in_period(V4P.get(a, []), m, LAST) is not None for a, m in zip(V.st, V.m)])
# a State-month in no v4 period carries the line's 0.0 between periods; the published line is also 0.0 there or absent (before the first peak)
rep('P4', float(diff.max()) == 0.0 and out4 == 0.0 and pin.all(), f"1979-07..{ym(LAST)}: {len(V)} State-months; largest |map grade - v4 line| inside a period = {float(diff.max()):.4f}; largest map grade outside every period = {out4:.4f}; period membership equal in {int(pin.sum())} of {len(V)}; "
    f"the v4 code path re-run inside this script reproduces the published v4 line in {repro['states_line_identical']}/50 States and the window table in {repro['states_windows_identical']}/50")
# P5 (v3.1, as PREREG-1052 v3 states it): the COLOUR of every month of a v4 recession period, 1979-07 on, is red or deeper. C1 makes this hold by construction (stated, not an empirical result).
R5 = []; MB = M.set_index(['st', 'month']).band
for st in STS:
    for q in V4P.get(st, []):
        if q['status'] != 'recession': continue
        te = q['t'] if q['t'] is not None else LAST
        for m in pd.date_range(max(q['p'], SEAM), te, freq='MS'): R5.append((st, m, LINES[st].get(ym(m), 0.0), MB[(st, ym(m))]))
r5 = sum(1 for x in R5 if x[3] in ('red', 'deep red')) / len(R5); low = sum(1 for x in R5 if x[2] < CUT)
rep('P5', r5 == 1.0, f"months of v4 recession periods 1979-07 on whose colour is red or deeper: {r5:.3f} ({sum(1 for x in R5 if x[3] in ('red', 'deep red'))} of {len(R5)}); "
    f"scored on colour as PREREG-1052 v3 states P5 (Amendment 1); C1 makes it hold by construction, so this is stated, not claimed as an empirical result. "
    f"{low} of these months have a running grade still under 2.0 (red by C1, not by grade)")

# P6: a listed State passes an episode if at least one of its months in the episode's years is red or orange (deep red counts); '1974-75 broadly' passes if in
# some month of 1974-1975 at least half of the States with data are red or orange at once. Windows are the calendar years the prereg names (set before running).
EP = [('1957-58 industrial', '1957-01', '1958-12', 'MI OH PA IN'), ('1960-61 industrial', '1960-01', '1961-12', 'MI OH PA IN'), ('1969-70 aerospace', '1969-01', '1970-12', 'WA CA'),
      ('1980-82', '1980-01', '1982-12', 'MI OH IN IL'), ('farm crisis 1984-86', '1984-01', '1986-12', 'IA NE KS'), ('oil bust 1986-87', '1986-01', '1987-12', 'TX OK LA WY AK'),
      ('New England 1990-91', '1990-01', '1991-12', 'MA CT RI NH'), ('Hawaii 1990s', '1990-01', '1999-12', 'HI'), ('Louisiana 2005', '2005-01', '2005-12', 'LA'),
      ('Michigan 2001-09', '2001-01', '2009-12', 'MI'), ('North Dakota 2015-16', '2015-01', '2016-12', 'ND')]
MI_ = M.set_index(['st', 'm']); ok6 = True; t6 = []
for nm, a, b, sts in EP:
    sub = M[(M.m >= a + '-01') & (M.m <= b + '-01')]; parts_ = []
    for st in sts.split():
        x = sub[sub.st == st]; ro = x.band.isin(['red', 'deep red', 'orange']); good = bool(ro.any()); ok6 &= good
        parts_.append(f"{st} {'yes' if good else 'NO'} (red/orange {int(ro.sum())}/{len(x)} months, red {int(x.band.isin(['red', 'deep red']).sum())}, highest grade {x.g.max():.2f}, layer {'/'.join(sorted(set(x.layer)))})")
    t6.append(f"  {nm} [{a}..{b}]: " + '; '.join(parts_))
x = SH[(SH.index >= '1974-01-01') & (SH.index <= '1975-12-01')]; ro = (x['red_or_deeper'] + x['orange']); g74 = float(ro.max()) >= 0.5; ok6 &= g74
t6.append(f"  1974-75 broadly: highest share of States red or orange at once = {float(ro.max()):.2f} in {ym(ro.idxmax())} (bar 0.50) -> {'yes' if g74 else 'NO'}")
rep('P6', ok6, 'known State episodes\n' + '\n'.join(t6))
# P7: for each national recession 1948-2020 (register v3.2 recession windows, peak..trough), the month in which the share of States red or deeper (running grade >= 2.0)
# is highest, searched from 12 months before the peak to 24 months after the trough (cut back so it never reaches another national recession window), must lie
# inside peak..trough+6. Ties: the first month.
ok7 = True; t7 = []; RW = [(p, t) for p, t in NREC if p.year >= 1948 and t is not None and t <= pd.Timestamp('2020-12-01')]
for i, (p, t) in enumerate(RW):
    lo = p - pd.DateOffset(months=12); hi = t + pd.DateOffset(months=24)
    if i > 0: lo = max(lo, RW[i - 1][1] + pd.DateOffset(months=1))
    if i + 1 < len(RW): hi = min(hi, RW[i + 1][0] - pd.DateOffset(months=1))
    s = SH['red_or_deeper'][(SH.index >= lo) & (SH.index <= hi)]; pk = s.idxmax(); good = p <= pk <= t + pd.DateOffset(months=6); ok7 &= good
    t7.append(f"  {ym(p)}..{ym(t)}: red share peaks {float(s.max()):.2f} in {ym(pk)} (search {ym(lo)}..{ym(hi)}) -> {'inside' if good else 'OUTSIDE'}")
rep('P7', ok7, 'red-share peak inside each national recession or within 6 months after\n' + '\n'.join(t7))
# the national page's two checks, on the map's periods
c1 = [(st, ym(q['p'])) for st in STS for q in L0P[st] if q['grade'] < NODMG and q['te'] >= START] + [(r.st, r.peak) for r in V4T[V4T.status.isin(['recession', 'disturbance']) & (V4T.grade < NODMG)].itertuples()]
c2 = [(st, ym(q['p']), q['line_at_end'], q['grade']) for st in STS for q in L0P[st] if q['t'] is not None and q['te'] >= START and abs((q['line_at_end'] or 0) - q['grade']) > 0.01]
c2 += [(r.st, r.peak, r.line_at_end, r.grade) for r in V4T[V4T.status.isin(['recession', 'disturbance']) & ~V4T.open.astype(bool)].itertuples() if abs(r.line_at_end - r.grade) > 0.01]
rep('CHECK-1 no band without damage', not c1, f"periods with grade under 0.05: {len(c1)} {c1[:10]}")
rep('CHECK-2 line at each closed trough equals the grade', not c2, f"closed periods where |line at trough - grade| > 0.01: {len(c2)} {c2[:10]}")

# ---------------- the tests file -------------
SNAP = ['1958-04', '1975-03', '1982-11', '1986-12', '1991-03', '2009-06', '2020-04', ym(LAST)]
def snap(k):
    r = SH.loc[pd.Timestamp(k + '-01')]; return f"  {k}: " + ', '.join(f"{b} {r[b]:.2f}" for b in ['deep red', 'red', 'orange', 'yellow', 'light green', 'green']) + (f"; grey (no data) {int(r['grey_states'])} States" if r['grey_states'] else '')
kr = pd.DataFrame(KR)
HEAD = [f"STRESS MAP V3.1 STATE LAYER: the v1 tests, code and bars unchanged except P5, scored on colour as PREREG-1052 v3 states it (Amendment 1: C1 kept, C2 withdrawn, pre-1979 layer = v1's). Built {pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%dT%H:%M:%SZ')} by code/stress_map_v3_1_1052.py. No AI.",
        f"Map: 50 States x {len(MONTHS)} months ({ym(START)}..{ym(LAST)}) = {len(M)} State-months. Layer v4 from 1979-07 (State chronology v4, data through {V4J['through']}); layer L0 before.",
        f"k = {K:.4f}: median over {len(kr)} v4 recession periods wholly inside 1979-07..1996-12 (peak >= 1979-07, trough <= 1996-12, insured-rate rise > 0) of v4 unemployment-rate rise / insured-rate rise "
        f"(insured rate seasonally adjusted, same base rule as v4: excess over its lowest value in the 12 months before the v4 peak, highest excess peak..trough). Ratio quartiles {kr.ratio.quantile(.25):.2f} / {kr.ratio.quantile(.75):.2f}.",
        f"L0 inputs: payrolls 954 data/state_nan (thousands of jobs, NSA), seasonally adjusted (2x12 ratio-to-moving-average, 7-year moving seasonal factors); insured rate = exp(FH log continued weeks)/4.33/(payroll x 1000) x 100, "
        f"seasonally adjusted the same way. Both current vintage. L0 runs from each State's first payroll month to {ym(CL_LAST)} (the claims' last month).",
        "Late starts (grey before): " + ', '.join(f"{st} {ym(PAYSTART[st])}" for st in STS if PAYSTART[st] > START) + '.',
        f"L0 periods reaching 1947 or later whose pre-peak base has fewer than 11 months of insured rate (peak before 1947-12; claims begin {ym(FH.index[0])}), base taken from the months held: {short_n}.",
        f"Quiet-record SD of the deviation (pp), median over States: L0 {np.median([QSD[(s, 'L0')] for s in STS]):.2f}, v4 {np.median([QSD[(s, 'v4')] for s in STS]):.2f}.",
        f"Summary: " + ', '.join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in RES.items()), '']
SN = ['', 'Share of States (with data) in each colour band at the named months:'] + [snap(k) for k in SNAP]
open(os.path.join(OUT, 'STRESS-MAP-V3_1-STATE-TESTS-1052.txt'), 'w').write('\n'.join(HEAD + T + SN) + '\n')
json.dump({'k': K, 'k_periods': KR, 'results': RES, 'repro': repro, 'late_start': {st: ym(PAYSTART[st]) for st in STS if PAYSTART[st] > START}, 'short_base_periods': short_n,
           'quiet_sd': {f'{a}|{b}': v for (a, b), v in QSD.items()}, 'snapshots': {k: {b: round(float(SH.loc[pd.Timestamp(k + '-01')][b]), 3) for b in SH.columns} for k in SNAP}},
          open(os.path.join(OUT, 'stress_map_v3_1_tests_state_1052.json'), 'w'), indent=1, default=str)
print('\n'.join(HEAD + T + SN))

# ---------------- PROVISIONAL MONTHS (PREREG-1052 v3 Amendment 2, Anthony 15 Nov 09:34 PT "it should at least go to October"; Amendment 3, 09:36 PT: through the current
# month, month to date). After v4's last month, through the month of the newest DOL ETA 539 week (1032 data/dol/ar539.csv; c19 = the State's insured unemployment
# rate, rptdate = the week-ending date). 1152 (19 Nov 2026, Anthony: "do it"): A STATE IN A v4 PERIOD STILL OPEN AT v4's LAST MONTH KEEPS THAT MONTH'S GRADE, COLOUR
# AND BAND in every provisional month (held=True), until v4 reaches the month. Before, such a State was graded from the insured rate alone, summed since the period
# began; that grade does not join the v4 grade (the mean of labour and output): September to October 2026 New York went 2.10 to 5.51 and Alabama 2.76 to 0.41, and
# four States classed as disturbances were painted red (RECORD-1151). The sentence about the running labour grade below describes what was replaced. The rest is
# unchanged: labour input = k x the State insured rate (monthly mean of the weeks ending in the month, seasonally adjusted as v1 by sa_log;
# a month still running is the mean of the weeks published so far, at least one). A State in a v4 period still open at v4's last month keeps it, with the running grade
# of the labour dimension alone (rise over the period's base = the lowest k x insured rate of the 12 months before its peak); a State in no open period is coloured from
# the labour score computed fresh (rise over the lowest of the previous 12 months), yellow under 0.05, no green side. Replaced by v4 when v4 reaches the month (the
# months start after V4J['through'] every run). The tests P1-P7 above cover v4 months only (unchanged); the new 24-month check is reported, not tuned. No AI.
W5 = pd.read_csv(os.path.join(V4D, 'data/dol/ar539.csv'), usecols=['st', 'rptdate', 'c19'], low_memory=False); W5['w'] = pd.to_datetime(W5.rptdate); W5 = W5[W5.st.isin(STS)]
W5['c19'] = pd.to_numeric(W5.c19, errors='coerce'); W5 = W5[W5.c19 > 0]; W5['m'] = W5.w.dt.to_period('M').dt.to_timestamp()
WLAST = W5.w.max(); PLAST = WLAST.to_period('M').to_timestamp(); MTD = (WLAST + pd.Timedelta(days=7)).month == WLAST.month   # another week of the month is still to come
PM = pd.date_range(LAST + pd.DateOffset(months=1), PLAST, freq='MS') if PLAST > LAST else pd.DatetimeIndex([])
KI = {}
for st in STS:
    s = W5[W5.st == st].groupby('m').c19.mean(); s = s.reindex(pd.date_range(s.index[0], s.index[-1], freq='MS')).interpolate(limit_area='inside')
    KI[st] = K * np.exp(sa_log(np.log(s)))
# Amendment 4 (Anthony 15 Nov 11:59 PT: gray States "should never happen"): a State with no week yet in a provisional month takes its newest published week
# (carried forward, any age; same k, seasonal adjustment and scoring). KIC[st] = the insured-rate series with that week's rate carried into every provisional month
# after the State's last month; used only for the carried cells (KI, and so the 24-month check, unchanged).
KIC = {}; CARRIED = {}
for st in STS:
    w_ = W5[W5.st == st].sort_values('w'); lastm = w_.m.max(); miss = [m for m in PM if m > lastm]
    if not miss: continue
    s = w_.groupby('m').c19.mean(); s = s.reindex(pd.date_range(s.index[0], s.index[-1], freq='MS')).interpolate(limit_area='inside')
    s = pd.concat([s, pd.Series(float(w_.c19.iloc[-1]), index=pd.DatetimeIndex(miss))])
    KIC[st] = K * np.exp(sa_log(np.log(s))); CARRIED[st] = dict(week=w_.w.iloc[-1].strftime('%Y-%m-%d'), months=[ym(m) for m in miss])
def prov_cell(st, m, open_q, carried=False):
    """(status, grade, colour value) for State st at month m from the insured rate held through m"""
    I = (KIC[st] if carried else KI[st]); I = I[I.index <= m]
    if m not in I.index or not np.isfinite(I[m]): return None   # no week of this month published for the State yet: grey
    if open_q is not None:
        pre = I[(I.index < open_q['p0']) & (I.index >= open_q['p0'] - pd.DateOffset(months=12))]
        if not len(pre): pre = I[I.index < open_q['p0']].tail(12)
        ex = (I[I.index >= open_q['p0']] - float(pre.min())).clip(lower=0); g = round(float(dd.labour_score(float(ex.max()), float(ex.sum()))), 2) if len(ex) else 0.0
        s = colour_value(True, g, 0.0); s = min(s, -3.0) if open_q['status'] == 'recession' else s
        return open_q['status'], g, s
    pre = I[(I.index < m) & (I.index >= m - pd.DateOffset(months=12))]; ex = max(0.0, float(I[m]) - float(pre.min())); g = round(float(dd.labour_score(ex, ex)), 2)
    return 'none', g, (colour_value(True, g, 0.0) if g >= NODMG else 0.0)
def open_at(st, m):
    for q in V4P.get(st, []):
        if q['p'] <= m and (q['t'] is None or q['t'] >= m): return q
    return None
HELD0 = M[(M.month == ym(LAST)) & M.period_status.isin(['recession', 'disturbance'])].set_index('st')   # 1152: each State's v4 row at v4's last month
PROWS = []
for st in STS:
    q = open_at(st, LAST); q = q if (q is not None and q['t'] is None) else None
    for m in PM:
        if q is not None and st in HELD0.index:   # 1152: the open period keeps v4's last grade, colour and band
            h0 = HELD0.loc[st]
            PROWS.append(dict(st=st, month=ym(m), layer='provisional', period_status=q['status'], period_peak=ym(q['p']), period_trough='open', provisional=True, grade=h0.grade,
                              deviation_pp='', deviation_sd='', colour_value=h0.colour_value, band=h0.band, colour_hex=h0.colour_hex, carried=False, carried_week='', held=True)); continue
        cw = CARRIED.get(st) and ym(m) in CARRIED[st]['months']
        pc = prov_cell(st, m, q, carried=bool(cw))
        if pc is None:
            PROWS.append(dict(st=st, month=ym(m), layer='provisional', period_status='no_data', period_peak='', period_trough='', provisional=True, grade='', deviation_pp='', deviation_sd='',
                              colour_value='', band='grey', colour_hex='#d5d9de')); continue
        stt, g, s = pc
        PROWS.append(dict(st=st, month=ym(m), layer='provisional', period_status=stt, period_peak=ym(q['p']) if q else '', period_trough='open' if q else '', provisional=True,
                          grade=g, deviation_pp='', deviation_sd='', colour_value=round(s, 3), band=band(stt if stt != 'none' or g < NODMG else 'disturbance', g, s) if (stt != 'none' or g >= NODMG) else 'yellow', colour_hex=hexof(s),
                          carried=bool(cw), carried_week=(CARRIED[st]['week'] if cw else '')))
# the 24-month check: each of the last 24 v4 months recomputed as if provisional (open period = a v4 period open at the month before, as published), band against v4's band
MB4 = M.set_index(['st', 'month']).band; CK = []
for m in pd.date_range(LAST - pd.DateOffset(months=23), LAST, freq='MS'):
    agree = 0; n_ = 0
    for st in STS:
        q = open_at(st, m - pd.DateOffset(months=1))
        if q is not None:   # 1152: held from the month before
            n_ += 1; agree += MB4[(st, ym(m - pd.DateOffset(months=1)))] == MB4[(st, ym(m))]; continue
        pc = prov_cell(st, m, q)
        if pc is None: continue
        stt, g, s = pc
        b = band(stt if stt != 'none' or g < NODMG else 'disturbance', g, s) if (stt != 'none' or g >= NODMG) else 'yellow'; n_ += 1; agree += b == MB4[(st, ym(m))]
    CK.append(dict(month=ym(m), states=n_, agree=agree, share=round(agree / n_, 3) if n_ else None))
ck_ok = sum(1 for c in CK if c['share'] is not None and c['share'] >= 0.70)
PROV = dict(first=ym(PM[0]) if len(PM) else None, last=ym(PM[-1]) if len(PM) else None, months=[ym(m) for m in PM], mtd=bool(MTD and len(PM)), weeks_through=WLAST.strftime('%Y-%m-%d'),
            weeks_in_last=int(W5[W5.m == PLAST].w.nunique()), v4_last=ym(LAST), k=K, carried=CARRIED, held=sorted({r['st'] for r in PROWS if r.get('held')}), grey_cells=sum(1 for r in PROWS if r['band'] == 'grey'), check24=dict(bar=0.70, months_at_or_above=ck_ok, of=len(CK), rows=CK))
json.dump(PROV, open(os.path.join(OUT, 'stress_map_v3_1_provisional_1052.json'), 'w'), indent=1)
open(os.path.join(OUT, 'STRESS-MAP-V3_1-STATE-TESTS-1052.txt'), 'a').write(
    f"\nPROVISIONAL MONTHS (Amendments 2 and 3): {PROV['months'] or 'none'} from the DOL ETA 539 weekly State insured rate (weeks through {PROV['weeks_through']}"
    f"{', the last month to date' if PROV['mtd'] else ''}); labour dimension only; replaced by v4 when published.\n"
    f"HELD (1152): a State in a v4 period open at {ym(LAST)} keeps that month's grade, colour and band: {', '.join(PROV['held']) or 'none'}.\n"
    f"CARRIED (Amendment 4): " + ('; '.join(f"{st} week {v['week']} carried into {', '.join(v['months'])}" for st, v in sorted(CARRIED.items())) or 'none') + f"; grey provisional cells {PROV['grey_cells']}.\n"
    f"CHECK-24 (reported, not tuned): in {ck_ok} of the last {len(CK)} v4 months the provisional colour band equals v4's in at least 70% of States; by month: "
    + ', '.join(f"{c['month']} {c['share']}" for c in CK) + '\n')
print('provisional months', PROV['months'], 'mtd', PROV['mtd'], 'weeks through', PROV['weeks_through'], '| check-24:', ck_ok, 'of', len(CK), 'months at >= 0.70')
if len(PM):   # the page carries v4 months and then the provisional months
    M = pd.concat([M, pd.DataFrame(PROWS)], ignore_index=True)
    M['m'] = pd.to_datetime(M.month + '-01'); M['inp'] = M.period_status.isin(['recession', 'disturbance']); M['rec'] = M.period_status == 'recession'; M['has'] = M.period_status != 'no_data'
    M['g'] = pd.to_numeric(M.grade, errors='coerce'); BY = M.groupby('m')
    SH = pd.DataFrame({b: BY.apply(lambda x, b=b: float((x.band == b).sum()) / float(x.has.sum())) for b in ['deep red', 'red', 'orange', 'yellow', 'light green', 'green']}); SH['grey_states'] = BY.apply(lambda x: int((~x.has).sum()))
    SH['red_or_deeper'] = SH['red'] + SH['deep red']; MONTHS = pd.date_range(START, PM[-1], freq='MS')
    M.drop(columns=['m', 'inp', 'rec', 'has', 'g']).to_csv(os.path.join(OUT, 'stress_map_v3_1_state_month_with_provisional.csv'), index=False)

# ---------------- the page: code/stress_map_template_1052.html (the national page_template's header, styles, wording and footer) + this data -------------
NAMES = dict(AL='Alabama', AK='Alaska', AZ='Arizona', AR='Arkansas', CA='California', CO='Colorado', CT='Connecticut', DE='Delaware', FL='Florida', GA='Georgia', HI='Hawaii', ID='Idaho', IL='Illinois', IN='Indiana', IA='Iowa', KS='Kansas', KY='Kentucky', LA='Louisiana', ME='Maine', MD='Maryland', MA='Massachusetts', MI='Michigan', MN='Minnesota', MS='Mississippi', MO='Missouri', MT='Montana', NE='Nebraska', NV='Nevada', NH='New Hampshire', NJ='New Jersey', NM='New Mexico', NY='New York', NC='North Carolina', ND='North Dakota', OH='Ohio', OK='Oklahoma', OR='Oregon', PA='Pennsylvania', RI='Rhode Island', SC='South Carolina', SD='South Dakota', TN='Tennessee', TX='Texas', UT='Utah', VT='Vermont', VA='Virginia', WA='Washington', WV='West Virginia', WI='Wisconsin', WY='Wyoming')
BCODE = {'deep red': 'D', 'red': 'r', 'orange': 'o', 'yellow': 'y', 'light green': 'l', 'green': 'g', 'grey': 'x'}
SHP = json.load(open(os.path.join(OUT, 'state_shapes_cb2024_svg_1052.json')))
ST = {}
for st in STS:
    x = M[M.st == st].sort_values('m'); cv = pd.to_numeric(x.colour_value, errors='coerce'); ds = pd.to_numeric(x.deviation_sd, errors='coerce')
    per = [[ym(q['p']), ym(q['t']) if q['t'] is not None else 'open', q['status'], q['grade'], q['provisional'], 'L0'] for q in L0P[st] if q['te'] >= START and q['p'] < SEAM]
    per += [[ym(q['p']), ym(q['t']) if q['t'] is not None else 'open', q['status'], q['grade'], q['provisional'], 'v4'] for q in V4P.get(st, []) if (q['t'] or LAST) >= SEAM]
    ST[st] = dict(c=[-1 if np.isnan(v) else int(round((v + 4) / 0.05)) for v in cv], g=[0 if np.isnan(v) else int(round(v * 100)) for v in x.g],
                  d=[0 if np.isnan(v) else int(round(v * 100)) for v in ds], s=''.join({'recession': 'R', 'disturbance': 'D', 'none': 'N', 'no_data': 'G'}[v] for v in x.period_status),
                  b=''.join(BCODE[v] for v in x.band), per=per, start=ym(PAYSTART[st]))
CNT = M.groupby('m').apply(lambda x: [int((x.band == b).sum()) for b in ['deep red', 'red', 'orange', 'yellow', 'light green', 'green', 'grey']])
nf = lambda t: ym(t) if t is not None else None
DESC = ''.join('<p>' + p + '</p>' for p in [
    "<b>What the colour is.</b> Each State-month gets one value on one scale. Inside a recession or disturbance period the colour is the period's running damage grade, the same "
    "grade the national register and the State chronology use (labour and output dimensions, the Great Depression at 10): orange while the grade is small, full red at 2.0 "
    "(the recession bar), deep red at 4.0 and above. When no period is open the colour is the State's coincident measure against its Hodrick-Prescott trend "
    "(λ = 133,107.94), in units of that State's own standard deviation in months with no period open, so each State is judged against itself: yellow at trend, "
    "light green at +1 SD, deep green at +2 SD, orange at −1 SD. The cut points (grade 0.05, 1.0, 2.0, 4.0; deviation −1, 0, +1, +2 SD) were fixed before the map was built.",
    f"<b>From July 1979: the State chronology v4, exactly.</b> The periods, their dates and the running grade are the State chronology v4 files unchanged (Philadelphia Fed State "
    f"coincident index; State unemployment rate), dated by the national register's own functions: Bry-Boschan windows on the deviation from trend, a window must fall at least "
    f"1.0 point, grade 2.0 or more is a recession. Over the {len(V)} State-months from July 1979 the largest difference between this map's grade and the v4 line is {float(diff.max()):.2f}.",
    f"<b>Before July 1979: the same method on older data.</b> The State coincident index and the State unemployment rate do not exist before 1979, so the v4 code runs unchanged "
    f"on two substitutes: BLS State nonfarm payrolls as the index (not seasonally adjusted at source; adjusted here by a ratio to a centred 2×12 moving average with 7-year "
    f"moving seasonal factors) and the State insured unemployment rate as the labour measure (continued weeks claimed ÷ 4.33 ÷ payroll jobs, DOL data as compiled by Fieldhouse, "
    f"Munro, Koch and Howard, 2024), scaled by k = {K:.3f}, the median ratio of the unemployment-rate rise to the insured-rate rise across the {len(KR)} v4 recession periods "
    f"of 1979–1996. The two layers join at July 1979; the join is stated here and not marked on the map. "
    + ("States without a payroll series yet are grey: " + ', '.join(f"{NAMES[s]} until {ymL}" for s, ymL in [(s, pd.Timestamp(PAYSTART[s]).strftime('%B %Y')) for s in STS if PAYSTART[s] > START]) + '.'),
    "<b>Vintages.</b> Every series on this map is current vintage, as published today: the Philadelphia Fed State coincident indexes (revised), the State unemployment rates, "
    "BLS State payrolls and the DOL State claims. No real-time vintage enters version 1; the map shows the record as we know it now, not what was known at the time. "
    "Dates near the end can still move: the trend is two-sided and the newest periods are provisional until their trough is two years old.",
    "<b>Bands on the timeline</b> are the national register v3.2 (recessions shaded grey; disturbances dashed). The red line in the strip is the share of States red or deeper each month.",
    "<b>Coming.</b> County drill-down (click a State to see its counties) is not part of version 1. Supplementary panels named in the design (aid to dependent children, "
    "general assistance, business failures, farm receipts, insured unemployment and claims from the Labor Market series) are not in the colour and are not yet shown."])
TESTS = [[k, v, next(t for t in T if t.startswith(k + ':')).split('  ', 1)[1].split('\n')[0]] for k, v in RES.items()]
DATA = dict(start=ym(START), n=len(MONTHS), seam=ym(SEAM), last=ym(MONTHS[-1]), last_v4=ym(LAST), prov=PROV, built=pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d'), pal=PAL, shapes=SHP['paths'], names=NAMES,
            states=ST, red=[int(round(v * 1000)) for v in SH['red_or_deeper']], share=[CNT[m] for m in MONTHS],
            nrec=[[ym(p), nf(t)] for p, t in NREC if (t or LAST) >= START], ndis=[[ym(p), nf(t)] for p, t in NDIS if (t or LAST) >= START], desc=DESC, tests=TESTS, k=K)
tpl = open(os.path.join(C, 'code', 'stress_map_template_1052.html')).read(); assert tpl.count('__DATA__') == 1
html = tpl.replace('__DATA__', json.dumps(DATA, separators=(',', ':')).replace('</', '<\\/'))
import re; assert not re.search(r'(src|href)\s*=\s*["\']?https?://|url\(\s*["\']?https?:|@import|fetch\(|XMLHttpRequest', html)   # self-contained: no network fetch
os.makedirs(WEB, exist_ok=True); open(os.path.join(WEB, 'state_layer_v3_1.html'), 'w').write(html); print('wrote', os.path.join(WEB, 'state_layer_v3_1.html'), len(html.encode()), 'bytes')
