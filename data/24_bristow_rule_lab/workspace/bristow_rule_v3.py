"""
The Bristow Rule, version 3.

A turning point is the month in which the deviation statistic stops rising.

    D(t) = [ max{ m(t-L), ..., m(t-1) } - m(t) ] / max{ m(t-L), ..., m(t-1) } x 100

where m is an n-month moving average of a pro-cyclical activity series.  The Sahm
indicator is the counter-cyclical twin of D applied to the unemployment rate; the
rule was first written for that series and generalizes to any activity level.

The trough of a contraction is the LATER of
    (a) the month D reaches its maximum, and
    (b) the CENTER month of the run that stays within a band alpha of the
        peak-to-trough amplitude above its low.  The shipped bands are TWELVE per
        cent at the trough and ONE at the peak, and the rule is flat in them: over
        more than 120 combinations of trough band, lookback and smoothing the total
        runs 144 to 147 endpoints of 166, so the setting is not load-bearing.
Clause (b) is what carries the rule across a flat bottom, and it is the same clause
the Economic and Social Research Institute of Japan uses in its own published rule:
"the last month when the historical diffusion index ... stays below the 50-percent
line corresponds to the cyclical trough."

The peak is the mirror: the last month the level stays within a band of its high,
searched over a window that begins no earlier than `peak_cap` months before the
episode's own two-percent crossing, so that the search cannot reach back into an
earlier expansion plateau.

Panels, not series.  Every channel is dated separately and the MEDIAN of the channel
dates is reported.  Dating each channel and taking the median beats building a
composite index and dating that, and beats dating the cross-channel median level;
both alternatives let one large-amplitude channel set the turning point.

Scope.  The rule dates a LEVEL turning point.  Where activity never fell - the depth
screen below - the episode is a growth-cycle event and the same rule must be given
the cyclical component instead of the level.  The two are different objects and the
tool says which one it dated.

The panel is quantities only, and it is the NBER's four criteria and nothing else:
volumes of output and sales, real income, and counts of persons employed.  Sectoral
detail - construction, and the capital / intermediate / durable goods breakdown - was
tested and removed; it adds nothing and costs two turning points.  Merchandise trade
values are not domestic value added and carry the exchange rate and the price level;
passenger car registrations are one product line;
the unemployment rate is a rate rather than a quantity and lags at the trough - the
NBER's own six coincident indicators exclude it for the same reason.  Putting it back,
at both ends or at either end alone, was tested: it is worth at most one turning point
and costs one elsewhere.  With those out, no remaining channel damages the result.

Five ways of choosing the estimator per episode were built and rejected, all losing to
fixed routing by the committee's documented concept: the median of the three
estimators, the estimator with the tightest cross-channel spread, the estimator least
sensitive to leaving one channel out, bagged jackknife dates, and channels weighted by
their leave-one-out accuracy on other episodes.  Equal weight and fixed routing win.

Anthony Hall and Duke Bristow, 2026.
"""
from __future__ import annotations
import math
import numpy as np, pandas as pd

__version__ = '3.0'
# NumPy and pandas are the only requirements.  SciPy is used for the sparse solve
# inside the Hodrick-Prescott filter when it happens to be installed; without it
# hp_trend() takes a dense solve that agrees to floating-point precision.


# ---------------------------------------------------------------- data handling
def load(path):
    """Read a two-column CSV - date, value - into a clean float series.

    Column NAMES are ignored and the first two columns are taken positionally, so a
    file headed date,value and one headed TIME_PERIOD,OBS_VALUE both load.  Values
    that will not parse become missing and are dropped; duplicate dates keep the LAST
    row, which is the convention every one of this program's sources uses when it
    revises a month in place; the index is sorted.
    """
    d = pd.read_csv(path)
    if d.shape[1] < 2:
        raise ValueError(f'{path}: expected at least two columns, found {d.shape[1]}')
    d = d.iloc[:, :2].copy(); d.columns = ['d', 'v']
    d['d'] = pd.to_datetime(d['d'], errors='coerce')
    d['v'] = pd.to_numeric(d['v'], errors='coerce')
    s = d.dropna().set_index('d')['v'].astype(float)
    if s.empty:
        raise ValueError(f'{path}: no rows survived parsing - check the date and value columns')
    return s[~s.index.duplicated(keep='last')].sort_index()

def procyclical(s, kind='level'):
    """Return a pro-cyclical series.  A rate in per cent that RISES in a contraction -
    unemployment is the case that matters - becomes 100 - r, which falls in one.

    `kind` is 'level' or 'rate'.  Anything else is a mistake rather than a default,
    because silently treating a rate as a level inverts the sign of every date this
    module would then produce.
    """
    if kind not in ('level', 'rate'):
        raise ValueError(f"kind must be 'level' or 'rate', not {kind!r}")
    return 100.0 - s if kind == 'rate' else s

def _ma(x, n):
    """Trailing n-month mean; n=1 is the series itself."""
    return x.rolling(n).mean()

# ---------------------------------------------------------------- the statistic
HORIZONS = (-3, 0, 3)   # months either side of `lookback` the statistic averages over


def deviation(x, lookback=12, smooth=3, horizons=None):
    """D(t), in percent below the trailing rolling maximum.

    The twelve-month lookback was always an arbitrary choice, and a turning point a
    twelve-month window sees clearly can be faint to a nine- or fifteen-month one.
    The statistic is therefore averaged over three lookbacks, a quarter either side
    of `lookback`.  Paper 1's own D is the single-horizon member of this family
    (pass horizons=(0,) for it); averaging costs no hits on the eighty-three
    official contractions and cuts the mean trough error from 1.70 months to 1.65.
    Chosen out of sample: leaving each chronology out in turn, the other eight pick
    this spread eight times in nine.
    """
    if not isinstance(x, pd.Series):
        raise TypeError('deviation() takes a pandas Series of LEVELS')
    if smooth < 1 or lookback < 2:
        raise ValueError(f'smooth must be >=1 and lookback >=2, got {smooth} and {lookback}')
    m = _ma(x, smooth)
    # D divides by a trailing maximum, so a level that reaches zero or goes negative
    # makes the statistic meaningless rather than merely noisy.  Say so here, with
    # the offending month, instead of returning an infinity that survives into a date.
    bad = m[(m <= 0) & m.notna()]
    if len(bad):
        raise ValueError(f'the level is non-positive at {bad.index[0]:%Y-%m} '
                         f'({float(bad.iloc[0])!r}); D is undefined on it. '
                         'Convert a rate with procyclical(s, "rate") first.')
    parts = []
    for h in (HORIZONS if horizons is None else horizons):
        w = lookback + h
        if w < 2: continue
        mx = m.shift(1).rolling(w).max()
        parts.append((mx - m) / mx * 100.0)
    if len(parts) == 1: return parts[0]
    return pd.concat(parts, axis=1).mean(axis=1)

def episodes(stat, threshold=2.0, gap=0):
    """Runs in which the statistic stays at or above `threshold`."""
    runs, cur = [], []
    for d, v in stat.dropna().items():
        if v >= threshold: cur.append(d)
        elif cur: runs.append(cur); cur = []
    if cur: runs.append(cur)
    if gap and len(runs) > 1:
        out = [runs[0]]
        for r in runs[1:]:
            if _md(r[0], out[-1][-1]) <= gap: out[-1] = out[-1] + r
            else: out.append(r)
        runs = out
    return runs

def _md(a, b):
    """Whole months from b to a, signed."""
    return (a.year - b.year) * 12 + (a.month - b.month)

# ---------------------------------------------------------------- one channel
PLATEAU_TROUGH = 'mid'   # where in the flat bottom the trough sits
TROUGH_CLAUSE = 'later'    # 'later' = later of D-peak and band center (shipped); 'dpeak' = D-peak alone
DPEAK_SMOOTH = None        # smoothing of the D statistic in clause (a); None = the channel's `smooth` (shipped)
REFINE_TROUGH = (3, 1)     # (back, forward) months: after the smoothed date, move to the level's minimum (trough)
REFINE_PEAK = (1, 0)       # or maximum (peak) inside that window; None = off
REFINE_SMOOTH = None       # one trailing mean for both ends before the refinement search; None = per end:
REFINE_SMOOTH_T = 1        #   the trough is searched on the unsmoothed level,
REFINE_SMOOTH_P = 2        #   the peak on a two-month mean
PLATEAU_PEAK   = 'mid'   # where in the flat top the peak sits
# The growth-cycle route may read its trough plateau differently from the level route:
# two of the three growth-cycle committees (the South African Reserve Bank in its 2023 note,
# Taiwan's National Development Council at its 1998 trough) take the LAST month of a flat
# floor.  None -> the level convention above; 'last' -> the committees' reading.  Test
# switch, off by default; set from the environment as BR_GROWTH_TROUGH=last.
import os as _os
PLATEAU_TROUGH_GROWTH = _os.environ.get('BR_GROWTH_TROUGH') or None
# THE OPENING EDGE (3 September 2026).  The trough clause abstains when the smoothed level's
# minimum sits at the window's CLOSING month (still falling); the peak clause abstains at both
# edges.  Until this date the trough clause said nothing about the OPENING month, so a channel
# rising from a low that IS the window's first month - the tail of the PREVIOUS trough, its
# deviation statistic D at its window maximum there - voted that earlier trough: on the vintage
# of 1 November 1984, in a window opened the month after the route's July 1980 trough date,
# real consumption and real disposable income dated the 1981-82 contraction's trough at May and
# June 1980, before the window itself, and the thin real-time panel's median landed at April
# 1982, seven months early (lab/rt/final_date_rt_windows.log).  The clause now abstains when
# the opening month is both the window's level low and D's maximum ('joint'): the narrowest
# reading of the failure, the mirror of the closing-edge rule the clause already had.
# Measured before adoption (lab/edge_abstain_test.py, refine_bounded_test.py, the 83 of
# tool_check.py, cmp/rulings_heldout.py with BR_TROUGH_EDGE): of the 83 contractions of the
# nine chronologies one end moves - Japan's January 1977 peak, from +1 to +2 months - and of
# the four held-out chronologies' 67 ends none; on the United States none of the 24 moves, and
# the 1981-82 trough, which had rested on the 24-month trim dropping one of two wrong-episode
# votes at 25 months and keeping the other at 23, now rests on the three channels that fell.
# On the American vintages the 1982 trough goes from -7 to exact at six, fourteen and
# twenty-four months and on the committee's own announcement day; the wider labor-heavy
# panel's 1982 reading moves from exact to +1 at two of its four horizons (six voters, later
# middle).  Chosen on the vintage failure and the symmetry, checked on the scores, not chosen
# on them.  The wider readings were measured and declined: 'dpeak' (D's maximum alone at the
# opening month) also moves Spain's 1974-75 contraction (peak Q3 to Q4, exact; trough Q2 to
# Q4), 'both' (the level's low alone) costs three American troughs, 'either' both sets.
# 'end' restores the pre-3 September clause (BR_TROUGH_EDGE=end).
TROUGH_EDGE_ABSTAIN = _os.environ.get('BR_TROUGH_EDGE') or 'joint'


def _plateau_pick(on, where):
    """Which month of the within-band run is the turning point.

    'last' - the last month inside the band - is the reading ESRI publishes for a
    diffusion index, and it is the right one there.  On a level it cannot be
    earlier than the extreme itself and is therefore biased late; taking the
    CENTER of the flat region instead is unbiased by construction and lets the band
    be set wide enough to find the whole plateau rather than its edge.  On the
    eighty-three official contractions this moves the mean error from 1.95 to 1.76
    months at peaks and from 1.93 to 1.67 at troughs, and the late bias at peaks
    from +0.51 months to +0.24.  Chosen out of sample.

    With an even-length run the center falls between two months and the later of the
    two is taken, for the same reason _median() takes the later of two channel dates:
    a turn is called once the evidence has accumulated, not on the first half of it.
    """
    if where not in ('mid', 'last'):
        raise ValueError(f"where must be 'mid' or 'last', not {where!r}")
    if len(on) == 0: return None
    return on.index[-1] if where == 'last' else on.index[len(on) // 2]


def channel_trough(level, w0, w1, band=0.12, smooth=3, lookback=12, abstain=True, where=None, refine=True):
    """Later of the peak of D and the last month within `band` of the low."""
    d = deviation(level, lookback, smooth if DPEAK_SMOOTH is None else DPEAK_SMOOTH)[w0:w1].dropna()
    if len(d) == 0: return None
    d_peak = d.idxmax()
    if TROUGH_CLAUSE == 'dpeak':
        # clause (a) alone: the month the deviation statistic peaked
        if abstain and d_peak == d.index[-1]:
            return None                  # still falling at the edge of the window
        return d_peak
    m = _ma(level, smooth)[w0:w1].dropna()
    if len(m) < 4: return d_peak
    lo = float(m.min()); i = m.idxmin()
    if abstain and i == m.index[-1]:
        return None                      # still falling at the edge of the window
    if abstain and TROUGH_EDGE_ABSTAIN != 'end':
        # the opening edge: 'both' abstains on a level low there; 'dpeak' when the deviation statistic
        # peaks there (the previous contraction's drawdown, not this one's); 'either' on either
        _lo0 = i == m.index[0]; _dp0 = d_peak == d.index[0]
        if ((TROUGH_EDGE_ABSTAIN == 'both' and _lo0) or (TROUGH_EDGE_ABSTAIN == 'dpeak' and _dp0)
                or (TROUGH_EDGE_ABSTAIN == 'either' and (_lo0 or _dp0)) or (TROUGH_EDGE_ABSTAIN == 'joint' and _lo0 and _dp0)):
            return None
    hi = float(m[:i].max())
    amp = max(hi - lo, 1e-9)
    on = m[m <= lo + band * amp]
    p = _plateau_pick(on, PLATEAU_TROUGH if where is None else where)
    t = max(d_peak, p) if p is not None else d_peak
    if (refine and REFINE_TROUGH is not None and smooth > 1
            and (PLATEAU_TROUGH if where is None else where) == 'mid'):
        t = _refine(level, t, REFINE_TROUGH, 'min', w0, w1)   # level clause only; a diffusion index keeps its last-month reading
    return t

# THE REFINEMENT STAYS INSIDE THE WINDOW (3 September 2026).  The refinement clause moved a
# smoothed date to the level's extremum up to three months back, and a date at the window's
# first month was therefore refined to a month BEFORE the window (the May 1980 vote above).  A
# clause asked for a turn inside [w0, w1] must answer inside it.  Alone this change exposed the
# knife-edge described above (the American 1981-82 trough went from +1 to -5 because both
# wrong-episode votes then survived the trim); with the opening-edge abstention it moves no end
# of the 190 scored.  BR_REFINE_BOUNDED=no restores the unbounded search.
REFINE_BOUNDED = (_os.environ.get('BR_REFINE_BOUNDED') or 'yes') == 'yes'

def _refine(level, date, window, kind, w0=None, w1=None):
    rs = REFINE_SMOOTH if REFINE_SMOOTH is not None else (REFINE_SMOOTH_T if kind == 'min' else REFINE_SMOOTH_P)
    """Move a smoothed-series date to the unsmoothed extremum inside `window` months of it.

    A trailing n-month mean lags the extremum it finds by about (n-1)/2 months; the
    unsmoothed series has the month but also the noise.  Bounding the search to a few
    months around the smoothed date keeps the month and drops the noise.

    With REFINE_BOUNDED the search also stays inside the clause's own window [w0, w1]:
    a date the clause found at the window's first month is otherwise refined to a month
    BEFORE the window (real consumption on the vintage of 1 November 1984, window opening
    August 1980, refined to May 1980 - final_date_rt_windows.log).
    """
    back, fwd = window
    x = level if rs <= 1 else _ma(level, rs)
    lo = date - pd.DateOffset(months=back); hi = date + pd.DateOffset(months=fwd)
    if REFINE_BOUNDED:
        if w0 is not None: lo = max(lo, pd.Timestamp(w0))
        if w1 is not None: hi = min(hi, pd.Timestamp(w1))
    seg = x[lo:hi].dropna()
    if len(seg) == 0: return date
    return seg.idxmin() if kind == 'min' else seg.idxmax()

def channel_peak(level, w0, w1, band=0.01, smooth=3, abstain=True, where=None, refine=True):
    """Last month within `band` of the high inside the window."""
    m = _ma(level, smooth)[w0:w1].dropna()
    if len(m) < 4: return None
    hi = float(m.max()); i = m.idxmax()
    if abstain and (i == m.index[0] or i == m.index[-1]):
        return None                      # never turned inside the window
    lo = float(m[i:].min())      # m[i:] always contains i, so this is never empty
    amp = max(hi - lo, 1e-9)
    on = m[m >= hi - band * amp]
    p = _plateau_pick(on, PLATEAU_PEAK if where is None else where)
    p = p if p is not None else i
    if (refine and REFINE_PEAK is not None and smooth > 1
            and (PLATEAU_PEAK if where is None else where) == 'mid'):
        p = _refine(level, p, REFINE_PEAK, 'max', w0, w1)
    return p

# ---------------------------------------------------------------- the panel
def _median(dates, q=0.5):
    """Order statistic of the channel dates; q=0.5 is the median.

    With an even number of dates the median falls between two months and the rule
    has to say which.  It takes the LATER of the two, for the same reason a higher
    q is the direction a committee leans: a turn is called once the slower-moving
    channels confirm it, not on the first half of them.  The choice is made by
    ceiling rather than rounding, so it is the same at every q and does not
    alternate with the parity of the panel.
    """
    ds = sorted(d for d in dates if d is not None)
    if not ds: return None
    if len(ds) == 1: return ds[0]
    i = int(math.ceil(q * (len(ds) - 1) - 1e-9))
    return ds[min(max(i, 0), len(ds) - 1)]

TRIM_MONTHS = 24   # a channel date further than this from the median is dropped


def _trimmed_median(dates_abstain, dates_all, trim=None):
    """The panel date: the median of the channel dates, with far-out votes trimmed.

    Channels that actually turned inside the window are preferred; if none did, every
    channel votes rather than the rule returning nothing.  Then a channel whose date
    is more than two years from the median is dropped and the median retaken - it is
    not describing the same turning point, it has locked onto a different episode
    inside the search window.  Two years is a full cycle by Bry and Boschan's own
    minimum-cycle censoring.  The trim needs at least four voting channels and never
    leaves fewer than two.  It costs no hits on the eighty-three official
    contractions and cuts the mean trough error from 1.65 months to 1.62.  Chosen out
    of sample, and flat from eighteen months to twenty-four.
    """
    t = TRIM_MONTHS if trim is None else trim
    ds = [d for d in dates_abstain if d is not None]
    if not ds: ds = [d for d in dates_all if d is not None]
    d = _median(ds)
    if d is None or t is None or len(ds) < 4: return d
    c = d.year * 12 + (d.month - 1)
    keep = [x for x in ds if abs((x.year * 12 + (x.month - 1)) - c) <= t]
    return _median(keep) if len(keep) >= 2 else d


def spread(dates):
    """First-to-last spread of the channel dates, in months.

    This is the panel's own disagreement about where the turning point is, and it is
    reported with every answer: a date backed by nine channels that agree to two
    months is worth more than the same date backed by nine that disagree by a year.
    None when fewer than two channels dated.
    """
    ds = sorted(d for d in dates if d is not None)
    return None if len(ds) < 2 else _md(ds[-1], ds[0])

def _panel_frame(channels, fn):
    """Build a frame from [(name, series)], one column per channel, names made unique.

    Two channels under one name would silently collapse into a single column and one
    of the two would vanish from every count the answer carries, so duplicates are
    suffixed rather than dropped.
    """
    chs = list(channels)
    if not chs:
        raise ValueError('the panel is empty')
    cols, seen = [], {}
    for nm, s in chs:
        if not isinstance(s, pd.Series):
            raise TypeError(f'channel {nm!r} is not a pandas Series')
        seen[nm] = seen.get(nm, 0) + 1
        cols.append(fn(s).rename(nm if seen[nm] == 1 else f'{nm} ({seen[nm]})'))
    return pd.concat(cols, axis=1, sort=True)


def composite_deviation(channels, lookback=12, smooth=3, min_channels=2, q=0.5):
    """Cross-channel order statistic of D: a depth-and-breadth detector."""
    D = _panel_frame(channels, lambda s: deviation(s, lookback, smooth))
    return D.quantile(q, axis=1).where(D.notna().sum(axis=1) >= min_channels)

def composite_level(channels, min_channels=1):
    """Equal-weight chain-linked activity index from an unbalanced panel.  Averages
    the log changes of whatever channels exist in both months, so a channel that
    begins late costs no history and introduces no jump."""
    D = _panel_frame(channels, lambda s: np.log(s.clip(lower=1e-9)).diff())
    g = D.mean(axis=1, skipna=True).where(D.notna().sum(axis=1) >= min_channels)
    first = g.first_valid_index()
    if first is None:
        raise ValueError(f'no month has {min_channels} channels with a change; '
                         'the panel cannot be chain-linked')
    g = g[first:]
    return np.exp(g.fillna(0.0).cumsum()) * 100.0

def max_drawdown(m):
    """Largest fall from a running maximum, in percent.  Unlike a peak-to-trough fall
    it does not depend on where the window happens to begin."""
    if len(m) < 4: return None
    run = m.cummax()
    if (run <= 0).any():
        raise ValueError('max_drawdown() needs a strictly positive level')
    return -float(((run - m) / run).max()) * 100.0

def depth(volume_channels, w0, w1, smooth=3):
    """Depth of the episode: maximum drawdown of the equal-weight volume composite.
    Rates carry no quantity and merchandise trade values carry prices, so neither
    belongs in this composite."""
    ci = composite_level(volume_channels)
    return max_drawdown(_ma(ci, smooth)[w0:w1].dropna())

# ---------------------------------------------------------------- the rule
def date_episode(channels, w0, w1, volume_channels=None, band_trough=0.03,
                 band_peak=0.02, smooth=3, lookback=12, peak_cap=12,
                 min_depth=2.0, max_spread=9, abstain=True):
    """The level clause on its own.  Use date_turning_points() instead: it always
    returns an answer, this one can return None when nothing turned in the window.

    channels          list of (name, pro-cyclical level series)
    volume_channels   the subset that measures quantities, used for the depth screen
    w0, w1            the search window
    peak_cap          months before the episode's 2 percent crossing at which the
                      peak search may begin

    verdict
      'dated'          a classical contraction, the channels in reasonable agreement
      'low confidence' dated, but the channels disagree by more than max_spread months
      'growth cycle'   activity never fell by min_depth percent, so a level rule
                       cannot date it; give the rule the cyclical component instead
      'no data'        nothing datable in the window
    """
    dt = [channel_trough(s, w0, w1, band_trough, smooth, lookback, abstain)
          for nm, s in channels]
    trough = _median(dt)
    if REFINE_TROUGH is not None:
        _u = _median([channel_trough(s, w0, w1, band_trough, smooth, lookback, abstain, refine=False)
                      for nm, s in channels])
        end = _u if _u is not None else (trough if trough is not None else w1)
    else:
        end = trough if trough is not None else w1

    comp = composite_deviation(channels, lookback, smooth, 1)[w0:end].dropna()
    cross = next((d for d, v in comp.items() if v >= 2.0), None)
    p0 = w0 if (cross is None or peak_cap is None) else max(w0, cross - pd.DateOffset(months=peak_cap))
    dp = [channel_peak(s, p0, end, band_peak, smooth, abstain) for nm, s in channels]
    peak = _median(dp)

    dep = depth(volume_channels or channels, w0, w1, smooth)
    sp_t, sp_p = spread(dt), spread(dp)

    if trough is None and peak is None:
        verdict = 'no data'
    elif dep is not None and dep > -abs(min_depth):
        verdict = 'growth cycle'
    elif (sp_t is not None and sp_t > max_spread) or (sp_p is not None and sp_p > max_spread):
        verdict = 'low confidence'
    else:
        verdict = 'dated'
    return dict(peak=peak, trough=trough, verdict=verdict, depth=dep,
                channels=len(channels), spread_peak=sp_p, spread_trough=sp_t,
                length=None if (peak is None or trough is None) else _md(trough, peak))

# ---------------------------------------------------------------- growth cycles
def hp_trend(y, lam=129600.0):
    """Hodrick-Prescott trend, lambda = 129600 for monthly data (Ravn-Uhlig).

    Solves (I + lam D'D) tau = y, where D is the second-difference operator.  The
    sparse solve is taken when SciPy is installed and a dense one when it is not;
    the two agree to floating-point precision, so the tool has no hard dependency
    beyond NumPy and pandas.
    """
    y = np.asarray(y, float); n = len(y)
    if n < 5: return y.copy()
    if not np.all(np.isfinite(y)):
        raise ValueError('hp_trend() needs a series with no gaps')
    try:
        from scipy.sparse import eye, diags
        from scipy.sparse.linalg import spsolve
        I = eye(n, format='csc')
        D = diags([np.ones(n-2), -2*np.ones(n-2), np.ones(n-2)], [0, 1, 2],
                  shape=(n-2, n), format='csc')
        return spsolve((I + lam * (D.T @ D)).tocsc(), y)
    except ImportError:
        D = np.zeros((n - 2, n))
        rows = np.arange(n - 2)
        D[rows, rows] = 1.0; D[rows, rows + 1] = -2.0; D[rows, rows + 2] = 1.0
        return np.linalg.solve(np.eye(n) + lam * (D.T @ D), y)

def cyclical_component(volume_channels, lam=129600.0, smooth=3):
    """The composite index divided by its own trend, in percent: the object a
    growth-cycle chronology refers to, and the object Statistics Korea dates."""
    ci = composite_level(volume_channels)
    m = np.log(_ma(ci, smooth).dropna())
    return pd.Series(np.exp(m.values - hp_trend(m.values, lam)) * 100.0, index=m.index)

def date_growth_cycle(volume_channels, w0, w1, band=0.03, lam=129600.0,
                      smooth=3, lookback=12, abstain=True):
    """The same rule, given the cyclical component instead of the level."""
    cy = cyclical_component(volume_channels, lam, smooth)
    trough = channel_trough(cy, w0, w1, band, 1, lookback, abstain, where=PLATEAU_TROUGH_GROWTH)
    end = trough if trough is not None else w1
    peak = channel_peak(cy, w0, end, band, 1, abstain)
    return dict(peak=peak, trough=trough, verdict='growth cycle')

# ---------------------------------------------------------------- standalone use
def date_all(channels, volume_channels=None, threshold=2.0, gap=6, min_months=3,
             tail=12, peak_cap=12, **kw):
    """Date every contraction the panel shows, using no official date anywhere."""
    out = []; prev = None
    comp = composite_deviation(channels, kw.get('lookback', 12), kw.get('smooth', 3), 2)
    for e in episodes(comp, threshold, gap):
        if len(e) < min_months: continue
        w0 = e[0] - pd.DateOffset(months=peak_cap)
        if prev is not None: w0 = max(w0, prev + pd.DateOffset(months=1))
        w1 = e[-1] + pd.DateOffset(months=tail)
        r = date_episode(channels, w0, w1, volume_channels, peak_cap=peak_cap, **kw)
        r['episode_start'], r['episode_end'] = e[0], e[-1]
        if r['trough'] is not None: prev = r['trough']
        out.append(r)
    return out

# ------------------------------------------------ the real-time call on claims data
def channel_phase(panel, amplitude=48.0, min_phase=13):
    """A turning point on every channel, computed causally.

    ESRI's historical diffusion index is built by putting a turning point on each
    component series FIRST, setting that series to +1 from its own trough to its own peak
    and -1 from its peak to its own trough, and taking the share at +1.  The index then
    changes only when a component turns, which is what makes a fifty-per-cent crossing
    readable.  Bry and Boschan's procedure is two-sided and cannot be used in real time;
    this is the causal form of the same idea.  A channel stays in its rising phase until
    it has fallen `amplitude` log points from its running maximum AND `min_phase` months
    have passed since its last turn, and in its falling phase until the mirror condition.
    No observation uses anything later than itself.

    `panel` is a DataFrame of LOG levels, one column per channel.  Returns a DataFrame of
    +1 (rising) and -1 (falling) with the same index and columns.
    """
    if not isinstance(panel, pd.DataFrame):
        raise TypeError('channel_phase() takes a DataFrame, one column per channel')
    if panel.shape[1] == 0 or len(panel) == 0:
        raise ValueError('channel_phase() needs a panel with at least one column and row')
    if amplitude <= 0 or min_phase < 0:
        raise ValueError(f'amplitude must be positive and min_phase non-negative, '
                         f'got {amplitude} and {min_phase}')
    _v = panel.values[np.isfinite(panel.values)]
    if _v.size and np.median(np.abs(_v)) > 50.0:
        # The amplitude is in LOG POINTS.  A raw level would make it meaningless, and the
        # mistake is silent: the monitor would simply never turn.  Claims in logs run
        # about 2 to 17; a raw claims count runs to the millions.
        raise ValueError('channel_phase() takes LOG levels; this panel looks like raw '
                         f'levels (median absolute value {np.median(np.abs(_v)):.3g})')
    X = (panel * 100.0).values
    T, N = X.shape
    out = np.zeros((T, N), dtype=np.int8)
    st = np.ones(N, dtype=np.int8)
    ext = np.where(np.isfinite(X[0]), X[0], 0.0).copy()
    since = np.zeros(N, dtype=np.int32)
    for t in range(T):
        x = X[t]; fin = np.isfinite(x); up = st == 1
        np.copyto(ext, np.maximum(ext, x), where=fin & up)
        np.copyto(ext, np.minimum(ext, x), where=fin & ~up)
        fd = fin & up & ((ext - x) >= amplitude) & (since >= min_phase)
        fu = fin & ~up & ((x - ext) >= amplitude) & (since >= min_phase)
        fl = fd | fu
        st = np.where(fd, np.int8(-1), np.where(fu, np.int8(1), st))
        ext = np.where(fl, x, ext); since = np.where(fl, 0, since + 1)
        out[t] = st
    return pd.DataFrame(out, index=panel.index, columns=panel.columns)

def claims_diffusion(panel, amplitude=48.0, min_phase=13):
    """The share of channels in the deteriorating phase, per cent.

    `panel` carries LOG levels of a COUNTER-CYCLICAL series - claims for unemployment
    insurance - so a channel in its rising phase is a labor market getting worse.
    """
    ph = channel_phase(panel, amplitude, min_phase)
    fin = np.isfinite((panel * 100.0).values)
    live = fin.sum(axis=1)
    with np.errstate(invalid='ignore', divide='ignore'):
        share = np.where(live > 0, (ph.values > 0).sum(axis=1) / np.maximum(live, 1) * 100.0,
                         np.nan)
    return pd.Series(share, index=panel.index).dropna()

def _check_diffusion(di, line, phase_min, cycle_min, publication_lag, warmup):
    """Guard the two diffusion clauses: the index is a share in per cent, 0 to 100."""
    if not isinstance(di, pd.Series):
        raise TypeError('the diffusion clauses take a pandas Series of the index')
    if len(di) == 0:
        raise ValueError('the diffusion index is empty')
    v = di.values[np.isfinite(di.values)]
    if v.size and (v.min() < 0.0 or v.max() > 100.0):
        raise ValueError('the diffusion index is a share in per cent and must lie in '
                         f'[0,100]; this one runs {v.min():.3g} to {v.max():.3g}')
    if not 0.0 <= line <= 100.0:
        raise ValueError(f'the line is a share in per cent, got {line}')
    if min(phase_min, cycle_min, publication_lag, warmup) < 0:
        raise ValueError('phase_min, cycle_min, publication_lag and warmup are month '
                         'counts and cannot be negative')


def diffusion_peak_calls(diffusion, line=50.0, run=1, phase_min=5, cycle_min=15,
                         publication_lag=1, warmup=24):
    """When would the rule have said a peak had happened?

    ESRI's clause: the peak is the last month the deteriorating share stood BELOW the
    fifty-per-cent line before it crossed and stayed.  ESRI's censoring: a phase of at
    least five months and a cycle of at least fifteen, which are the third of the three
    criteria the Institute states for setting a date.  `publication_lag` is one month
    because the Department of Labor's ETA 5159 report "is due in the ETA National Office
    on the 15th day of the month following each calendar month to which it relates".

    `warmup` suppresses calls in the first two years of the index.  The phase monitor
    has to start every channel somewhere, and until a channel has had the chance to turn
    once its phase is an assumption rather than a reading; without the warm-up the index
    stands at a hundred per cent in its first month and the detector fires on that.

    Returns a list of (published, dated) month pairs.  Uses no official chronology.
    """
    _check_diffusion(diffusion, line, phase_min, cycle_min, publication_lag, warmup)
    d = diffusion.values; idx = diffusion.index; n = len(d)
    on = d >= line
    if run > 1:
        on = np.convolve(on.astype(int), np.ones(run, dtype=int), 'full')[:n] == run
    lastb = np.maximum.accumulate(np.where(d < line, np.arange(n), 0))
    out = []; i = 0; last = None; state = 0; off = 0
    while i < n:
        if state == 0 and on[i] and i >= warmup:
            pub = idx[i] + pd.DateOffset(months=publication_lag)
            if last is None or (pub.year * 12 + pub.month) - last >= cycle_min:
                j = lastb[i]
                out.append((pd.Timestamp(pub.year, pub.month, 1),
                            pd.Timestamp(idx[j].year, idx[j].month, 1)))
                last = pub.year * 12 + pub.month; state = 1; off = 0
        elif state == 1:
            off = off + 1 if d[i] < line else 0
            if off >= phase_min: state = 0
        i += 1
    return out

def diffusion_trough_calls(diffusion, line=50.0, phase_min=5, cycle_min=15,
                           publication_lag=1, warmup=24):
    """ESRI's other clause on the same index - and a documented negative.

    The Institute states both clauses on one index: the trough is the last month the index
    stays below the fifty-per-cent line, the peak the last month it stays above.  The index
    here counts the share DETERIORATING, so the readings swap and the trough is the last
    month the share stood at or above the line.

    ON THE SEVEN AMERICAN TROUGHS THIS CLAUSE FINDS NONE, and makes eight other calls; the
    level clause finds six of the seven with no other call.  The peak is a diffusion
    question and the trough is a level question, and that is not put in by hand - it comes
    out of American claims data.  The function is kept because the one thing the clause
    DOES find is Paper 1's rolling-episode end: the deteriorating share crosses back below
    half in March 2026, dating a trough at February 2026 against Paper 1's May 2026.  A
    classic recession's trough is a level event; a rolling episode's end is a diffusion
    event; the rule's two clauses separate them.

    Returns a list of (published, dated) month pairs.  Uses no official chronology.
    """
    _check_diffusion(diffusion, line, phase_min, cycle_min, publication_lag, warmup)
    d = diffusion.values; idx = diffusion.index; n = len(d)
    lasta = np.maximum.accumulate(np.where(d >= line, np.arange(n), 0))
    out = []; i = 0; last = None; state = 0; off = 0; run = 0
    while i < n:
        run = run + 1 if d[i] < line else 0
        if state == 0 and run >= phase_min and i >= warmup:
            pub = idx[i] + pd.DateOffset(months=publication_lag)
            pm = pub.year * 12 + pub.month
            if last is None or pm - last >= cycle_min:
                j = lasta[i]
                out.append((pd.Timestamp(pub.year, pub.month, 1),
                            pd.Timestamp(idx[j].year, idx[j].month, 1)))
                last = pm; state = 1; off = 0
        elif state == 1:
            off = off + 1 if d[i] >= line else 0
            if off >= phase_min: state = 0
        i += 1
    return out

def level_trough_calls(claims_log, smooth=2, lookback=30, run=1, drop=1.0,
                       arm_gap=50.0, rearm_gap=None, min_phase=3, publication_lag=1):
    """When would the rule have said a trough had happened?

    `claims_log` is the LOG level of seasonally adjusted national claims.  Claims are
    counter-cyclical, so the month claims peak is the month activity bottoms - which is
    the rule's own level clause, read on an inverted series.  The detector arms when the
    smoothed series stands `arm_gap` log points above its own trailing `lookback`-month
    minimum, fires once that maximum has been passed and the series has fallen away from
    it, and dates the trough at the month claims peaked.  After a call it returns to
    quiet only once the gap has stood below `rearm_gap` for `min_phase` months, so no
    episode can be called twice; `rearm_gap` defaults to half the arm, the convention
    the weekly continued-claims detector (memo section 8d, Finding 2) and the German
    toll-index clause already use.  Until 2 September 2026 the default was five log
    points - a tenth of the arm - and on the 1947-on national claims field the clause,
    once it had called the 1949 trough, never found three months that close to base
    again until 1971 and so could call none of 1954, 1958 and 1961; on the 1971-on file
    it was set on, the two defaults give the same calls at every month (the self-test
    and the reproducer check this).  The maximum it reads is the current spike's: it
    restarts whenever the series stands at its trailing `lookback` minimum (gap zero),
    the base the gap is measured from - the definition under which no higher spike
    further back can veto a call (memo section 8f, the initial-claims correction).

    Returns a list of (published, dated) month pairs.  Uses no official chronology.
    """
    if not isinstance(claims_log, pd.Series):
        raise TypeError('level_trough_calls() takes a pandas Series of the LOG level')
    if smooth < 1 or lookback < 2:
        raise ValueError(f'smooth must be >=1 and lookback >=2, got {smooth} and {lookback}')
    _v = claims_log.values[np.isfinite(claims_log.values)]
    if _v.size and np.median(np.abs(_v)) > 50.0:
        raise ValueError('level_trough_calls() takes the LOG level; this series looks '
                         f'like a raw level (median absolute value {np.median(np.abs(_v)):.3g})')
    if rearm_gap is None:
        rearm_gap = arm_gap / 2.0
    N = (claims_log * 100.0).rolling(smooth).mean()
    G = N - N.rolling(lookback, min_periods=lookback // 2).min()
    df = pd.concat([N.rename('n'), G.rename('g')], axis=1).dropna()
    n = df['n'].values; g = df['g'].values; idx = df.index
    out = []; state = 'quiet'; off = 0; nmax = -1e9; ni = 0; fall = 0
    prev = n[0] if len(n) else 0.0
    for i in range(1, len(n)):
        # the maximum is the current spike's: a new lookback-low (gap zero) restarts it,
        # so a higher spike further back can never stand in for the one being read
        if g[i] <= 0 or n[i] > nmax: nmax = n[i]; ni = i; fall = 0
        elif n[i] < prev: fall += 1
        else: fall = 0
        prev = n[i]
        if state == 'called':
            off = off + 1 if g[i] < rearm_gap else 0
            if off >= min_phase: state = 'quiet'; off = 0
            continue
        if state == 'quiet':
            if g[i] >= arm_gap: state = 'armed'; nmax = n[i]; ni = i; fall = 0
            continue
        if fall >= run and (nmax - n[i]) >= drop and g[ni] >= arm_gap:
            pub = idx[i] + pd.DateOffset(months=publication_lag)
            out.append((pd.Timestamp(pub.year, pub.month, 1),
                        pd.Timestamp(idx[ni].year, idx[ni].month, 1)))
            state = 'called'; off = 0
    return out

# ---------------------------------------------------------------- the claims conjunct
def claims_conjunct(initial_nsa, continued_nsa, weeks=52, smooth=4):
    """The smaller of the year-over-year log changes in unadjusted weekly initial and
    continued claims, then a `smooth`-week mean: the one object of the program's earlier
    two-tier claims detector (the 'Onset Detector' page of 20 August 2026) that survived
    re-examination.  Read year over year it needs no seasonal model at all.  Across the
    2,237 quiet weeks of the Department of Labor's national file since 1968 - outside a
    recession and more than a year past a trough - its highest reading is +0.170 log
    points and the lowest maximum inside a recession is +0.350, so a line anywhere between
    separates the two without a fitted parameter (memo section 8f).

    Takes the two UNADJUSTED weekly levels as pandas Series on one weekly index; returns
    the conjunct in log points (natural log units, not x100).
    """
    for nm, s in (('initial_nsa', initial_nsa), ('continued_nsa', continued_nsa)):
        if not isinstance(s, pd.Series):
            raise TypeError(f'claims_conjunct() takes pandas Series; {nm} is not one')
        if (s.dropna() <= 0).any():
            raise ValueError(f'{nm} has a non-positive level; the conjunct takes raw weekly counts')
    if weeks < 2 or smooth < 1:
        raise ValueError(f'weeks must be >= 2 and smooth >= 1, got {weeks} and {smooth}')
    ic = np.log(initial_nsa.astype(float)); cc = np.log(continued_nsa.astype(float))
    c = pd.concat([ic - ic.shift(weeks), cc - cc.shift(weeks)], axis=1).min(axis=1)
    return c.rolling(smooth).mean().dropna()

def conjunct_peak_calls(conjunct, line=0.20, quiet_weeks=26, publication_days=7):
    """When would the conjunct have said a recession had begun?

    An episode begins at the first week at or above `line` that follows at least
    `quiet_weeks` consecutive weeks below it - a hysteresis rule with no counter, so the
    dating does not depend on where the scan started, and the aftermath of a recession
    (the conjunct stays high for a year after 2020) cannot open a second episode.  The
    call is published `publication_days` after the week's end, the Department's Thursday
    release.  Returns a list of publication Timestamps.  The conjunct carries no date: the
    peak's month comes from the state diffusion index (memo section 8f).  Uses no official
    chronology.
    """
    if not isinstance(conjunct, pd.Series):
        raise TypeError('conjunct_peak_calls() takes the pandas Series claims_conjunct() returns')
    _v = conjunct.values[np.isfinite(conjunct.values)]
    if _v.size and np.nanmax(np.abs(_v)) > 10.0:
        raise ValueError('conjunct_peak_calls() takes natural-log units; this series looks like log points x100 '
                         f'(largest absolute value {np.nanmax(np.abs(_v)):.3g})')
    if quiet_weeks < 1:
        raise ValueError(f'quiet_weeks must be >= 1, got {quiet_weeks}')
    out = []; below = 0
    for t, v in conjunct.items():
        if not np.isfinite(v): continue
        if v >= line:
            if below >= quiet_weeks: out.append(t + pd.Timedelta(days=publication_days))
            below = 0
        else:
            below += 1
    return out

def earliest_call(*call_lists, min_gap_days=365):
    """The union rule of memo section 8f: the call is the earliest publication among the
    objects, one per episode - after a call, nothing for `min_gap_days`.  Each argument is
    a list whose items are either Timestamps or (published, dated) pairs; only the
    publication is read here.  Returns sorted publication Timestamps.  Has no parameter
    beyond the episode gap and chooses nothing among the objects.
    """
    pubs = []
    for calls in call_lists:
        for c in calls:
            p = c[0] if isinstance(c, (tuple, list)) else c
            if not isinstance(p, pd.Timestamp):
                raise TypeError('earliest_call() takes Timestamps or (published, dated) pairs')
            pubs.append(p)
    out = []; last = None
    for p in sorted(pubs):
        if last is None or (p - last).days > min_gap_days:
            out.append(p); last = p
    return out

# ---------------------------------------------------------------- the American route
AMERICAN_ROUTE = """The shipped American real-time route (adopted 2 September 2026; memo section 8f;
rebuilt as ONE CALL, ONE DATE at every turn on 3 September 2026, night - memo section 8j;
american_chronology below; lab/weekly/american_chronology.py).

Every object the record holds is read in publication order by a state machine.  Closed:
the first peak call opens a downturn and its date is the onset, final at the call.  Open:
the first trough call published after it and dated after the onset closes it, final at the
call.  Nothing is pending, nothing is revised, nothing confirms anything later - the peak
call and the trough call ARE the confirmation (Anthony).  The route has no parameter of
its own and chooses nothing among the objects: each leg keeps its own setting and its own
record.  An object with no dating clause of its own (B, M, P) dates the turn to the month
of the data it read - the week's month, the survey's month - a convention, not a number.

DEFAULT (version 39 = version 38's onsets, with leg S at the ends): the peak call is the claims objects AND one of two labor-market
objects at its line - Sahm's gap at 0.5 on the unemployment rate as first published, OR the
vacancy rate's fall in its fast form, the TWO-month mean 0.36 points below its maximum over
the previous SIX months (route B'') - whichever is public first; dated by the claims object.
The committee's twelve and the 2023-26 downturn are called, nothing else since 1948; onsets
a median of 40 days after the peak month, six of twelve within a month after (version 37's
three-month, twelve-month form at 0.6: 80 days; version 36's rate-only route B: 111).  The
vacancy object is Michaillat and Saez's v-hat read alone, on Petrosky-Nadeau and Zhang's
series to 2000 and JOLTS after (lab/vac/vacancy_rate_PNZ_JOLTS.csv; JOLTS as first published
from the first ALFRED vintage, August 2010).  The form and line were chosen leave-one-peak-out
(lab/speed2/vacancy_forms.log): every fold picks (2, 6) with the line at the midpoint between
the disturbances' ceiling (0.24: 1951, 1952, 1967) and the eleven's floor (0.49, 1960); the
form has no crossing outside a recession window on the record from 1949, reaches all six
interwar recessions 1920-1945 out of sample with one crossing outside them (October 1946,
the reconversion), and on JOLTS first prints crosses nowhere in 2010-19 before the December
2019 reading (0.46, public 11 February 2020), then May 2020 and August 2022.  Public near the
end of the month after its month (the Conference Board's index; JOLTS in the first week of
the second month).  The claims objects alone (route
A) remain available and call 1951, 1952 and 1967 too; the rate alone (route B) remains
available.  The second condition's window closes at the claims field's own end (the first
trough call the claims legs make), so a disturbance already closed cannot be confirmed by the
next recession's rate.

PEAKS   A  the Department of Labor's monthly state claims file, the diffusion index of
           claims_diffusion (amplitude 36, minimum phase 8) and diffusion_peak_calls,
           factors in real time, 1947 on; published the 20th of the month after the
           data month.  The dating leg where no weekly object exists.
        B  the national weekly claims conjunct (claims_conjunct, conjunct_peak_calls at
           0.20), 1969 on; published seven days after the week.  A call, not a date.
        C  the weekly state claims file's breadth index (lab/weekly/speed_final.py),
           1991 on; published the 28th of the month.  The dating leg where it exists.
        M  the same conjunct at the same 0.20 line on the Fieldhouse field's national
           monthly unadjusted claims, 1948 on (lab/weekly/legs_1948.py); published the
           10th of the month after.  A call, not a date; the object that reaches the
           four peaks before the weekly file exists.
TROUGHS P  the Philadelphia Fed survey read after the panel's D has opened (memo
           section 8c, general activity a=5 r=1); published the third Thursday of its
           month.  A call whose own date runs early.
        K  weekly continued claims, real-time factors, the section 8d Finding 2 detector
           (level_trough_calls: four-week mean, arm 30, six falling weeks, drop 4);
           published five days after the week.  The dating leg.
        I  weekly initial claims, the level clause of lab/weekly/final_caller.py
           (eight-week mean, six falling weeks, drop 10, arm 40) on the Department's
           national file, 1969 on; published seven days after the week.
        D  the panel's own real_time_trough_calls, published a month after.
        J  the Fieldhouse field's national monthly continued claims, real-time factors,
           1947 on, read with level_trough_calls at its defaults (legs_1948.py);
           published the 10th of the month after.  The object that reaches 1949-1961.
        H  the same clause on the field's national monthly initial claims.
        S  Paper 1's own end rule - the original Bristow Rule - on the rate as first
           published (sahm_end_calls): the downturn ends in the month Sahm's gap attains
           its maximum, called after three readings below it; admitted only in episodes
           where no claims level object armed (version 39, 3 September 2026, night, fifth
           pass).  It ends the 2023-24 downturn at August 2024, called 5 December 2024 -
           Paper 1's own month - where the diffusion index's return below fifty had said
           February 2026.  On the twelve the claims legs always fire first.
        T  the Department's monthly index's own trough clause (diffusion_trough_calls on
           the 48/13 index, 1971 on) and F, the same on leg A's index (1947-2024): the
           last resort where neither the claims legs nor the rate can end a downturn.
           Their dates run seven to twenty-eight months after the committee's on the
           twelve, so they close only what nothing else does.
TROUGH FLOORS (3 September 2026, night; lab/weekly/trough_floor.py).  Under one call, one
date the first trough object to fire ENDS the downturn, and in 1970 the shipped level
clauses (drop one log point on H and J, ten on I) fired on the spring pause - initial
claims dipped sixteen log points from April to August 1970 and rose again to November -
ending the 1969-70 recession in May 1970, six months early.  The lowest drop on each
clause with no 1970 misfire is H 8, J 5, I 20 (K's shipped 4 has none); these are set by
that negative, not by the twelve, and the speed at them is what it is: the ends are called
at a median of 30 days after the trough month with the survey leg P, 44 without it.
THE SECOND CONDITION (Sahm's gap at 0.5, first prints; conjunction_calls, sahm_gap).  The
unemployment rate is the only object on the Mac that is present in 2023-24 and absent in
1951 and 1967 (lab/slack/bound.log: every household-survey component, the hours, the
payrolls, the vacancy rate and the insured rate were read at the lowest line that excludes
both episodes); its own line cannot be lowered in real time (lab/slack/ur_forms_rt.log:
the 1967 episode reached 0.43 on first prints, 0.47 on FRED's SAHMREALTIME, with the
September and October 1967 rates first published at 4.1 and 4.3); and it is monthly, so it
reaches 0.5 two to four months after the peak month (1973-74: eight).  The states'
unemployment rates as a breadth (lab/slack/state_breadth.log) cross earlier only because
they read the same rise at a lower national line, and cannot be tested on 1951 or 1967.
RECORD under the default (american_chronology.log, first prints, the committee as the
comparator - Rule 11): onsets 13 since 1948, the committee's twelve and July 2023 (called
28 August 2023), no other; published a median of 40 days after the peak month (two inside
the month, six within a month after; worst 142, July 1981; version 37: 80; the rate-only
route B: 111), dated 6 of 12 to the month and 8 within one; the 2023-24 downturn ends
August 2024 (leg S, called 5 December 2024);
ends 12 of 12 and February 2026, a median of 30 days after the trough month (six within a
month), dated 2 of 12 to the month and 8 within one (without P: 44 days, 5 and 9).  The
claims objects alone (route A): onsets a median of 30 days after the peak month (seven
within a month), and 1951, 1952 and 1967 called as well.  Anthony's standard of one month
at every turn is met by the data at 2 of 12 onsets and 6 of 12 ends; the walls are the
rate's speed and the 1970 pause, and they are stated, not fitted away (Rule 18).
THE SPEED HUNT (3 September 2026, night, third pass; lab/speed2/, memo section 8k).  Read at
the sixteen claims calls, as a fast second condition: the S&P 500's drawdown (separates the
three disturbances on the record - weakest recession -10.7 per cent within thirty days of
the call, strongest disturbance -6.0 - but a random quiet day sees an 8 per cent drawdown
inside sixty days 31 per cent of the time: three negatives cannot certify it, and it is not
adopted); Moody's Baa-Aaa, the term spread, the bill rate's change, freight-car loadings and
business failures (1967 reads as a recession on every one); the claims objects' own depth
(the conjunct at 0.30, the breadth at 80: excludes the disturbances but reaches the twelve
later than the rate); payrolls' first fall (four of twelve late, and the 1952 steel strike).
Only the vacancy rate separates and adds speed.  Fourth pass (memo section 8l): the
vacancy object's forms leave-one-out, temporary-help employment (1990 on: a razor-thin line
over 1990's 3.5 and no gain in 2007 - not adopted), payrolls' first fall (falls in 1951 and
in the 1967 episode's first prints - not adopted), a factor-free weekly state breadth from
the 1986 file (at the route's fifty-per-cent line it crosses in September 1990, not July;
the Paper 2 chat's July 23 sits at 25 of 51 states - not adopted), and the Paper 2 chat's
fitted rule read for what transfers (its curve gate is untestable before 1962 and admits
1967; its end calls are withdrawable).
"""

def union_calls(legs, date_order=(), min_gap_days=365):
    """The union rule of memo section 8f on any set of objects.

    `legs` maps a name to that object's calls, each a (published, dated) pair (dated may
    be None for an object that carries no date) or a bare publication Timestamp.  Calls
    from every object are read in publication order; a call opens a new episode when it
    is published more than `min_gap_days` after the episode's opening call, otherwise
    it joins the episode.  The date carried is the first object in `date_order` that
    has fired inside the episode (`date_at_call` reads it at the opening publication,
    `date` at the episode's last call); None while no dating object has fired.

    Returns a list of episodes, each a dict with 'published', 'leg', 'date_at_call',
    'date', 'date_leg' and 'members' (every (leg, published, dated) in the episode).
    Chooses nothing among the objects and uses no official chronology.
    """
    items = []
    for name, calls in legs.items():
        for c in calls:
            if isinstance(c, (tuple, list)):
                p, d = c[0], c[1]
            else:
                p, d = c, None
            if not isinstance(p, pd.Timestamp):
                raise TypeError('union_calls() takes Timestamps or (published, dated) pairs')
            items.append((p, name, d))
    for name in date_order:
        if name not in legs:
            raise KeyError(f'date_order names {name!r}, which is not a leg')
    items.sort(key=lambda x: x[0])
    episodes = []
    for p, name, d in items:
        if episodes and (p - episodes[-1]['published']).days <= min_gap_days:
            episodes[-1]['members'].append((name, p, d))
        else:
            episodes.append({'published': p, 'leg': name, 'members': [(name, p, d)]})
    for ep in episodes:
        ep['date_at_call'] = None; ep['date'] = None; ep['date_leg'] = None
        for dn in date_order:
            fired = [(pp, dd) for nn, pp, dd in ep['members'] if nn == dn and dd is not None]
            if fired:
                ep['date'] = min(fired)[1]; ep['date_leg'] = dn
                at = [dd for pp, dd in fired if pp <= ep['published']]
                if at and ep['date_at_call'] is None: ep['date_at_call'] = at[0]
                break
        if ep['date_at_call'] is None:
            # the earliest-published dating object that had fired by the opening call
            for dn in date_order:
                at = [dd for nn, pp, dd in ep['members'] if nn == dn and dd is not None and pp <= ep['published']]
                if at: ep['date_at_call'] = at[0]; break
    return episodes

# ---------------------------------------------------------------- confirmation (3 September 2026)
def seasonal_factors_realtime(panel, window_years=7, own_years=5):
    """Seasonally adjust a monthly panel of LEVELS in real time, the program's routine.

    Month-of-year factors are re-estimated each December from the years then available -
    medians of the deviation from a centered thirteen-month mean over a moving
    `window_years` window - applied unchanged through the following year, and pooled
    across the columns until a column has `own_years` of its own history.  No month uses
    anything later than the December before it; the first two years pass through
    unadjusted (they are the warm-up and are outside any record).  This is the routine of
    lab/dol/mpanel4.py and lab/fh/build_rt.py, ported so that the confirmation leg below
    is self-contained; the self-test checks the port against build_rt's own output.
    Returns the LOG level, adjusted, one column per channel.
    """
    if not isinstance(panel, pd.DataFrame):
        raise TypeError('seasonal_factors_realtime() takes a DataFrame of monthly levels')
    X = np.log(panel.replace(0, np.nan)).interpolate().bfill()
    out = pd.DataFrame(index=X.index, columns=X.columns, dtype=float)
    for y in sorted(set(X.index.year)):
        hist = X[(X.index.year < y) & (X.index.year >= y - window_years)]
        m = (X.index.year == y)
        if len(hist) < 24:
            out.loc[m] = X.loc[m]; continue
        R = hist - hist.rolling(13, center=True, min_periods=7).mean()
        own = {}; pooled = {}
        for mth in range(1, 13):
            sel = R[R.index.month == mth]
            if len(sel) == 0: continue
            v = sel.values[~np.isnan(sel.values)]
            if len(v): pooled[mth] = float(np.median(v))
            for c in X.columns:
                q = sel[c].dropna()
                if len(q) >= 3: own[(c, mth)] = float(np.median(q))
        if pooled:
            mu = np.median(list(pooled.values())); pooled = {k: v - mu for k, v in pooled.items()}
        if own:
            mo = np.median(list(own.values())); own = {k: v - mo for k, v in own.items()}
        for c in X.columns:
            use_own = len(X[X.index.year < y][c].dropna()) >= own_years * 12
            adj = np.array([(own.get((c, t.month), pooled.get(t.month, 0.0)) if use_own
                             else pooled.get(t.month, 0.0)) for t in X.index[m]])
            out.loc[m, c] = X.loc[m, c].values - adj
    return out.dropna(how='all')

def payroll_breadth_calls(state_payrolls, amplitude=0.75, min_phase=6, smooth=3,
                          line=50.0, phase_min=5, record_start='1949-01-01', day=20):
    """The CONFIRMATION leg of the American route: the breadth of states whose payroll
    employment is falling (leg E, 3 September 2026).

    `state_payrolls` is a DataFrame of monthly state nonfarm payrolls, unadjusted levels,
    one column per state (the Fieldhouse-Munro-Koch-Howard field, December 1946 on).
    Each state is adjusted in real time (seasonal_factors_realtime), smoothed `smooth`
    months, negated so that falling employment is a deteriorating phase, put through the
    causal phase monitor (channel_phase: a state turns down after falling `amplitude`
    log points from its running maximum, `min_phase` months after its last turn), and
    the share of states deteriorating is read with ESRI's clause (diffusion_peak_calls).
    A call on month T is published the `day`th of T+1, the state employment release.

    The amplitude and minimum phase were chosen leave-one-peak-out on the twelve postwar
    peaks (lab/weekly/legs_state_payroll.py): every fold chooses 0.75 and 6 with a
    three-month mean, and the setting calls all twelve with NO other call from 1949 to
    2024 - 1951, 1967, 1995, 2015 and 2022-24 silent (two to eight per cent of states
    falling in 2023-24 against fifty or more in every recession).  It is slow: 81 to 447
    days after the peak month, median 188.  Measured as a confirmer on 3 September 2026
    and withdrawn from the route the same day (Anthony: one call, one date); kept as a
    measured object - the slowest, and the only one, that has never fired outside a
    committee recession.  Returns a list of (published, dated) pairs from `record_start`
    (the real-time factors need twenty-four months).  Uses no official chronology.
    """
    P = state_payrolls.loc[:, state_payrolls.notna().mean() > 0.9]
    SA = seasonal_factors_realtime(P)
    X = -(SA.rolling(smooth).mean().dropna(how='all') if smooth > 1 else SA)
    D = claims_diffusion(X, amplitude, min_phase)
    calls = diffusion_peak_calls(D, line=line, phase_min=phase_min)
    out = [(pd.Timestamp(p.year, p.month, day), d) for p, d in calls]
    return [x for x in out if x[0] >= pd.Timestamp(record_start)]

def confirm_episodes(episodes, confirmers, horizon_months=18, asof=None):
    """A confirmation reading - MEASURED 3 SEPTEMBER 2026 AND NOT PART OF THE ROUTE.  Anthony's
    instruction the same day: one call, one date; once an object reaches its line the downturn
    is called and nothing confirms it after the fact.  Kept as a measured object.

    A CALL from the claims objects, then a CONFIRMATION from an object that has never fired
    outside a contraction.

    `episodes` is union_calls' output; `confirmers` maps a name to that object's calls
    ((published, dated) pairs).  For each episode the first confirmer publication inside
    [call, call + horizon] is the confirmation.  Verdicts: 'confirmed' with the leg and
    the days from the call; 'unconfirmed' once the horizon has passed with no
    confirmation - a broad deterioration of the claims field that did not become a
    contraction (1951, 1967, 2023 on the record); 'pending' inside the horizon when
    `asof` is given.  Adds 'verdict', 'confirmed_by', 'confirmed_on' and 'confirm_days'
    to each episode and returns the list.  Uses no official chronology.
    """
    asof = pd.Timestamp(asof) if asof is not None else None
    for ep in episodes:
        p0 = ep['published']; hi = p0 + pd.DateOffset(months=horizon_months)
        hits = []
        for name, calls in confirmers.items():
            for c in calls:
                pp = c[0] if isinstance(c, (tuple, list)) else c
                if p0 - pd.Timedelta(days=45) <= pp <= hi: hits.append((pp, name))
        if hits:
            pp, name = min(hits)
            ep['verdict'] = 'confirmed'; ep['confirmed_by'] = name; ep['confirmed_on'] = pp
            ep['confirm_days'] = (pp - p0).days
        elif asof is not None and asof < hi:
            ep['verdict'] = 'pending'; ep['confirmed_by'] = None; ep['confirmed_on'] = None; ep['confirm_days'] = None
        else:
            ep['verdict'] = 'unconfirmed'; ep['confirmed_by'] = None; ep['confirmed_on'] = None; ep['confirm_days'] = None
    return episodes

# ---------------------------------------------------------------- the conjunction call (3 September 2026, night)
def sahm_gap(unrate):
    """Sahm's indicator: the three-month mean of the unemployment rate minus its lowest value over
    the previous twelve months, in percentage points (Sahm 2019).  `unrate` is the monthly rate
    in per cent.  The published line is 0.5; the rate for month m is public the first Friday of
    m+1.  Uses no official chronology."""
    if not isinstance(unrate, pd.Series):
        raise TypeError('sahm_gap() takes a pandas Series of the unemployment rate in per cent')
    # Sahm's own form (FRED SAHMREALTIME): the minimum is over the PREVIOUS twelve months, not the
    # current one - corrected 3 September 2026 (night); until then the window included the current
    # month, and with the rate given to one decimal the gap sat at 0.4999 in July 2024 on first prints
    # where Sahm's published value is 0.53.  Rounded to four decimals (the gap is a multiple of 1/30).
    m3 = unrate.rolling(3).mean()
    return (m3 - m3.shift(1).rolling(12).min()).dropna().round(4)

def conjunction_calls(episodes, unrate, line=0.5, horizon_months=18, pub_day=5, back_months=6):
    """The American call under Anthony's rule of 3 September 2026 - every committee recession and
    the 2023-24 downturn called, no other disturbance called - as ONE call with ONE date.

    `episodes` is union_calls' output on the claims objects (the route's own episodes);
    `unrate` the monthly unemployment rate.  An episode is called when the claims objects have
    reached their line AND Sahm's gap has reached `line` (0.5, Sahm's published number) inside
    [opening call - back_months, opening call + horizon_months]; the call is published at the
    later of the two publications (the rate's on the `pub_day`th of the month after its month).
    The date is the later of the claims date the route carried at its call and the Sahm crossing
    month less three (Sahm's and Paper 1's own onset convention).  Episodes with no crossing are
    not called.

    Measured on the route's fifteen episodes since 1948 (lab/conjunction_route.log, current
    vintage of the rate): the twelve committee recessions and the 2023-24 downturn are called
    (the Sahm gap peaked at 0.33 in 1951 and 0.23 in 1967 - 0.43 on first prints - and reached
    0.5 with the July 2024 figure), no other episode is; dates 5 of 12 exact and 9 within a
    month under this function's 'later' date rule, April 2024 for the 2023-24 episode; the
    price is speed - median 96 days after the peak month against 30 for the claims call alone,
    one of twelve inside the month against seven.  The unemployment rate is the one object on
    disk that separates 2024 from 1951 and 1967, and it is monthly.  The shipped route reads
    the same condition through american_chronology with the claims date kept (6 of 12 exact
    on first prints against 2 under the 'later' rule).  Returns a list of dicts: published,
    date, claims_call, sahm_month, episode.  Uses no official chronology.
    """
    g = sahm_gap(unrate)
    out = []
    for ep in episodes:
        p0 = ep['published']
        seg = g[p0 - pd.DateOffset(months=back_months): p0 + pd.DateOffset(months=horizon_months)]
        t = next((tt for tt, v in seg.items() if v >= line), None)
        if t is None: continue
        pub_s = pd.Timestamp(t.year, t.month, 1) + pd.DateOffset(months=1) + pd.Timedelta(days=pub_day - 1)
        d0 = ep.get('date_at_call') if ep.get('date_at_call') is not None else ep.get('date')
        s3 = t - pd.DateOffset(months=3)
        date = max(d0, s3) if d0 is not None else s3
        out.append(dict(published=max(p0, pub_s), date=date, claims_call=p0, sahm_month=t, episode=ep))
    return out

def sahm_end_calls(gap, armed=None, line=0.5, below=3, pub_day=5):
    """Paper 1's own end rule - the original Bristow Rule - as a trough leg (leg S, 3 September 2026,
    night, fifth pass): a downturn the unemployment rate confirmed ends in the month Sahm's gap
    attains its episode maximum; the call is made when `below` consecutive monthly readings have
    printed under that maximum (Paper 1's real-time convention), published the `pub_day`th of the
    month after the last of them, dated to the maximum's month.  An episode of the rate opens when
    the gap crosses `line` from below and closes at the call.

    `armed`, if given, is a monthly boolean Series that is True in any month a claims level object
    stood armed (a claims recession); a call is then emitted only if no month between the rate's
    crossing and the call was armed.  The reason is the record: read alone, the rule ends the
    1973-75 recession in March 1974, where the rate paused at 5.1 for three months while claims
    went on rising - the claims legs end a claims recession, and the rate ends a downturn the
    claims field never carried far enough for its level clauses to arm (2023-24: August 2024,
    called 5 December 2024).  Read on the rate as first published.  Returns (published, dated)
    pairs.  Uses no official chronology.
    """
    if not isinstance(gap, pd.Series):
        raise TypeError('sahm_end_calls() takes the pandas Series sahm_gap() returns')
    out = []; runmax = None; runmax_t = None; n_below = 0; on = False; prev = None; start = None
    for t, v in gap.items():
        if not np.isfinite(v): continue
        if not on:
            if v >= line and (prev is None or prev < line):
                on = True; runmax = float(v); runmax_t = t; n_below = 0; start = t
        else:
            if v > runmax:
                runmax = float(v); runmax_t = t; n_below = 0
            else:
                n_below += 1
                if n_below >= below:
                    ok = True
                    if armed is not None:
                        seg = armed[start:t]
                        ok = not bool(seg.astype(bool).any())
                    if ok:
                        out.append((pd.Timestamp(t.year, t.month, 1) + pd.DateOffset(months=1) + pd.Timedelta(days=pub_day - 1), runmax_t))
                    on = False
        prev = float(v)
    return out

def american_chronology(peak_legs, trough_legs, sahm=None, line=0.5, horizon_months=18,
                        pub_day=5, back_months=6, min_gap_days=0, date_rule='claims', second=None):
    """ONE CALL, ONE DATE at every peak and every trough (Anthony, 3 September 2026, night):
    "for all of the peaks and troughs we want only one call, no confirmation call tagged
    alongside; the peak and the trough calls should be the confirmation."

    `peak_legs` and `trough_legs` map a leg name to that object's calls as (published, dated)
    pairs, where `dated` is the month the object itself dates the turn to; an object that
    carries no dating clause of its own gives the month of the data it read (the week's month
    for a weekly object, the survey's month for a survey) - a convention, not a fitted
    number, and the caller says which legs use it.  `sahm`, if given, is Sahm's gap
    (sahm_gap on the unemployment rate as first published) and adds the second condition
    of conjunction_calls to every peak call: the claims object has reached its line AND the
    gap reaches `line` inside [claims call - back_months, claims call + horizon_months];
    the call is then published at the later of the two and dated by `date_rule`: 'claims'
    (the default) keeps the claims object's date - the object with the dating record dates
    the turn, the rate is only the condition; 'later' takes the later of that date and the
    crossing month less three (conjunction_calls' convention of version 35, kept for
    comparison: it was adopted on the 2024 episode's date and Rule 18 does not allow that).
    `second` generalizes the condition to ANY of several gap objects: a list of dicts, each
    with 'name', 'gap' (a monthly Series), 'line', and 'pub_day' (the day of the month AFTER
    month m on which the reading for m is public: 5 for the unemployment rate - the first
    Friday of m+1 - and 30 for the vacancy rate, whose month is public near the end of m+1);
    the condition is met by the first object to reach its line inside the window, and the
    call is published at the later of the claims call and that object's publication.  An
    entry may carry 'pub_lag_days' instead: the object is then read on its own dates (a daily
    or weekly series) and each reading is public that many days after it (3 September 2026,
    night, fifth pass: the daily and weekly sweep, lab/data/screen.py).  The
    window closes at `horizon_months` after the claims call OR at the claims field's own end
    - the first trough call the claims legs would make after that claims call, read by this
    same machine without any second condition - whichever comes first: a disturbance the
    claims field has already closed cannot be confirmed by the next recession's rate (the
    March 1952 episode closed in October 1952; without this the vacancy rate's fall of
    October 1953 would have confirmed it and swallowed the 1953 recession).  `sahm`
    with `line` and `pub_day` is the one-object case of this (3 September 2026, night, second
    half: the vacancy rate as a second object beside the rate; lab/speed2/vacancy_veto.log).

    The chronology is a state machine read in publication order.  Closed: the first peak
    call (that passes the Sahm condition, if one is set) opens a downturn, and its date is
    the downturn's onset - final at the call.  Open: the first trough call published after
    the opening call and dated after the onset closes it, and its date is the end - final
    at the call.  Every other call while the state does not change is nothing: no second
    date, no confirmation, no revision.  Returns a list of turns, each a dict with 'kind'
    ('peak' or 'trough'), 'published', 'leg', 'date', and for a peak under the Sahm
    condition 'claims_published' and 'sahm_month'.  Uses no official chronology.
    """
    def items(legs, kind):
        out = []
        for name, calls in legs.items():
            for c in calls:
                if not (isinstance(c, (tuple, list)) and len(c) == 2 and isinstance(c[0], pd.Timestamp) and isinstance(c[1], pd.Timestamp)):
                    raise TypeError(f'american_chronology(): leg {name!r} must give (published, dated) Timestamp pairs')
                out.append((c[0], name, pd.Timestamp(c[1].year, c[1].month, 1), kind))
        return out
    peaks = sorted(items(peak_legs, 'peak')); troughs = sorted(items(trough_legs, 'trough'))
    conds = None
    if second is not None:
        conds = []
        for c in second:
            if not all(k in c for k in ('name', 'gap', 'line', 'pub_day')):
                raise KeyError("each entry of `second` needs 'name', 'gap', 'line', 'pub_day'")
            conds.append((c['name'], c['gap'], float(c['line']), int(c['pub_day']), c.get('pub_lag_days')))
        if sahm is not None:
            conds.append(('Sahm', sahm, float(line), int(pub_day), None))
    elif sahm is not None:
        conds = [('Sahm', sahm, float(line), int(pub_day), None)]
    g = None if conds is None else True
    ends_after = {}
    if conds is not None:
        # the claims field's own ends, from the same machine with no second condition
        plain = american_chronology(peak_legs, trough_legs, min_gap_days=min_gap_days)
        for i, t in enumerate(plain):
            if t['kind'] == 'peak':
                nxt = [u for u in plain[i + 1:] if u['kind'] == 'trough']
                ends_after[t['published']] = nxt[0]['published'] if nxt else None
    turns = []; state = 'closed'; onset = None; opened_at = pd.Timestamp.min; last_end = pd.Timestamp.min; last_close_pub = pd.Timestamp.min
    pi = 0; ti = 0
    while pi < len(peaks) or ti < len(troughs):
        if state == 'closed':
            if pi >= len(peaks): break
            p, leg, d, _ = peaks[pi]; pi += 1
            if p <= last_close_pub or d <= last_end: continue
            if g is None:
                turns.append(dict(kind='peak', published=p, leg=leg, date=d)); onset = d; opened_at = p; state = 'open'
            else:
                best = None   # the earliest publication among the objects that reach their line in the window
                w_end = p + pd.DateOffset(months=horizon_months)
                own_end = ends_after.get(p)
                if own_end is None:
                    # a claims call inside an episode another claims call opened: the window is that episode's
                    opened = [q for q in ends_after if q <= p and (ends_after[q] is None or ends_after[q] > p)]
                    if opened: own_end = ends_after[max(opened)]
                if own_end is not None and own_end < w_end: w_end = own_end
                for nm, gg, ln, lag, lag_days in conds:
                    seg = gg[p - pd.DateOffset(months=back_months): w_end]
                    t = next((tt for tt, v in seg.items() if v >= ln), None)
                    if t is None: continue
                    if lag_days is not None:      # a daily or weekly object, public `pub_lag_days` after each reading
                        pub_s = t + pd.Timedelta(days=int(lag_days))
                    else:
                        pub_s = pd.Timestamp(t.year, t.month, 1) + pd.DateOffset(months=1) + pd.Timedelta(days=lag - 1)
                    if best is None or pub_s < best[0]: best = (pub_s, t, nm)
                if best is None: continue
                pub_s, t, nm = best
                if date_rule not in ('claims', 'later'):
                    raise ValueError(f"date_rule must be 'claims' or 'later', got {date_rule!r}")
                date = d if date_rule == 'claims' else max(d, t - pd.DateOffset(months=3)); pub = max(p, pub_s)
                if pub <= last_close_pub or date <= last_end: continue
                turns.append(dict(kind='peak', published=pub, leg=leg, date=date, claims_published=p, sahm_month=t, condition=nm))
                onset = date; opened_at = pub; state = 'open'
                # claims calls swallowed by the wait are not re-read
                while pi < len(peaks) and peaks[pi][0] <= pub: pi += 1
        else:
            while ti < len(troughs) and (troughs[ti][0] <= opened_at or troughs[ti][2] <= onset): ti += 1
            if ti >= len(troughs): break
            p, leg, d, _ = troughs[ti]; ti += 1
            turns.append(dict(kind='trough', published=p, leg=leg, date=d)); last_end = d; last_close_pub = p; state = 'closed'
            while pi < len(peaks) and peaks[pi][0] <= p + pd.Timedelta(days=min_gap_days): pi += 1
    return turns

# ---------------------------------------------------------------- the real-time call
def real_time_trough_calls(channels, threshold=2.0, fall_months=4, drop=0.5,
                           publication_lag=1, min_cycle=15, lookback=12, smooth=3,
                           min_channels=2, warmup=24):
    """When would the rule have said a trough had happened, using nothing but the data?

    At each month the composite deviation statistic is recomputed from what was known
    then.  A trough is called once the statistic has reached `threshold` percent and has
    then fallen for `fall_months` consecutive months and by `drop` points from its
    maximum: the recovery is visible in the data, so the contraction is over.  The month
    dated is the month the statistic peaked.  The call is published `publication_lag`
    months after the month of data that triggered it, which is when that month's data
    would actually be in hand.

    `min_cycle` is Bry and Boschan's minimum-cycle censoring: a call whose trough falls
    less than that many months after the previous call's is suppressed, so a long
    recovery with a pause in it is not called twice.

    Returns a list of (published, trough) pairs in time order.  This is a genuine
    real-time rule: it uses no official chronology, at any point, for anything.
    """
    D = composite_deviation(channels, lookback, smooth, min_channels).dropna()
    out = []
    start = D.index[0] if len(D) else None
    for i in range(warmup, len(D)):
        t = D.index[i]
        seg = D[start:t]
        if len(seg) < 4: continue
        at = seg.idxmax(); hi = float(seg.max())
        if hi < threshold: continue
        after = seg[seg.index > at]
        if len(after) < fall_months: continue
        tail = list(after.iloc[-fall_months:])
        prev = float(after.iloc[-fall_months - 1]) if len(after) > fall_months else hi
        falling = all(tail[k] < (tail[k - 1] if k > 0 else prev) for k in range(fall_months))
        if falling and (hi - float(after.iloc[-1])) >= drop:
            start = t + pd.DateOffset(months=1)
            if out and min_cycle and _md(at, out[-1][1]) < min_cycle: continue
            out.append((t + pd.DateOffset(months=publication_lag), at))
    return out

def panel_quality(channels, w0, w1):
    """How much evidence stands behind a date."""
    usable = [(nm, s) for nm, s in channels if s.index.min() <= w0 and s.index.max() >= w1]
    return dict(channels=len(usable),
                spread=spread([channel_trough(s, w0, w1) for nm, s in usable]))

# ---------------------------------------------------------------- diffusion form
def _alternate(out, v):
    """Force peaks and troughs to alternate, keeping the more extreme of any pair."""
    res = []
    for i, k in out:
        if res and res[-1][1] == k:
            j, _ = res[-1]
            if (k == 'P' and v[i] > v[j]) or (k == 'T' and v[i] < v[j]): res[-1] = (i, k)
        else: res.append((i, k))
    return res

def bry_boschan(x, smooth=3, window=5, min_phase=5, min_cycle=15):
    """Bry and Boschan (1971): local extrema, alternation, minimum phase five months,
    minimum cycle fifteen months.  Alternation is re-imposed after every censoring
    pass; censoring can delete a turning point that separated two of the same kind,
    and a routine that does not re-alternate returns runs of consecutive peaks, which
    corrupts any phase or diffusion series built from its output.

    Censoring and re-alternation are iterated to a fixed point.  Over the 118 channels
    of the benchmark the fixed point is reached in at most two passes, so the cap of
    fifty is far from binding; if it were ever reached the routine would be returning
    a set that still breaks one of its own conditions, so it raises instead."""
    m = x.rolling(smooth, center=True).mean().dropna()
    v = m.values; idx = m.index
    cand = []
    for i in range(window, len(v) - window):
        seg = v[i-window:i+window+1]
        if seg.max() == seg.min(): continue
        if v[i] == seg.max(): cand.append((i, 'P'))
        elif v[i] == seg.min(): cand.append((i, 'T'))
    out = _alternate(cand, v)
    for _ in range(50):
        before = list(out)
        changed = True
        while changed and len(out) > 2:
            changed = False
            for a in range(len(out) - 1):
                if out[a+1][0] - out[a][0] < min_phase:
                    keep_first = abs(v[out[a][0]]) >= abs(v[out[a+1][0]])
                    out.pop(a + (1 if keep_first else 0)); changed = True; break
        out = _alternate(out, v)
        changed = True
        while changed and len(out) > 3:
            changed = False
            for a in range(len(out) - 2):
                if out[a+2][0] - out[a][0] < min_cycle:
                    out.pop(a+1); changed = True; break
        out = _alternate(out, v)
        if out == before: break
    else:
        raise RuntimeError('bry_boschan(): censoring did not reach a fixed point')
    return [(idx[i], k) for i, k in out]

def historical_diffusion(channels, smooth=3):
    """The share of components in their own expansion phase, in percent - the index
    the Economic and Social Research Institute of Japan dates."""
    cols = []
    for nm, s in channels:
        tp = bry_boschan(s, smooth)
        if not tp: continue
        idx = s.rolling(smooth, center=True).mean().dropna().index
        ph = pd.Series(np.nan, index=idx)
        for d, k in tp: ph[d] = 0.0 if k == 'P' else 1.0
        ph = ph.ffill()
        ph[:tp[0][0]] = 1.0 if tp[0][1] == 'P' else 0.0
        cols.append(ph.rename(nm))
    if not cols: return None
    P = pd.concat(cols, axis=1, sort=True)
    return (P.mean(axis=1, skipna=True) * 100.0).where(P.notna().sum(axis=1) >= 1)

def date_diffusion(di, w0, w1, line=45.0, run=4, band=0.20, smooth=5):
    """Date a diffusion index.

    The two ends need different clauses because the object has different shapes at
    them.  In an expansion a diffusion index sits near its ceiling for years and has
    no well-identified maximum, so the peak is a threshold event: the last month the
    index stays above the line - which is the rule ESRI publishes.  In a contraction
    the index has a distinct minimum, so the trough is the band clause, the last
    month the index stays within `band` of its low.
    """
    d = di[w0:w1].dropna()
    if len(d) < 6: return dict(peak=None, trough=None)
    # ESRI's published rule is the LAST month the index stays below the line.  The one
    # is added because a diffusion index can read exactly zero and D divides by a trailing
    # maximum; shifting a share in per cent to 1..101 keeps the statistic defined and
    # does not move the answer - across the sixteen Japanese contractions the trough
    # date is the same for every shift from 0.001 to 10.
    trough = channel_trough(d + 1.0, w0, w1, band, smooth, 12, abstain=False, where='last')
    end = trough if trough is not None else w1
    seg = d[w0:end]
    peak = _first_sustained_fall(seg, line, run)
    return dict(peak=peak, trough=trough, verdict='diffusion')


def _first_sustained_fall(seg, line=45.0, run=4):
    """The last month above the line before the FIRST run of at least `run`
    consecutive months below it.

    A threshold rule says the expansion ends when the index goes below the line
    and stays there.  Reading it as the LAST month above the line anywhere before
    the minimum gives the same answer in a short contraction and the wrong one in
    a long one, where the index can rise back above the line mid-slide and the
    peak is then dated from that rebound - a month inside the contraction rather
    than its start.  Returns None when the index never crosses the line, which a
    narrow panel makes common: the index then has only a few coarse steps and can
    sit above the line throughout.  The caller falls back to the level form.
    """
    v = (seg >= line).values; idx = seg.index
    for i in range(len(v) - 1):
        if v[i] and not v[i + 1]:
            j = i + 1; c = 0
            while j < len(v) and not v[j]: c += 1; j += 1
            if c >= run: return idx[i]
    return None

# ---------------------------------------------------------------- the anchored form
def channel_trough_anchored(level, peak_date, w1, band=0.02, smooth=3, abstain=True):
    """The trough measured from the episode's own peak rather than from a rolling
    twelve-month maximum, which makes the rule unbound in time.

    Tested and NOT adopted.  On the nine chronologies, on the sample as it then stood,
    the anchored form dates 51/71 peaks against 50/71 and 46/71 troughs against 49/71,
    and on contractions longer
    than twenty-four months it is worse at both ends.  The twelve-month window is not
    what limits the rule; the panel and the chronology's concept are.  Kept here so
    the test can be reproduced.
    """
    m = _ma(level, smooth)[peak_date:w1].dropna()
    if len(m) < 4: return None
    ref = float(m.iloc[0]); lo = float(m.min()); i = m.idxmin()
    if abstain and i == m.index[-1]: return None
    amp = max(ref - lo, 1e-9)
    on = m[m <= lo + band * amp]
    return max(i, on.index[-1]) if len(on) else i

# ---------------------------------------------------------------- quarterly variant
def to_quarter(s):
    """Quarterly average of a monthly series, stamped at the first month of the quarter.

    A committee that publishes quarterly dates is dated at quarterly frequency: the
    channels are averaged to quarters and the same two clauses are applied with no
    further smoothing and a four-quarter lookback.  Dating a monthly panel and then
    rounding the answer to a quarter mixes two frequencies.
    """
    return s.resample('QS').mean().dropna()

def date_episode_quarterly(channels, w0, w1, band_trough=0.03, band_peak=0.02,
                           lookback=4, peak_cap=4, abstain=True):
    """The same rule run at quarterly frequency, for a chronology that dates quarters.

    Every channel is averaged to quarters first and the lookback becomes four
    quarters.  On the three quarterly committees this is better at troughs and worse
    at peaks than dating months and converting; the two are close, so the monthly
    rule is the default and this is offered for a caller who wants the frequency of
    the answer to match the frequency of the question.
    """
    q = [(nm, to_quarter(s)) for nm, s in channels]
    dt = [channel_trough(s, w0, w1, band_trough, 1, lookback, abstain) for nm, s in q]
    trough = _median(dt)
    end = trough if trough is not None else w1
    comp = composite_deviation(q, lookback, 1, 1)[w0:end].dropna()
    cross = next((d for d, v in comp.items() if v >= 2.0), None)
    p0 = w0 if cross is None else max(w0, cross - pd.DateOffset(months=3 * peak_cap))
    dp = [channel_peak(s, p0, end, band_peak, 1, abstain) for nm, s in q]
    return dict(peak=_median(dp), trough=trough, verdict='quarterly',
                spread_peak=spread(dp), spread_trough=spread(dt))

# ================================================================= the entry point
#
# date_turning_points() ALWAYS returns a peak and a trough.  The verdict labels the
# answer; it never withholds one.  Where one form yields nothing the other fills in,
# and where both do, the extremum of the composite activity index is used.
#
# `concept` is a property of the QUESTION, not of the data, so the caller may set it:
#
#   'level'      the classical turning point - the month activity stops falling.
#                What the NBER, the C.D. Howe Institute, CODACE, CEPR-EABCN, the AEE
#                and the AFSE committees date.
#   'growth'     the growth-cycle turning point - the month the gap to trend stops
#                widening.  What Statistics Korea dates (동행지수 순환변동치).
#   'diffusion'  the diffusion turning point - the month breadth crosses a half.
#                What Japan's ESRI dates.
#   'auto'       level, unless no channel fell by min_depth percent, in which case
#                there is no level turning point to find and the growth-cycle form
#                is used instead.  This is the default.

def date_turning_points(channels, w0, w1, volume_channels=None, concept='auto',
                        band_trough=0.12, band_peak=0.01, smooth=3, lookback=12,
                        peak_cap=18, min_depth=5.0, max_spread=9, lam=500000.0,
                        di_line=45.0, di_run=4, di_band=0.30,
                        reference_series='monthly reference GDP',
                        dating_series=None):
    """Date one contraction.  The entry point; everything else serves this.

    ARGUMENTS
      channels          [(name, series)] - the panel, in pro-cyclical LEVELS.  A
                        counter-cyclical series must be converted by procyclical()
                        before it is passed in.
      w0, w1            the search window.  Twelve months either side of the official
                        dates is the scoring convention used throughout this program;
                        it is a convention, not a parameter, and narrowing it makes
                        the task easier rather than the rule better.
      volume_channels   the subset used for the DEPTH screen.  Quantities only: a
                        deflated value series can fall on price alone.
      concept           'level', 'growth', 'diffusion', 'quarterly GDP', or 'auto'.
                        Route each chronology to the concept its own committee names.
                        'auto' decides from the data, which is a fallback, not a
                        method.
      band_trough,      the widths of the two within-band runs, as fractions of the
      band_peak         episode's own peak-to-trough amplitude.  Shipped at 0.12 and
                        0.01.  The rule is flat in them.
      smooth, lookback  n and L of the deviation statistic.  Monthly panels use 3 and
                        12; a quarterly chronology uses 1 and 4, which is the same
                        rule read at the frequency the committee publishes in.
      peak_cap          how far before the episode's own two-per-cent crossing the
                        peak search may reach, so that it cannot find an earlier
                        expansion's plateau.
      min_depth         the depth screen, in per cent.  Below it the episode has no
                        level turning point to find and the cyclical component is
                        dated instead - and the answer says so.
      max_spread        beyond this many months of channel disagreement the verdict
                        is 'wide band'.  It labels the answer; it never withholds it.
      dating_series     an explicit override for a committee that names the series it
                        dates: France's quarterly GDP, Canada's asymmetric route.

    RETURNS a dict carrying peak, trough, the verdict, the concept actually dated,
    the number of channels behind each date, their first-to-last spread, and the
    depth of the deepest channel.  Those four numbers are what make an
    always-answering rule honest rather than merely confident: the rule never
    declines, so the answer has to carry how much it is worth.
    """
    channels = list(channels)
    if not channels:
        raise ValueError('date_turning_points() needs at least one channel')
    w0, w1 = pd.Timestamp(w0), pd.Timestamp(w1)
    if w0 >= w1:
        raise ValueError(f'the window is empty or reversed: {w0:%Y-%m} to {w1:%Y-%m}')
    if concept not in ('auto', 'level', 'growth', 'diffusion', 'quarterly GDP'):
        raise ValueError(f'unknown concept {concept!r}')
    for _b, _n in ((band_trough, 'band_trough'), (band_peak, 'band_peak')):
        if not 0.0 <= _b <= 1.0:
            raise ValueError(f'{_n} is a fraction of the amplitude and must lie in [0,1], got {_b}')

    q = list(volume_channels) if volume_channels else channels
    deepest = None
    for nm, s in q:
        d = max_drawdown(_ma(s, smooth)[w0:w1].dropna())
        if d is not None and (deepest is None or d < deepest): deepest = d
    # Whether the episode has a level contraction to date is a fact about the data,
    # not about the chronology: a chronology that dates levels can still contain an
    # episode in which no channel fell far enough to have a level trough, and the
    # cyclical form is then the one that carries information about it.  A growth
    # chronology is routed to the cyclical form whatever the depth.
    if dating_series is not None:
        # Some committees document the single series they date - the AFSE dates French
        # quarterly GDP, the C.D. Howe Council monthly Canadian GDP since 1961 and
        # industrial production before it.  Where that is so, the two clauses go
        # straight to that series.  If it does not yield both ends the panel below
        # answers instead, so this never costs an answer.
        # (name, series, n, L).  The second element may be one series, a list of
        # series read at both ends, or a dict {'peak': [...], 'trough': [...],
        # 'trough_diffusion': [...]} when the committee's own document names different
        # evidence at the two ends.  The C.D. Howe Council's does: the peak comes from
        # the output series alone, the trough from that series together with monthly
        # employment and the industry diffusion index.
        if len(tuple(dating_series)) != 4:
            raise ValueError('dating_series must be (name, series, smooth, lookback)')
        _nm, s0, _n, _L = dating_series
        if isinstance(s0, dict):
            _sp, _st = list(s0.get('peak', [])), list(s0.get('trough', []))
            _sd = list(s0.get('trough_diffusion', []))
        elif isinstance(s0, list):
            _sp = _st = list(s0); _sd = []
        else:
            _sp = _st = [s0]; _sd = []
        _td = [channel_trough(x, w0, w1, band_trough, _n, _L, False) for x in _st]
        # a diffusion index is read with the diffusion clause wherever it appears
        _td += [channel_trough(x, w0, w1, di_band, 3, 12, False, where='last') for x in _sd]
        tr = _median(_td)
        pk = _median([channel_peak(x, w0, tr if tr is not None else w1, band_peak, _n, False)
                           for x in _sp])
        if pk is not None and tr is not None:
            if pk > tr: pk, tr = tr, pk
            return dict(peak=pk, trough=tr, verdict=_nm,
                        confidence=confidence_tier(None, None), deepest=deepest,
                        channels=len(_st) + len(_sd), spread_peak=None, spread_trough=None,
                        length=_md(tr, pk))

    growth = (concept == 'growth') or (deepest is None or deepest > -abs(min_depth))

    # level form
    dt_a = [channel_trough(s, w0, w1, band_trough, smooth, lookback, True) for nm, s in channels]
    dt_b = [channel_trough(s, w0, w1, band_trough, smooth, lookback, False) for nm, s in channels]
    l_tr = _trimmed_median(dt_a, dt_b)
    # the peak search ends at the trough as the smoothed series places it; the refinement
    # moves the reported trough, not the window
    if REFINE_TROUGH is not None:
        _u = _trimmed_median([channel_trough(s, w0, w1, band_trough, smooth, lookback, True, refine=False) for nm, s in channels],
                             [channel_trough(s, w0, w1, band_trough, smooth, lookback, False, refine=False) for nm, s in channels])
        end = _u if _u is not None else (l_tr if l_tr is not None else w1)
    else:
        end = l_tr if l_tr is not None else w1
    comp = composite_deviation(channels, lookback, smooth, 1)[w0:end].dropna()
    cross = next((d for d, v in comp.items() if v >= 2.0), None)
    p0 = w0 if (cross is None or peak_cap is None) else max(w0, cross - pd.DateOffset(months=peak_cap))
    dp_a = [channel_peak(s, p0, end, band_peak, smooth, True) for nm, s in channels]
    dp_b = [channel_peak(s, p0, end, band_peak, smooth, False) for nm, s in channels]
    l_pk = _trimmed_median(dp_a, dp_b)

    # cyclical form
    #
    # A growth-cycle committee dates a DETRENDED aggregate activity index.  Two
    # instances of that object, in order of preference:
    #   (i)  a published ratio-to-trend reference series, when the statistical
    #        system publishes one (the OECD's measure RS, adjustment RT);
    #   (ii) otherwise the Hodrick-Prescott cyclical component of the panel's own
    #        quantity composite.
    # A detrended series oscillates about its trend and has a sharp extremum, so
    # the flat-bottom band that clause (b) needs on a level is set to zero here.
    g_pk = g_tr = None
    g_note = None
    ref = next((s for nm, s in channels if nm == reference_series), None)
    try:
        if ref is not None and len(_ma(ref, smooth)[w0:w1].dropna()) >= 6:
            g_tr = channel_trough(ref, w0, w1, 0.0, smooth, lookback, False)
            _gu = channel_trough(ref, w0, w1, 0.0, smooth, lookback, False, refine=False)
            g_pk = channel_peak(ref, w0, _gu if _gu is not None else w1, band_peak, smooth, False, refine=False)
        else:
            cy = cyclical_component(q, lam, smooth)
            if len(cy[w0:w1].dropna()) >= 6:
                g_tr = channel_trough(cy, w0, w1, 0.0, 1, lookback, False)
                g_pk = channel_peak(cy, w0, g_tr if g_tr is not None else w1, band_peak, 1, False)
            else:
                g_note = 'fewer than six months of cyclical component in the window'
    # The cyclical form is a FALLBACK, so a panel that cannot support it must not stop
    # the level form from answering.  Only the failures that mean "this panel cannot be
    # detrended" are caught, and the reason is carried out in the answer rather than
    # swallowed; anything else is a bug and is allowed to raise.
    except (ValueError, np.linalg.LinAlgError) as e:
        g_note = f'{type(e).__name__}: {e}' 

    # diffusion form
    d_pk = d_tr = None
    if concept == 'diffusion':
        di = historical_diffusion(channels, 5)
        if di is not None:
            r = date_diffusion(di, w0, w1, di_line, di_run, di_band, 3)
            d_pk, d_tr = r['peak'], r['trough']

    # The fallback order.  A diffusion chronology tries the diffusion form first and
    # then falls back to whichever of the level and cyclical forms fits the episode:
    # a shallow episode has no level contraction to date, so the cyclical form is the
    # one that carries information about it.
    _rest = [(g_pk, g_tr), (l_pk, l_tr)] if growth else [(l_pk, l_tr), (g_pk, g_tr)]
    order = ([(d_pk, d_tr)] + _rest) if concept == 'diffusion' else _rest
    peak = next((p for p, t in order if p is not None), None)
    trough = next((t for p, t in order if t is not None), None)
    if peak is None or trough is None:                    # last resort: the composite
        m = _ma(composite_level(q), smooth)[w0:w1].dropna()
        if len(m) >= 4:
            if trough is None: trough = m.idxmin()
            if peak is None:
                pre = m[:trough]
                peak = pre.idxmax() if len(pre) > 1 else m.idxmax()
    if peak is not None and trough is not None and peak > trough: peak, trough = trough, peak

    sp_t = spread([d for d in dt_a if d is not None] or dt_b)
    sp_p = spread([d for d in dp_a if d is not None] or dp_b)
    parts = []
    if concept == 'diffusion': parts.append('diffusion')
    elif growth: parts.append('growth cycle')
    if len(channels) < 5: parts.append('thin panel')
    if g_note and growth: parts.append(f'no cyclical form ({g_note})')
    return dict(peak=peak, trough=trough,
                verdict=', '.join(parts) or 'level',
                confidence=confidence_tier(sp_p, sp_t),
                deepest=deepest, channels=len(channels),
                spread_peak=sp_p, spread_trough=sp_t,
                length=None if (peak is None or trough is None) else _md(trough, peak))

def confidence_tier(spread_peak, spread_trough):
    """How far apart the channels' own dates fall, in months, turned into a tier.

    READ THIS BEFORE USING IT AS A CONFIDENCE MEASURE, BECAUSE IT NO LONGER IS ONE.
    On the 81 contractions of the nine chronologies for which a spread can be
    computed, the share dated correctly at BOTH ends is:

        tight     both spreads 6 months or less   96 percent  (24/25)
        moderate  7 to 20 months                  93 percent  (26/28)
        wide      more than 20 months             93 percent  (26/28)

    In version 11 the gap between the tight and wide tiers was twenty-five points; in
    version 18 it was nine; it is now three.  The correlation between the spread and
    the worst-end absolute error is +0.08, and finer cuts show no ordering at all
    (0-3 months: 93 per cent; 4-6: 100; 7-12: 95; 13-20: 88; 21-60: 93).

    THE TIER IS DESCRIPTIVE, NOT PREDICTIVE.  It says how much the channels argued.
    It does not say how likely the date is to be wrong, because routing each
    chronology to the object its own committee dates removed most of the episodes
    where a wide spread used to mean a wrong answer.  The measure did not stop
    working; the thing it warned about was largely fixed.  It is kept, and reported,
    because a reader is entitled to know how much disagreement stands behind a date.
    """
    w = max(spread_peak or 0, spread_trough or 0)
    return 'tight' if w <= 6 else 'moderate' if w <= 20 else 'wide'

# ================================================================= speed
def two_stage(channels, w0, from_month, band_trough=0.03, smooth=3, lookback=12,
              horizon=36, stable=3, pub_lag=1, after=None):
    """When a date can first be published, and when it stops changing.

    Pass `after` = the previous trough, so that the search cannot reach back into an
    earlier contraction; without it a double dip reports the first trough twice.

    PROVISIONAL uses clause (a) alone - the month the deviation statistic reached its
    maximum.  It is a complete answer and it is the fastest honest one: on the eight
    US recessions since 1969 it is available 2.5 months after the trough on average
    and is within two months of the NBER's eventual date in seven of the eight.
    FINAL is the first month the full rule's answer stops changing, 9.6 months on
    average.  The NBER announced the 1991, 2001, 2009 and 2020 troughs 21, 20, 15 and
    15 months after the fact.
    """
    if after is not None: w0 = max(w0, after + pd.DateOffset(months=1))
    prov = prov_date = None; path = []
    for k in range(horizon + 1):
        T = from_month + pd.DateOffset(months=k)
        a = []; b = []
        for nm, s in channels:
            ss = s[:T]
            if len(ss) < lookback + smooth + 4: continue
            d = deviation(ss, lookback, smooth)[w0:T].dropna()
            if len(d): a.append(d.idxmax())
            t = channel_trough(ss, w0, T, band_trough, smooth, lookback, True)
            if t is not None: b.append(t)
        pa = _median(a); pb = _median(b)
        if prov is None and pa is not None and pa < T:
            prov = T + pd.DateOffset(months=pub_lag); prov_date = pa
        path.append((T, pb if pb is not None else pa))
    final = path[-1][1]; run = 0; first = None
    for T, d in path:
        if d == final:
            if first is None: first = T
            run += 1
            if run >= stable: break
        else: run = 0; first = None
    return dict(provisional_at=prov, provisional_date=prov_date,
                final_at=None if first is None else first + pd.DateOffset(months=pub_lag),
                final_date=final)

# ================================================================= validation record
#
# SAMPLE.  Eight economies, nine official chronologies, 83 official contractions.
# Shipped configuration: smoothing 3, lookback 12, trough band 0.12, peak band 0.01,
# peak window 18, depth threshold 5.0, both turning points read at the CENTER of the
# within-band run (the diffusion index keeps ESRI's last-month reading), then moved to
# the level's own extremum by the refinement clause described below.
#
#   peaks   78/83 within three months (94%)
#   troughs 80/83 within three months (96%)
#   The 64 contractions dated in months, 63 of them dated: mean absolute error 1.51
#   months at peaks and 1.14 at troughs; exact month 25/63 and 31/63; within one
#   month 42/63 and 47/63; within two 52/63 and 55/63; within three 59/63 and 61/63.
#   (3 September 2026, the opening-edge clause: Japan's January 1977 peak moved from
#   one month late to two; every other end as measured 2 September.)
#   The 19 contractions dated in quarters (three quarterly chronologies and the two
#   Brazilian contractions CODACE dates in quarters): mean absolute error 0.42 and
#   0.32 quarters; exact
#   quarter 11/19 and 13/19; within one quarter 19/19 at each end.  (Brazil's employment
#   channel chained onto PNAD Continua on 2 September 2026: the 2016-Q4 trough moved
#   from one quarter early to the quarter; nothing else moved.)
#   One contraction undated: Japan 1951, no monthly series exists before 1953.
#   (Measured 2 September 2026 with the refinement clause below in force; re-measured
#   3 September with the opening-edge clause, one end moved, above.)
#
# This module is checked against the benchmark harness episode by episode and agrees
# on all 83 dates, not merely on the totals.
#
# REFINEMENT CLAUSE (2 September 2026).  Both dating clauses read a trailing
# three-month mean, and a trailing n-month mean reaches its extremum (n-1)/2 months
# after the level does; the later-of-two-readings trough clause adds up to two more.
# Before the refinement the 63 monthly contractions showed exactly that: mean signed
# error +0.56 months at peaks and +0.65 at troughs, exact month 18/63 and 10/63,
# within one month 34/63 and 28/63, within two 53/63 and 50/63, within three 59/63
# and 60/63 (mean absolute error 1.73 and 1.89).  The clause: after the smoothed
# clauses place a date, move it to the
# extremum of the level inside a small window - the trough to the minimum of the
# UNSMOOTHED level within three months back and one forward (REFINE_TROUGH = (3, 1)),
# the peak to the maximum of a two-month mean within one month back and none forward
# (REFINE_PEAK = (1, 0)).  The peak-search window still ends at the UNREFINED trough,
# so refining the trough never moves the window the peak is looked for in.  It
# applies only to plateau-center searches: a diffusion index keeps its last-month
# reading, and the cyclical form's peak (a detrended index has no trailing-mean
# plateau to correct) keeps its smoothed date.  Chosen by trial over windows (0-4
# back, 0-2 forward) and smoothings (1-3) at each end on the nine chronologies; the
# choice was then run on the four held-out chronologies, whose dates were not used
# to choose anything:
#   nine chronologies   peaks   exact 18 -> 25, within one 34 -> 43, within two 53 -> 52,
#   (63 monthly)                within three 59 -> 59; signed error +0.56 -> +0.13
#                       troughs exact 10 -> 31, within one 28 -> 47, within two 50 -> 55,
#                               within three 60 -> 61; signed error +0.65 -> -0.25
#   held out            peaks   (33) exact 10 -> 12, within one 19 -> 21, within three 28 -> 27
#                       troughs (33) exact  6 -> 14, within one 19 -> 24, within three 29 -> 28
#                       (South Africa and Taiwan on the committee's own object, Germany and
#                       Mexico on the panel; Mexico's 1983 trough, whose contraction has no
#                       published peak, is the 34th and moves from three months out to two)
#   Two held-out dates cross three months: Germany's January 1974 peak (Council)
#   moves from October to September 1973, which is one month from ECRI's August 1973;
#   Taiwan's December 1998 trough moves from September to July 1998 on a floor the
#   NDC index holds flat from July to November 1998 (96.58 - 96.68): the committee
#   took the last month of the floor, the clause the lowest.  Quarterly dating is
#   untouched (smooth = 1 there).  Over all thirteen chronologies 105/116 peaks and
#   109/117 troughs are within three months (before: 106/116 and 109/117).
#
# FREQUENCY.  A chronology that dates quarters is dated in quarters: the channels are
# averaged with to_quarter() and the two clauses applied with smooth=1, lookback=4 -
# the same n and L the French route already used.  Dating a monthly panel and then
# rounding the answer to a quarter mixes two frequencies.  This takes the euro area
# to 6/6 and 6/6 with a mean peak error of exactly zero, and the exactly-right peaks
# across the three quarterly chronologies from 6 to 10; it costs Spain's 1978 peak,
# on a three-channel panel, which moves from one quarter out to two (measured again
# on 2 September 2026 with the current panel: one quarter out, +1).
#
# DOCUMENTED DATING SERIES.  Two committees name the evidence they date, and both are
# routed to it rather than to a generic panel.
#   FRANCE.  The AFSE dates French quarterly GDP in constant euros from INSEE.
#   Routed to it: 5/5 and 5/5, mean trough error zero.
#   CANADA.  Cross and Bergevin, "Turning Points: Business Cycles in Canada since
#   1926", C.D. Howe Institute Commentary 366, p.4: "for recent decades, we use
#   quarterly GDP and employment data to identify probable instances of recession,
#   with the exact monthly data then refined with either monthly GDP post-1961 or
#   industrial production prior to 1961, along with monthly employment."  And: "we
#   use a diffusion index for GDP, which Statistics Canada formerly calculated, that
#   shows the percentage of industries that expand output in a particular month."
#   The document is asymmetric between the ends and says so episode by episode: the
#   peak comes from the output series alone ("Industrial production peaked in March
#   1960, which points to this month as the peak for this cycle"), the trough from
#   all three together ("Monthly GDP and employment started to level off in April
#   1992, one month after the diffusion index struggled to reach the 50 percent
#   barrier").  Routed exactly so: Canada 11/12 peaks with nine of twelve exact, and
#   11/12 troughs, up from 9/12.  Adding the diffusion index to the peak as well,
#   which the document does not do, costs a peak.
#   The diffusion index is not published any more and is rebuilt from Statistics
#   Canada tables 36-10-0378 (14 SIC divisions, 1961-1997) and 36-10-0434 (20 two-
#   digit NAICS sectors, 1997 on) as the share of industries rising each month.  It
#   is read with the DIFFUSION clause - wider band, last month inside it - because
#   that is how the rule reads a diffusion index wherever it appears.
#   The CEPR-EABCN and Spanish committees are NOT routed to GDP even though it would
#   now cost nothing, because both documents name a panel.  A routing rule that is
#   allowed to follow the score is not a routing rule.
#
# SPEED, on claims data, at both ends, with no look-ahead of any kind.
#
#   THIS REPLACES THE VERSION 17 RECORD, WHICH IS WITHDRAWN.  Two faults were found in
#   it here, and both are stated because the number that changes is the headline.
#     (1) The seasonal factors were estimated on the WHOLE HISTORY TO DATE.  That is
#         real time - no observation used information that did not yet exist - but it
#         fits one fixed calendar to fifty-five years, and the seasonal calendar of
#         state claims has moved a great deal since the 1970s.  It left 10.4 log points
#         of month-of-year pattern in the adjusted national series and 18.8 over
#         2015-2026.  The state field crossed its threshold every May and June because
#         of it.  Re-estimated on a MOVING SEVEN-YEAR WINDOW - the span of the default
#         3x5 seasonal filter in X-13ARIMA-SEATS, so the length is the standard one -
#         with MEDIANS across the years in the window, the residual falls to 4.5 and
#         6.9.  On the corrected series the version 17 detectors fall from 7/9 and 7/9
#         to 5/9 and 6/9.
#     (2) Continued weeks claimed in ETA 539 is field c8.  The version 17 panel took it
#         from c7, which is WORK-SHARE EQUIVALENT INITIAL CLAIMS and is zero or near
#         zero for most jurisdictions in most weeks.  Field names now come from the
#         Department's own data map for TABLE ar539 and TABLE ar5159
#         (oui.doleta.gov/dmstree/handbooks/402/402_4/4024c6/4024c6.pdf, pp. 41, 58).
#
#   DATA (all public, no registered key), with the Department's own field names:
#     ETA 5159 line 101 col.1  c1   initial claims, state UI            monthly 1971-01
#     ETA 5159 line 201 col.10 c21  continued weeks claimed, intrastate monthly 1971-01
#     ETA 5159 line 301 col.14 c38  weeks compensated, all weeks        monthly 1971-01
#     ETA 5159 line 303 col.21 c51  first payments, state UI total      monthly 1971-01
#     ETA 539                  c3   initial claims                      weekly  1986-02
#     ETA 539                  c8   continued weeks claimed             weekly  1986-02
#   The weekly file's first row is 1984-06-02 but fewer than fifteen jurisdictions report
#   before 1986-02-08, so 1986 is the honest start and the monthly file carries 1971-1986.
#
#   SEASONAL ADJUSTMENT in real time with a pooled warm-up: month-of-year factors
#   re-estimated each December from the data then available, on a moving seven-year
#   window, as medians across the years in the window, applied unchanged for twelve
#   months, and POOLED ACROSS JURISDICTIONS until a jurisdiction has five years of its
#   own history.  Every jurisdiction shares the calendar, so one year of fifty-three of
#   them carries as much information about the month-of-year pattern as fifty-three
#   years of one.
#
#   PEAK is a diffusion question, and the index is built the way ESRI builds one -
#   channel_phase() then claims_diffusion() then diffusion_peak_calls().  A turning
#   point goes on EACH of the 106 channels first (fifty-three jurisdictions' initial
#   claims and the same jurisdictions' continued weeks claimed), so the index changes
#   only when a channel turns and the fifty-per-cent crossing is readable.  Amplitude 48
#   log points, minimum phase 13 months.  The crossing is read with ESRI's own clause -
#   the peak is the last month the deteriorating share stood below the line - and
#   censored by ESRI's own duration rule, a phase of at least five months and a cycle of
#   at least fifteen.  Those two numbers are NOT fitted: the record is identical at every
#   censoring length from three months to eight and from fifteen to twenty-four, so using
#   the committee's numbers costs nothing and removes two free parameters.
#
#   TROUGH is a level question - level_trough_calls().  Claims are counter-cyclical, so
#   the month claims peak is the month activity bottoms.  Arms at fifty log points above
#   the trailing thirty-month minimum, fires once the maximum has been passed and the
#   series has fallen away from it, dates the trough at the maximum, and returns to quiet
#   only once the gap has closed and stayed closed for three months.
#
#   published   dated      official     lag  error
#   Dec 1973    Oct 1973   Nov 1973     +1     -1     peak
#   Apr 1975    Jan 1975   Mar 1975     +1     -2     trough
#   Feb 1980    Dec 1979   Jan 1980     +1     -1     peak
#   Aug 1980    Jun 1980   Jul 1980     +1     -1     trough
#   Sep 1990    Jul 1990   Jul 1990     +2      0     peak
#   May 1991    Mar 1991   Mar 1991     +2      0     trough
#   May 2001    Mar 2001   Mar 2001     +2      0     peak
#   Jan 2002    Nov 2001   Nov 2001     +2      0     trough
#   Aug 2008    Jun 2008   Dec 2007     +8     +6     peak   (late, see below)
#   Jun 2009    Apr 2009   Jun 2009      0     -2     trough
#   Apr 2020    Feb 2020   Feb 2020     +2      0     peak
#   Jun 2020    Apr 2020   Apr 2020     +2      0     trough
#   Aug 2023    Jun 2023   Jun 2023     +2      0     peak   (the episode Paper 1 dates)
#
#   THIRTEEN CALLS IN FIFTY-FOUR YEARS.  Every one of the thirteen falls inside a
#   recession - the false-alarm count is ZERO at both ends - and twelve of them are
#   inside two months on both lag and error.  Six of nine peaks and six of nine troughs
#   are inside the bar.  Mean absolute dating error 0.33 months at peaks and 0.83 at
#   troughs; mean publication lag 1.67 and 1.33 months.
#   PAPER 1's EPISODE IS DATED EXACTLY: published August 2023, dated June 2023, which is
#   Paper 1's own onset month.  It is the only peak call between 2020 and the data edge.
#
#   WHAT IS MISSED, AND WHY.  One call is late: December 2007, fired in August 2008 and
#   dated June 2008.  The claims field did not broaden until then; the NBER's date rests
#   on payroll employment, which turned first.  It is shown rather than dropped, and even
#   so it beats the committee's own announcement by four months.
#   The 1981-82 double dip is ONE episode to a machine that emits one call per episode:
#   the 1980 trough and the 1981 peak are twelve months apart and the state claims field
#   never returned to base between them, so the July 1981 peak and the November 1982
#   trough are absent from the record entirely and no censoring length recovers them.
#   The same structural limit accounts for Paper 1's March 2024 peak, which stands inside
#   the episode already called in 2023, and for Paper 1's August 2024 and May 2026 ends,
#   which are return-to-base events in a rolling episode rather than claims-maximum
#   events, and which the level clause has no way to express.
#
#   CHOSEN OUT OF SAMPLE.  Leaving each of the nine turning points out in turn and
#   choosing the three settings on the other eight over 924 candidates, ALL NINE FOLDS
#   CHOOSE THE SAME CONFIGURATION and it is the shipped one; out of sample it reaches the
#   same six of nine.  The neighbourhood is a plateau, not a point: every amplitude from
#   44 to 48 log points crossed with every minimum phase from 12 to 14 months gives six
#   hits and one or two other calls.
#
#   TRIED AND LOST, recorded because the negatives are the reason to believe the rest:
#     a level breadth index (share of jurisdictions a fixed distance above their own
#       trailing minimum, which is what version 17 used) - 5/9 with 2 other calls at
#       best, over 1.5 million settings, four channel combinations, fixed and
#       noise-scaled distances, and both a level and a rise-from-trailing-low clause;
#     a two-key design, diffusion dates and the level field confirms - 5/9 at best;
#     scaling the amplitude filter to each channel's own noise, which is how Bry and
#       Boschan's filter is conventionally set - 5/9 at best, at every kappa from 2 to
#       12 and every floor.  Third time a noise-scaled variant has lost in this program;
#     adding weeks compensated and first payments to the two channels used - worse;
#     the raw diffusion index, share of channels higher than k months earlier with no
#       per-channel turning point - 7/9 but with 41 other calls.  The per-channel turning
#       point is what makes the crossing readable, which is ESRI's reason for it;
#     the Daily Treasury Statement's withheld income and FICA taxes, daily from October
#       2005 and published one business day after the day they cover - the fastest payroll
#       measure that exists.  A real-time detector on the smoothed year-over-year rate
#       reaches 1 of the 4 turning points it can reach, with 9 other calls; retrospectively
#       it dates the December 2007 peak exactly and nothing else.  The month-to-month noise
#       in federal tax deposits is larger than the cycle in them.
#       (CORRECTION: version 17 took this series from the wrong table.  The withheld series
#       is federal_tax_deposits / "Withheld Income and Employment Taxes" to 2023-02-13 and
#       deposits_withdrawals_operating_cash / "Taxes - Withheld Individual/FICA" after it;
#       the earlier pull took "Individual Income and Employment Taxes, NOT Withheld" -
#       $270m against $11,736m on 2019-03-15.  The correct series was rebuilt and it is the
#       correct series that fails.)
#   THE TROUGH WAS SEARCHED EXHAUSTIVELY: 987,000 settings over seven national objects,
#   four smoothings, six lookbacks, three run lengths, seven fall thresholds, eight arming
#   gaps, seven re-arming gaps and five confirmation lengths.  Six of nine with no other
#   call is the ceiling; no setting reaches seven.  November 1982 and March 1991 are never
#   both caught - every setting that finds one loses the other, which is the double-dip
#   limit seen from the trough end.
#
#   THE WEEKLY FILE FINDS DECEMBER 2007 AND THE MONTHLY FILE DOES NOT.  The same detector
#   on the weekly panel (same 106 channels, 1986 on, amplitude in the same log points,
#   minimum phase in weeks, warm-up set to twice the minimum phase so the length is a rule
#   and not a choice) publishes in November 2007 and dates the peak November 2007 - a month
#   before the committee's month and thirteen months before the committee said so - and
#   also gets 2001-03 at -1/-1, 2020-02 at +1/+1 and Paper 1's 2023-06 at -2/-2.  Four of
#   the six turning points inside its span.  IT PAYS TWO FALSE ALARMS: over 1,260 settings
#   the weekly ceiling is four hits with two calls outside every recession, and no setting
#   reaches five.  A different family of settings reaches Paper 1's 2024-03 peak at +2/+2
#   but never together with 2007-12.  The monthly record is shipped because a rule that
#   says nothing false is the one a committee could use; the weekly result is reported
#   because it locates the missing evidence - December 2007 is in the claims data at weekly
#   frequency and the monthly aggregate destroys it.
#
#   THE FLOOR IS PUBLICATION, NOT THE RULE.  UI Reports Handbook No. 401, ETA 5159
#   section C: the report "is due in the ETA National Office on the 15th day of the month
#   following each calendar month to which it relates."  So a call resting on month t can
#   be made in the middle of month t+1 and not before, and the table's publication month
#   is t+1 throughout - the earliest the data allows, with nothing added by the rule.
#   The weekly report is due "by the opening of business on the Tuesday following the
#   close of the reference week", so a weekly implementation would be about a month
#   faster at the cost of a noisier index.
#
#   AGAINST THE COMMITTEES.  Against the NBER's own announcement dates the rule is
#   earlier on every one of the ten turning points where a comparison is possible, by two
#   to nineteen months - including the one call it makes late.
#   ESRI's announcement dates are the second such comparison and carry a published
#   vintage, since the Institute sets a PROVISIONAL date and then a FINAL one:
#     peak   Feb 2008  provisional Jan 2009 at Oct 2007   final 19 Oct 2011 at Feb 2008
#     trough Mar 2009  provisional Jun 2010 at Mar 2009   final 19 Oct 2011 at Mar 2009
#     peak   Mar 2012  provisional 21 Aug 2013 at Apr 2012 final 24 Jul 2015 at Mar 2012
#     trough Nov 2012  provisional 30 May 2014 at Nov 2012 final 24 Jul 2015 at Nov 2012
#     peak   Oct 2018  provisional 30 Jul 2020 at Oct 2018 final 19 Jul 2022 at Oct 2018
#     trough May 2020  provisional 30 Nov 2021 at May 2020 final 19 Jul 2022 at May 2020
#   TWO OF THE SIX PROVISIONAL DATES WERE LATER REVISED - the 2008 peak by four months
#   and the 2012 peak by one.  A committee's own date moves by more than this rule's mean
#   error.  Provisional dates run 11 to 21 months after the event, final ones 26 to 45.
#
#   THE TWO CLAUSES SEPARATE TWO DIFFERENT OBJECTS.  ESRI states both clauses on one
#   index, so it costs nothing to ask what this one says at the trough -
#   diffusion_trough_calls().  On the seven American troughs it finds NONE and makes eight
#   other calls, while the level clause finds six of seven with no other call: the peak is
#   a diffusion question and the trough is a level question, and that comes out of the
#   American claims data rather than being put in.  The one thing the diffusion clause
#   DOES find is Paper 1's rolling-episode end - the deteriorating share crosses back below
#   half in March 2026, dating a trough at February 2026 against Paper 1's May 2026, three
#   months early, published June to August 2026 depending on the confirmation length.  At
#   amplitude 46 and minimum phase 18 it dates March 2026 and publishes July 2026, inside
#   two months at both ends, but that setting makes seven other calls and is not shippable.
#   Paper 1's August 2024 end is found by neither clause: the deteriorating share never
#   falls below half in 2024 and the national claims gap never exceeds twenty log points.
#
#   The question "how fast can it name a trough it is TOLD has occurred" stays withdrawn:
#   giving the rule data through month T and asking for a trough in a window ending at T
#   is an oracle, since the trough clause then has nowhere to look but the window's end.
#
#   FIRST PRINTS OUTSIDE THE UNITED STATES (2 September 2026, memo v26 section 8c).  The
#   OECD's short-term-statistics revisions database - every monthly edition of its Main
#   Economic Indicators from February 1999, each carrying the full history as it stood
#   that month; public SDMX, no key - was walked edition by edition with the level route
#   on production, retail and (where carried) employment, the contraction called at the
#   first edition in which D reaches 2 per cent and the trough by real_time_trough_calls'
#   decision (lab/oecd_rt/replay_oecd.py).  Thirty-eight contractions in eleven
#   economies.  Of the ends called, first prints date about as well as the final edition
#   of the same two- or three-channel panel (monthly peaks 6 exact / 10 within one / 15
#   within three of 19 called; troughs 4 / 12 / 18 of 19); the losses are the thin panel
#   and the concept (nine uncalled peaks, every one a growth-cycle or diffusion committee
#   date), not the revisions.  NO END IS CALLED WITHIN THE MONTH: the earliest peak call
#   is four months after the peak month, the earliest trough call three - the monthly
#   floor the American rows show, which the weekly claims file is what breaks, and no
#   other economy publishes a weekly file.  On the three quarterly committees' own object
#   - GDP volume as first published (replay_oecd_q.py) - the rule calls 6 of 8 peaks, 5 to
#   the quarter, and 7 of 8 troughs, all within a quarter, with no other dated call in
#   twenty-seven years; the two it does not date are the second dips of the double-dip
#   contractions (the euro area's 2011Q3, Spain's 2010Q4).  Two zero-lag sources were
#   then tried: Germany's registered unemployment (a negative: troughs 5/7 within six
#   months with five other calls, peaks 1/7) and Canada's Labour Force Survey by
#   province, on which the American breadth detector reaches 4/4 Council peaks since 1981
#   within three months (one exact) on data zero to four months after, with one or two
#   other calls a decade - a grid ceiling, not a record, and the standard is not met.
#
#   EVERY MONTHLY END ON ONE DENOMINATOR (2 September 2026, memo v27 section 1;
#   lab/monthly_ends_all.py).  The nine chronologies' reachable monthly ends (61 peaks,
#   62 troughs) and the four held-out chronologies' (33 and 34) together: peaks exact
#   36/94, within one 66/94, within three 87/94, mean absolute error 1.62 months; troughs
#   44/96, 70/96, 91/96, 1.31 months.  With the 19 quarterly ends, 106/113 and 110/115.
#
# LEAVE ONE CHRONOLOGY OUT, nine times: out of sample 77/83 peaks and 79/83 troughs,
# 94 percent; in sample 95 - 156 endpoints of 166 out of sample against 157 in.  All
# nine folds pick the same bands and the same peak window; EIGHT OF NINE PICK THE
# SHIPPED DEPTH THRESHOLD OF 5, and the Japanese fold picks 3.  The gap is one
# endpoint and has stayed one endpoint through the two largest gains the rule has
# made, because those gains came from reading committees' own methodology documents
# and finding the series they name rather than from where the parameters sat.  The
# center-of-plateau reading is picked by eight folds of nine; the
# later-of-two-middle-months median by nine of nine.
#
# HELD OUT.  The NBER's interwar contractions of 1920, 1923 and 1926 were added after
# the configuration was frozen and were never used to choose anything.  All six of
# their endpoints are dated correctly.
#
# HELD OUT, a tenth chronology.  The South African Reserve Bank publishes an official
# reference chronology and states its own concept: it "identifies reference turning
# points in the business cycle according to the growth cycle definition, which entails
# identifying turning points in the fluctuations around the long-term trend of aggregate
# economic activity" (Quarterly Bulletin, September 2025).  Eleven of its contractions
# fall inside the monthly evidence.  Nothing about South Africa entered any choice; the
# configuration below is unchanged.  On the SARB's own composite coincident business
# cycle indicator (series DIFN002A, monthly and seasonally adjusted from January 1960,
# through the Reserve Bank's public API), divided by its own Hodrick-Prescott trend in
# logs and read with the growth clauses:
#     the OECD's ratio-to-trend reference series - the public substitute   5/11   5/11
#     the panel of South African channels, growth form                     5/11   5/11
#     the SARB's own indicator dated as a LEVEL rather than a growth cycle 5/11   7/11
#     the SARB's own indicator, growth clauses                             8/11   9/11
# This is the paper's claim reproduced on evidence the rule has never seen: the failure
# mode is the object, not the method.  It is also the controlled version of the Korean
# argument, since there the committee's own object is public and Korea's is not.
# Counting South Africa in rather than holding it out, the sample is 94 contractions and
# the rule dates 83 peaks and 87 troughs.
#
# SPAIN'S PANEL, WIDENED.  The Banco de Espana's Boletin Estadistico is a free keyless
# CSV service and carries four monthly PRODUCTION VOLUMES that reach further back than
# the OECD's Spanish panel: cement production from 1955-01 (D_1IE00000), steel
# production from 1968-01 (D_1ID10000), and gasoline and diesel consumption from
# 1969-01 (D_1IN1100T, D_1IN1200T), all from
# www.bde.es/webbe/es/estadisticas/compartido/datos/csv/.  They are the same class of
# object as the channels already voting.  The 1974 contraction goes from two channels
# to six and the 1978 contraction from three to seven, and SPAIN GOES FROM 5/6 AND 5/6
# TO 6/6 AND 6/6 with the 1978-Q3 peak dated exactly.  The choice is flat: adding steel
# availability and apparent cement consumption changes nothing; adding vehicle
# registrations is worse and would contradict the panel's own skip list.
# TRAP: the path in the Bank's own CSV manual (webbde/es/estadis/infoest/series/) is
# dead and returns an HTML 404 page under HTTP 200 - a soft 404 that a status check
# alone reads as success.  File names must also be lower case.
#
# HELD OUT, a twelfth chronology: GERMANY - and the panel-dating committee the
# channel-depth question needed.  The German Council of Economic Experts is a statutory
# body (Act of 14 August 1963) that has dated German cycles since 1950 in MONTHS.  Its
# own words: it dates "klassische Konjunkturzyklen" and "folgt dabei keinem festen
# Algorithmus"; "zur Identifikation der zyklischen Hoch- und Tiefpunkte werden MEHRERE
# makrooekonomische Indikatoren auf Monats- und Quartalsbasis herangezogen"; the monthly
# ones are "die Produktion im Produzierenden Gewerbe ohne Bau, die realen
# Auftragseingaenge in der Industrie, die realen Umsaetze im Einzelhandel sowie die
# Arbeitslosenquote"; and "die BESCHRAENKUNG AUF LEDIGLICH EINE REFERENZZEITREIHE stellt
# EINEN NACHTEIL dar".  (Arbeitspapier 13/2018, pp. 10, 12, 41.)
# Seven contractions, shipped configuration, nothing about Germany in any choice:
#     the two named monthly channels available in a long series   5/7  5/7
#     the full six-channel German panel                           6/7  6/7
#   (those two rows are as first measured; the refinement clause of 2 September 2026 made
#   them 4/7 6/7 and 5/7 6/7.  The Council's other two named channels - real orders from
#   1952 and the unemployment rate from 1949, Bundesbank via DBnomics - were found later
#   that day, and THE COUNCIL'S OWN FOUR ARE THE SHIPPED HELD-OUT ROUTE since memo v27:
#     the four monthly channels the Council itself names           5/7  7/7
#   troughs 1967, 1975, 1982, 1993 and 2009 to the month, 2003 three months early instead
#   of seventeen, 2020 two months late; peaks 1974 and 2020 eleven and ten months early
#   because real orders lead - both were misses at three months on the six-channel panel
#   too.  Over the fourteen ends: exact 6 = 6, within one 10 vs 9, within three 12 vs 11,
#   mean absolute error 2.14 vs 2.43 months.  All thirteen chronologies 106/113 peaks and
#   110/115 troughs on the reachable sample.)
# NOTE THE DIRECTION.  In Japan, Korea, South Africa and Taiwan the committee's own
# composite beats the panel.  In Germany the PANEL beats the named channels.  Same rule:
# Germany's committee reads a panel, so a panel is the right object there.
#
# HELD OUT, a thirteenth chronology: MEXICO - and the earlier "Mexico stays out" is
# withdrawn.  The Comite de Fechado de Ciclos de la Economia de Mexico was established
# 3 February 2021 under an INEGI-IMEF convenio of 16 December 2020, the direct successor
# of the 2020 INEGI working group that the earlier note cited as evidence that no
# committee existed.  Six recessions, 1980-2020, monthly.  Its own words: "ha adoptado
# el ENFOQUE CLASICO"; "el CFCEM hace sus analisis principalmente ... A PARTIR DE SERIES
# DE TIEMPO MENSUALES ... el IGAE total y desagregado en cada uno de sus quince
# subsectores ... Numero de Asegurados Permanentes del IMSS, Indice de Ventas Netas al
# Por Menor ... la Tasa de Desocupacion Urbana y las Importaciones Totales"; criteria are
# Shiskin's three D's.  Six-channel OECD Mexican panel: peaks 3/5, troughs 6/6 with a
# mean trough error of 1.33 months.
#
# A DEPTH-WEIGHTED CHANNEL MEDIAN IS NOT ADOPTED EITHER, and it is the twelfth
# selection or weighting rule to lose.  Weighting each channel's date by its own
# percentage fall raised to gamma, gamma=0.5 takes the UNITED STATES TO 12/12 - the
# 1969 peak fixed - and its mean peak error from 1.25 to 1.08 months.  It costs
# GERMANY two peaks (5/7 to 3/7) and does nothing for Mexico.  Same verdict as the
# hard filter, by a different route, on the same two fresh chronologies: every device
# that fixes 1969 is fitted to 1969.
#
# THE CHANNEL-LEVEL DEPTH FILTER IS NOT ADOPTED, and the reason is now measured.  It
# fixes the American 1969 peak and had never been tested on a panel chronology outside
# the nine.  Run on both new ones: on MEXICO not one date moves at any threshold from
# 0 to 5 per cent; on GERMANY the 1-per-cent setting - the setting that fixes 1969 -
# leaves every date exactly as it was, and 1.5 per cent and above moves one peak from
# +2 to +1 and nothing else.  A filter that fixes one episode in one chronology and
# moves nothing on two fresh panel chronologies is fitted to that episode.
#
# COUNTING ALL FOUR HELD-OUT CHRONOLOGIES IN: 117 contractions across twelve economies
# and thirteen official chronologies; 105 of the 116 published peaks and 109 of the 117
# troughs.  (Mexico's first cycle has no published peak, which is why the denominators
# differ.)
#
# HELD OUT, an eleventh chronology.  The National Development Council of the Republic of
# China has set official reference dates for fifteen Taiwanese business cycles since 1954.
# It states its own concept - "Taiwan's identification of the reference date of economic
# cycle is based on the concept of GROWTH CYCLES" - and its own evidence: "a set of
# representative economic indicators composed into one reference series" drawn from
# "production, consumption, employment, trade, and transaction", "compiled into a
# Diffusion Index that aids in the determination of the reference date of economic cycle".
# The rule already had a branch for the concept and a branch for the diffusion index;
# nothing was added.  Nothing about Taiwan entered any choice; the configuration below is
# the shipped one, unchanged.  Ten of the fifteen contractions fall inside the span of the
# Council's own index (monthly from January 1982), twelve inside the panel's.
#     the panel of Taiwanese channels, growth form                       4/12   5/12
#     the Council's composite index read as a LEVEL                      9/10   7/10
#     the Council's composite index, detrended by the rule's own filter  9/10   9/10
#     the Council's OWN DETRENDED INDEX, growth clauses                 10/10   9/10
# TEN OF TEN PEAKS, MEAN ABSOLUTE ERROR HALF A MONTH - the best peak record of any
# chronology in the paper, on one the configuration has never seen.  Errors 0 0 +1 0 -1 0
# +1 -1 0 +1.  The one bad answer is the 2012 trough, eleven months late on a double
# bottom, which is the mirror of the two South African failures.
# THE GAP BETWEEN THE SUBSTITUTE AND THE OBJECT IS THE LARGEST IN THE PAPER: 4 of 12 on a
# panel of Taiwanese industrial production, employment, exports, earnings and tax receipts,
# against 10 of 10 on the index the committee publishes.  The panel is not bad data; it is
# the wrong object for this committee.
# The Council names a diffusion index too, so that branch was asked: on the same panel it
# dates 8/10 peaks and 7/10 troughs, twice the level panel's score at the peak.  The
# Council's own description of its evidence predicts which branch works.
# Nothing turns on the parameters: 10/10 at every lookback from 9 to 24 months and
# identical at bands 0.00/0.00, 0.12/0.01 and 0.05/0.05.
# DATA, all public, no registered key, through the DGBAS macro statistics database at
# nstatdb.dgbas.gov.tw (webMain.aspx?sys=220&funid=<table>&cycle=<41 monthly>&outmode=8,
# JSON, once a session cookie is held; dates are Republic of China years, +1911):
#   A120101010  the Council's leading and coincident indices, with and without trend, 1982
#   A050104010  industrial and manufacturing production                              1982
#   A040107010  labor force and employment                                          1978
#   A081201010  exports and imports, NTD and USD                                     1981
#   A046301010  regular monthly earnings                                             1973
#   A100101010  national tax receipts                                                1974
# (Counting South Africa and Taiwan alone: 104 contractions, 96 peaks, 97 troughs.)
#
# PLACEBO.  Of the 11 contractions still missed at one end or both, 3 are reachable
# by some setting in a 576-point grid.  Displace the target by +/-12, +/-24 or +36
# months and repeat the whole search: 0 of 11 every time.  The reachability is
# signal, and there is little of it left - 3 of 11, against 10 of 17 two versions ago.
#
# PARAMETER SURFACE.  Over 120 combinations of trough band, lookback and smoothing
# the total runs 144 to 147 endpoints of 166 at the previous clause; the Hodrick-
# Prescott constant is inert between 14,400 and 2,000,000 because the growth route
# dates a published reference series and never reaches the filter; abstention is
# inert because the panels are now wide enough that some channel always turns; the
# 2-percent crossing that anchors the peak search is flat between 1.5 and 3.0.
# The search window (12 months either side of the official dates) is a SCORING
# convention and is not tuned: narrowing the tail makes the task easier, not the rule
# better.
#
# ARCHITECTURE, all three inside the same cascade and with the same concept routing,
# but without the committee-specific dating series and without quarterly aggregation,
# for which the two alternatives have no counterpart:
#   median of the channel dates (used here)        74 peaks / 73 troughs of 83
#   cross-channel median of the normalized levels  64 / 71
#   chain-linked composite index dated once        60 / 72
#
# ESTIMATOR ROUTING.  Eleven ways of choosing the branch per episode from observable
# information have been built and tested against fixed routing by the committee's
# documented concept, and all eleven lose: channels weighted by leave-one-out
# accuracy, the median of the three estimators, a trend-gap-and-spread discriminant,
# diffusion when the panel is wide, the tightest cross-channel spread, the estimator
# least sensitive to dropping a channel, bagged jackknife dates, routing a thin level
# panel to the cyclical form, taking the diffusion trough on a wide level panel (the
# only scheme ever to beat fixed routing in sample - by one hit, which vanished out
# of sample), and a discriminant built from panel width, diffusion depth, contraction
# depth, length and spread (nothing separates the groups).
#
# THE TWO CLAUSES, TESTED BY REMOVAL.  Dropping clause (a) at the trough and using
# the plateau alone costs 15 hits and 26 dates that were inside two months, and
# swings the trough bias from zero to 1.5 months early; the midpoint or the earlier
# of the two is worse still.  Adding the mirror-image partner clause at the peak -
# the last month before the deviation statistic clears a threshold, with the peak the
# earlier of that and the plateau - is worse at every threshold tried, by 5 to 22
# hits.  The asymmetry between the two ends is a property of the object.
#
# CLAUSE READINGS TESTED AND REJECTED.  The threshold clause read as the last month
# above the line anywhere before the minimum (costs 3 peaks); that same threshold
# clause applied to a level rather than a diffusion index (costs 13 peaks); the peak
# window ending at the first 2-percent crossing, or 6 or 12 months after it, rather
# than at the trough (costs 2, 11 and 2 peaks); the FIRST month of the within-band
# run rather than its center (costs 5 peaks); the growth-cycle band set as on a level
# rather than to zero (costs 5 troughs on Korea); the plain extremum and the largest
# peak-to-trough swing as growth-cycle datings; Phase Average Trend in place of the
# published ratio-to-trend series for Korea (no gain, and it breaks 2002).
#
# CHANNELS AND SOURCES TESTED AND REJECTED, each on the full sample: dwellings
# started (-3 peaks), dwelling permits (-1 trough), business confidence balances (-5
# peaks), consumer confidence balances (-6 peaks), a second industrial production
# index added as an extra channel rather than chained onto the front of the first (-5
# peaks), restoring the excluded channels whenever the core panel is thin (-2
# troughs), quarterly GDP pooled into the monthly panels (no change), Brazilian
# production by category of use (no change), Canadian railway freight ton-miles from
# 1946 (-1 trough), dropping the ratio-to-trend reference series from the level route
# (-6 peaks), and routing the euro area and Spain to quarterly GDP alongside France
# (net negative, and against those committees' own documented criteria).
#
# ALSO TESTED AND REJECTED earlier: the anchored form (no rolling window), a
# signal-to-noise channel filter, a noise-scaled band, the formally symmetric peak
# clause, a standardized composite, no smoothing, and lookbacks of 6, 9, 18 and 24.
#
# TWO DEFECTS FIXED, both of which had been costing hits silently:
#   (1) every internal cache keyed on id(), a memory address, without holding the
#       object; a freed temporary's address can be reused, so a cached answer could
#       belong to a question never asked and results depended on allocation history.
#       Each cache now retains a reference to the object it keyed on.  Verified
#       deterministic across three passes with deliberate cache churn between them.
#   (2) the growth-cycle flag was gated on concept == 'auto', so an explicitly
#       routed chronology could never fall back to the cyclical form.  Whether an
#       episode has a level contraction to date is a fact about the data, not about
#       the chronology.
# And one convention that was never stated: with an even number of channel dates the
# median falls between two months.  Python's rounding was silently choosing, and
# differently depending on the parity of half the panel - worth four hits.  The rule
# now takes the later of the two.

# ================================================================= self-test
def self_test(verbose=True):
    """Check this module against its own specification.

    Thirty-one assertions in five groups: the statistic's arithmetic and invariants,
    the two clauses, the panel's median and trim, the errors that must be NAMED rather
    than silent, and the shipped real-time record.  The first twenty-seven run on
    series built here and hold on any machine; the last four need the claims panels and
    are skipped, loudly, when those files are absent.

    Run the module directly to execute them.  Raises AssertionError on the first
    failure, naming it, rather than reporting a count a reader has to interpret.
    Returns the number that passed.
    """
    ok = 0
    def chk(name, cond):
        nonlocal ok
        if cond:
            ok += 1
            if verbose: print(f'  ok   {name}')
        else:
            raise AssertionError(name)
    def raises(exc, fn, *a, **k):
        try: fn(*a, **k)
        except exc: return True
        except Exception: return False
        return False

    idx = pd.date_range('2000-01-01', periods=60, freq='MS')

    # ---- the statistic ------------------------------------------------------
    up = pd.Series(np.arange(100.0, 160.0), index=idx)
    chk('D is never positive on a monotone rise',
        float(deviation(up, 12, 1).dropna().max()) < 0.0)
    step = pd.Series([100.0] * 30 + [90.0] * 30, index=idx)
    chk('D reads a ten-per-cent fall as 10',
        abs(float(deviation(step, 12, 1).dropna().max()) - 10.0) < 1e-9)
    chk('D is scale-invariant',
        np.allclose(deviation(step, 12, 1).dropna().values,
                    deviation(step * 7.3, 12, 1).dropna().values))
    single = [deviation(step, 12 + h, 1, horizons=(0,)) for h in HORIZONS]
    chk('the three-horizon D is the mean of its three single-horizon members',
        np.allclose(deviation(step, 12, 1).dropna().values,
                    pd.concat(single, axis=1).mean(axis=1).dropna().values))
    stat = pd.Series([0, 0, 3, 3, 0, 0, 4, 0, 0], index=idx[:9])
    chk('episodes() finds two runs above the threshold', len(episodes(stat, 2.0)) == 2)
    chk('episodes() merges two runs across a gap', len(episodes(stat, 2.0, gap=3)) == 1)

    # ---- the two clauses ----------------------------------------------------
    tent = pd.Series(np.r_[np.arange(100.0, 130.0), np.arange(130.0, 100.0, -1.0)], index=idx)
    chk('the peak clause finds the apex of a tent',
        channel_peak(tent, idx[0], idx[-1], 0.0, 1) == tent.idxmax())
    valley = pd.Series(np.r_[np.arange(130.0, 100.0, -1.0), np.arange(100.0, 130.0)], index=idx)
    chk('the trough clause finds the bottom of a valley',
        channel_trough(valley, idx[0], idx[-1], 0.0, 1, 12) == valley.idxmin())
    chk('the peak clause abstains when the high sits at the window edge',
        channel_peak(up, idx[0], idx[-1], 0.01, 1) is None)
    chk('the trough clause abstains when still falling at the window edge',
        channel_trough(pd.Series(np.arange(160.0, 100.0, -1.0), index=idx),
                       idx[0], idx[-1], 0.12, 1, 12) is None)
    # the opening edge (3 September 2026): a series that bottomed just before the window and
    # rises through it carries the previous contraction's drawdown at the window's first month
    _tail = pd.Series(np.r_[np.arange(130.0, 100.0, -1.0), np.arange(100.0, 130.0)], index=idx)
    chk('the trough clause abstains when the deviation statistic peaks at the opening month',
        channel_trough(_tail, idx[32], idx[-1], 0.12, 3, 12) is None)
    chk("that abstention is the opening-edge rule and not the closing one (the same series votes with abstain=False)",
        channel_trough(_tail, idx[32], idx[-1], 0.12, 3, 12, abstain=False) is not None)
    chk('the refinement never answers before the window opens',
        channel_trough(_tail, idx[32], idx[-1], 0.12, 3, 12, abstain=False) >= idx[32])
    flat = pd.Series(np.r_[np.arange(100.0, 120.0), [120.0] * 10,
                           np.arange(120.0, 100.0, -1.0), [100.0] * 10], index=idx)
    # The band is a fraction of the amplitude, not of the level: hi=120, lo=100 after
    # the high, so 0.02 admits months at or above 119.6 - the eleven months of the flat
    # top, positions 20 to 30.  Their center is 25 and their last is 30.
    chk('the plateau clause takes the CENTER of a flat top, not its end',
        channel_peak(flat, idx[0], idx[-1], 0.02, 1) == idx[25])
    chk("and the diffusion reading takes the LAST month inside the band",
        channel_peak(flat, idx[0], idx[-1], 0.02, 1, where='last') == idx[30])

    _y = np.cumsum(np.sin(np.arange(240) / 7.0)) + np.arange(240) / 12.0 + 100.0
    _sp = hp_trend(_y)
    import builtins as _b
    _real = _b.__import__
    def _noscipy(nm, *a_, **k_):
        if nm.startswith('scipy'): raise ImportError('scipy withheld for the test')
        return _real(nm, *a_, **k_)
    _b.__import__ = _noscipy
    try:
        _np_ = hp_trend(_y)
    finally:
        _b.__import__ = _real
    chk('the HP filter gives the same trend with and without SciPy',
        float(np.max(np.abs(_sp - _np_))) < 1e-6)

    # ---- the panel ----------------------------------------------------------
    ds = [pd.Timestamp('2000-01-01'), pd.Timestamp('2000-02-01'),
          pd.Timestamp('2000-03-01'), pd.Timestamp('2000-04-01')]
    chk('the median takes the later middle month', _median(ds) == pd.Timestamp('2000-03-01'))
    far = ds + [pd.Timestamp('2004-01-01')]
    chk('the trim drops a channel more than two years from the median',
        _trimmed_median(far, far) == pd.Timestamp('2000-03-01'))
    two = [pd.Timestamp('2000-01-01'), pd.Timestamp('2010-01-01')]
    chk('the trim never leaves fewer than two channels',
        _trimmed_median(two, two) is not None)
    chk('spread is None below two dates', spread([ds[0]]) is None)
    chk('spread is the first-to-last distance in months', spread(ds) == 3)
    dup = _panel_frame([('a', tent), ('a', valley)], lambda x: x)
    chk('two channels under one name do not collapse into one column',
        dup.shape[1] == 2 and list(dup.columns) == ['a', 'a (2)'])

    # ---- errors named rather than silent ------------------------------------
    chk('procyclical rejects an unknown kind', raises(ValueError, procyclical, up, 'levl'))
    neg = pd.Series(np.r_[np.arange(50.0, 20.0, -1.0), np.arange(-10.0, 20.0)], index=idx)
    chk('D refuses a level that reaches zero, and names the month',
        raises(ValueError, deviation, neg, 12, 1))
    chk('the entry point refuses an empty panel',
        raises(ValueError, date_turning_points, [], idx[0], idx[-1]))
    chk('the entry point refuses a reversed window',
        raises(ValueError, date_turning_points, [('a', tent)], idx[-1], idx[0]))
    chk('the entry point refuses a band outside [0,1]',
        raises(ValueError, date_turning_points, [('a', tent)], idx[0], idx[-1],
               band_trough=1.5))
    chk('the entry point refuses an unknown concept',
        raises(ValueError, date_turning_points, [('a', tent)], idx[0], idx[-1],
               concept='vibes'))
    chk('the phase monitor refuses a panel of raw levels, not logs',
        raises(ValueError, channel_phase, pd.DataFrame({'a': [100000.0] * 40})))
    chk('the diffusion clause refuses an index outside 0 to 100 per cent',
        raises(ValueError, diffusion_peak_calls, pd.Series([50.0, 140.0, 20.0])))
    chk('the level clause refuses a raw claims level, not logs',
        raises(ValueError, level_trough_calls, pd.Series([300000.0] * 60)))
    chk('the conjunct refuses a non-positive claims count',
        raises(ValueError, claims_conjunct, pd.Series([100.0, 0.0, 100.0]), pd.Series([100.0] * 3)))
    chk('the conjunct clause refuses log points x100',
        raises(ValueError, conjunct_peak_calls, pd.Series([20.0, 35.0, 12.0])))
    _wk = pd.date_range('2000-01-08', periods=260, freq='7D')
    _ic = pd.Series(300000.0, index=_wk); _cc = pd.Series(2000000.0, index=_wk)
    _ic.iloc[130:170] *= 1.5; _cc.iloc[130:170] *= 1.4          # one rise of 40 log points, lasting 40 weeks
    _cj = claims_conjunct(_ic, _cc)
    _calls = conjunct_peak_calls(_cj, line=0.20, quiet_weeks=26)
    chk('the conjunct is the smaller of the two year-over-year changes',
        abs(float(_cj.loc[_wk[140]]) - np.log(1.4)) < 1e-9)
    chk('one rise gives one call, published seven days after the week the four-week mean crosses',
        len(_calls) == 1 and _calls[0] == _wk[132] + pd.Timedelta(days=7))
    _ic2 = _ic.copy(); _ic2.iloc[180:200] *= 1.5; _cc2 = _cc.copy(); _cc2.iloc[180:200] *= 1.4
    chk('a second rise inside the quiet window does not open a second episode',
        len(conjunct_peak_calls(claims_conjunct(_ic2, _cc2), line=0.20, quiet_weeks=26)) == 1)
    chk('the union takes the earliest publication and one per episode',
        earliest_call([pd.Timestamp('2001-04-28')], [(pd.Timestamp('2001-03-31'), None)],
                      [pd.Timestamp('2007-12-28')]) == [pd.Timestamp('2001-03-31'), pd.Timestamp('2007-12-28')])
    _u = union_calls({'K': [(pd.Timestamp('1971-01-14'), pd.Timestamp('1970-11-01')),
                            (pd.Timestamp('2002-07-25'), pd.Timestamp('2001-11-01'))],
                      'I': [(pd.Timestamp('1970-07-18'), pd.Timestamp('1970-05-01')),
                            (pd.Timestamp('1970-12-26'), pd.Timestamp('1970-11-01')),
                            (pd.Timestamp('2002-01-19'), pd.Timestamp('2001-11-01'))],
                      'P': [(pd.Timestamp('1975-02-18'), pd.Timestamp('1974-12-01'))]},
                     date_order=('K', 'I'))
    chk('the route groups calls into episodes by publication, the earliest opening each',
        [(e['published'], e['leg']) for e in _u] == [(pd.Timestamp('1970-07-18'), 'I'),
                                                     (pd.Timestamp('1975-02-18'), 'P'),
                                                     (pd.Timestamp('2002-01-19'), 'I')])
    chk('the date at the call is the dating object that had fired, the final date the first in date_order',
        (_u[0]['date_at_call'], _u[0]['date'], _u[0]['date_leg'], _u[1]['date_at_call'], _u[1]['date'],
         _u[2]['date_at_call'], _u[2]['date'], _u[2]['date_leg'])
        == (pd.Timestamp('1970-05-01'), pd.Timestamp('1970-11-01'), 'K', None, None,
            pd.Timestamp('2001-11-01'), pd.Timestamp('2001-11-01'), 'K'))
    chk('the route refuses a date_order naming no leg and a call that is not a Timestamp',
        raises(KeyError, union_calls, {'K': []}, ('Z',)) and raises(TypeError, union_calls, {'K': ['2001-03']}))
    chk('the panel builder refuses a non-Series channel',
        raises(TypeError, _panel_frame, [('a', [1, 2, 3])], lambda x: x))

    # ---- behavior -----------------------------------------------------------
    v = np.concatenate([np.linspace(100, 130, 30), np.linspace(130, 105, 18),
                        np.linspace(105, 125, 12)])
    ch = [('a', pd.Series(v, index=idx)), ('b', pd.Series(v * 1.01 + 3, index=idx))]
    a1 = date_turning_points(ch, idx[0], idx[-1], concept='level')
    _ = [deviation(pd.Series(np.random.RandomState(k).rand(60) + 5, index=idx), 12, 3)
         for k in range(20)]
    a2 = date_turning_points(ch, idx[0], idx[-1], concept='level')
    chk('the same question twice gives the same answer',
        (a1['peak'], a1['trough']) == (a2['peak'], a2['trough']))
    chk('the answer never declines: it carries both a peak and a trough',
        a1['peak'] is not None and a1['trough'] is not None)
    chk('the peak never comes after the trough', a1['peak'] <= a1['trough'])
    chk('the answer carries the four numbers that qualify it',
        all(k in a1 for k in ('verdict', 'channels', 'spread_peak', 'deepest')))
    rate = pd.Series(100.0 - v, index=idx)
    ar = date_turning_points([('u', procyclical(rate, 'rate'))], idx[0], idx[-1],
                             concept='level')
    al = date_turning_points([('l', pd.Series(v, index=idx))], idx[0], idx[-1],
                             concept='level')
    chk('a rate read through procyclical() dates the same turn as the level',
        (ar['peak'], ar['trough']) == (al['peak'], al['trough']))

    # ---- the shipped real-time record ---------------------------------------
    import os
    pan = '/home/claude/lab/dol/US_state_monthly_4ch_sa.csv'
    nat = '/home/claude/lab/dol/US_nat_monthly_4ch_sa.csv'
    if os.path.exists(pan) and os.path.exists(nat):
        import hashlib
        chk('the two claims panels are the files the record was measured on',
            [hashlib.sha256(open(f, 'rb').read()).hexdigest() for f in (pan, nat)]
            == ['e03c4511af8d5c0ec058f0e608061514d98263e2b929e93b7a33bea21ef51577',
                '43f60bba15bd57f9143b6a2c097ef04bea848635630e6b854e466ee925094f8f'])
        P = pd.read_csv(pan, index_col=0, parse_dates=True)
        N = pd.read_csv(nat, index_col=0, parse_dates=True)
        cols = [c for c in P.columns
                if c.endswith('| initial claims') or c.endswith('| continued weeks claimed')]
        D = claims_diffusion(P[cols], 48.0, 13)
        pk = [(a.strftime('%Y-%m'), b.strftime('%Y-%m')) for a, b in diffusion_peak_calls(D)]
        tr = [(a.strftime('%Y-%m'), b.strftime('%Y-%m'))
              for a, b in level_trough_calls(np.log(N['initial claims']))]
        chk('seven peak calls, as recorded', pk == [
            ('1973-12','1973-10'), ('1980-02','1979-12'), ('1990-09','1990-07'),
            ('2001-05','2001-03'), ('2008-08','2008-06'), ('2020-04','2020-02'),
            ('2023-08','2023-06')])
        chk('six trough calls, as recorded', tr == [
            ('1975-04','1975-01'), ('1980-08','1980-06'), ('1991-05','1991-03'),
            ('2002-01','2001-11'), ('2009-06','2009-04'), ('2020-06','2020-04')])
        chk('the half-arm re-arm gives the same six calls as the old five-point one on this file',
            level_trough_calls(np.log(N['initial claims']), rearm_gap=5.0) ==
            level_trough_calls(np.log(N['initial claims'])))
        dt = [b.strftime('%Y-%m') for _, b in diffusion_trough_calls(D)]
        chk('the diffusion clause makes eight trough calls and none is an NBER trough',
            len(dt) == 8 and not ({'1975-03','1980-07','1982-11','1991-03','2001-11',
                                   '2009-06','2020-04'} & set(dt)))
        chk("and it is the clause that finds Paper 1's rolling-episode end",
            '2026-02' in dt)
    elif verbose:
        print('  --   the five real-time checks need the claims panels; not on disk')
    # the confirmation leg (3 September 2026)
    _sp = '/home/claude/lab/fh/FH_state_payrolls_nsa.csv'
    if os.path.exists(_sp):
        _P = pd.read_csv(_sp, index_col=0, parse_dates=True)
        _E = [(p.strftime('%Y-%m-%d'), d.strftime('%Y-%m')) for p, d in payroll_breadth_calls(_P)]
        chk('the payroll-breadth confirmer calls the twelve postwar peaks and nothing else, 1949-2024', _E == [
            ('1949-06-20','1949-04'), ('1953-10-20','1953-08'), ('1957-12-20','1957-10'), ('1960-12-20','1960-10'),
            ('1970-09-20','1970-07'), ('1975-02-20','1974-12'), ('1980-07-20','1980-05'), ('1981-11-20','1981-09'),
            ('1991-03-20','1991-01'), ('2001-09-20','2001-07'), ('2008-10-20','2008-08'), ('2020-05-20','2020-03')])
    elif verbose:
        print('  --   the confirmation-leg checks need the state payroll field; not on disk')
    # the conjunction call (3 September 2026, night): a synthetic check of the mechanics
    _u = pd.Series(4.0, index=pd.date_range('2000-01-01', periods=48, freq='MS'))
    _u['2002-01-01':'2003-12-01'] = [4.0, 4.1, 4.3, 4.6, 4.9, 5.2, 5.4, 5.5, 5.5, 5.5, 5.4, 5.3] + [5.2] * 12
    _g = sahm_gap(_u)
    chk("Sahm's gap: flat rate reads zero, the 2002 rise crosses 0.5 in May 2002",
        float(_g['2001-06-01']) == 0.0 and next(t for t, v in _g.items() if v >= 0.5) == pd.Timestamp('2002-05-01'))
    _eps = [{'published': pd.Timestamp('2002-02-20'), 'date_at_call': pd.Timestamp('2001-12-01'), 'date': pd.Timestamp('2001-12-01')},
            {'published': pd.Timestamp('2000-06-20'), 'date_at_call': pd.Timestamp('2000-04-01'), 'date': pd.Timestamp('2000-04-01')}]
    _c = conjunction_calls(_eps, _u)
    chk('the conjunction calls the episode whose Sahm gap crosses (published 5 June 2002, dated February 2002 - the crossing less three) and not the one whose rate never moved',
        len(_c) == 1 and _c[0]['published'] == pd.Timestamp('2002-06-05') and _c[0]['date'] == pd.Timestamp('2002-02-01'))
    # Sahm's own form: the minimum is over the PREVIOUS twelve months (3 September 2026, night)
    _u2 = pd.Series([3.4, 3.7, 3.6, 3.5, 3.8, 3.8, 3.9, 3.7, 3.7, 3.7, 3.9, 3.8, 3.9, 4.0, 4.1, 4.3],
                    index=pd.date_range('2023-04-01', periods=16, freq='MS'))     # the rate as first published, April 2023 to July 2024
    chk("Sahm's form on the 2023-24 first prints reads 0.5333 in July 2024, her published 0.53, not the 0.4999 of a window that includes the current month",
        abs(float(sahm_gap(_u2)['2024-07-01']) - 0.5333) < 1e-3)
    # one call, one date at every turn (3 September 2026, night): the state machine on synthetic legs
    _T = pd.Timestamp
    _pk = {'A': [(_T('2001-04-20'), _T('2001-02-01')), (_T('2001-09-20'), _T('2001-07-01')), (_T('2008-01-20'), _T('2007-12-01'))],
           'B': [(_T('2001-03-31'), _T('2001-03-01')), (_T('2005-03-31'), _T('2005-03-01'))]}
    _tr = {'H': [(_T('2000-12-10'), _T('2000-10-01')), (_T('2002-01-10'), _T('2001-11-01')), (_T('2002-04-10'), _T('2002-02-01')), (_T('2005-09-10'), _T('2005-07-01'))]}
    _ch = american_chronology(_pk, _tr)
    chk('the chronology opens on the first peak call and carries ITS date, ignores the later peak call inside the episode, closes on the first trough call after it, then opens again',
        [(t['kind'], t['leg'], t['published'].strftime('%Y-%m-%d'), t['date'].strftime('%Y-%m')) for t in _ch] ==
        [('peak', 'B', '2001-03-31', '2001-03'), ('trough', 'H', '2002-01-10', '2001-11'), ('peak', 'B', '2005-03-31', '2005-03'), ('trough', 'H', '2005-09-10', '2005-07'), ('peak', 'A', '2008-01-20', '2007-12')])
    _u3 = pd.Series(4.0, index=pd.date_range('1999-01-01', periods=120, freq='MS'))
    _u3['2001-03-01':'2001-08-01'] = [4.1, 4.3, 4.5, 4.7, 4.9, 5.0]; _u3['2001-09-01':] = 5.0
    _chB = american_chronology(_pk, _tr, sahm=sahm_gap(_u3))
    chk('with the rate as the second condition the 2001 call waits for the crossing (June 2001, published 5 July) and keeps the claims date; the 2005 episode, whose rate never moved, is not called',
        [(t['kind'], t['published'].strftime('%Y-%m-%d'), t['date'].strftime('%Y-%m')) for t in _chB] ==
        [('peak', '2001-07-05', '2001-03'), ('trough', '2002-01-10', '2001-11')] and _chB[0]['sahm_month'] == _T('2001-06-01'))
    _chL = american_chronology(_pk, _tr, sahm=sahm_gap(_u3), date_rule='later')
    chk("the 'later' date rule dates the same call to the crossing less three (March 2001) when that is later than the claims date",
        _chL[0]['date'] == _T('2001-03-01') and len(_chL) == 2)
    # a second object beside the rate: whichever is public first carries the condition; the window closes at the claims field's own end
    _v = pd.Series(0.0, index=pd.date_range('1999-01-01', periods=120, freq='MS')); _v['2001-04-01':'2001-12-01'] = 0.9
    _ch2 = american_chronology(_pk, _tr, sahm=sahm_gap(_u3), second=[dict(name='vacancy', gap=_v, line=0.6, pub_day=30)])
    chk('a vacancy object at its line in April 2001 (public 30 May) carries the 2001 call before the rate (5 July); the 2005 episode, where neither object moved, is still not called',
        [(t['kind'], t['published'].strftime('%Y-%m-%d'), t.get('condition')) for t in _ch2 if t['kind'] == 'peak'] == [('peak', '2001-05-30', 'vacancy')])
    _vd = pd.Series(0.0, index=pd.date_range('1999-01-01', '2008-12-31', freq='D')); _vd['2001-04-15':'2001-12-31'] = 1.0
    _chd = american_chronology(_pk, _tr, sahm=sahm_gap(_u3), second=[dict(name='daily', gap=_vd, line=0.5, pub_day=0, pub_lag_days=1)])
    chk('a daily object read on its own dates, public the next day: at its line on 15 April 2001 it carries the 2001 call on 16 April, before the vacancy and the rate',
        [(t['published'].strftime('%Y-%m-%d'), t.get('condition')) for t in _chd if t['kind'] == 'peak'] == [('2001-04-16', 'daily')])
    _v2 = _v.copy(); _v2['2005-10-01':'2005-12-01'] = 0.9     # a crossing after the claims field's own end (10 September 2005) must not confirm the 2005 episode
    _ch3 = american_chronology(_pk, _tr, second=[dict(name='vacancy', gap=_v2, line=0.6, pub_day=30)])
    # Paper 1's end rule as leg S (3 September 2026, night, fifth pass)
    _u4 = pd.Series(4.0, index=pd.date_range('2022-01-01', periods=42, freq='MS'))
    _u4['2023-06-01':'2024-03-01'] = [4.1, 4.2, 4.3, 4.5, 4.7, 4.9, 5.0, 5.0, 4.9, 4.8]; _u4['2024-04-01':] = 4.8
    _gs = sahm_gap(_u4); _S = sahm_end_calls(_gs)
    chk("leg S: the gap crosses 0.5, peaks, and three lower readings later the end is called, dated to the maximum's month and published the 5th of the month after the third reading",
        len(_S) == 1 and _S[0][1] == _gs.idxmax() and _S[0][0] == pd.Timestamp(_gs.idxmax().year, _gs.idxmax().month, 1) + pd.DateOffset(months=4) + pd.Timedelta(days=4))
    _arm = pd.Series(False, index=_u4.index); _arm['2023-10-01'] = True
    chk('leg S is silent where a claims level object armed inside the rate\'s episode', sahm_end_calls(_gs, armed=_arm) == [])
    chk("the second condition's window closes at the claims field's own end: a crossing in October 2005, after the field closed the 2005 episode on 10 September, confirms nothing",
        [t['published'].strftime('%Y-%m-%d') for t in _ch3 if t['kind'] == 'peak'] == ['2001-05-30'])
    if verbose: print(f'{ok} checks passed')
    return ok


def _cli(argv=None):
    """`python bristow_rule_v3.py` runs the self-test.  With --date it dates one
    episode from a directory of two-column CSVs, one per channel:

        python bristow_rule_v3.py --date PANEL_DIR --from 2007-01 --to 2010-06 \
               [--concept level|growth|diffusion|auto] [--rate unemployment.csv]
    """
    import argparse, glob, os
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[1])
    ap.add_argument('--date', metavar='DIR', help='directory of one CSV per channel')
    ap.add_argument('--from', dest='w0', help='window start, YYYY-MM')
    ap.add_argument('--to', dest='w1', help='window end, YYYY-MM')
    ap.add_argument('--concept', default='auto',
                    choices=['auto', 'level', 'growth', 'diffusion'])
    ap.add_argument('--rate', action='append', default=[],
                    help='a file name in DIR that is a RATE rising in a contraction; '
                         'repeatable')
    a = ap.parse_args(argv)
    if not a.date:
        return 0 if self_test() else 1
    if not (a.w0 and a.w1):
        ap.error('--date needs --from and --to')
    files = sorted(glob.glob(os.path.join(a.date, '*.csv')))
    if not files:
        ap.error(f'no CSV files in {a.date}')
    chs = []
    for f in files:
        nm = os.path.splitext(os.path.basename(f))[0]
        kind = 'rate' if os.path.basename(f) in a.rate else 'level'
        chs.append((nm, procyclical(load(f), kind)))
    r = date_turning_points(chs, pd.Timestamp(a.w0), pd.Timestamp(a.w1),
                            concept=a.concept)
    f = lambda d: d.strftime('%Y-%m') if d is not None else '--'
    print(f'peak    {f(r["peak"])}')
    print(f'trough  {f(r["trough"])}')
    print(f'verdict {r["verdict"]}')
    n = lambda x: '--' if x is None else f'{x:g}'          # spreads are whole months
    print(f'channels {r["channels"]}  spread peak {n(r["spread_peak"])} '
          f'trough {n(r["spread_trough"])}  deepest fall '
          f'{"--" if r["deepest"] is None else format(r["deepest"], ".1f") + "%"}')
    return 0


if __name__ == '__main__':
    import sys as _sys
    _sys.exit(_cli())
