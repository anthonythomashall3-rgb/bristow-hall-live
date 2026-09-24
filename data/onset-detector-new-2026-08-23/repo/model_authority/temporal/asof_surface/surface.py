#!/usr/bin/env python3
"""daily_observed_information_state + as-of P/E reconstruction (instrument.v2.g1).

Faithful to the adopted predecessor instrument:
  * method_source/index_v1.py   — deterioration transforms, per-member z vs a
    clean-expansion baseline, channel means, fixed channel weights, renormalized
    headline daily line (= pressure line P).
  * method_source/energy_build.py — standardize the line, 21-day mean (the
    "official reading"), 4-sigma compression, trailing-365-day integral / 30.44
    = E12 in sigma-months. BAR_E=7.5, RESET=2.0.

The ONLY difference between the current_revised and archive_snapshot_asof lanes
is the governed INPUT (SKILL.md: "current-revised and as-of executions use
identical code with different governed inputs"). This module carries the same
math and selects inputs by decision cutoff.

Contracts enforced here (data_vault/catalog/timing_model.json, SKILL.md):
  * as-of value = the latest vintage whose availability <= decision_cutoff, for
    reference periods whose period end <= decision_cutoff (no future actuals, no
    future revisions);
  * native reference period + frequency preserved; a monthly/quarterly actual is
    never relabeled a daily actual — the daily-grid value is a typed
    `carried_for_computation` projection with staleness, not a new actual;
  * every clock kept distinct (reference period, availability, decision cutoff).
"""
from __future__ import annotations

import bisect
import datetime as dt
from collections import deque
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence

# ---- energy constants inherited from energy_build.py (operating_calibrated) ----
BAR_E = 7.5
RESET = 2.0
COMPRESS_HINGE = 4.0
SMOOTH_DAYS = 21
INTEGRAL_DAYS = 365
DAYS_PER_MONTH = 30.44


# ============================================================================
# 1. Observed information state
# ============================================================================

@dataclass(frozen=True)
class ObsRecord:
    """One publisher observation of one reference period in one vintage.

    reference_period_end : canonical date of the economic period measured.
    value                : the published value in that vintage.
    available_at         : provider_available_at / realtime_start — the earliest
                           date this exact value was knowable (revision-validity
                           interval start). MUST NOT be a reference period or a
                           scheduled date.
    vintage_label        : opaque vintage id (e.g. ASOF20220115) for lineage.
    reference_period_start : optional; defaults to reference_period_end.
    """
    reference_period_end: dt.date
    value: float
    available_at: dt.date
    vintage_label: str = ""
    reference_period_start: Optional[dt.date] = None

    @property
    def rp_start(self) -> dt.date:
        return self.reference_period_start or self.reference_period_end


def daily_observed_information_state(
    records: Sequence[ObsRecord],
    decision_cutoff: dt.date,
    native_frequency: str = "monthly",
) -> Dict:
    """Latest-vintage-by-cutoff observed state; no future periods, no future revisions.

    Returns a dict with:
      observations : ordered list of {reference_period_end, value, available_at,
                     vintage_label, value_status:"actual", native_frequency}
      period_index : {reference_period_end -> value} for the chosen vintage
      last_release_at : max(available_at) among selected observations, or None
      staleness_days  : decision_cutoff - last_release_at (>=0), or None
      decision_cutoff, native_frequency
    Never carries a value forward; contains ONLY released actuals at native periods.
    """
    # eligible: available by cutoff AND the reference period has ended by cutoff.
    eligible = [
        r for r in records
        if r.available_at <= decision_cutoff and r.reference_period_end <= decision_cutoff
    ]
    # for each reference period pick the vintage in effect as-of the cutoff:
    # the record with the LATEST availability <= cutoff (breaking ties by vintage).
    chosen: Dict[dt.date, ObsRecord] = {}
    for r in eligible:
        cur = chosen.get(r.reference_period_end)
        if cur is None or (r.available_at, r.vintage_label) > (cur.available_at, cur.vintage_label):
            chosen[r.reference_period_end] = r
    periods = sorted(chosen)
    observations = [
        {
            "reference_period_start": chosen[p].rp_start.isoformat(),
            "reference_period_end": p.isoformat(),
            "value": chosen[p].value,
            "available_at": chosen[p].available_at.isoformat(),
            "vintage_label": chosen[p].vintage_label,
            "native_frequency": native_frequency,
            "value_status": "actual",
        }
        for p in periods
    ]
    last_release = max((chosen[p].available_at for p in periods), default=None)
    return {
        "decision_cutoff": decision_cutoff.isoformat(),
        "native_frequency": native_frequency,
        "observations": observations,
        "period_index": {p: chosen[p].value for p in periods},
        "last_release_at": last_release.isoformat() if last_release else None,
        "staleness_days": (decision_cutoff - last_release).days if last_release else None,
    }


def daily_carry(state: Dict, day: dt.date) -> Optional[Dict]:
    """Step-function carry of the last released actual onto a daily grid day.

    This is index_v1.asof(): value at or before `day`. The result is TYPED
    `carried_for_computation` with staleness — it is NOT a new daily actual and
    must never be relabeled one (SKILL.md; timing_model missing_clock_policy).
    Returns None before the first released period.
    """
    periods = sorted(dt.date.fromisoformat(o["reference_period_end"]) for o in state["observations"])
    if not periods:
        return None
    i = bisect.bisect_right(periods, day) - 1
    if i < 0:
        return None
    p = periods[i]
    val = state["period_index"][p]
    return {
        "day": day.isoformat(),
        "value": val,
        "as_of_reference_period_end": p.isoformat(),
        "carried": p != day,
        "carry_age_days": (day - p).days,
        "value_status": "carried_for_computation",
    }


# ============================================================================
# 2. instrument.v2.g1 deterioration transforms (index_v1.py, exact)
# ============================================================================

def _sorted_items(series: Dict[dt.date, float]):
    ks = sorted(series)
    return ks, [series[k] for k in ks]


def yoy(series: Dict[dt.date, float]) -> Dict[dt.date, float]:
    """Year-over-year % change vs the nearest prior obs ~365d back (index_v1.yoy)."""
    out: Dict[dt.date, float] = {}
    ks = sorted(series)
    for k in ks:
        prior = k - dt.timedelta(days=365)
        i = bisect.bisect_left(ks, prior)
        cand = [x for x in ks[max(0, i - 1):i + 2] if abs((x - prior).days) <= 20]
        if cand:
            p = min(cand, key=lambda x: abs((x - prior).days))
            if series[p] != 0:
                out[k] = (series[k] / series[p] - 1) * 100
    return out


def _window_extreme(series: Dict[dt.date, float], look: int, take_max: bool):
    ks, vals = _sorted_items(series)
    out: Dict[dt.date, float] = {}
    lo = 0
    dq: deque = deque()
    for i, k in enumerate(ks):
        while lo < i and (k - ks[lo]).days > look:
            lo += 1
        while dq and dq[0] < lo:
            dq.popleft()
        while dq and ((vals[dq[-1]] <= vals[i]) if take_max else (vals[dq[-1]] >= vals[i])):
            dq.pop()
        dq.append(i)
        out[k] = vals[dq[0]]
    return out, ks


def drawdown(series: Dict[dt.date, float]) -> Dict[dt.date, float]:
    """% below trailing 12-month max (index_v1.drawdown)."""
    mx, ks = _window_extreme(series, 370, True)
    return {k: (series[k] / mx[k] - 1) * 100 if mx[k] else 0 for k in ks}


def rise_floor(series: Dict[dt.date, float], look: int = 370) -> Dict[dt.date, float]:
    """Current minus trailing-min (Sahm-style rise; index_v1.rise_floor)."""
    mn, ks = _window_extreme(series, look, False)
    return {k: series[k] - mn[k] for k in ks}


def _neg(d: Dict[dt.date, float]) -> Dict[dt.date, float]:
    return {k: -v for k, v in d.items()}


# transform registry: name -> callable(raw_series)->transformed_series, oriented
# so higher = more recessionary, matching index_v1.py's T{} block exactly.
TRANSFORMS: Dict[str, Callable[[Dict[dt.date, float]], Dict[dt.date, float]]] = {
    "yoy": yoy,                                        # ICSA
    "rise_floor": rise_floor,                          # IURSA
    "rise_floor120": lambda s: rise_floor(s, 120),     # UNRATE
    "level": lambda s: dict(s),                        # SAHM, BAA10Y, NFCI, VIX
    "neg_yoy": lambda s: _neg(yoy(s)),                 # INDPRO, CMRMT, TCU, PERMIT, HOUST, W875
    "neg_level": lambda s: _neg(s),                    # PHILLY diffusion
    "neg_drawdown": lambda s: _neg(drawdown(s)),       # NASDAQ, UMCSENT
}


# ============================================================================
# 3. standardization, channel composite, daily line P
# ============================================================================

def baseline_mu_sd(series: Dict[dt.date, float], is_baseline: Callable[[dt.date], bool]):
    """Clean-expansion mean/sd (index_v1: exclude recessions / COVID / 2023-25 window)."""
    base = [v for k, v in series.items() if is_baseline(k)]
    if not base:
        return None, None
    mu = sum(base) / len(base)
    sd = (sum((x - mu) ** 2 for x in base) / len(base)) ** 0.5 or 1.0
    return mu, sd


def standardize(series: Dict[dt.date, float], mu: float, sd: float) -> Dict[dt.date, float]:
    return {k: (v - mu) / sd for k, v in series.items()}


@dataclass(frozen=True)
class MemberSpec:
    series_id: str
    channel: str
    transform: str


def _zval_asof(z_series: Dict[dt.date, float], keys: List[dt.date], day: dt.date) -> Optional[float]:
    i = bisect.bisect_right(keys, day) - 1
    return z_series[keys[i]] if i >= 0 else None


# channel weights (index_v1.CHANNELS), fixed / robustness-validated, not outcome-fitted.
CHANNEL_WEIGHTS = {
    "labor": 0.30,
    "realactivity": 0.25,
    "creditequity": 0.20,
    "finconditions": 0.10,
    "housingincome": 0.15,
}


def reconstruct_P_asof(
    member_raw: Dict[str, Dict[dt.date, float]],
    members: Sequence[MemberSpec],
    grid: Sequence[dt.date],
    is_baseline: Callable[[dt.date], bool],
    channel_weights: Dict[str, float] = None,
) -> Dict[dt.date, float]:
    """Daily pressure line P from as-of member series (index_v1 headline, exact).

    member_raw : {series_id -> {reference_period_end -> as-of value}}. Callers
    build these from daily_observed_information_state.period_index so the values
    are already governed by the decision cutoff. The daily-grid combination uses
    the same step-function carry (asof) as index_v1; carried values are for
    computation only.
    """
    channel_weights = channel_weights or CHANNEL_WEIGHTS
    # transform -> z vs baseline, per member
    z_by_member: Dict[str, tuple] = {}
    for m in members:
        raw = member_raw.get(m.series_id, {})
        transformed = TRANSFORMS[m.transform](raw)
        mu, sd = baseline_mu_sd(transformed, is_baseline)
        if mu is None:
            continue
        z = standardize(transformed, mu, sd)
        z_by_member[m.series_id] = (z, sorted(z))
    by_channel: Dict[str, List[MemberSpec]] = {}
    for m in members:
        by_channel.setdefault(m.channel, []).append(m)

    line: Dict[dt.date, float] = {}
    for day in grid:
        tot = 0.0
        wsum = 0.0
        for ch, mems in by_channel.items():
            vals = []
            for m in mems:
                zk = z_by_member.get(m.series_id)
                if zk is None:
                    continue
                v = _zval_asof(zk[0], zk[1], day)
                if v is not None:
                    vals.append(v)
            if vals:
                cs = sum(vals) / len(vals)
                w = channel_weights[ch]
                tot += w * cs
                wsum += w
        if wsum:
            line[day] = tot / wsum   # renormalize over available channels
    return line


# ============================================================================
# 4. E12 energy (energy_build.py, exact)
# ============================================================================

def _compress(v: float, hinge: float = COMPRESS_HINGE) -> float:
    return v if v <= hinge else hinge + (v - hinge) ** 0.25


def e12_from_reading(line: Dict[dt.date, float], exp_mu: float, exp_sd: float) -> Dict[dt.date, float]:
    """E12 sigma-months from the daily line (energy_build.py, exact).

    standardize -> trailing 21-day mean (official reading) -> 4-sigma compress ->
    trailing 365-day integral of max(reading,0) / 30.44.
    """
    days = sorted(line)
    std = {d: (line[d] - exp_mu) / exp_sd for d in days}
    # 21-day trailing mean
    sm: Dict[dt.date, float] = {}
    q: deque = deque()
    s = 0.0
    for d in days:
        q.append(std[d])
        s += std[d]
        while len(q) > SMOOTH_DAYS:
            s -= q.popleft()
        sm[d] = s / len(q)
    sm = {d: _compress(v) for d, v in sm.items()}
    # 365-day trailing integral of positive readings / 30.44
    E: Dict[dt.date, float] = {}
    q2: deque = deque()
    s2 = 0.0
    for d in days:
        v = max(sm[d], 0.0)
        q2.append((d, v))
        s2 += v
        while (d - q2[0][0]).days > INTEGRAL_DAYS:
            s2 -= q2.popleft()[1]
        E[d] = s2 / DAYS_PER_MONTH
    return E


def reconstruct_E_asof(
    line: Dict[dt.date, float],
    is_baseline: Callable[[dt.date], bool],
) -> Dict[dt.date, float]:
    """E12 with the expansion baseline recomputed from the SAME governed line
    (energy_build reads exp_mu/exp_sd from index_v1_out; here we recompute from
    the as-of line's own baseline days so the observed_only lane is self-contained).
    """
    base = [v for d, v in line.items() if is_baseline(d)]
    if not base:
        raise ValueError("empty expansion baseline for E12")
    exp_mu = sum(base) / len(base)
    exp_sd = (sum((x - exp_mu) ** 2 for x in base) / len(base)) ** 0.5 or 1.0
    return e12_from_reading(line, exp_mu, exp_sd)
