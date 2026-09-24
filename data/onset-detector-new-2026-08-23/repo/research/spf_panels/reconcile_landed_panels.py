#!/usr/bin/env python3
"""Reconcile landed SPF panel cells to CH-R46's microdata aggregates.

Reads immutable normalized objects through their source heads, recomputes every
CH-R46 aggregate row for the 21 landed targets, and requires exact equality at
the four-decimal precision published by CH-R46.  No store or network writes.
"""
from __future__ import absolute_import

import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "live_data/config/sources.v1.json"
HEADS = ROOT / "live_data/runtime/source_heads"
STORE = ROOT / "live_data/store"
PANEL_DIR = ROOT / "research/spf_panels"
OUT = PANEL_DIR / "landed_reconciliation.v1.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _percentile(values, probability):
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return values[int(position)]
    return (
        values[low] * (high - position)
        + values[high] * (position - low)
    )


def _metrics(values):
    ordered = sorted(values)
    p25 = _percentile(ordered, 0.25)
    p75 = _percentile(ordered, 0.75)
    return {
        "iqr": "%.4f" % (p75 - p25),
        "mean": "%.4f" % (sum(ordered) / len(ordered)),
        "median": "%.4f" % _percentile(ordered, 0.5),
        "n": str(len(ordered)),
        "p10": "%.4f" % _percentile(ordered, 0.10),
        "p90": "%.4f" % _percentile(ordered, 0.90),
        "sd": "%.4f" % (
            statistics.pstdev(ordered) if len(ordered) > 1 else 0.0
        ),
    }


def _actual_rows(source):
    source_id = source["source_id"]
    head_path = HEADS / (source_id + ".json")
    head = _load(head_path)
    digest = head["normalized_sha256"]
    normalized_path = (
        STORE / "normalized" / "sha256" / digest[:2] / (digest + ".json")
    )
    normalized = _load(normalized_path)
    grouped = defaultdict(list)
    for record in normalized["records"]:
        period = record["observation_period"]
        year = int(period[:4])
        quarter = (int(period[5:7]) - 1) // 3 + 1
        variable = "%s%s" % (
            record["spf_target_code"], record["spf_horizon"]
        )
        grouped[(str(year), str(quarter), variable)].append(
            float(record["value"])
        )
    return {
        key: _metrics(values) for key, values in sorted(grouped.items())
    }, {
        "head_sha256": hashlib.sha256(head_path.read_bytes()).hexdigest(),
        "normalized_sha256": digest,
        "record_count": head["record_count"],
    }


def _expected_rows(target):
    path = PANEL_DIR / ("panel__%s.csv" % target)
    rows = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row["year"], row["quarter"], row["variable"])
            rows[key] = {
                name: row[name]
                for name in ("iqr", "mean", "median", "n", "p10", "p90", "sd")
            }
    return rows, hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    config = _load(CONFIG)
    sources = sorted(
        (
            source
            for source in config["sources"]
            if source.get("snapshot_projection") == "archival_panel.v1"
        ),
        key=lambda source: source["source_id"],
    )
    mismatches = []
    targets = {}
    for source in sources:
        target = source["series"]["spf_target_code"]
        actual, binding = _actual_rows(source)
        expected, expected_sha = _expected_rows(target)
        keys = sorted(set(actual) | set(expected))
        target_mismatches = 0
        for key in keys:
            if actual.get(key) != expected.get(key):
                target_mismatches += 1
                if len(mismatches) < 50:
                    mismatches.append({
                        "actual": actual.get(key),
                        "expected": expected.get(key),
                        "key": list(key),
                        "target": target,
                    })
        targets[target] = {
            "actual_aggregate_rows": len(actual),
            "binding": binding,
            "expected_aggregate_rows": len(expected),
            "expected_panel_sha256": expected_sha,
            "mismatch_count": target_mismatches,
            "source_id": source["source_id"],
        }

    pointer = _load(ROOT / "live_data/public/latest.pointer.json")
    payload = {
        "active_generation_sha256": pointer["generation_sha256"],
        "comparison": (
            "every landed cell regrouped by survey quarter and horizon; "
            "n/mean/median/population-sd/IQR/p10/p90 compared exactly at "
            "CH-R46's published four-decimal precision"
        ),
        "mismatch_count": sum(
            target["mismatch_count"] for target in targets.values()
        ),
        "mismatch_examples": mismatches,
        "panel_source_count": len(sources),
        "schema_version": "recession-monitor-v2.spf-panel-reconciliation.v1",
        "status": "PASS" if not mismatches else "FAIL",
        "targets": dict(sorted(targets.items())),
    }
    OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "%s sources=%d aggregate_rows=%d mismatches=%d"
        % (
            payload["status"],
            len(sources),
            sum(row["actual_aggregate_rows"] for row in targets.values()),
            payload["mismatch_count"],
        )
    )
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
