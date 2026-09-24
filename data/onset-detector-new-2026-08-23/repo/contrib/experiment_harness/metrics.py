"""Pre-registered metric computer for Phase-5 experiments (B-EXP-0 deliverable 3).

Coded ONCE, pre-registered. These functions score whatever candidate-rule output the
caller hands them; they adopt no unit, threshold, chronology, or severity order (CLAUDE.md
boundary). The docstrings cite the docket text that fixed each metric BEFORE any run.

Source of pre-registration — SCIENCE_DOCKET_v1.md:

  S10, "2022 A/B EXPERIMENT — OWNER-ORDERED 2026-08-05": scored on objective criteria fixed
  BEFORE running:
    (1) which threshold set is stabler (bootstrap variance of boundaries);
    (2) false-positive rate on measured non-episodes (1966/1995/2015-16);
    (3) era cross-check — rule fit excluding 2020s must still admit/exclude 2022 the same way;
    (4) detection lead on held-out historical episodes, as-of.

  S22, "Value-stream bake-off (Routes A/B/C/D)": score on the S13 acceptance test + as-of
  detection metrics, recommend the measured winner.

All dates are datetime.date. No I/O, no randomness at import: bootstrap resampling is an
explicit, seedable helper the caller drives.
"""
import datetime as dt
import random
import statistics


def detection_lead(onset_date, reference_peak):
    """S10 criterion (4): detection lead on a held-out episode, as-of.

    Returns integer days by which the model's onset signal PRECEDES the reference peak
    (positive = led the peak, negative = lagged it). Returns None when the rule never
    fired for the episode (``onset_date is None``) — a miss, distinct from a zero lead.
    """
    if onset_date is None:
        return None
    return (reference_peak - onset_date).days


def false_alarm_rate(firings, nonepisode_windows):
    """S10 criterion (2): false-positive rate on measured non-episodes (1966/1995/2015-16).

    ``firings`` is the list of dates on which the candidate rule signalled an onset.
    ``nonepisode_windows`` is a list of (start, end) inclusive date windows known to be
    non-episodes. Returns the fraction of those windows in which the rule fired at least
    once. Returns None when no windows are supplied (undefined rate).
    """
    if not nonepisode_windows:
        return None
    fired = 0
    for start, end in nonepisode_windows:
        if any(start <= f <= end for f in firings):
            fired += 1
    return fired / len(nonepisode_windows)


def boundary_stability(boundary_samples):
    """S10 criterion (1): stability of a threshold set = variance of its boundaries.

    ``boundary_samples`` are boundary estimates (e.g. one per bootstrap resample or per
    era-refit). Returns the population variance; lower = stabler. A single sample is
    perfectly stable (0.0). Dates are accepted and measured in days from the mean.
    """
    if len(boundary_samples) <= 1:
        return 0.0
    vals = [_to_number(s) for s in boundary_samples]
    return statistics.pvariance(vals)


def bootstrap_boundaries(data, estimator, n_resamples, seed):
    """Seedable bootstrap helper: resample ``data`` with replacement ``n_resamples``
    times, apply ``estimator`` (a callable mapping a resample to a scalar boundary), and
    return the list of boundary estimates. Feed the result to ``boundary_stability``.

    Kept explicit and seeded so experiment runs are reproducible (no import-time RNG).
    """
    rng = random.Random(seed)
    n = len(data)
    out = []
    for _ in range(n_resamples):
        resample = [data[rng.randrange(n)] for _ in range(n)]
        out.append(estimator(resample))
    return out


def era_consistency(labels_full, labels_excluded):
    """S10 criterion (3): rule fit excluding the 2020s must classify each target the same
    way the full-fit rule does.

    ``labels_full`` and ``labels_excluded`` map target id -> label. Returns a dict with the
    agreement fraction, the sorted list of disagreeing targets, and ``consistent`` (True iff
    every shared target agrees). Only targets present in both maps are compared.
    """
    shared = [k for k in labels_full if k in labels_excluded]
    disagreements = sorted(k for k in shared if labels_full[k] != labels_excluded[k])
    agreement = (len(shared) - len(disagreements)) / len(shared) if shared else None
    return {
        "agreement": agreement,
        "disagreements": disagreements,
        "consistent": len(disagreements) == 0 and bool(shared),
    }


def detection_scorecard(leads, firings, nonepisode_windows, boundary_samples):
    """S22 bake-off aggregate: bundle the pre-registered as-of detection metrics for one
    candidate route into a single comparable object.

    ``leads`` maps episode id -> lead-in-days-or-None (from ``detection_lead``). The rest
    feed the corresponding metric above. Detected episodes are those with a non-None lead.
    """
    detected = [v for v in leads.values() if v is not None]
    return {
        "median_lead": statistics.median(detected) if detected else None,
        "n_detected": len(detected),
        "n_missed": sum(1 for v in leads.values() if v is None),
        "false_alarm_rate": false_alarm_rate(firings, nonepisode_windows),
        "boundary_stability": boundary_stability(boundary_samples),
    }


def _to_number(x):
    if isinstance(x, dt.date):
        return x.toordinal()
    return float(x)
