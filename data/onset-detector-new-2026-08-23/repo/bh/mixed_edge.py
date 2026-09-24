"""mixed_edge — the owner's third data-time as a first-class COMPOSITION (B-MODE-MIXED).

The owner (2026-08-08) named three data-times: REVISED (`current_revised`),
REAL-TIME (`archive_snapshot_asof` / `stitched_strict_first_release`), and MIXED —
"real-time where there is real-time, most up-to-date revised everywhere else, plus
nowcast where there is no data yet." Mixed is what a live monitor actually shows.

Mixed is NOT a fifth canonical mode. `information_set_modes` in
`data_vault/catalog/timing_model.json` stays pinned at four and
`verify_data_vault.py` FAILS if that list changes. mixed_edge is a NAMED, DISCLOSED
composition OVER the four (rulebook §3.6 — a coarser lane is a distinct lane, never
relabelled). It is also distinct from `combined_edge`, which is a decision-cutoff
PRESET; combined_edge picks one lane at a cutoff, mixed_edge stamps every point with
the lane it came from and discloses the mix.

Contract, from the schema at `data_vault/catalog/mixed_edge_composition.v1.json`:

  1. Per-observation provenance stamp REQUIRED. A mixed series with any unstamped
     point is PROHIBITED (§3.1, §3.2 — silent substitution is what the stamp
     prevents). `compose()` never emits an unstamped point; `validate()` fails one.
  2. Fixed precedence, declared not inferred:
     stitched_strict_first_release > archive_snapshot_asof > current_revised > nowcast.
  3. nowcast fills only reference periods no observed lane covers, bounded by the
     existing two-phase nowcast contract (`method_source/index_v1.py:141-153,215-226`).
  4. Coverage summary per series — the honesty disclosure (§14.1); renders wherever
     the series renders.
  5. `official_use_permitted` for a real-time CLAIM is FALSE. A backtest on mixed is
     `pseudo_real_time` (research/datatime/DATATIME_CROSSWALK.md, CH-R113).
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

# Source lanes, highest precedence first. Declared, never inferred (§ schema
# fixed_precedence). Reordering this tuple silently is exactly what the contract
# forbids; a test pins it.
PRECEDENCE: Tuple[str, ...] = (
    "stitched_strict_first_release",
    "archive_snapshot_asof",
    "current_revised",
    "nowcast",
)

STAMP_DOMAIN = frozenset(PRECEDENCE)

# A backtest run on a mixed_edge series is never true real-time; it is labelled this.
PSEUDO_REAL_TIME = "pseudo_real_time"


class MixedEdgeError(ValueError):
    """A mixed_edge contract violation. Named, never silent."""


class MixedPoint:
    """One observation with its mandatory provenance stamp.

    `source_mode` names which lane produced the value and must be in STAMP_DOMAIN.
    Construction with a missing or foreign stamp raises — there is no such thing as
    an unstamped mixed point.
    """

    __slots__ = ("reference_period", "value", "source_mode")

    def __init__(self, reference_period: str, value: float, source_mode: str) -> None:
        if not source_mode:
            raise MixedEdgeError(
                f"mixed point {reference_period!r} has no provenance stamp"
            )
        if source_mode not in STAMP_DOMAIN:
            raise MixedEdgeError(
                f"mixed point {reference_period!r} stamp {source_mode!r} "
                f"not in {sorted(STAMP_DOMAIN)}"
            )
        self.reference_period = reference_period
        self.value = value
        self.source_mode = source_mode

    def as_dict(self) -> Dict[str, object]:
        return {
            "reference_period": self.reference_period,
            "value": self.value,
            "source_mode": self.source_mode,
        }

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"MixedPoint({self.reference_period!r}, {self.value!r}, "
            f"{self.source_mode!r})"
        )


def compose(
    lanes: Mapping[str, Mapping[str, float]],
    reference_periods: Optional[Iterable[str]] = None,
) -> List[MixedPoint]:
    """Compose one mixed_edge series from per-lane {reference_period: value} maps.

    `lanes` maps a source-mode name (must be in STAMP_DOMAIN) to its available
    values. For each reference period, the highest-precedence lane carrying a value
    wins, and the emitted point is stamped with that lane. Every emitted point is
    stamped; unstamped output is impossible by construction (contract rule 1).

    `reference_periods` fixes the output order and set; if omitted, the sorted union
    of all lanes' periods is used. A period with no value in any lane is skipped
    (mixed shows only values that exist — §14.1).
    """
    for mode in lanes:
        if mode not in STAMP_DOMAIN:
            raise MixedEdgeError(
                f"lane {mode!r} not a known source mode {sorted(STAMP_DOMAIN)}"
            )

    if reference_periods is None:
        periods: List[str] = sorted(
            {p for lane in lanes.values() for p in lane}
        )
    else:
        periods = list(reference_periods)

    out: List[MixedPoint] = []
    for period in periods:
        for mode in PRECEDENCE:  # declared precedence, high to low
            lane = lanes.get(mode)
            if lane is None:
                continue
            if period in lane:
                out.append(MixedPoint(period, lane[period], mode))
                break
    return out


def validate(points: Sequence[object]) -> None:
    """Fail if ANY point lacks a valid provenance stamp (contract rule 1).

    Accepts MixedPoint objects or plain mappings with a `source_mode` key, so a
    series loaded from disk is checked the same way as one just composed. A mixed
    series missing a stamp on any point must FAIL the suite — this is that check.
    """
    for i, pt in enumerate(points):
        if isinstance(pt, MixedPoint):
            continue  # MixedPoint cannot exist unstamped
        if isinstance(pt, Mapping):
            mode = pt.get("source_mode")
        else:
            mode = getattr(pt, "source_mode", None)
        if not mode:
            raise MixedEdgeError(
                f"mixed point index {i} has no provenance stamp — prohibited"
            )
        if mode not in STAMP_DOMAIN:
            raise MixedEdgeError(
                f"mixed point index {i} stamp {mode!r} not in {sorted(STAMP_DOMAIN)}"
            )


def coverage_summary(points: Sequence[object]) -> Dict[str, object]:
    """The honesty disclosure: fraction of points from each source lane (rule 4).

    Validates first — a coverage summary over unstamped points is meaningless and
    would hide the very substitution the summary exists to disclose.
    """
    validate(points)
    counts: Dict[str, int] = {mode: 0 for mode in PRECEDENCE}
    for pt in points:
        mode = pt.source_mode if isinstance(pt, MixedPoint) else (
            pt["source_mode"] if isinstance(pt, Mapping) else pt.source_mode
        )
        counts[mode] += 1
    n = len(points)
    fraction = {
        mode: (counts[mode] / n if n else 0.0) for mode in PRECEDENCE
    }
    return {
        "n_points": n,
        "by_source_mode_counts": counts,
        "by_source_mode_fraction": fraction,
    }


def official_use_permitted(for_realtime_claim: bool) -> bool:
    """mixed_edge may NOT back a real-time / as-of CLAIM (contract rule 5).

    It is for display and the live edge. True only for non-real-time use.
    """
    return not for_realtime_claim


def evaluation_label() -> str:
    """A backtest run on mixed_edge is pseudo_real_time, never true real-time."""
    return PSEUDO_REAL_TIME
