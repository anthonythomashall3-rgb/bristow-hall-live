"""
The Bristow Rule, version 3.

A turning point is the month in which the deviation statistic stops rising.

    D(t) = [ max{ m(t-L), ..., m(t-1) } - m(t) ] / max{ m(t-L), ..., m(t-1) } x 100

where m is an n-month moving average of a pro-cyclical activity series.  The Sahm
indicator is the counter-cyclical twin of D applied to the unemployment rate; the
rule was first written for that series and generalizes to any activity level.

The trough of a contraction is the LATER of
    (a) the month D reaches its maximum, and
    (b) the CENTRE month of the run that stays within a band alpha of the
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
tested and removed; it adds nothing and costs two turning points.  Merchandise trade values are not domestic value added and carry the
exchange rate and the price level; passenger car registrations are one product line;
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

# ---------------------------------------------------------------- data handling
def load(path):
    """Read a two-column CSV - date, value - into a clean float series.

    Column NAMES are ignored and the first two columns are taken positionally, so a
    file headed date,value and one headed TIME_PERIOD,OBS_VALUE both load.  Values
    that will not parse become missing and are dropped; duplicate dates keep the LAST
    row, which is the convention every one of this program's sources uses when it
    revises a month in place; the index is sorted.
    """
    d = pd.read_csv(path); d.columns = ['d','v']
    d['d'] = pd.to_datetime(d.d); d['v'] = pd.to_numeric(d.v, errors='coerce')
    s = d.dropna().set_index('d')['v'].astype(float)
    return s[~s.index.duplicated(keep='last')].sort_index()

def procyclical(s, kind='level'):
    """Return a pro-cyclical, strictly positive series.  A rate in percent that rises
    in a contraction (unemployment) becomes 100 - r."""
    return 100.0 - s if kind == 'rate' else s

def _ma(x, n): return x.rolling(n).mean()

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
    m = _ma(x, smooth)
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

def _md(a, b): return (a.year - b.year) * 12 + (a.month - b.month)

# ---------------------------------------------------------------- one channel
PLATEAU_TROUGH = 'mid'   # where in the flat bottom the trough sits
PLATEAU_PEAK   = 'mid'   # where in the flat top the peak sits


def _plateau_pick(on, where):
    """Which month of the within-band run is the turning point.

    'last' - the last month inside the band - is the reading ESRI publishes for a
    diffusion index, and it is the right one there.  On a level it cannot be
    earlier than the extreme itself and is therefore biased late; taking the
    CENTRE of the flat region instead is unbiased by construction and lets the band
    be set wide enough to find the whole plateau rather than its edge.  On the
    eighty-three official contractions this moves the mean error from 1.95 to 1.76
    months at peaks and from 1.93 to 1.67 at troughs, and the late bias at peaks
    from +0.51 months to +0.24.  Chosen out of sample.
    """
    if len(on) == 0: return None
    return on.index[-1] if where == 'last' else on.index[len(on) // 2]


def channel_trough(level, w0, w1, band=0.12, smooth=3, lookback=12, abstain=True, where=None):
    """Later of the peak of D and the last month within `band` of the low."""
    d = deviation(level, lookback, smooth)[w0:w1].dropna()
    if len(d) == 0: return None
    d_peak = d.idxmax()
    m = _ma(level, smooth)[w0:w1].dropna()
    if len(m) < 4: return d_peak
    lo = float(m.min()); i = m.idxmin()
    if abstain and i == m.index[-1]:
        return None                      # still falling at the edge of the window
    hi = float(m[:i].max())
    amp = max(hi - lo, 1e-9)
    on = m[m <= lo + band * amp]
    p = _plateau_pick(on, PLATEAU_TROUGH if where is None else where)
    return max(d_peak, p) if p is not None else d_peak

def channel_peak(level, w0, w1, band=0.01, smooth=3, abstain=True, where=None):
    """Last month within `band` of the high inside the window."""
    m = _ma(level, smooth)[w0:w1].dropna()
    if len(m) < 4: return None
    hi = float(m.max()); i = m.idxmax()
    if abstain and (i == m.index[0] or i == m.index[-1]):
        return None                      # never turned inside the window
    lo = float(m[i:].min()) if len(m[i:]) else float(m.min())
    amp = max(hi - lo, 1e-9)
    on = m[m >= hi - band * amp]
    p = _plateau_pick(on, PLATEAU_PEAK if where is None else where)
    return p if p is not None else i

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

def composite_deviation(channels, lookback=12, smooth=3, min_channels=2, q=0.5):
    """Cross-channel order statistic of D: a depth-and-breadth detector."""
    D = pd.concat([deviation(s, lookback, smooth).rename(nm) for nm, s in channels], axis=1)
    return D.quantile(q, axis=1).where(D.notna().sum(axis=1) >= min_channels)

def composite_level(channels, min_channels=1):
    """Equal-weight chain-linked activity index from an unbalanced panel.  Averages
    the log changes of whatever channels exist in both months, so a channel that
    begins late costs no history and introduces no jump."""
    D = pd.concat([np.log(s.clip(lower=1e-9)).diff().rename(nm) for nm, s in channels], axis=1)
    g = D.mean(axis=1, skipna=True).where(D.notna().sum(axis=1) >= min_channels)
    g = g[g.first_valid_index():]
    return np.exp(g.fillna(0.0).cumsum()) * 100.0

def max_drawdown(m):
    """Largest fall from a running maximum, in percent.  Unlike a peak-to-trough fall
    it does not depend on where the window happens to begin."""
    if len(m) < 4: return None
    run = m.cummax()
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
    """Hodrick-Prescott trend, lambda = 129600 for monthly data (Ravn-Uhlig)."""
    from scipy.sparse import eye, diags
    from scipy.sparse.linalg import spsolve
    y = np.asarray(y, float); n = len(y)
    if n < 5: return y.copy()
    I = eye(n, format='csc')
    D = diags([np.ones(n-2), -2*np.ones(n-2), np.ones(n-2)], [0,1,2], shape=(n-2,n), format='csc')
    return spsolve((I + lam * (D.T @ D)).tocsc(), y)

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
    trough = channel_trough(cy, w0, w1, band, 1, lookback, abstain)
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
    insurance - so a channel in its rising phase is a labour market getting worse.
    """
    ph = channel_phase(panel, amplitude, min_phase)
    fin = np.isfinite((panel * 100.0).values)
    return pd.Series((ph.values > 0).sum(axis=1) / fin.sum(axis=1) * 100.0,
                     index=panel.index).dropna()

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
                       arm_gap=50.0, rearm_gap=5.0, min_phase=3, publication_lag=1):
    """When would the rule have said a trough had happened?

    `claims_log` is the LOG level of seasonally adjusted national claims.  Claims are
    counter-cyclical, so the month claims peak is the month activity bottoms - which is
    the rule's own level clause, read on an inverted series.  The detector arms when the
    smoothed series stands `arm_gap` log points above its own trailing `lookback`-month
    minimum, fires once that maximum has been passed and the series has fallen away from
    it, and dates the trough at the month claims peaked.  After a call it returns to
    quiet only once the gap has closed and stayed closed for `min_phase` months, so no
    episode can be called twice.

    Returns a list of (published, dated) month pairs.  Uses no official chronology.
    """
    N = (claims_log * 100.0).rolling(smooth).mean()
    G = N - N.rolling(lookback, min_periods=lookback // 2).min()
    df = pd.concat([N.rename('n'), G.rename('g')], axis=1).dropna()
    n = df['n'].values; g = df['g'].values; idx = df.index
    out = []; state = 'quiet'; off = 0; nmax = -1e9; ni = 0; fall = 0
    prev = n[0] if len(n) else 0.0
    for i in range(1, len(n)):
        if n[i] > nmax: nmax = n[i]; ni = i; fall = 0
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
    corrupts any phase or diffusion series built from its output."""
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
    P = pd.concat(cols, axis=1)
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
    # ESRI's published rule is the LAST month the index stays below the line.
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

    Tested and NOT adopted.  On the nine chronologies the anchored form dates 51/71
    peaks against 50/71 and 46/71 troughs against 49/71, and on contractions longer
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
    q = volume_channels or channels
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
        _nm, s0, _n, _L = dating_series
        # The third element may be one series, a list of series read at both ends, or
        # a dict {'peak': [...], 'trough': [...]} when the committee's own document
        # uses different evidence at the two ends.  The C.D. Howe Council's does: the
        # peak comes from the output series alone and the trough from that series
        # together with monthly employment.
        # A committee may name different evidence at the two ends, and may name a
        # diffusion index among it.  The C.D. Howe Council's document does both: the
        # peak comes from the output series alone, the trough from that series together
        # with monthly employment and the industry diffusion index.
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
    ref = next((s for nm, s in channels if nm == reference_series), None)
    try:
        if ref is not None and len(_ma(ref, smooth)[w0:w1].dropna()) >= 6:
            g_tr = channel_trough(ref, w0, w1, 0.0, smooth, lookback, False)
            g_pk = channel_peak(ref, w0, g_tr if g_tr is not None else w1, band_peak, smooth, False)
        else:
            cy = cyclical_component(q, lam, smooth)
            if len(cy[w0:w1].dropna()) >= 6:
                g_tr = channel_trough(cy, w0, w1, 0.0, 1, lookback, False)
                g_pk = channel_peak(cy, w0, g_tr if g_tr is not None else w1, band_peak, 1, False)
    except Exception:
        pass

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
    return dict(peak=peak, trough=trough,
                verdict=', '.join(parts) or 'level',
                confidence=confidence_tier(sp_p, sp_t),
                deepest=deepest, channels=len(channels),
                spread_peak=sp_p, spread_trough=sp_t,
                length=None if (peak is None or trough is None) else _md(trough, peak))

def confidence_tier(spread_peak, spread_trough):
    """How far apart the channels' own dates fall, in months, turned into a tier.

    Calibrated on the 74 contractions of the nine chronologies for which a spread can
    be computed.  The share of episodes dated correctly at BOTH ends:

        tight     both spreads 6 months or less   82 percent
        moderate  7 to 20 months                  64 percent
        wide      more than 20 months             50 percent

    The spread is available at the moment the date is produced and needs no official
    chronology, so it is a usable confidence statement rather than a retrospective one.
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
# within-band run (the diffusion index keeps ESRI's last-month reading).
#
#   peaks   78/83 (94%)
#   troughs 79/83 (95%)
#   Six monthly chronologies, 65 dated contractions: mean absolute error 1.95 months
#   at peaks and 1.74 at troughs; within two months 52/65 and 54/65; within three
#   59/65 and 62/65.  Three quarterly chronologies, 17 contractions: mean absolute
#   error 0.47 and 0.41 quarters; within one quarter 16/17 at each end.
#   One contraction undated: Japan 1951, no monthly series exists before 1953.
#
# This module is checked against the benchmark harness episode by episode and agrees
# on all 83 dates, not merely on the totals.
#
# FREQUENCY.  A chronology that dates quarters is dated in quarters: the channels are
# averaged with to_quarter() and the two clauses applied with smooth=1, lookback=4 -
# the same n and L the French route already used.  Dating a monthly panel and then
# rounding the answer to a quarter mixes two frequencies.  This takes the euro area
# to 6/6 and 6/6 with a mean peak error of exactly zero, and the exactly-right peaks
# across the three quarterly chronologies from 6 to 10; it costs Spain's 1978 peak,
# on a three-channel panel, which moves from one quarter out to two.
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
#   A040107010  labour force and employment                                          1978
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
    """Check the module against its own specification, with no external data.

    Ten assertions.  The first six are arithmetic on series built here, so they hold
    on any machine; the last four need the claims panels and are skipped, loudly,
    when those files are absent.  Run the module directly to execute them.  Returns
    the number of checks that passed; raises AssertionError on the first failure,
    named, rather than reporting a count that a reader has to interpret.
    """
    import io
    ok = 0
    def chk(name, cond):
        nonlocal ok
        if cond:
            ok += 1
            if verbose: print(f'  ok   {name}')
        else:
            raise AssertionError(name)

    idx = pd.date_range('2000-01-01', periods=60, freq='MS')

    # 1. D is zero on a series that never falls, and equals the percentage fall
    #    from the trailing maximum on one that does.
    up = pd.Series(np.arange(100.0, 160.0), index=idx)
    chk('D is never positive on a monotone rise',
        float(deviation(up, 12, 1).dropna().max()) < 0.0)
    step = pd.Series([100.0] * 30 + [90.0] * 30, index=idx)
    d = deviation(step, 12, 1).dropna()
    chk('D reads a ten-per-cent fall as 10', abs(float(d.max()) - 10.0) < 1e-9)

    # 2. procyclical() inverts a rate and leaves a level alone.
    r = pd.Series([4.0, 5.0, 6.0], index=idx[:3])
    chk('a rate is inverted', list(procyclical(r, 'rate')) == [96.0, 95.0, 94.0])
    chk('a level is not', list(procyclical(r, 'level')) == [4.0, 5.0, 6.0])

    # 3. The median convention: with an even number of channel dates the rule takes
    #    the LATER of the two middle months, at every q, and not by rounding.
    ds = [pd.Timestamp('2000-01-01'), pd.Timestamp('2000-02-01'),
          pd.Timestamp('2000-03-01'), pd.Timestamp('2000-04-01')]
    chk('the median takes the later middle month',
        _median(ds) == pd.Timestamp('2000-03-01'))

    # 4. Determinism: the same question asked twice gets the same answer, with cache
    #    churn in between.  This is the check that caught the id()-keyed cache.
    v = np.concatenate([np.linspace(100, 130, 30), np.linspace(130, 105, 18),
                        np.linspace(105, 125, 12)])
    ch = [('a', pd.Series(v, index=idx)), ('b', pd.Series(v * 1.01 + 3, index=idx))]
    w0, w1 = idx[0], idx[-1]
    a1 = date_turning_points(ch, w0, w1, concept='level')
    _ = [deviation(pd.Series(np.random.RandomState(k).rand(60) + 5, index=idx), 12, 3)
         for k in range(20)]
    a2 = date_turning_points(ch, w0, w1, concept='level')
    chk('the same question twice gives the same answer',
        (a1['peak'], a1['trough']) == (a2['peak'], a2['trough']))

    # 5-7. The shipped real-time record, when the claims panels are on disk.
    import os
    pan = '/home/claude/lab/dol/US_state_monthly_4ch_sa.csv'
    nat = '/home/claude/lab/dol/US_nat_monthly_4ch_sa.csv'
    if os.path.exists(pan) and os.path.exists(nat):
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
        dt = [b.strftime('%Y-%m') for _, b in diffusion_trough_calls(D)]
        chk('the diffusion clause makes eight trough calls and none is an NBER trough',
            len(dt) == 8 and not ({'1975-03','1980-07','1982-11','1991-03','2001-11',
                                   '2009-06','2020-04'} & set(dt)))
        chk("and it is the clause that finds Paper 1's rolling-episode end",
            '2026-02' in dt)
    elif verbose:
        print('  --   the three real-time checks need the claims panels; not on disk')
    if verbose: print(f'{ok} checks passed')
    return ok

if __name__ == '__main__':
    self_test()
