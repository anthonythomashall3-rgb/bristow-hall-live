"""WALK 88 - THE SAME LADDER, WITH THE TIE-BREAKER AIMED AT ONE MONTH EARLY (16 September 2026).

Pre-registered in PREREG-v349-2026-09-16.md before this was run.

WHAT WALK 86 SHOWED. Dropping legs A, J and F and offering E, S, T, Z in their place cost the 2020
call (fell to leg K, +41 days late) and the 2024 call (fell to core leg X, +3 late), and the walk chose
none of E, S, T or Z anywhere. Withdrawn under its own condition 4. Legs A and F fail the
false-discovery test and are nonetheless the legs the walk-forward procedure selects for 2020 and
2024 -- both facts stand, and the paper reports both.

WHY THE WALK REFUSES LEGS THAT CALL LATER, STATED FOR THE FIRST TIME. The walk takes the MINIMUM of
its objective tuple (walk38, `best=min(ok.values())`). After the count of out-of-window calls, the
next key is the median lead, and leads are negative days. Minimising the median lead means preferring
the EARLIEST calls available. A leg whose contribution is to call a peak at -14 instead of -35 raises
the median toward zero and is refused by construction. Every one of walks 79, 82, 83, 84 and 85
changed the violation window and left this tie-breaker alone; walk 86 offered legs that call late and
watched them refused. This walk changes it: among clean configurations the walk prefers the median lead closest to
thirty days early. The violation key -- any call outside [-92, -1] -- is untouched, so the requirement
is exactly as before; only the preference among records that already satisfy it moves. Walk 87 is the
control with the old tie-breaker.

Ladder, declared: None, A, AY, AYG, AYGJ, AYGJF, AYGJFE, AYGJFES, AYGJFEST, AYGJFESTZ.
Run:  python3 walk88.py 1962 2026 w88"""
import sys, pickle, os, csv
SEARCH_TERMS = ['unemp', 'layoffs', 'laidoff']; os.environ['BHS_SEARCH_TERMS'] = ','.join(SEARCH_TERMS)
_MARK = "# ---- the walk " + "itself"
import pandas as pd, numpy as np

_ROOT = os.path.expanduser('~/Projects/Onset Detector Data')
if not os.path.isdir(_ROOT):
    _ROOT = os.path.expanduser('~/mnt/Onset Detector Data')

_WP = os.path.join(_ROOT, '121_warn_causal_breadth_2026-09-14/out/warn_leg_proposals.csv')
WARN_PROPOSALS = {}
for _r in csv.DictReader(open(_WP)):
    WARN_PROPOSALS.setdefault((int(_r['warnw']), int(_r['warnp'])), []).append(
        (pd.Timestamp(_r['published']), pd.Timestamp(_r['dated'])))
print('WARN leg settings loaded:', {k: len(v) for k, v in sorted(WARN_PROPOSALS.items())}, flush=True)

# ---- the two new legs, at the single settings collection 177 priced clean ----
_C177 = os.path.join(_ROOT, '177_new_legs_priced_2026-09-15/out')

def _load_A():
    """BBKMCOIX six-month cumulative, 5th percentile of trailing 120 months, 60-day lag."""
    p = os.path.join(_ROOT, '177_new_legs_priced_2026-09-15/data/BBKMCOIX.csv')
    d = pd.read_csv(p); c = list(d.columns)
    s = pd.Series(pd.to_numeric(d[c[1]], errors='coerce').values,
                  index=pd.to_datetime(d[c[0]], errors='coerce')).dropna().sort_index()
    x = s.rolling(6).sum()
    line = x.shift(1).rolling(120, min_periods=60).quantile(0.05)
    hit = (x < line) & line.notna()
    out, last = [], None
    for t in x.index[hit]:
        if last is not None and (t - last).days < 540: continue
        out.append((t + pd.Timedelta(days=60), t.to_period('M').to_timestamp())); last = t
    return out

def _load_M():
    """paper-bill spread, 20-day mean over its 95th expanding percentile, gated by the term
    spread below the 2nd percentile of its own expanding history."""
    d = pd.read_csv(os.path.join(_C177, 'leg_M_money_proposals.csv'))
    d = d[(d.mwin == 20) & (d.mq == 95)].copy()
    d['published'] = pd.to_datetime(d['published']); d['dated'] = pd.to_datetime(d['dated'])
    S = os.path.join(_ROOT, '176_financial_leg_conjunction_2026-09-15/data')
    def rd(sid):
        q = pd.read_csv(os.path.join(S, sid + '.csv')); c = list(q.columns)
        z = pd.Series(pd.to_numeric(q[c[1]], errors='coerce').values,
                      index=pd.to_datetime(q[c[0]], errors='coerce')).dropna().sort_index()
        return z[~z.index.duplicated(keep='last')]
    g10, g1 = rd('GS10'), rd('GS1')
    ts = (g10 - g1.reindex(g10.index, method='ffill')).dropna()
    ts.index = ts.index + pd.Timedelta(days=15)
    line = ts.shift(1).expanding(min_periods=120).quantile(0.02)
    out = []
    for _, r in d.iterrows():
        t = r['published']
        pv, pl = ts[ts.index <= t], line[line.index <= t]
        if len(pv) and len(pl) and pd.notna(pl.iloc[-1]) and float(pv.iloc[-1]) <= float(pl.iloc[-1]):
            out.append((t, r['dated']))
    return out

def _load_generic(sid, coll, transform, q, win, lag_days, gate=None, gq=None):
    """A transmission leg: HIGH = deteriorating, a rolling quantile of its own past, optionally
    gated by the term spread below a quantile of its own expanding history."""
    import numpy as _np
    p = os.path.join(_ROOT, coll, 'data', sid + '.csv')
    d = pd.read_csv(p); c = list(d.columns)
    s = pd.Series(pd.to_numeric(d[c[1]], errors='coerce').values,
                  index=pd.to_datetime(d[c[0]], errors='coerce')).dropna().sort_index()
    s = s[~s.index.duplicated(keep='last')]
    x = transform(s).dropna()
    x.index = x.index + pd.Timedelta(days=lag_days)
    ln = x.shift(1).rolling(win, min_periods=max(20, win // 3)).quantile(q / 100.0)
    hit = (x > ln) & ln.notna()
    out, last = [], None
    for t in x.index[hit]:
        if last is not None and (t - last).days < 540: continue
        out.append((t, t.to_period('M').to_timestamp())); last = t
    if gate is not None:
        S = os.path.join(_ROOT, '176_financial_leg_conjunction_2026-09-15', 'data')
        def _rd(i):
            q2 = pd.read_csv(os.path.join(S, i + '.csv')); cc = list(q2.columns)
            z = pd.Series(pd.to_numeric(q2[cc[1]], errors='coerce').values,
                          index=pd.to_datetime(q2[cc[0]], errors='coerce')).dropna().sort_index()
            return z[~z.index.duplicated(keep='last')]
        g10b, g1b = _rd('GS10'), _rd('GS1')
        ts = (g10b - g1b.reindex(g10b.index, method='ffill')).dropna()
        ts.index = ts.index + pd.Timedelta(days=15)
        gl = ts.shift(1).expanding(min_periods=120).quantile(gq / 100.0)
        keep = []
        for a, b in out:
            pv, pl = ts[ts.index <= a], gl[gl.index <= a]
            if len(pv) and len(pl) and pd.notna(pl.iloc[-1]) and float(pv.iloc[-1]) <= float(pl.iloc[-1]):
                keep.append((a, b))
        out = keep
    return out

_T = '183_transmission_channels_2026-09-15'
# leg H  housing units authorised but NOT STARTED -- an intention withdrawn. 1973 -50, 1980 -51.
_H = _load_generic('AUTHNOTT', _T, lambda s: -s.pct_change(6) * 100, 99, 60, 40, gate='TERM', gq=20)
# leg D  single-family mortgage delinquency. 2007 -63.
_D = _load_generic('DRSFRMACBS', _T, lambda s: s, 95, 60, 120, gate='SAHM', gq=None) \
     if False else _load_generic('DRSFRMACBS', _T, lambda s: s, 95, 60, 120)
# leg O  nondefence capital goods orders falling. 2007 -81.
_O = _load_generic('NEWORDER', _T, lambda s: -s.pct_change(6) * 100, 97, 60, 40)


# ---- leg U: the unemployment rate year on year, FIRST PRINTS, gated by housing starts falling.
# Priced in collection 186 (code/leg_U_gated.py): three firings 1960-2026, zero quiet firings, zero
# firings in the 1965-68 credit crunch, 2001 at -57 and 2007 at -59, and no revised number anywhere in
# it. UNRATE first prints from 1960-03 and HOUST first prints from 1960-07, each dated the day ALFRED
# says it appeared rather than by an assumed lag.
_V186 = os.path.join(_ROOT, '186_realtime_channels_2026-09-15', 'vintages')

def _fp(sid):
    q = pd.read_csv(os.path.join(_V186, sid + '_firstprint.csv'))
    d = pd.to_datetime(q['date'], errors='coerce'); p = pd.to_datetime(q['published'], errors='coerce')
    v = pd.to_numeric(q['value'], errors='coerce'); k = d.notna() & p.notna() & v.notna()
    s = pd.Series(v[k].values, index=d[k]).sort_index()
    pb = pd.Series(p[k].values, index=d[k]).sort_index()
    return s[~s.index.duplicated(keep='first')], pb[~pb.index.duplicated(keep='first')]

def _load_U(pq=95, pwin=60, gq=90, gwin=60, lock=540):
    import numpy as _np
    U, UPUB = _fp('UNRATE'); HS, HSPUB = _fp('HOUST')
    x = (U.pct_change(12) * 100).dropna()
    ln = x.shift(1).rolling(pwin, min_periods=max(6, pwin // 2)).quantile(pq / 100.0)
    hit = (x > ln) & ln.notna()
    g = (-HS.pct_change(12) * 100).dropna()
    # The lockout is applied to the UNGATED proposals and the gate filters what survives it. That is
    # the order collection 186 priced the leg in; applying the gate first and the lockout afterwards
    # lets a suppressed proposal re-arm the clock and gives eight firings instead of three.
    prop, last = [], None
    for t in x.index[hit]:
        if last is not None and (t - last).days < lock: continue
        a = UPUB.get(t)
        if a is None or pd.isna(a): continue
        prop.append((pd.Timestamp(a), t)); last = t
    out = []
    for a, t in prop:
        # the gate, answered with only the starts figures published by that day
        idx = [u for u in g.index if pd.notna(HSPUB.get(u)) and pd.Timestamp(HSPUB.get(u)) <= a]
        gs = g.reindex(idx).sort_index()
        if len(gs) < max(24, gwin): continue
        hist = gs.iloc[:-1].tail(gwin)
        if len(hist) < max(6, gwin // 2): continue
        if float(gs.iloc[-1]) <= float(_np.quantile(hist.values, gq / 100.0)): continue
        out.append((a, t.to_period('M').to_timestamp()))
    return out


# ---- THE MECHANISM LEGS. Chosen by the frozen screen of 573 channels in collection 186, not by trying
# ---- them here. Each is a conjunction in the episode form: a cause-side proposer held open, conjoined
# ---- with a causally different confirmer held open, and the day each episode of the conjoined state
# ---- opens is one leg proposal. Every setting below is the one the screen recorded; nothing is
# ---- re-tuned here, and the leg letters G, J and F were checked against the core's (B C I K L U V W X)
# ---- before pricing, not after.
_D186 = os.path.join(_ROOT, '186_realtime_channels_2026-09-15')
_IDX = pd.date_range('1946-01-31', '2026-09-30', freq='D')

def _rd186(sid):
    import numpy as _np
    for d in ('data', 'data_highfreq', 'data_nber'):
        p = os.path.join(_D186, d, sid + '.csv')
        if os.path.exists(p):
            q = pd.read_csv(p); c = list(q.columns)
            z = pd.Series(pd.to_numeric(q[c[1]], errors='coerce').values,
                          index=pd.to_datetime(q[c[0]], errors='coerce')).dropna().sort_index()
            return z[~z.index.duplicated(keep='last')]
    return None

def _fp186(sid):
    p = os.path.join(_D186, 'vintages', sid + '_firstprint.csv')
    if not os.path.exists(p): return None, None
    q = pd.read_csv(p)
    d = pd.to_datetime(q['date'], errors='coerce'); pb = pd.to_datetime(q['published'], errors='coerce')
    v = pd.to_numeric(q['value'], errors='coerce'); k = d.notna() & pb.notna() & v.notna()
    z = pd.Series(v[k].values, index=d[k]).sort_index(); b = pd.Series(pb[k].values, index=d[k]).sort_index()
    return z[~z.index.duplicated(keep='first')], b[~b.index.duplicated(keep='first')]

def _as_of(sid, fn):
    """First prints dated by their actual publication day where they exist; otherwise the current file
    with the frequency's publication lag charged. Identical to collection 186's `as_of`."""
    import numpy as _np
    def _sp(z):
        return float(_np.median(_np.diff(z.index.values).astype('timedelta64[D]').astype(int))) if len(z) > 8 else 30.0
    z, pb = _fp186(sid)
    if z is not None and len(z) > 60:
        sp = _sp(z); k = max(1, int(round(182.0 / max(sp, 1))))
        x = fn(z, k).replace([_np.inf, -_np.inf], _np.nan).dropna()
        idx, vals = [], []
        for t, vv in x.items():
            aa = pb.get(t)
            if aa is None or pd.isna(aa): continue
            idx.append(pd.Timestamp(aa)); vals.append(vv)
        if len(idx) > 60:
            y = pd.Series(vals, index=idx).sort_index()
            return y[~y.index.duplicated(keep='first')], max(1, int(round(365.0 / max(sp, 1))))
    z = _rd186(sid)
    if z is None or len(z) < 60: return None, None
    sp = _sp(z); k = max(1, int(round(182.0 / max(sp, 1))))
    x = fn(z, k).replace([_np.inf, -_np.inf], _np.nan).dropna()
    if len(x) < 60: return None, None
    lag = 1 if sp <= 3 else (12 if sp <= 10 else (40 if sp <= 45 else 120))
    x.index = x.index + pd.Timedelta(days=lag)
    return x, max(1, int(round(365.0 / max(sp, 1))))

def _daily186(b): return b.reindex(_IDX.union(b.index)).ffill().reindex(_IDX).fillna(False).astype(bool)
def _hold186(b, d): return b.rolling(d, min_periods=1).max().astype(bool)
def _overq186(x, q, win):
    ln = x.shift(1).rolling(win, min_periods=max(10, win // 2)).quantile(q / 100.0)
    return (x > ln) & ln.notna()
def _episodes186(fire, minexp=9):
    out, armed, last = [], True, None
    for t, f in fire.items():
        if armed and f: out.append(t); armed = False; last = t
        elif not armed and last is not None and (t - last).days >= minexp * 30 and not f: armed = True
    return out

_YOY_UP   = lambda z, k: z.pct_change(2 * k) * 100
_CONF186 = {
 'starts_falling': ('HOUST',  lambda z, k: -z.pct_change(2 * k) * 100),
 'hours_falling':  ('AWHMAN', lambda z, k: -z.diff(k)),
}
def _load_state_leg(sid, dfn, pq, pwy, phold, cname, cq, cwy):
    x, ny = _as_of(sid, dfn)
    csid, cfn = _CONF186[cname]
    cx, cny = _as_of(csid, cfn)
    if x is None or cx is None: return []
    P = _hold186(_daily186(_overq186(x, pq, max(12, int(pwy * ny)))), phold)
    C = _hold186(_daily186(_overq186(cx, cq, max(12, int(cwy * cny)))), 270)
    return [(t, t.to_period('M').to_timestamp()) for t in _episodes186(P & C)]

# leg G  financial plumbing: total borrowings from the Federal Reserve. 1973 -44, 2007 -81. Two firings.
_G = _load_state_leg('BORROW', _YOY_UP, 95, 10, 180, 'starts_falling', 95, 20)
# leg J  money: M1 year on year. 1973 -44, 1981 -81. Three firings. 1981 is the thinnest peak in the screen.
_J = _load_state_leg('M1SL', _YOY_UP, 95, 10, 180, 'starts_falling', 95, 20)
# leg F  business formation: applications with planned wages. Scored call: 2020 -86. Two firings.
_F = _load_state_leg('WBUSAPPWNSAUS', _YOY_UP, 95, 20, 180, 'hours_falling', 90, 20)



# The leg-letter check that walk 73 did not have. Walk 73 named a new leg U, the core already used U,
# `legs[_L] = _keep` silently overwrote it, and a 9-of-9 record had to be VOIDED because it could not
# be attributed. Assert first, price second.
_CORE_LETTERS = set('BCIKLUVWX')
_USED_LETTERS = set('AMNHDOYGJFPQR')
_NEW86 = set('ESTZ')
assert not (_NEW86 & _CORE_LETTERS), 'leg letter collides with the core: %s' % sorted(_NEW86 & _CORE_LETTERS)
assert not (_NEW86 & _USED_LETTERS), 'leg letter already used by an amendment: %s' % sorted(_NEW86 & _USED_LETTERS)

# ---- WALK 86'S VETTED LEGS. Same episode form as G, J and F: a cause-side proposer held open,
# ---- conjoined with a causally different confirmer held open, each episode opening one proposal.
# ---- What is new is only that the horizon over which a channel is read, and the confirmer's hold,
# ---- are part of the configuration rather than fixed at 182 days and 270 days. Every setting below
# ---- is the one the screen recorded. Nothing is re-tuned here.
def _as_of_h(sid, fn, horizon):
    """`_as_of`, with the change interval as an argument instead of hard-coded at 182 days."""
    import numpy as _np
    def _sp(z):
        return float(_np.median(_np.diff(z.index.values).astype('timedelta64[D]').astype(int))) if len(z) > 8 else 30.0
    z, pb = _fp186(sid)
    if z is not None and len(z) > 60:
        sp = _sp(z); k = max(1, int(round(horizon / max(sp, 1))))
        x = fn(z, k).replace([_np.inf, -_np.inf], _np.nan).dropna()
        a = pd.to_datetime(pd.Series(pb).reindex(x.index), errors='coerce')
        m = a.notna().values
        if int(m.sum()) > 60:
            y = pd.Series(x.values[m], index=pd.DatetimeIndex(a.values[m])).sort_index()
            return y[~y.index.duplicated(keep='first')], max(1, int(round(365.0 / max(sp, 1))))
    z = _rd186(sid)
    if z is None or len(z) < 60: return None, None
    sp = _sp(z); k = max(1, int(round(horizon / max(sp, 1))))
    x = fn(z, k).replace([_np.inf, -_np.inf], _np.nan).dropna()
    if len(x) < 60: return None, None
    lag = 1 if sp <= 3 else (12 if sp <= 10 else (40 if sp <= 45 else 120))
    x = x.copy(); x.index = x.index + pd.Timedelta(days=lag)
    return x, max(1, int(round(365.0 / max(sp, 1))))

_RISE   = lambda z, k: z.diff(k)
_FALL   = lambda z, k: -z.diff(k)
_PCTUP  = lambda z, k: z.pct_change(k) * 100
_PCTDN  = lambda z, k: -z.pct_change(k) * 100
_CONF86 = {
 'starts_falling':     ('HOUST',  _PCTDN),
 'hours_falling':      ('AWHMAN', _FALL),
 'ip_falling':         ('INDPRO', _PCTDN),
 'layoff_rate_rising': ('M0852BUSM497NNBR', _RISE),
}
def _load_leg86(sid, dfn, ph, pq, pwy, phold, cname, ch, cq, chold):
    x, ny = _as_of_h(sid, dfn, ph)
    csid, cfn = _CONF86[cname]
    cx, cny = _as_of_h(csid, cfn, ch)
    if x is None or cx is None: return []
    P = _hold186(_daily186(_overq186(x, pq, max(12, int(pwy * ny)))), phold)
    C = _hold186(_daily186(_overq186(cx, cq, max(12, int(10 * cny)))), chold)
    return [(t, t.to_period('M').to_timestamp()) for t in _episodes186(P & C)]

# leg E  Federal Reserve total resources and assets. 337x against forty fake chronologies, P=0.000.
_E = _load_leg86('TOTRA', _PCTDN, 182, 97, 10, 180, 'starts_falling', 273, 95, 135)
# leg S  cash assets of all commercial banks. 680x, P=0.000. H.8 family passes 11 of 14.
_S = _load_leg86('CASACBW027NBOG', _PCTDN, 182, 97, 20, 90, 'ip_falling', 182, 95, 135)
# leg T  industrial production of durable consumer goods. 111x, P=0.000.
_T86 = _load_leg86('IPDCONGD', _PCTDN, 273, 95, 20, 180, 'starts_falling', 91, 90, 135)
# leg Z  total borrowings of depository institutions from the Federal Reserve. 118x, P=0.000.
_Z = _load_leg86('TOTBORR', _RISE, 273, 95, 10, 180, 'starts_falling', 91, 90, 270)

NEW_LEGS = {'G': _G, 'J': _J, 'F': _F, 'Y': _load_U(), 'A': _load_A(), 'M': _load_M(), 'H': _H, 'D': _D, 'O': _O, 'E': _E, 'S': _S, 'T': _T86, 'Z': _Z}
print('leg proposals:', {k: len(v) for k, v in NEW_LEGS.items()}, flush=True)

_hdr = open('walk54.py').read().split(_MARK)[0].replace("walk54_%s.out", "walk88_%s.out")
_old = "    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)"
assert _hdr.count(_old) == 1
_new = _old + """
    def _bars_from(turns):
        bars = []; op = None
        for x in turns:
            if x['kind'] == 'peak' and op is None:
                op = x['published']
            elif x['kind'] == 'trough' and op is not None:
                bars.append((op, x['published'] + pd.DateOffset(months=18))); op = None
        if op is not None:
            bars.append((op, pd.Timestamp('2100-01-01')))
        return bars
    _added = False
    # THE ARMING BAR, AS STATED RATHER THAN AS PREVIOUSLY IMPLEMENTED. Every pre-registration since
    # v3.36 says a leg "may accelerate a call the rule is already leaning towards -- it may never open
    # an episode by itself." The implementation only refused a proposal while the record was open or
    # within eighteen months of a close, which is a different and weaker thing: with the record closed
    # since September 2024, leg N's proposal of 28 April 2026 was not barred, and it opened an episode
    # on its own. That unclosed 2026 record is what withdrew walks 68, 71 and 72.
    # A leg proposal is now kept only if the CORE chronology -- the one built without any leg -- opens
    # within four hundred days AFTER it. The leg can move a call the core already makes earlier. It
    # cannot make a call the core does not make.
    _core_opens = [x['published'] for x in turns if x['kind'] == 'peak']
    def _accelerates(a_):
        return any(0 <= (o - a_).days <= 400 for o in _core_opens)
    if p.get('warnw'):
        _prop = WARN_PROPOSALS.get((p['warnw'], p['warnp']), [])
        if _prop:
            _bars = _bars_from(turns)
            _keep = [(a, b) for a, b in _prop
                     if not any(s <= a <= e for s, e in _bars) and _accelerates(a)]
            if _keep:
                legs['N'] = _keep; _added = True
    for _L in (p.get('newlegs') or ''):
        _prop = NEW_LEGS.get(_L, [])
        if _prop:
            _bars = _bars_from(turns)
            _keep = [(a, b) for a, b in _prop
                     if not any(s <= a <= e for s, e in _bars) and _accelerates(a)]
            if _keep:
                legs[_L] = _keep; _added = True
    if _added:
        with contextlib.redirect_stdout(io.StringIO()): turns = B.american_chronology(legs, TL)"""
_hdr = _hdr.replace(_old, _new)
exec(_hdr)

EARLY = 92

def obj(vw):
    v, w = vw
    # THE TIE-BREAKER, CHANGED FOR THE FIRST TIME. The first key is untouched: any call outside
    # [-92, -1] is a violation and the walk still takes the minimum. But among clean configurations
    # the walk now prefers the one whose median lead is CLOSEST TO THIRTY DAYS EARLY, not the one whose
    # median lead is most negative. Walks 79-85 never touched this key, and it is the reason a leg that
    # calls a peak at -14 instead of -35 was refused every time it was offered.
    TARGET = -30.0
    a = (sum(1 for x in v if x > -1 or x < -92), abs(float(np.median(v)) - TARGET), abs(float(np.mean(v)) - TARGET))
    if not w: return a + (0, 0.0, 0.0)
    return a + (sum(1 for x in w if x > 31 or x < 0),
                float(np.median([abs(x) for x in w])), float(np.mean([abs(x) for x in w])))

GRID = [(n, [0.60, 0.55, 0.50, 0.45, 0.35, 0.30, 0.25, 0.20, 0.15]) if n == 'low' else (n, g) for n, g in GRID]
GRID = GRID + [('warnw', [26, 13, None]), ('warnp', [95, 90, 85]), ('newlegs', [None, 'A', 'AY', 'AYG', 'AYGJ', 'AYGJF', 'AYGJFE', 'AYGJFES', 'AYGJFEST', 'AYGJFESTZ'])]
NAMES = [n for n, _ in GRID]; GD = dict(GRID)
BASE15 = dict(BASE15); BASE15.update(warnw=None, warnp=90, newlegs=None)

exec(open('walk39.py').read().split(_MARK)[1].split("\n", 1)[1])
