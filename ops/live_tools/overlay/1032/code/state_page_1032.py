#!/usr/bin/env python3
"""1032: the State Recession Indicator page, built FROM the national page (bhrrealtime.pages.dev/detector/, saved in
web/ref_national/detector.html): same header, layout, chart engine, Edit Graph, Download, Notes, speed panels and
footer; the data object S is swapped for each state's (chosen by the picker in the top-right corner, kept in #XX).
Every replacement is asserted. Writes web/state-onset/index.html. No AI at run time."""
import os, sys, json, re, math, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import harness_1032 as H, recon_1032 as R, chron_current_1032 as CC
COLL = H.COLL; OUT = H.OUT; WEB = os.path.join(COLL, 'web')
nat = open(os.path.join(WEB, 'ref_national', 'detector.html')).read()
# 13 Nov 2026 (Anthony 12:42 PT, A148): the graph is the state DAMAGE grade and the shading is the Bristow-Hall State Chronology v1 (recessions shaded, disturbances lined)
_RL = {}   # A195 (Anthony, 14 Nov 2026 06:15 PT): relapses are counted - a renewed fall in jobs before the peak was regained is banded, classed by the level the grade reaches
if os.path.exists(os.path.join(OUT, 'relapses_a194_1032.csv')):
    for _x in pd.read_csv(os.path.join(OUT, 'relapses_a194_1032.csv')).to_dict('records'): _RL.setdefault(_x['st'], []).append({k_: (None if isinstance(v_, float) and v_ != v_ else v_) for k_, v_ in _x.items()})
_RT = json.load(open(os.path.join(OUT, 'damage_realtime_tail_a179_1032.json')))['states']   # A179: census months of open episodes uncapped; payroll releases after the census ends
_V4 = pd.read_csv(os.path.join(OUT, 'BH-STATE-CHRONOLOGY-V4-1032.csv')); _V4 = _V4[_V4.status.isin(['recession', 'disturbance'])]; _V4L = json.load(open(os.path.join(OUT, 'damage_line_v4_a198_1032.json')))
_C2 = {}
for _x in pd.read_csv(os.path.join(OUT, 'state_class2_a205_1032.csv')).to_dict('records'): _C2.setdefault(_x['st'], []).append(_x)
_BHM = json.load(open(os.path.join(OUT, 'bh_state_chronology_v1_1032.json'))); _BHE = pd.read_csv(os.path.join(OUT, 'BH-STATE-CHRONOLOGY-V3_2-1032.csv')); _BHE['open'] = _BHE['open'].astype(str) == 'True'; _BHE = _BHE[_BHE['class'].isin(['recession', 'disturbance'])]
data = json.load(open(os.path.join(WEB, 'data.json')))            # index levels, chronology, signal (build_web_1032.py)
# the rule on the page since 11 Nov 2026: A63d, scored by the census standard both ways (doc/PREREG-1032-A69-census-standard-three-month-floor-2026-11-11.md); A57b's page: state_page_1032_A57b_v6.py
A46C = {st: [pd.Timestamp(c) for c in cs] for st, cs in json.load(open(os.path.join(OUT, 'rule_a142_calls_1032.json')))['rules']['A142g in sample']['calls'].items()}   # A92k6 = A75a + six of seven witnesses (PREREG-1032-A92), on the page from 12 Nov 2026; before: state_page_1032_A75a_v10.py; A75a (A63d + the no-index gate route; PREREG-1032-A75); A63d's page: state_page_1032_A63d_v7.py
_P63 = json.load(open(os.path.join(OUT, 'rule_a142_calls_1032.json')))['parts']; C_UN = {st: set(pd.Timestamp(c) for c in cs) for st, cs in _P63['unemployment_witnesses'].items()}; C_HH = {st: set(pd.Timestamp(c) for c in cs) for st, cs in _P63['six_readings_both_job_counts'].items()}; C_NI = {st: set(pd.Timestamp(c) for c in cs) for st, cs in _P63['no_index_three_witnesses'].items()}; C_V7 = {st: set(pd.Timestamp(c) for c in cs) for st, cs in _P63['six_of_seven'].items()}; C_IC = {st: set(pd.Timestamp(c) for c in cs) for st, cs in _P63['claims_route'].items()}; C_EP = {st: set(pd.Timestamp(c) for c in cs) for st, cs in _P63['persisting_episode'].items()}; C_JR = {st: set(pd.Timestamp(c) for c in cs) for st, cs in _P63['jobs_route'].items()}; C_CE = {st: set(pd.Timestamp(c) for c in cs) for st, cs in _P63['certified_episode'].items()}; C_LV = {st: set(pd.Timestamp(c) for c in cs) for st, cs in _P63['lasting_vote'].items()}; C_CR = {st: set(pd.Timestamp(c) for c in cs) for st, cs in _P63['census_route'].items()}
_me = lambda q: (pd.Period(q, 'M') + 1).to_timestamp() - pd.Timedelta(days=1); _CZ = {}
for _r in pd.read_csv(os.path.join(OUT, 'STATE-CENSUS-RECESSION-CHRONOLOGY-A124-1032.csv')).itertuples(): _CZ.setdefault(_r.st, []).append((_me(_r.first_month) - pd.Timedelta(days=365), _me(_r.last_month) + pd.Timedelta(days=365)))   # A142 (13 Nov 2026): a call inside a census recession is a right call on the second benchmark
_CS = json.load(open(os.path.join(OUT, 'score_census_a142g_1032.json')))['floors']['3']['rows']['A142g | 1994-2026']   # A69: census job loss = at least three months below a year earlier
_A49 = {st: set(pd.Timestamp(c) for c in cs) for st, cs in json.load(open(os.path.join(OUT, 'rule_a49_1032.json')))['rules']['A46 RT1 + benchmark renewals']['calls'].items()}
_A46 = {st: set(pd.Timestamp(c) for c in cs) for st, cs in json.load(open(os.path.join(OUT, 'rule_a46_1032.json')))['rules']['A40 base + national-gated RT1 (two domains)']['calls'].items()}
C_REN = {st: _A49[st] - _A46.get(st, set()) for st in _A49}
def _J(f, k): return {st: set(pd.Timestamp(c) for c in cs) for st, cs in json.load(open(os.path.join(OUT, f)))['rules'][k]['calls'].items()}
C_RT6B = _J('rule_a38_1032.json', 'RT6 benchmark-confirmed'); C_EB = _J('rule_a30_1032.json', 'EBleg held13'); C_MK = _J('rule_rt2_1032.json', 'mK|veto.P1')
_A39 = _J('rule_a39_1032.json', 'A38 + PHCI bench'); _A38 = _J('rule_a38_1032.json', 'RT6 bench + held13'); C_PH = {st: _A39[st] - _A38.get(st, set()) for st in _A39}
import rescore_kfree_1032 as KF
_DEP = [x for x in json.load(open(os.path.join(OUT, 'diag_index_depth_a80_1032.json'))) if x['span'] == '1994-2026']   # scope ruling 12 Nov 2026: the record is stated by the official index's own fall (2% or more; milder)
_SEC = json.load(open(os.path.join(OUT, 'rule_a89k5_second_signal_calls_1032.json')))['second_signal_calls']
import pickle
from rule_a6_1032_lib import gate1
LIVE37 = pickle.load(open(os.path.join(OUT, 'a37b_live_1032.pkl'), 'rb')); _VE = json.load(open(os.path.join(OUT, 'vintage_episodes_1032.json')))
PHL = {st: [(pd.Timestamp(r[0]), bool(r[2])) for r in rows] for st, rows in _VE.items()}
_w = pd.read_csv(os.path.join(H.COLL, 'data/dol/ar539.csv'), low_memory=False); _w['w'] = pd.to_datetime(_w['rptdate'])
for _c in ('c3', 'c8'): _w[_c] = pd.to_numeric(_w[_c], errors='coerce')
WIC = _w.pivot_table(index='w', columns='st', values='c3', aggfunc='sum'); WCW = _w.pivot_table(index='w', columns='st', values='c8', aggfunc='sum')
def s13(x): return x.rolling(13, min_periods=13).sum()
def wyoy(x, k=52): return np.log(s13(x)) - np.log(s13(x).shift(k))
def wav(g): return g.abs().expanding(min_periods=260).mean().shift(1)
m = re.search(r'const S = (\{.*?\});\n', nat, flags=re.S); NATS = json.loads(m.group(1))
IC, CW = H.load_5159()
def m3(x): return x.rolling(3).sum()
def yoy(x, k=12): return np.log(m3(x)) - np.log(m3(x).shift(k))
def avgmove(g): return g.abs().expanding(min_periods=60).mean().shift(1)
def mend_iso(p): return H.mend(p).strftime('%Y-%m-%d')
import datetime as _dt, zoneinfo as _zi
BUILT_AT = _dt.datetime.now(_zi.ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M')
months_all = [str(p) for p in pd.period_range('1948-01', '2026-10', freq='M')]
ALL = {}
for st in R.STATES:
    if st == 'DC': continue
    d = data['states'][st]; name = d['name']
    ic = WIC[st].where(WIC[st] > 0); cw = WCW[st].where(WCW[st] > 0)
    gi, gc = wyoy(ic), wyoy(cw); gate = (wyoy(ic, 104) > 0) & (wyoy(cw, 104) > 0)
    reading = np.minimum(gc / wav(gc), gi / wav(gi)).clip(lower=0); reading = reading.where(gate, np.minimum(reading, 0.99))
    rm = reading.groupby(reading.index.to_period('M')).last(); last = ic.dropna().index.max().to_period('M')
    vals = {str(p): (None if not np.isfinite(v) else round(float(v), 3)) for p, v in rm.items() if p <= last}
    ser_dates = [mm for mm in months_all if '1979-01' <= mm[:7] and mm <= str(last)]; ser_vals = [vals.get(mm) for mm in ser_dates]
    # the rule's calls (A46 RT1 two domains), each with the part of the rule that made it; the signal = the state index's newest live reading
    def _route(c):
        r = []
        if c in C_V7.get(st, set()): r.append('six of seven signals')
        if c in C_CR.get(st, set()): r.append('the census of jobs, as published: below a year earlier six months, 1% below in one')
        if c in C_LV.get(st, set()): r.append('five of seven signals for 45 days, with payroll jobs down in a quarter of the states')
        if c in C_CE.get(st, set()): r.append('the state index has dated the same downturn six releases running; payroll jobs down on the year; the jobless rate up for over a month')
        if c in C_JR.get(st, set()): r.append('payroll and household jobs both down on the year, the jobless rate up, the index in recession, permits down')
        if c in C_EP.get(st, set()): r.append('inside the national window: the state index has dated the same downturn six releases running, and payroll growth has stalled')
        if c in C_IC.get(st, set()): r.append('new claims up 25% for six months, with the insured rate, the jobless rate and benefit exhaustions up')
        if c in C_NI.get(st, set()): r.append('inside the national window: payrolls down on the year, insured and total unemployment both up, at least as fast as the nation')
        if c in C_HH.get(st, set()): r.append('state index, 6 releases; payroll and household jobs both down on the year')
        if c in C_UN.get(st, set()): r.append('state index inside the national window; insured and total unemployment both up, at least as fast as the nation')
        if c in C_EB.get(st, set()): r.append('insured unemployment held up 13 weeks')
        if c in C_MK.get(st, set()): r.append('claims and payrolls')
        if c in C_RT6B.get(st, set()): r.append('state index, 6 releases, at the benchmark')
        if c in C_PH.get(st, set()): r.append('published index, 6 releases, at the benchmark')
        if c in C_REN.get(st, set()): r.append('state index still in recession at the next benchmark')
        return '; '.join(dict.fromkeys(r)) or 'state index inside the national Bristow-Hall window; state jobs down on the year'
    def _live(t):
        ph = [f for d0, f in PHL.get(st, []) if d0 <= t]; rb = [f for d0, f in LIVE37.get(st, []) if d0 <= t]
        return bool(ph[-1]) if ph else (bool(rb[-1]) if rb else False)
    eps = []; _grp = []
    for c in A46C.get(st, []):   # calls within 182 days of a group's first call are one call (the scoring's own grouping); the parts are listed together
        if _grp and (c - _grp[-1][0]).days < 182: _grp[-1][1].append(_route(c)); continue
        _grp.append((c, [_route(c)]))
    # 13 Nov 2026 (Anthony 12:35 PT): the line on the graph is the RULE, not the claims signal: 1.00 from the month of a call, held while the rule keeps calling and
    # for 182 days after its last call (the scoring's own grouping window); the claims signal stays available as its own series
    _gl = []
    for c in A46C.get(st, []):
        if _gl and (c - _gl[-1][1]).days < 182: _gl[-1][1] = c
        else: _gl.append([c, c])
    _onm = set()
    for _a, _b in _gl: _onm |= {str(q) for q in pd.period_range(_a.to_period('M'), (_b + pd.Timedelta(days=182)).to_period('M'), freq='M')}
    ser_claims = ser_vals; ser_vals = [(None if mm[:7] < '1994-03' else (1.0 if mm[:7] in _onm else 0.0)) for mm in ser_dates]
    ser_rule = ser_vals; _dm = dict(_V4L['states'][st]['line']); ser_vals = [(_dm.get(mm[:7]) if mm[:7] > _V4L['through'] else (_dm.get(mm[:7]) or 0.0)) for mm in ser_dates]
    # 15 Nov 2026 (1052, for 1032): the series end at the State's own data month (dg.rt = the v4 line's unemployment_through for the State); the last grade is
    # no longer held forward to the claims' last month (that drew a phantom point one month past the data on /state-onset/)
    # 20 Nov 2026 (1052): the grade is v4's, which needs BOTH the State unemployment rate and the Philadelphia Fed index: the series end at the
    # newest month both have (min of the two). The BLS State release comes about two weeks before the index; a month past the index has no grade
    # (null: the page's script cannot draw it, 24 States failed to render on 20 Nov 2026 15:49Z) and stays off the chart until v4 reaches it
    _rt = min(_V4L['unemployment_through'][st], _V4L['through']); _keep = [i for i, mm in enumerate(ser_dates) if mm[:7] <= _rt]
    ser_dates = [ser_dates[i] for i in _keep]; ser_vals = [ser_vals[i] for i in _keep]; ser_claims = [ser_claims[i] for i in _keep]; ser_rule = [ser_rule[i] for i in _keep]
    for c, rts in _grp:
        mo = str((c - pd.Timedelta(days=35)).to_period('M')); rt = '; '.join(dict.fromkeys(x for r in rts for x in r.split('; ')))
        eps.append({'open_month': mo, 'open_pub': c.strftime('%Y-%m-%d'), 'close_month': mo, 'close_pub': c.strftime('%Y-%m-%d'), 'route': rt,
                    'close_basis': 'real time', 'walk': False, 'damage_score': None, 'damage_pm': None, 'damage_depth': None,
                    'damage_labour': None, 'damage_output': None, 'damage_production': None, 'gdp_pt_pct': None,
                    'gdp_cum_pct_quarters': None, 'gdp_nowcast': False, 'ip_pt_pct': None, 'ip_cum_pct_months': None,
                    'open_branch': 'state', 'close_branch': 'state'})
    KR = KF.score_kfree(A46C.get(st, []), st, pd.Timestamp('1994-03-01'), pd.Timestamp('2026-10-31'))
    # the state's recessions (shaded; provisional = lined)
    lastm = d['now']['last_month']
    nb = []
    for e in d['rec']:
        if not e['p'] or e.get('gone'): continue
        prov = e['c'] == 'provisional' or e['t'] is None
        nb.append({'peak': e['p'], 'trough': e['t'] or lastm, 'prov': prov, 'cls': e['c']})
    nb = [{'peak': r.peak, 'trough': r.trough, 'prov': bool(r._asdict()['open']) or _BHE.loc[r.Index, 'class'] == 'disturbance', 'cls': _BHE.loc[r.Index, 'class'], 'damage': None if r.damage != r.damage else float(r.damage), 'industry': r.largest_industry_loss if isinstance(r.largest_industry_loss, str) else '', 'open': bool(r._asdict()['open']), 'depth': None if r.depth != r.depth else float(r.depth)} for r in _BHE[_BHE.st == st].itertuples()]
    for _r in nb:   # A186 (Anthony, 14 Nov 2026 04:58 PT): a downturn still under way is classed on its live grade (the highest so far, census then payroll releases), and its band runs to the latest month while the loss stands
        _ol = _RT[st]['open_live'].get(_r['peak']) if _r['open'] else None
        if _ol: _r.update({'damage': _ol['live_highest'], 'cls': 'recession' if _ol['live_highest'] >= 2.0 else 'disturbance', 'depth': min(_ol['depth_so_far_pct'], _ol['job_loss_latest_pct']), 'trough': _RT[st]['real_time_through'] if _ol['live_latest'] > 0 else _r['trough']})
        if _r['open'] and (not _ol or _ol['live_latest'] <= 0): _r['open'] = False; _r['prov'] = _r['cls'] == 'disturbance'   # jobs are back at the peak: the downturn is over, its trough stands
        _r['prov'] = _r['cls'] == 'disturbance'
    nb += [{'peak': x['low_month'], 'trough': x['high_month'], 'prov': x['line_at_high'] < 2.0, 'cls': 'recession' if x['line_at_high'] >= 2.0 else 'disturbance', 'damage': x['line_at_high'], 'industry': '', 'open': False, 'depth': x.get('job_fall_pct'), 'relapse': x['after_the_downturn_that_peaked']} for x in _RL.get(st, [])]
    nb.sort(key=lambda r: r['peak'])
    jb = nb
    nb = [{'peak': r.peak, 'trough': r.trough if isinstance(r.trough, str) else _V4L['through'], 'prov': r.status == 'disturbance', 'cls': r.status, 'damage': float(r.grade), 'industry': '', 'open': bool(r.open), 'depth': -float(r.index_fall_pct), 'dev': (None if r.dev_fall_pp != r.dev_fall_pp else float(r.dev_fall_pp)), 'ur': float(r.ur_rise_pp), 'pv': bool(r.provisional)} for r in _V4[_V4.st == st].itertuples()]
    for _c in _C2.get(st, []):
        if _c['kind'] == 'label':
            _hit = [r for r in nb if r['peak'] == _c['peak'] and r['cls'] == 'disturbance']; assert len(_hit) == 1, (st, _c['peak'])
            _hit[0]['c2'] = True
        else:
            nb.append({'peak': _c['peak'], 'trough': _c['trough'], 'prov': True, 'cls': 'disturbance', 'damage': float(_c['grade']), 'industry': '', 'open': False, 'depth': -float(_c['index_fall_pct']), 'ur': float(_c['ur_rise_pp']), 'pv': False, 'c2': True, 'nested': True})
    for _r in nb:
        if _r.get('nested'): continue
        _on = [str(q) for q in pd.period_range(_r['peak'], _r['trough'], freq='M') if (_dm.get(str(q)) or 0) >= 0.05]
        _r['slow'] = _r['peak']
        if _on: _r['peak'] = max(_r['peak'], str(pd.Period(_on[0], 'M') - 1))
    nb.sort(key=lambda r: r['peak'])
    # speed panels: each dated recession from 1977 with a trough: the rule's first call inside [peak end-200 d, trough end]
    ann = []; notcalled = []
    for r in nb:
        if r['prov'] or r['peak'] < '1994-09': continue
        pe = H.mend(pd.Period(r['peak'], 'M')); te = H.mend(pd.Period(r['trough'], 'M'))
        calls = [e for e in eps if pe - pd.Timedelta(days=365) <= pd.Timestamp(e['open_pub']) <= te + pd.Timedelta(days=365)]
        if not calls: continue
        e0 = calls[0]
        ann.append({'peak': r['peak'], 'trough': r['trough'], 'peak_ann': None, 'trough_ann': None, 'rule_open': e0['open_pub'],
                    'rule_close': e0['close_pub'], 'rule_open_month': e0['open_month'], 'rule_close_month': e0['close_month'],
                    'close_basis': 'real time', 'source': 'Philadelphia Fed' if r['cls'] == 'official' else 'BH',
                    'sahm_peak': None, 'sahm_month': None, 'bristow_end': None, 'bristow_known': None})
    # latest view of each live call: confirmed (a recession in today's data covers it), withdrawn (none, call a year old), pending
    LASTD = pd.Timestamp(data['built'])
    zones = [(H.mend(pd.Period(r['peak'], 'M')) - pd.Timedelta(days=365), H.mend(pd.Period(r['trough'], 'M')) + pd.Timedelta(days=365)) for r in nb]; notcalled = list(KR['missed'])
    calls_view = []
    for e in eps:
        c = pd.Timestamp(e['open_pub'])
        if c > LASTD: continue
        stt = ('confirmed' if any(a <= c <= b for a, b in zones) else ('withdrawn' if c < LASTD - pd.Timedelta(days=365) else 'pending'))
        calls_view.append({'called': e['open_pub'], 'from': e['open_month'], 'to': e['close_month'], 'route': e['route'], 'view': stt})
    ci = d['index']; cid = sorted(ci)
    _n1 = {pd.Timestamp(x.split()[1]) for x in _CS['neutral_calls'] if x.split()[0] == st}; _n2 = [x for x in _CS['neutral_recessions'] if x.split()[0] == st]; _n2c = [x for x in _CS['neutral_recessions_that_were_caught'] if x.split()[0] == st]
    _n1 |= {pd.Timestamp(x) for x in KR['fa_dates'] if any(a <= pd.Timestamp(x) <= b for a, b in _CZ.get(st, []))}
    _yr = pd.Timedelta(days=365); _mE = lambda q: (pd.Period(q, 'M') + 1).to_timestamp() - pd.Timedelta(days=1); _cs = sorted(A46C.get(st, []))
    _br = [r for r in nb if r['cls'] == 'recession' and not r['prov'] and r['peak'] >= '1994-03']; _bz = [(_mE(r['peak']) - _yr, _mE(r['trough']) + _yr) for r in nb]
    _bc = sum(any(_mE(r['peak']) - _yr <= c <= _mE(r['trough']) + _yr for c in _cs) for r in _br); _bo = 0; _lo = None
    for c in _cs:
        if c < pd.Timestamp('1994-03-01') or c > pd.Timestamp('2025-09-30') or any(a <= c <= b for a, b in _bz): continue
        if _lo is None or (c - _lo).days >= 182: _bo += 1
        _lo = c
    rec = {'must': KR['must'] - len(_n2), 'caught': KR['caught'] - len(_n2c), 'fa': KR['fa'] - len(_n1), 'pending': KR['pending']}; assert rec['fa'] >= 0
    rec.update({'bh_n': len(_br), 'bh_c': int(_bc), 'bh_out': int(_bo)})
    for x in calls_view:
        if x['view'] == 'withdrawn' and any(abs((pd.Timestamp(x['called']) - t).days) < 182 for t in _n1): x['view'] = 'census'
    # A89 (12 Nov 2026): the second signal - five of six real-time witnesses - shown beside the rule, not part of it or of the record
    for _c in _SEC.get(st, []):
        if any(abs((pd.Timestamp(_c) - _t).days) < 182 for _t in A46C.get(st, [])): continue
        calls_view.append({'called': _c, 'from': _c[:7], 'to': _c[:7], 'route': 'five of six signals', 'view': 'second'})
    calls_view.sort(key=lambda x: x['called'])
    _dp = [dict(x, caught=(x['rec'].split()[1] not in {str(m)[:7] for m in KR['missed']})) for x in _DEP if x['rec'].split()[0] == st]   # A142: caught by the rule on the page, not by A75a
    _dd = [x for x in _dp if x['index_fall_pct'] is not None and x['index_fall_pct'] <= -2]; _dm = [x for x in _dp if x['index_fall_pct'] is not None and x['index_fall_pct'] > -2]
    if _dp and len(_dd) + len(_dm) == len(_dp) == rec['must']: rec.update({'deep_n': len(_dd), 'deep_c': sum(x['caught'] for x in _dd), 'mild_n': len(_dm), 'mild_c': sum(x['caught'] for x in _dm)})
    ALL[st] = {'code': 'BHRSTATE' + st, 'name': name, 'built': data['built'], 'built_at': BUILT_AT,
               'calendar': [c for c in NATS.get('calendar', []) if c.get('kind') == 'claims'],
               'series': {'frequency': 'Monthly', 'dates': ser_dates, 'values': ser_vals, 'reading': ser_vals,
                          'damage': [None] * len(ser_dates), 'phase': [''] * len(ser_dates), 'branch': ['claims'] * len(ser_dates), 'provisional': False},
               'nber': nb, 'episodes': eps, 'announcements': ann, 'notcalled': notcalled,
               'sahm': {'dates': [k for k in cid if k[:7] >= '1979-01'], 'values': [ci[k][0] for k in cid if k[:7] >= '1979-01']}, 'sahm_other': [],
               'through': {'claims': ic.dropna().index.max().strftime('%Y-%m-%d')}, 'notes': {},
               'now': dict(d['now'], last_month=ser_dates[-1][:7] if ser_dates else d['now']['last_month']), 'signal_on': _live(LASTD),
               'record': rec, 'calls_view': calls_view, 'claims': {'dates': ser_dates, 'values': ser_claims}, 'rule': {'dates': ser_dates, 'values': ser_rule}}
    ALL[st].update({'episodes': [], 'announcements': [], 'notcalled': [], 'calls_view': [], 'record': {}, 'claims': {'dates': [], 'values': []}, 'rule': {'dates': [], 'values': []}, 'signal_on': False})
import collections as _co
# A171 (14 Nov 2026): the three-stage real-time chronology on the page (A173 episodes and final dates; out/realtime_chronology_final_a173_1032.csv)
_T3 = pd.read_csv(os.path.join(OUT, 'realtime_chronology_final_a173_1032.csv')); _nz = lambda v: None if v != v or v is None else str(v)[:10]
for _k in ALL: ALL[_k]['dg'] = {'census': _V4L['through'], 'rt': _V4L['unemployment_through'][_k]}
for _k in ALL: ALL[_k]['chron'] = [{'announced': _nz(r.announced), 'prov_start': _nz(r.prov_start), 'final_start': _nz(r.final_start), 'final_start_day': _nz(r.final_start_day), 'end_announced': _nz(r.end_announced), 'prov_trough': _nz(r.prov_trough), 'final_trough': _nz(r.final_trough), 'final_end_day': _nz(r.final_end_day), 'grade': (None if r.grade != r.grade else float(r.grade))} for r in _T3[_T3.st == _k].sort_values('announced').itertuples()]
json.dump({'counts': dict(_co.Counter(x['view'] for v in ALL.values() for x in v['calls_view'])), 'per_state': {k: v['calls_view'] for k, v in ALL.items()}},
          open(os.path.join(OUT, 'calls_view_1032.json'), 'w'), indent=1)
# ---------- the page: the national page, transformed ----------
h = nat
def rep(old, new, count=1):
    global h
    n = h.count(old)
    assert n == count, (n, old[:90])
    h = h.replace(old, new)
rep('<title>Bristow-Hall Business Cycle Program — Real-Time Bristow-Hall Rule Recession Indicator</title>',
    '<title>Bristow-Hall Business Cycle Program — State Recession Chronology and Damage Grade</title>')
rep('<a href="/detector/" aria-current="page">Recession Indicator</a>', '<a href="/detector/">Recession Indicator</a>')
rep('<a href="/state-onset/">State Recession</a>', '<a href="/state-onset/" aria-current="page">State Recession</a>')
h1 = re.search(r'(<h1 id="series"><span class="star">.*?</span>)Real-time Bristow-Hall Rule Recession Indicator <span class="id">\(BHRREALTIME\)</span></h1>', h, flags=re.S)
assert h1
PICK = ('<span class="dd stp"><button class="btn" id="stbtn" type="button" aria-haspopup="true" aria-expanded="false"><span id="stname"></span>'
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>'
        '<span class="menu" id="stmenu" hidden role="menu"></span></span>')
h = h.replace(h1.group(0), h1.group(1) + '<span id="h1t">State Recession Chronology and Damage Grade</span> <span class="id" id="h1c"></span>' + PICK + '</h1>')
rep('<div class="unt"><div class="lab">Units:</div>Index,<br>1.00 = recession, 0&ndash;10 damage</div>',
    '<div class="unt"><div class="lab">Units:</div>Damage grade,<br>0 to 10</div>')
notes_old = h[h.index('<h2>Notes</h2>'):h.index('<h2>How fast the rule speaks')]
NOTES = ('<h2>Notes</h2>\n<div class="notes">\n'
 '  <p class="kv"><b>Source:</b> <a href="https://www.marshall.usc.edu/personnel/duke-bristow" target="_blank" rel="noopener">Bristow, Duke</a> and <a href="https://www.linkedin.com/in/anthonyhall-/" target="_blank" rel="noopener">Hall, Anthony</a> &nbsp;&nbsp;&nbsp; <b>Release:</b> <a>State Recession Chronology and Damage Grade</a></p>\n'
 '  <p class="kv"><b>Units:</b> Damage grade, 0 to 10: labor and output, Great Depression = 10</p>\n'
 '  <p class="kv"><b>Data through:</b> <span id="ver"></span></p>\n'
 '  <p class="kv"><b>Frequency:</b> <span id="freq2"></span></p>\n'
 '  <p class="kv"><b>Notes:</b></p>\n'
 '  <p>Shaded: recessions (damage grade 2.0 or more). Lined: disturbances (below 2.0). Each state is dated as the nation is: a fall of the Philadelphia Fed&rsquo;s state coincident index against its trend. Shading starts when damage starts. A period under way, or ended within 24 months, is provisional. &ldquo;Jobless recovery&rdquo; marks a disturbance within 24 months after a national recession, as in 2002&ndash;03.</p>\n'
 '  <p>Damage grade: the mean of the national labor and output scores (Great Depression = 10). Index through <span id="dgc"></span>; unemployment rate through <span id="dgr"></span>. The District of Columbia is not covered.</p>\n'
 '  <p class="kv"><b>Citation:</b></p>\n  <p id="cite"></p>\n</div>\n\n'
 '<h2>Chronology: recessions and disturbances</h2>\n<div class="notes">\n  <p>Newest first. Start: the first month with damage. End: the month the index reached its low against trend.</p>\n  <table class="calls" id="epis"><thead><tr><th>Class</th><th>Start</th><th>End</th><th>Damage, 0 to 10</th><th>Rise in the unemployment rate</th><th>Fall against trend</th></tr></thead><tbody></tbody></table>\n</div>\n\n')
h = h.replace(notes_old, NOTES)
rep("<h2>How fast the rule speaks: the rule's call against the NBER's announcement</h2>", "<h2>How fast the rule speaks: the rule's call against the state's recessions</h2>")
# 13 Nov 2026 (Anthony 12:21 PT: the speed section did not line up with the graph): the state rule only calls, it has no day it turns off, so the trough panel
# (which plotted the call day against the trough) is removed; and every call of the rule is drawn on the graph as a dashed line, so the panel and the graph show the same days.
_m1 = re.search(r"'<line x1=\"'\+ml\+'\" x2=\"'\+\(W-mr\)\+'\" y1=\"'\+ysL\(1\)\.toFixed\(1\)\+'\" y2=\"'\+ysL\(1\)\.toFixed\(1\)\+'\" stroke=\"#111111\" stroke-width=\"1\.3\"/>'", h); assert _m1; h = h.replace(_m1.group(0), "''")   # the 1.00 line belonged to the old index; the damage grade has no line
rep('<div class="speed" id="speed">', '<div class="speed" id="speed" style="grid-template-columns:minmax(0,580px)">')
rep('<div class="pan"><h3>Troughs', '<div class="pan" style="display:none"><h3>Troughs')
# 14 Nov 2026 (Anthony 00:21 PT): the dashed call lines are taken off the graph
# 1159 (20 Nov 2026): a State whose newest month holds no grade yet (the October rate was out at BLS, the October payrolls not) stopped the whole page
# ("Cannot read properties of null (reading 'toFixed')"; 24 States failed the render check in run 44766448481). The line now shows the newest month that holds a grade.
rep("$('#obs').innerHTML=(ld.length>7?fmtD(ld):fmtM(ld))+': <b>'+lv.toFixed(2)+'</b>'",
    "$('#obs').innerHTML=(()=>{ let k=N-1; while(k>0&&(SER.values[k]===null||SER.values[k]===undefined||!isFinite(SER.values[k]))) k--; const d=SER.dates[k], v=SER.values[k]; return (d.length>7?fmtD(d):fmtM(d))+': <b>'+((v===null||v===undefined||!isFinite(v))?'\\u2014':(+v).toFixed(2))+'</b>'; })()")
rep('<p class="sub">Months after the end of the peak month (for 2024, the peak month Paper 1 gives*)</p>', '<p class="sub">Months after the end of the peak month</p>')
rep('<p class="sub">Months after the end of the trough month (for 2024, the trough month Paper 1 gives*)</p>', '<p class="sub">Months after the end of the trough month (the day the rule turned off)</p>')
sahmcite = re.search(r'<p class="sum" style="color:#2e8b57">The Sahm rule:.*?</p>', h, flags=re.S); assert sahmcite; h = h.replace(sahmcite.group(0), '<p class="sum" id="stmiss"></p>')
brcite = re.search(r'<p class="sum" style="color:#1f5fbf">The Bristow Rule:.*?</p>', h, flags=re.S); assert brcite; h = h.replace(brcite.group(0), '')
key = re.search(r'<p class="key" style="padding:0">.*?</p>', h, flags=re.S); assert key
h = h.replace(key.group(0), '<p class="key" style="padding:0"><span><i></i>The rule fired</span><span id="speednote"></span></p>')
# ---------- the script ----------
js_old = m.group(0)
SEL = ('const ALL = ' + json.dumps(ALL, separators=(',', ':')) + ';\n'
       'const ST = (function(){ let k=(location.hash||"").slice(1).toUpperCase(); return ALL[k]?k:"CA"; })();\n'
       'const S = ALL[ST]; const STNAME = S.name; const CODE = S.code;\n')
h = h.replace(js_old, SEL)
rep("const NB=S.nber.filter(r=>r.peak<'2024');", "const NB=S.nber.filter(r=>!r.prov);")
rep("const REF=S.nber.filter(r=>!(r.peak<'2024'));", "const REF=S.nber.filter(r=>r.prov);")
mi = re.search(r"  const _notNB=S\.episodes\.filter.*?\n  // a rule episode.*?\n  const missed=.*?\n", h, flags=re.S); assert mi
h = h.replace(mi.group(0), "  const missed=REF.map(r=>({a:toT(r.peak+'-01'),b:monthEnd(+r.trough.slice(0,4),+r.trough.slice(5,7)),e:null,ref:r}));\n")
lt = re.search(r"  var LINED_TXT=\(function\(\)\{.*?\}\)\(\);\n", h, flags=re.S); assert lt
h = h.replace(lt.group(0), "  var LINED_TXT=missed.length?'Lined: provisional.':'';\n")
rep("""_lg.innerHTML='<a href="https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions">Shaded areas indicate U.S. recessions.</a>'""",
    """_lg.innerHTML='<a href="https://www.philadelphiafed.org/surveys-and-data/regional-economic-analysis/state-coincident-indexes">Shaded areas indicate '+esc(STNAME)+' recessions, lined areas disturbances (Bristow-Hall State Chronology).</a>'""")
rep("let nd=first?first.date:null; const nc=nextClose(now); if(nc&&(!nd||nc<nd)) nd=nc;", "let nd=first?first.date:null;")
rep("<title>BHRREALTIME</title>", "<title>'+CODE+'</title>")
rep("const domL=domain(vis('left'),FMT.log,idxOnly&&!FMT.log);", "const domL=(idxOnly&&!FMT.log)?{lo:0,hi:10,step:2}:domain(vis('left'),FMT.log,idxOnly&&!FMT.log);")   # A188 (Anthony, 14 Nov 2026 05:02 PT): the damage grade is always drawn on 0 to 10, in every state and at every zoom
rep("+'<h1>Real-time Bristow-Hall Rule Recession Indicator (BHRREALTIME)</h1><p>Units: Index, 1.00 = recession, 0&ndash;10 damage</p>",
    "+'<h1>State Recession Chronology and Damage Grade: '+esc(STNAME)+' ('+CODE+')</h1><p>Units: Damage grade, 0 to 10</p>")
rep("const CITE='Bristow, Duke and Hall, Anthony, Real-time Bristow-Hall Rule Recession Indicator [BHRREALTIME], retrieved from the Bristow-Hall System.';",
    "const CITE='Bristow and Hall, State Recession Chronology and Damage Grade: '+STNAME+' ['+CODE+'].';")
lm = re.search(r"  if\(missed\.length\)\{ const lm=missed\.map.*?\.linedmonths'\)\.forEach\(n=>n\.textContent=lm\); \}\n", h, flags=re.S); assert lm
h = h.replace(lm.group(0), '')
cat = re.search(r"  const CAT=\[\n.*?\n  \];\n", h, flags=re.S); assert cat
h = h.replace(cat.group(0), """  const CAT=[
    {code:CODE,name:'State Recession Chronology and Damage Grade: '+STNAME,units:'Damage grade, 0 to 10',native:'Monthly',dates:SER.dates,values:SER.values.map(v=>v===null?null:Math.max(0,v))},
    {code:'PHCI'+ST,name:'Coincident index, '+STNAME+' (Philadelphia Fed)',units:'Index',native:'Monthly',dates:S.sahm.dates,values:S.sahm.values},
    {code:ST+'REC',name:STNAME+' recessions, 1 from the peak month through the trough month',units:'+1 or 0',native:'Monthly',dates:SER.dates,values:SER.dates.map(d=>{const m=d.slice(0,7); return S.nber.some(r=>r.peak<=m&&m<=r.trough)?1:0;})},
  ];
""")
rep("""aria-label="Months after the '+side+' month: the rule\\'s call against the NBER\\'s announcement">""",
    """aria-label="Months after the '+side+' month: the rule\\'s call against the state\\'s recessions">""")
rep("'. Median over the '+scored.length+' recessions the NBER dated: the rule '", "'. Median over the '+scored.length+': the rule '")
# the page's own small script: name, code, picker, now, record, not called
EXTRA = r"""<script>
(function(){
  const $=s=>document.querySelector(s); const MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const fm=s=>MON[+s.slice(5,7)-1]+' '+s.slice(0,4);
  document.title='Bristow-Hall Business Cycle Program — State Recession Chronology and Damage Grade: '+STNAME;
  $('#h1t').textContent='State Recession Chronology and Damage Grade: '+STNAME; $('#h1c').textContent='('+CODE+')'; $('#stname').textContent=STNAME;
  const menu=$('#stmenu'), btn=$('#stbtn');
  Object.keys(ALL).sort((a,b)=>ALL[a].name.localeCompare(ALL[b].name)).forEach(k=>{ const a=document.createElement('a'); a.setAttribute('role','menuitem'); a.textContent=ALL[k].name; a.href='#'+k; if(k===ST) a.setAttribute('aria-current','true');
    a.addEventListener('click',e=>{ e.preventDefault(); if(k===ST){ menu.hidden=true; return; } try{ location.hash=k; }catch(x){} location.reload(); }); menu.appendChild(a); });
  btn.addEventListener('click',e=>{ e.stopPropagation(); const o=menu.hidden; menu.hidden=!o; btn.setAttribute('aria-expanded',String(o)); if(o){ const c=menu.querySelector('[aria-current]'); if(c) c.scrollIntoView({block:'center'}); } });
  document.addEventListener('click',()=>{ menu.hidden=true; btn.setAttribute('aria-expanded','false'); });
  window.addEventListener('hashchange',()=>{ const k=(location.hash||'').slice(1).toUpperCase(); if(ALL[k]&&k!==ST) location.reload(); });
  const te=document.querySelector('#epis tbody'); const nx=m=>{ let y=+m.slice(0,4), k=+m.slice(5,7)+1; if(k>12){ k=1; y++; } return y+'-'+String(k).padStart(2,'0'); };
  (S.nber||[]).slice().reverse().forEach(r=>{ const tr=document.createElement('tr'); [(r.cls==='recession'?'Recession':'Disturbance')+(r.relapse?' (relapse after the '+fm(nx(r.relapse))+' downturn)':'')+(r.open?', under way':''), fm(nx(r.peak)), r.open?'under way':fm(r.trough), r.damage!=null?r.damage.toFixed(1):'no grade (dated by the Philadelphia Fed only)', r.depth!=null?r.depth.toFixed(2)+'%':'—', r.industry||'—'].forEach(t=>{ const td=document.createElement('td'); td.textContent=t; tr.appendChild(td); }); te.appendChild(tr); });
  if(!(S.nber||[]).length){ const tr=document.createElement('tr'); const td=document.createElement('td'); td.colSpan=6; td.textContent='none'; tr.appendChild(td); te.appendChild(tr); }
  te.innerHTML=''; (S.nber||[]).slice().reverse().forEach(r=>{ const tr=document.createElement('tr'); [(r.cls==='recession'?'Recession':'Disturbance')+(r.c2?(r.nested?' (jobless recovery, inside the recession period)':' (jobless recovery)'):'')+(r.open?', under way':'')+(r.pv?' (provisional)':''), fm(nx(r.peak)), r.open?'under way':fm(r.trough), r.damage.toFixed(2), '+'+r.ur.toFixed(1)+' points', r.dev>0?'\u2212'+r.dev.toFixed(2)+' points':'\u2014'].forEach(t=>{ const td=document.createElement('td'); td.textContent=t; tr.appendChild(td); }); te.appendChild(tr); });
  document.querySelectorAll('h2').forEach(x=>{ if(/^How fast the rule speaks/.test(x.textContent)){ let n=x; while(n&&!(n.classList&&n.classList.contains('sitefoot'))&&!(n!==x&&n.tagName==='H2')){ const nxt=n.nextElementSibling; n.style.display='none'; n=nxt; } } });
  if(S.dg){ $('#dgc').textContent=fm(S.dg.census); $('#dgr').textContent=fm(S.dg.rt); }
})();
</script>
"""
i = h.index('<script>'); h = h[:i] + h[i:].replace('</script>', '</script>\n' + EXTRA, 1)
# picker styles
h = h.replace('</style>', '#series{display:flex;align-items:center;flex-wrap:wrap;gap:6px 10px}#series .stp{margin-left:auto;position:relative;font-size:16px}#series .stp .btn{display:inline-flex;align-items:center;gap:8px;font-size:17px;padding:9px 14px;line-height:1.2}#series .stp .menu{position:absolute;right:0;left:auto;top:calc(100% + 6px);max-height:62vh;overflow:auto;min-width:230px;z-index:30}#series .stp .menu a{display:block;white-space:nowrap}#series .stp .menu a[aria-current]{font-weight:700}table.calls{border-collapse:collapse;font-size:15px;margin:4px 0 8px}table.calls th,table.calls td{text-align:left;padding:6px 26px 6px 0;border-bottom:1px solid #e3e6ea}table.calls th{font-weight:700;border-bottom:2px solid #cfd6de}table.calls td.v-confirmed{color:#2e7d32}table.calls td.v-withdrawn{color:#990000}table.calls td.v-pending{color:#6b6b70}table.calls td.v-aftertheend{color:#7a5c00}\n</style>', 1)
rep('function speedPanel(side){', 'function speedPanel(side){ if(!ANN.length) return {rows:[],svg:"",sum:""};')
os.makedirs(os.path.join(WEB, 'state-onset'), exist_ok=True)
open(os.path.join(WEB, 'state-onset', 'index.html'), 'w').write(h)
print('wrote state-onset/index.html', len(h), 'states', len(ALL))
