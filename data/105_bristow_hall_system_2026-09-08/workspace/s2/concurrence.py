# s2/concurrence.py -- THE CONCURRENCE BRANCH (v3.68, 22 September 2026; collections 300 and 301).
# Executed by bhs_build.py in the walk preamble's namespace (it reads spl, gm, RT, SI, SW, BR, ICfp, rel_iu, rel_ic,
# rel_state, _tenths, cosign, EPS, MED_W, ALPHA, leg_gapL_cx, leg_ic_cx from there). Nothing here is fitted anew.
#
# A labour proposal - U (the insured rate over its rolling low, co-signed), L (over its 52-week low, window re-arm),
# I (initial claims), W and V (the survey-week rate), B (state breadth) and, before 1971, the monthly and weekly forms of
# U and L - at the labour core's own lines is confirmed on the first day, from its publication to the end of its
# confirmation window (the dated month + 4), on which the activity picture ACT(0.010) holds AND the proposal's own
# object, as published that day, still stands at the line it crossed. ACT(0.010) is the activity opener's four
# conditions with the production line at 0.010 (s2/activity_opener.py writes its days to out/activity_picture_days.csv).
# The branch was walked from 1956 (production line from [None, 0.015, 0.010], 0.010 at every cut; leave-one-out on all
# 13 recessions unchanged): PREREG and RECORD-the-four-round2-2026-09-22, collection 300, amendment A2.
#
# The engine below is collection 276's mech.py engine (_core, _prep, _wrap, the leg functions, _still and the E17c
# clause of _confirm) with every other mechanism off - verbatim arithmetic, so the branch's history reproduces the walk
# (check 2 of PREREG-v368-port-2026-09-22).
import numpy as _cbnp, pandas as _cbpd

CB_LINE = 0.010                      # the production line of ACT (walked; 0.010 at every cut 1956-2026)
CB_BACK, CB_FWD = 6, 4               # the confirmation window of the labour core (dated month - 6 .. + 4); ACT uses + 4

def _cb_mo(t): return _cbpd.Timestamp(t.year, t.month, 1)
_CB_UB = leg_gapL_cx.__defaults__[0]            # the co-sign bands are the live leg functions' own default arguments
_CB_IB = leg_ic_cx.__defaults__[0]
assert leg_ic_cx.__defaults__[1] == 52, 'leg_ic_cx look default is not 52'

def _cb_core(tt, vv, pubs, months, line, band=None, rearm='zero', cmp_eps=EPS, zero_eps=EPS):
    out = []; armed = True; last = None; n = len(tt)
    for i in range(n):
        v = vv[i]; t = tt[i]; L = line
        if armed and v >= L - cmp_eps:
            if band is not None and not (v >= L + band - cmp_eps or cosign(pubs[i])):
                continue
            out.append((pubs[i], months[i], L)); armed = False; last = t
        elif not armed:
            if rearm == 'zero':
                if v <= zero_eps: armed = True
            elif rearm == 'window':
                if v < L - cmp_eps and t >= last + _cbpd.DateOffset(months=4): armed = True
            elif rearm == 'half':
                if v < line * 0.5: armed = True
    return out

def _cb_prep(gap, pubf, monthf):
    tt = list(gap.index); vv = _cbnp.asarray(gap.values, dtype=float)
    pubs = [pubf(t) for t in tt]; months = [monthf(t) for t in tt]
    pa = _cbnp.array([_cbnp.datetime64(d) for d in pubs]); o = _cbnp.lexsort((_cbnp.arange(len(pa)), pa))
    return tt, vv, pubs, months, (pa[o], vv[o])

def _cb_wrap(props, SO, ce, who): return [(d, m, (SO, L, ce), who) for d, m, L in props]
_CB_PM = {}
def _cb_pm(key, thunk):
    v = _CB_PM.get(key)
    if v is None: v = thunk(); _CB_PM[key] = v
    return list(v)

def _cb_legU(line, look):
    def f():
        gap = _tenths(spl - spl.rolling(look, min_periods=look).min().shift(1)).dropna()
        tt, vv, pubs, months, SO = _cb_prep(gap, rel_iu, _cb_mo)
        return _cb_wrap(_cb_core(tt, vv, pubs, months, line, band=_CB_UB, rearm='zero'), SO, EPS, 'U')
    return _cb_pm(('U', line, look), f)
def _cb_legL(line):
    def f():
        gap = _tenths(spl - spl.rolling(52, min_periods=52).min().shift(1)).dropna()
        tt, vv, pubs, months, SO = _cb_prep(gap, rel_iu, _cb_mo)
        return _cb_wrap(_cb_core(tt, vv, pubs, months, line, rearm='window'), SO, EPS, 'L')
    return _cb_pm(('L', line), f)
def _cb_legI(pct):
    def f():
        m4 = ICfp.rolling(4).mean(); low = m4.rolling(52, min_periods=52).min().shift(1); med = m4.rolling(MED_W, min_periods=156).median().shift(1)
        rel_ = ((m4 / _cbnp.maximum(low, ALPHA * med) - 1) * 100).dropna()
        tt, vv, pubs, months, SO = _cb_prep(rel_, rel_ic, _cb_mo)
        return _cb_wrap(_cb_core(tt, vv, pubs, months, pct, band=_CB_IB, rearm='zero'), SO, EPS, 'I')
    return _cb_pm(('I', pct), f)
def _cb_legSV(line, rearm):
    def f():
        gap = _tenths(SI - SI.rolling(52, min_periods=52).min().shift(1)).dropna()
        tt, vv, pubs, months, SO = _cb_prep(gap, lambda t: rel_iu(SW[t]), lambda t: t)
        return _cb_wrap(_cb_core(tt, vv, pubs, months, line, rearm=rearm), SO, EPS, 'W' if rearm == 'zero' else 'V')
    return _cb_pm(('SV', line, rearm), f)
def _cb_legB(share):
    def f():
        tt, vv, pubs, months, SO = _cb_prep(BR, rel_state, _cb_mo)
        return _cb_wrap(_cb_core(tt, vv, pubs, months, share, rearm='half'), SO, EPS, 'B')
    return _cb_pm(('B', share), f)
def _cb_legF(line, is_u):
    def f():
        stop = _cbpd.Timestamp('1971-01-01'); who = 'U' if is_u else 'L'
        g = gm.round(9)
        tt, vv, pubs, months, SO = _cb_prep(g, lambda m: _cbpd.Timestamp(m.year, m.month, 1) + _cbpd.DateOffset(months=1) + _cbpd.Timedelta(days=9), lambda m: m)
        a = [x for x in _cb_wrap(_cb_core(tt, vv, pubs, months, line, rearm='window', cmp_eps=0.0, zero_eps=0.0), SO, 0.0, who) if x[1] < stop]
        r_ = _tenths(RT - RT.rolling(52, min_periods=52).min().shift(1)).dropna()
        tt, vv, pubs, months, SO = _cb_prep(r_, rel_iu, _cb_mo)
        b = [x for x in _cb_wrap(_cb_core(tt, vv, pubs, months, line, rearm='zero'), SO, EPS, who) if x[1] < stop]
        return a + b
    return _cb_pm(('F', line, is_u), f)

def _cb_still(info, day):
    (pa, pv), L, ce = info
    k = int(_cbnp.searchsorted(pa, _cbnp.datetime64(day), side='right')) - 1
    return True if k < 0 else bool(pv[k] >= L - ce)

def cb_proposals(p):
    """every labour proposal at configuration p's lines, whole history: (published, dated month, info, proposer)"""
    props = _cb_legU(p['u45'], p['look']) + _cb_legF(p['u45'], True) + _cb_legL(p['low']) + _cb_legF(p['low'], False) + _cb_legI(p['ic'])
    if p.get('wline'): props += _cb_legSV(p['wline'], 'zero')
    if p.get('wline2'): props += _cb_legSV(p['wline2'], 'window')
    if p.get('bshare'): props += _cb_legB(p['bshare'])
    return props

def cb_calls(p, act_days):
    """the branch's calls at configuration p's lines: (call day, dated month of the proposal, proposer). act_days is a
    sorted numpy datetime64 array of the days on which ACT(CB_LINE) holds."""
    out = []
    for x in cb_proposals(p):
        p_, dd = x[0], x[1]
        _wend = _cbnp.datetime64(_cbpd.Timestamp(dd.year, dd.month, 1) + _cbpd.DateOffset(months=CB_FWD) + _cbpd.offsets.MonthEnd(0))
        k = int(_cbnp.searchsorted(act_days, _cbnp.datetime64(_cbpd.Timestamp(p_)), side='left'))
        while k < len(act_days) and act_days[k] <= _wend:
            d = _cbpd.Timestamp(act_days[k])
            if _cb_still(x[2], d): out.append((d, dd, x[3])); break
            k += 1
    return sorted(out, key=lambda z: (z[0], z[2]))
