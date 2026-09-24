#!/usr/bin/env python3
"""Build the canonical as-of replay gap map without network or store mutation.

The realtime coverage manifest is the single authority for the adopted channel
roster, landed vintage sources, per-source spans, and month-by-month deployed
replay membership.  This builder deliberately does not maintain a second
hard-coded roster or infer coverage from draft endpoints.
"""
from __future__ import absolute_import

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LEDGER_REL = Path(
    "model_authority/target_ledger/instrument_onset_target_ledger.v1.json"
)
REPLAY_REL = Path(
    "model_authority/temporal/realtime_coverage_manifest.v1.json"
)
OUT_REL = Path("model_authority/temporal/asof_surface_gap_map.v1.json")
SCHEMA_VERSION = "recession-monitor-v2.asof-surface-gap-map.v1"


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _counts(values):
    counts = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _tier_of(cutoff_iso):
    cutoff = dt.date.fromisoformat(cutoff_iso)
    if cutoff < dt.date(1957, 6, 1):
        return "pre_reconstruction"
    if cutoff < dt.date(1976, 6, 1):
        return "monthly_era"
    return "daily_era"


def _asof_class(member):
    status = member["realtime_status"]
    if status == "vintage":
        return "a"
    if status == "unrevised_certified":
        if member.get("certificate") == "pending":
            return "b-PENDING"
        return "b"
    return "d"


def _coverage_lookup(replay):
    by_month = {row["month"]: row for row in replay["monthly_coverage"]}
    months = sorted(by_month)

    def lookup(cutoff_iso):
        month = cutoff_iso[:7]
        if month in by_month:
            return by_month[month]
        prior = [candidate for candidate in months if candidate <= month]
        if prior:
            return by_month[prior[-1]]
        return {
            "month": month,
            "covered_members": [],
            "member_states": {
                member_id: "outside_coverage_window"
                for member_id in replay["members"]
            },
            "channels_nonempty": [],
            "nonempty_channel_count": 0,
            "available_channel_weight_raw": 0.0,
            "renormalized_available_weight": 0.0,
        }

    return lookup


def _grade_episode(
    episode_id,
    cutoff_iso,
    ledger_as_of_replayable,
    replay,
    coverage_at,
):
    row = coverage_at(cutoff_iso)
    all_members = set(replay["members"])
    available = set(row["covered_members"])
    blocking = all_members - available
    return {
        "episode_id": episode_id,
        "cutoff": cutoff_iso,
        "tier": _tier_of(cutoff_iso),
        "ledger_as_of_replayable": bool(ledger_as_of_replayable),
        "composite_fully_asof_replayable": bool(
            ledger_as_of_replayable and not blocking
        ),
        "available_members": sorted(available),
        "available_count": len(available),
        "blocking_members": sorted(blocking),
        "blocking_count": len(blocking),
        "member_states": {
            member_id: row["member_states"].get(member_id, "unknown")
            for member_id in sorted(all_members)
        },
        "channels_nonempty": row["channels_nonempty"],
        "nonempty_channel_count": row["nonempty_channel_count"],
        "available_channel_weight_raw": row["available_channel_weight_raw"],
        "available_channel_weight_share": row[
            "renormalized_available_weight"
        ],
        "coverage_manifest_month": row["month"],
    }


def _members(replay):
    rows = []
    for member_id, member in sorted(replay["members"].items()):
        rows.append(
            {
                "member_id": member_id,
                "series_id": member.get("fred_series"),
                "channel": member["channel"],
                "channel_weight": member["channel_weight"],
                "realtime_status": member["realtime_status"],
                "asof_class": _asof_class(member),
                "certificate": member.get("certificate"),
                "vintage_sources": sorted(member["store_vintage_sources"]),
                "first_vintage_date": member.get("first_vintage_date"),
                "latest_vintage_date": member.get("latest_vintage_date"),
                "first_vintage_month": member.get("first_vintage_month"),
                "per_source_vintage_span": member.get(
                    "per_source_vintage_span", {}
                ),
                "contaminated_before_month": member.get(
                    "contaminated_before_month"
                ),
                "note": member.get("pending_note")
                or member.get("contamination_note"),
            }
        )
    return rows


def _vintage_sources(members):
    sources = {}
    for member in members:
        for source_id in member["vintage_sources"]:
            span = member["per_source_vintage_span"].get(source_id, {})
            sources[source_id] = {
                "member_id": member["member_id"],
                "series_id": member["series_id"],
                "first_vintage": span.get("first_vintage"),
                "latest_vintage": span.get("latest_vintage"),
                "deep_lane": source_id.endswith("_deep"),
            }
    return dict(sorted(sources.items()))


def build(project_root=ROOT):
    root = Path(project_root).resolve()
    ledger_path = root / LEDGER_REL
    replay_path = root / REPLAY_REL
    ledger = _read_json(ledger_path)
    replay = _read_json(replay_path)
    coverage_at = _coverage_lookup(replay)
    members = _members(replay)
    vintage_sources = _vintage_sources(members)

    recessions = [
        _grade_episode(
            row["episode_id"],
            row["onset_T_star"],
            row["as_of_replayable"],
            replay,
            coverage_at,
        )
        for row in ledger["recession_targets"]
    ]
    disturbances = [
        _grade_episode(
            row["episode_id"],
            row["start"],
            _tier_of(row["start"]) != "pre_reconstruction",
            replay,
            coverage_at,
        )
        for row in ledger["disturbance_background_windows"]
    ]

    classes = _counts(member["asof_class"] for member in members)
    full = [
        row["episode_id"]
        for row in recessions
        if row["composite_fully_asof_replayable"]
    ]
    blocked = [
        row["episode_id"]
        for row in recessions
        if row["ledger_as_of_replayable"]
        and not row["composite_fully_asof_replayable"]
    ]
    certificate_queue = [
        {
            "member_id": member["member_id"],
            "channel": member["channel"],
            "action": "issue the B1.4 unrevised-series certificate",
        }
        for member in members
        if member["asof_class"] == "b-PENDING"
    ]
    no_path_queue = [
        {
            "member_id": member["member_id"],
            "channel": member["channel"],
            "action": "establish and land a point-in-time source path",
        }
        for member in members
        if member["asof_class"] == "d"
    ]
    deep_sources = {
        source_id: source
        for source_id, source in vintage_sources.items()
        if source["deep_lane"]
    }
    latest_row = replay["monthly_coverage"][-1]

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_class": "asof_surface_gap_map_receipt",
        "operation": "DERIVE",
        "status": "RECEIPT_NO_ADMISSIONS",
        "generation_binding": "instrument.v2.g1",
        "recorded_by": "codex",
        "recorded_context": (
            "canonical replay-derived gap map; no duplicate roster"
        ),
        "source_bytes": {
            "ledger": {
                "path": str(LEDGER_REL),
                "sha256": _sha256(ledger_path),
            },
            "realtime_coverage_manifest": {
                "path": str(REPLAY_REL),
                "sha256": _sha256(replay_path),
            },
            "instrument_composite": "method_source/index_v1.py",
            "timing_model": "data_vault/catalog/timing_model.json",
        },
        "classification_legend": {
            "a": "immutable store-held point-in-time vintages",
            "b": "unrevised final plus an issued publication certificate",
            "b-PENDING": (
                "unrevised final whose required B1.4 certificate is pending"
            ),
            "d": "no point-in-time path yet",
        },
        "existing_vintage_bases": vintage_sources,
        "headline_members": members,
        "coverage_grid_recessions": recessions,
        "coverage_grid_disturbances": disturbances,
        "summary": {
            "headline_member_count": len(members),
            "asof_class_counts": classes,
            "episodes_fully_asof_replayable_now": full,
            "episodes_asof_replayable_in_ledger_but_composite_blocked_now": blocked,
            "latest_coverage": {
                "month": latest_row["month"],
                "available_members": len(latest_row["covered_members"]),
                "total_members": replay["member_count"],
                "available_channel_weight_share": latest_row[
                    "renormalized_available_weight"
                ],
            },
            "headline_finding": (
                "%d members have immutable vintage lanes; %d unrevised "
                "members await B1.4 certificates; %d members have no as-of "
                "path. Episode completeness is derived from the canonical "
                "monthly replay coverage rather than a fixed endpoint date."
                % (
                    classes.get("a", 0),
                    classes.get("b-PENDING", 0),
                    classes.get("d", 0),
                )
            ),
            "nearest_completable_window": (
                "Latest deployed coverage is %d/%d members at %s; issue the "
                "%d pending unrevised-series certificates and resolve any "
                "remaining typed no-path gaps before labeling full replay."
                % (
                    len(latest_row["covered_members"]),
                    replay["member_count"],
                    latest_row["month"],
                    len(certificate_queue),
                )
            ),
        },
        "certificate_queue": certificate_queue,
        "acquisition_queue": no_path_queue,
        "deep_vintage_lane_finding": {
            "source_count": len(deep_sources),
            "member_ids": sorted(
                {source["member_id"] for source in deep_sources.values()}
            ),
            "sources": deep_sources,
            "finding": (
                "Deep-lane effects are already reflected in each episode's "
                "available_members and blockers through the canonical replay "
                "manifest."
            ),
        },
        "no_admissions": True,
        "no_store_mutation": True,
        "no_network": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="build canonical as-of gap map")
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    out = Path(args.out).resolve() if args.out else root / OUT_REL
    payload = build(root)
    body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print("WROTE", out)
    print("sha256", hashlib.sha256(body.encode("utf-8")).hexdigest())
    print("asof_class_counts", payload["summary"]["asof_class_counts"])
    print(
        "fully_replayable_now",
        payload["summary"]["episodes_fully_asof_replayable_now"] or "NONE",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
