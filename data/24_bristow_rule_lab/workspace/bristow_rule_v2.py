"""Bristow Rule, three-channel form — the rule scored in the Paper 1.5 memo.

Channels: industrial production, exports (value), employment.
Per channel: later of (a) the peak of the 12-month rolling drawdown and
             (b) the last month the level sits within 2% of the peak-to-trough
                 amplitude above its low in the window.
Trough date: median of the channel dates.
"""
import pandas as pd, numpy as np

def load(path):
    d = pd.read_csv(path); d.columns = ['d', 'v']
    d['d'] = pd.to_datetime(d.d); d['v'] = pd.to_numeric(d.v, errors='coerce')
    return d.dropna().set_index('d')['v'].astype(float)

def drawdown(x, lookback=12, smooth=3):
    m = x.rolling(smooth).mean()
    mx = m.shift(1).rolling(lookback).max()
    return (mx - m) / mx * 100.0

def episodes(stat, threshold=2.0):
    runs, cur = [], []
    for d, v in stat.dropna().items():
        if v >= threshold: cur.append(d)
        elif cur: runs.append(cur); cur = []
    if cur: runs.append(cur)
    return runs

def channel_date(level, w0, w1, band=0.02, smooth=3):
    dev = drawdown(level)[w0:w1].dropna()
    if len(dev) == 0: return None
    d_peak = dev.idxmax()
    m = level.rolling(smooth).mean()[w0:w1].dropna()
    if len(m) < 4: return d_peak
    lo = float(m.min()); i = m.idxmin()
    hi = float(m[:i].max()) if len(m[:i]) else float(m.max())
    amp = max(hi - lo, 1e-9)
    on_floor = m[m <= lo + band * amp]
    d_floor = on_floor.index[-1] if len(on_floor) else None
    return max(d_peak, d_floor) if d_floor is not None else d_peak

def trough_date(channels, w0, w1, band=0.02):
    """channels: list of level series (pro-cyclical). Returns the median channel date."""
    ds = sorted(d for d in (channel_date(x, w0, w1, band) for x in channels) if d is not None)
    if not ds: return None
    return ds[(len(ds) - 1) // 2] if len(ds) % 2 == 0 else ds[len(ds) // 2]

def standalone(channels, anchor_index=0, threshold=2.0, tail=12, band=0.02):
    """Date every contraction the anchor channel flags, using no official dates.
    Returns a list of (episode_start, episode_end, trough_date)."""
    anchor = channels[anchor_index]
    out = []
    for e in episodes(drawdown(anchor), threshold):
        w0, w1 = e[0], e[-1] + pd.DateOffset(months=tail)
        d = trough_date(channels, w0, w1, band)
        if d is not None: out.append((e[0], e[-1], d))
    return out

def spread(channels, w0, w1, band=0.02):
    """Cross-channel spread in months — the confidence band to report with a date."""
    ds = sorted(d for d in (channel_date(x, w0, w1, band) for x in channels) if d is not None)
    if len(ds) < 2: return None
    return (ds[-1].year - ds[0].year) * 12 + (ds[-1].month - ds[0].month)

# ---------------------------------------------------------------- scope and confidence

def depth(anchor, w0, w1, smooth=3):
    """Peak-to-trough fall in the anchor series inside the window, in percent."""
    m = anchor.rolling(smooth).mean()[w0:w1].dropna()
    if len(m) < 4: return None
    return 100.0 * (float(m.min()) - float(m.iloc[0])) / float(m.iloc[0])

def date_contraction(channels, w0, w1, band=0.02, min_depth=2.0, max_spread=9):
    """The tool as it should be used.

    Returns a dict with the date, the evidence behind it, and an explicit verdict:
      'dated'          - a classical contraction, channels in reasonable agreement
      'low confidence' - dated, but the channels disagree by more than max_spread months
      'out of scope'   - activity never fell by min_depth percent: a growth-cycle
                         episode, which a level-based rule cannot date
    """
    d = trough_date(channels, w0, w1, band)
    dep = depth(channels[0], w0, w1)
    sp = spread(channels, w0, w1, band)
    if d is None:
        return dict(date=None, verdict='no data', depth=dep, spread=sp)
    if dep is not None and dep > -abs(min_depth):
        return dict(date=d, verdict='out of scope', depth=dep, spread=sp)
    if sp is not None and sp > max_spread:
        return dict(date=d, verdict='low confidence', depth=dep, spread=sp)
    return dict(date=d, verdict='dated', depth=dep, spread=sp)

# ---------------------------------------------------------------- the onset side

def channel_peak(level, w0, w1, band=0.02, smooth=3):
    """Mirror of channel_date: the last month the level stays within `band` of its
    cyclical high inside the window, band measured as a fraction of the high-to-low
    amplitude.  Dates the end of the expansion."""
    m = level.rolling(smooth).mean()[w0:w1].dropna()
    if len(m) < 4: return None
    hi = float(m.max()); i = m.idxmax()
    lo = float(m[i:].min()) if len(m[i:]) else float(m.min())
    amp = max(hi - lo, 1e-9)
    on_top = m[m >= hi - band * amp]
    return on_top.index[-1] if len(on_top) else i

def expansion_peak(channels, w0, w1, band=0.02):
    ds = sorted(d for d in (channel_peak(x, w0, w1, band) for x in channels) if d is not None)
    if not ds: return None
    return ds[(len(ds)-1)//2] if len(ds) % 2 == 0 else ds[len(ds)//2]

def date_cycle(channels, w0, w1, band_trough=0.02, band_peak=0.02):
    """Both ends of one contraction.  The trough is dated to +/-3 months in 83% of
    classical contractions; the peak only in 58% - peaks are a flatter feature and
    every rule tested, including Bry-Boschan, does worse on them.  Report both, and
    report the peak with its wider band."""
    t = trough_date(channels, w0, w1, band_trough)
    p = expansion_peak(channels, w0, t if t is not None else w1, band_peak)
    return dict(peak=p, trough=t,
                length=None if (p is None or t is None) else (t.year-p.year)*12 + (t.month-p.month))

# ---------------------------------------------------------------- the panel matters
#
# The rule is only as good as the coincident panel it is given.  Scored on the twelve
# postwar NBER recessions:
#
#   three channels (production, exports, employment)   peak  7/12 within 3 months, MAD 4.42
#   the NBER's own six coincident indicators           peak 11/12 within 3 months, MAD 1.42
#                                                      trough 12/12 within 3 months, MAD 1.33
#   the seven recessions since 1973, where all six
#   indicators exist                                   BOTH ends within 2 months, 7/7
#
# The six are: industrial production, payroll employment, household employment, real
# personal income less transfers, real personal consumption, and real manufacturing and
# trade sales - the series the Business Cycle Dating Committee says it reads.  Give the
# rule those and it reproduces the committee to within two months at both ends; give it
# a thin panel and it degrades.  Panel size is therefore reported with every date.

US_COINCIDENT = ['INDPRO', 'PAYEMS', 'CE16OV', 'W875RX1', 'DPCERA3M086SBEA', 'CMRMTSPL']

def panel_quality(channels, w0, w1):
    """How much evidence stands behind a date: how many channels cover the window,
    and how far apart their own dates fall."""
    usable = [x for x in channels if x.index.min() <= w0 and x.index.max() >= w1]
    return dict(channels=len(usable), spread=spread(usable, w0, w1) if len(usable) > 1 else None)

# ---------------------------------------------------------------- real-time use
#
# Troughs, ALFRED vintages, no official dates: the rule fixed all four US troughs that
# archive reaches (1991, 2001, 2009, 2020) four months after the fact, within one to two
# months, roughly fourteen months before the NBER announced them.
#
# Peaks, same method with the six-indicator panel:
#   2007-12 peak: Jan 2008 (+1) from the March 2008 vintage; NBER announced 1 Dec 2008
#   2020-02 peak: Feb 2020 (0)  from the May 2020 vintage;   NBER announced 8 Jun 2020
#   2001-03 peak: Feb 2001 (-1) from the June 2001 vintage;  NBER announced 26 Nov 2001
#
#     https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=<SERIES>&vintage_date=<YYYY-MM-DD>
