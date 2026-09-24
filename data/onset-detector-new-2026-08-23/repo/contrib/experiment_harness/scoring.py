"""Phase-5 probabilistic evaluation scorer (B-TEST-HARNESS deliverable).

Phase 5 decides whether a rebuilt instrument is REAL. This scorer is built BEFORE there is
anything to evaluate — §22.3: architecture is data-independent and may be settled any time.
Building the metric first removes the temptation to pick it after seeing the result.

The scorer adopts NO unit, threshold, chronology, member set or severity order
(CLAUDE.md boundary). It scores whatever probabilistic forecast the caller hands it and
labels the information set of the run. It never fits a model and never touches the store.

Pins from the batch brief (B-TEST-HARNESS):
  * proper scoring: Brier, skill vs climatology (base rate 0.155), log score, reliability,
    ECE, sharpness. AUC is REPORTED but NEVER primary — it is rank-only, threshold-free,
    and looks excellent while calibration is broken (the displayed forecaster: ECE 0.2278,
    self-declared ``reads_as_probability: false``).
  * mandatory baselines: climatology and persistence are first-class competitors. A result
    that does not beat BOTH on leave-one-recession-out log-score is not an improvement.
  * information-set switch: every evaluation is LABELLED ``archive_snapshot_asof`` (where an
    as-of lane exists) or ``pseudo_real_time``; the label is emitted, never omitted (§19.4).
  * decision-level metrics: crossing-date error, false crossings, missed crossings,
    lead-time distribution.
  * a deliberately-leaking split is DETECTED and refused; leave-one-day-out is rejected —
    days are ~250x oversampled and adjacent days near-identical, so day-level CV reports a
    fantasy (the repo inventory records an unconstrained weight search hitting ~0.93
    in-sample rank corr that FAILED leave-one-recession-out).

No I/O, no randomness at import.
"""
import datetime as dt
import math
import statistics

# Climatology reference: the recession base rate. External comparator, NOT a construction
# input (CLAUDE.md). Used as the constant climatology forecast and BSS reference.
CLIMATOLOGY_BASE_RATE = 0.155

# Clip bound so a confident-wrong forecast yields a finite (large) penalty, never -inf.
_EPS = 1e-15


class LeakageError(Exception):
    """Raised when a train/test split shares a recession episode across both sides."""


# ---- proper scoring rules -------------------------------------------------

def _clip(p):
    return min(1.0 - _EPS, max(_EPS, float(p)))


def brier_score(probs, outcomes):
    """Mean squared error of probabilistic forecasts against 0/1 outcomes. Lower better."""
    n = len(probs)
    if n == 0 or n != len(outcomes):
        raise ValueError("probs and outcomes must be non-empty and equal length")
    return sum((float(p) - float(y)) ** 2 for p, y in zip(probs, outcomes)) / n


def log_score(probs, outcomes):
    """Mean log-likelihood (higher = better; 0 is perfect). Forecasts are clipped to
    ``[_EPS, 1-_EPS]`` so a confident-wrong forecast is heavily but FINITELY penalised."""
    n = len(probs)
    if n == 0 or n != len(outcomes):
        raise ValueError("probs and outcomes must be non-empty and equal length")
    total = 0.0
    for p, y in zip(probs, outcomes):
        c = _clip(p)
        total += math.log(c) if float(y) >= 0.5 else math.log(1.0 - c)
    return total / n


def brier_skill_score(probs, outcomes, base_rate=CLIMATOLOGY_BASE_RATE):
    """Brier skill vs a constant climatology forecast: ``1 - BS_model / BS_ref``.
    Positive = better than climatology; 0 = no skill over climatology; can be negative."""
    bs_model = brier_score(probs, outcomes)
    bs_ref = brier_score([base_rate] * len(outcomes), outcomes)
    if bs_ref == 0.0:
        return 0.0
    return 1.0 - bs_model / bs_ref


def reliability_diagram(probs, outcomes, n_bins=10):
    """Bin forecasts into ``n_bins`` equal-width [0,1] bins; per bin report mean forecast,
    observed frequency, and count. Empty bins carry count 0 and None statistics."""
    bins = [{"lo": i / n_bins, "hi": (i + 1) / n_bins, "_p": [], "_y": []}
            for i in range(n_bins)]
    for p, y in zip(probs, outcomes):
        idx = min(n_bins - 1, int(float(p) * n_bins))
        bins[idx]["_p"].append(float(p))
        bins[idx]["_y"].append(float(y))
    out = []
    for b in bins:
        c = len(b["_p"])
        out.append({
            "lo": b["lo"], "hi": b["hi"], "count": c,
            "mean_forecast": (sum(b["_p"]) / c) if c else None,
            "observed_freq": (sum(b["_y"]) / c) if c else None,
        })
    return out


def ece(probs, outcomes, n_bins=10):
    """Expected Calibration Error: count-weighted mean |mean_forecast - observed_freq|
    across occupied bins. 0 = perfectly calibrated."""
    diag = reliability_diagram(probs, outcomes, n_bins)
    n = len(probs)
    if n == 0:
        return 0.0
    total = 0.0
    for b in diag:
        if b["count"]:
            total += (b["count"] / n) * abs(b["mean_forecast"] - b["observed_freq"])
    return total


def sharpness(probs):
    """Sharpness = population variance of the forecast probabilities. Higher = more
    decisive (concentrated away from the base rate). Sharpness without calibration is
    worthless, hence it is reported ALONGSIDE ECE, never alone."""
    if len(probs) <= 1:
        return 0.0
    return statistics.pvariance(float(p) for p in probs)


def auc(probs, outcomes):
    """Area under ROC (Mann-Whitney). RANK-ONLY, threshold-free. REPORTED but NEVER the
    primary metric — it looks excellent while calibration is broken. Ties score 0.5."""
    pos = [float(p) for p, y in zip(probs, outcomes) if float(y) >= 0.5]
    neg = [float(p) for p, y in zip(probs, outcomes) if float(y) < 0.5]
    if not pos or not neg:
        return None
    wins = 0.0
    for pp in pos:
        for pn in neg:
            if pp > pn:
                wins += 1.0
            elif pp == pn:
                wins += 0.5
    return wins / (len(pos) * len(neg))


# ---- mandatory baselines --------------------------------------------------

def climatology_forecast(n, base_rate=CLIMATOLOGY_BASE_RATE):
    """Constant base-rate forecast of length ``n`` — the climatology competitor."""
    return [base_rate] * n


def persistence_forecast(states, prior=CLIMATOLOGY_BASE_RATE):
    """Persistence competitor: forecast_t = state_{t-1}. The first forecast uses ``prior``
    (default base rate) since there is no prior state."""
    out = []
    prev = prior
    for s in states:
        out.append(float(prev))
        prev = float(s)
    return out


def beats_baselines(model, climatology, persistence):
    """A candidate is an improvement iff it beats BOTH baselines on log-score (higher =
    better). Ties do NOT count as beating. Returns the componentwise verdict too."""
    beats_clim = model > climatology
    beats_pers = model > persistence
    return {
        "beats_climatology": beats_clim,
        "beats_persistence": beats_pers,
        "is_improvement": beats_clim and beats_pers,
    }


# ---- information-set switch -----------------------------------------------

def label_information_set(has_asof_lane):
    """archive_snapshot_asof where an as-of vintage lane exists, else pseudo_real_time.
    The four project information-set modes are current_revised, archive_snapshot_asof,
    stitched_strict_first_release, substituted_diagnostic (CLAUDE.md); an evaluation with
    no as-of lane is pseudo-real-time and MUST be labelled as such."""
    return "archive_snapshot_asof" if has_asof_lane else "pseudo_real_time"


# ---- decision-level metrics -----------------------------------------------

def _match(pred, ref, tolerance_days):
    """Nearest predicted crossing to ``ref`` within tolerance, else None."""
    best, best_gap = None, None
    for p in pred:
        gap = abs((p - ref).days)
        if gap <= tolerance_days and (best_gap is None or gap < best_gap):
            best, best_gap = p, gap
    return best


def crossing_date_error(predicted, reference, tolerance_days=90):
    """Signed day error (predicted - reference) for each reference crossing that has a
    predicted crossing within ``tolerance_days``. Positive = predicted late."""
    errs = []
    for r in reference:
        m = _match(predicted, r, tolerance_days)
        if m is not None:
            errs.append((m - r).days)
    return errs


def false_crossings(predicted, reference, tolerance_days=90):
    """Predicted crossings with no reference crossing within tolerance (spurious signals)."""
    return sum(1 for p in predicted if _match(reference, p, tolerance_days) is None)


def missed_crossings(predicted, reference, tolerance_days=90):
    """Reference crossings with no predicted crossing within tolerance (missed onsets)."""
    return sum(1 for r in reference if _match(predicted, r, tolerance_days) is None)


def lead_time_distribution(leads):
    """Summarise a list of lead-times-in-days; None entries are misses and skipped.
    Reports the count of detected leads so the miss count is never silently absorbed."""
    hit = [v for v in leads if v is not None]
    if not hit:
        return {"n": 0, "min": None, "median": None, "max": None, "mean": None}
    return {
        "n": len(hit),
        "min": min(hit),
        "median": statistics.median(hit),
        "max": max(hit),
        "mean": statistics.mean(hit),
    }


# ---- leak detection & granularity guard -----------------------------------

def detect_leak(split):
    """True iff any test-episode label also appears in the train set. Episode identity is
    the ``label`` field (a recession id); the same recession on both sides is leakage."""
    train_labels = {e.get("label") for e in split.train}
    return any(e.get("label") in train_labels for e in split.test)


def assert_no_leakage(split):
    """Raise ``LeakageError`` when a split leaks a recession across train/test. The harness
    REFUSES a leaking split rather than silently scoring it (brief step 7)."""
    if detect_leak(split):
        shared = sorted({e.get("label") for e in split.test}
                        & {e.get("label") for e in split.train})
        raise LeakageError(f"recession(s) leak across train/test: {shared}")


def require_episode_granularity(granularity):
    """Reject leave-one-day-out (brief step 1). Days are ~250x oversampled and adjacent days
    near-identical, so day-level CV reports a fantasy. Only episode/recession/era units are
    admissible cross-validation granularities."""
    allowed = {"recession", "episode", "era"}
    if granularity not in allowed:
        raise ValueError(
            f"granularity {granularity!r} rejected; day-level CV is a fantasy. "
            f"Use one of {sorted(allowed)}")
    return granularity


# The four named leave-one-era-out strata (brief step 2). Great Moderation begins 1984
# (Kim-Nelson / McConnell-Perez-Quiros volatility break); post-2008 and post-2020 split the
# GFC and COVID regimes off.
def standard_era(date):
    """Map a peak date to one of the four leave-one-era-out strata:
    pre-1984, great-moderation, post-2008, post-2020."""
    y = date.year
    if y < 1984:
        return "pre-1984"
    if y < 2008:
        return "great-moderation"
    if y < 2020:
        return "post-2008"
    return "post-2020"


# ---- bundle ---------------------------------------------------------------

def evaluate(probs, outcomes, has_asof_lane, base_rate=CLIMATOLOGY_BASE_RATE, n_bins=10):
    """Bundle every proper score + AUC into one comparable result object, tagged with the
    information-set label. ``primary_metric`` names a PROPER score (log_score); AUC is
    included but ``auc_is_primary`` is hard-False — it is rank-only and must never drive a
    decision (brief step 3)."""
    return {
        "n": len(probs),
        "information_set": label_information_set(has_asof_lane),
        "brier_score": brier_score(probs, outcomes),
        "brier_skill_score": brier_skill_score(probs, outcomes, base_rate),
        "log_score": log_score(probs, outcomes),
        "ece": ece(probs, outcomes, n_bins),
        "sharpness": sharpness(probs),
        "reliability": reliability_diagram(probs, outcomes, n_bins),
        "auc": auc(probs, outcomes),
        "auc_is_primary": False,
        "primary_metric": "log_score",
    }
