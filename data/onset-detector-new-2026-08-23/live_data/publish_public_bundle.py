#!/usr/bin/env python3
"""Publish the verified live generation as a public, CORS-ready static bundle.

A Claude artifact, a GPT artifact, and a Cloudflare-hosted page are all
sandboxed browser pages. They can fetch public https URLs and nothing else.
They cannot reach http://127.0.0.1:8792 : browsers block http subresources on
an https page, and 127.0.0.1 resolves to each visitor's own machine rather
than to the Mac running the collector. So the data needs a public address.

This script produces that address's contents. It reads only the
cryptographically verified active generation, never loose runtime files, and
writes a small deterministic tree that Cloudflare Pages (or any static host)
can serve directly.

It performs no acquisition, computes no scientific output, and grants no
scientific admission.
"""

from __future__ import absolute_import, print_function

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from live_data.rmv2_live.canonical import (  # noqa: E402
    CanonicalDataError,
    atomic_write,
    canonical_json_bytes,
    sha256_bytes,
)
from live_data.rmv2_live.store import read_verified_generation  # noqa: E402
from live_data.rmv2_live.publish_gate import (  # noqa: E402
    assert_series_publishable,
    load_source_publish_class_map,
    series_item_is_publishable,
)

BUNDLE_SCHEMA = "recession-monitor-v2.public-web-bundle.v1"
CORS_HEADERS = """/data/live/*
  Access-Control-Allow-Origin: *
  Cache-Control: public, max-age=60, must-revalidate
  Content-Type: application/json; charset=utf-8
"""


def build(project_root, out_root=None):
    project_root = Path(project_root).resolve()
    store_public = project_root / "live_data" / "public"
    generations = project_root / "live_data" / "store" / "generations"
    # Post-publish readback is a hot operational reader (store.py docstring): the
    # per-source binding closure is authenticated via the content-addressed
    # attestation cache, making generation read O(changed sources) instead of
    # O(total normalized bytes). Every structural check (pointer, manifest, member
    # SHA-256s, receipt binding, storage fingerprint) is unchanged. The full raw ->
    # normalized -> receipt closure still runs as `verify --full`, which the nightly
    # executes as step 1 immediately before this publish. Without this flag the full
    # O(store) re-hash overran the 1800s publish budget on 3 consecutive nightlies
    # (Aug 9-11 2026, elapsed 1800.0-1800.3s, completed=false); server.py and
    # pipeline.py already read this way (B-NIGHTFIX-1).
    generation = read_verified_generation(
        store_public, generations, attest_bindings=True
    )

    members = generation["members"]
    pointer = generation["pointer"]
    status = members["status.json"]
    coverage = members["coverage.json"]
    snapshot = members["snapshot.json"]

    # One latest observation per stable series. This is what charts and value
    # tiles read. The full 21 MB snapshot is deliberately not published.
    raw_series = snapshot.get("series") or {}
    series = []
    for series_id in sorted(raw_series):
        latest = (raw_series[series_id] or {}).get("latest") or {}
        series.append({
            "available_at": latest.get("available_at"),
            "forecast_horizon": latest.get("forecast_horizon"),
            "forecast_origin": latest.get("forecast_origin"),
            "information_set_mode": latest.get("information_set_mode"),
            "label": latest.get("label"),
            "observation_period": latest.get("observation_period"),
            "series_id": series_id,
            "source_id": latest.get("source_id"),
            "unit": latest.get("unit"),
            "value": latest.get("value"),
            "value_status": latest.get("value_status"),
        })

    # Publish-side rights firewall (B-LAND-11-R2). The public bundle carries the
    # PUBLISHABLE set only: internal_only series (licensed families landed for
    # internal scientific use, e.g. dbnomics ISM) are EXCLUDED here, exactly as
    # the P2 HTTP API filters them (publish_gate.filter_snapshot_series) and per
    # OWNER_RULING_20260806_RIGHTS_ALL_CHANNELS.md ("USE all data; do NOT
    # republish private raw data"). This is a PUBLISH-SET change, never a gate
    # weakening (B-NIGHTFIX-1): dropping a licensed series from the public feed is
    # the fail-closed-correct behaviour. assert_series_publishable then remains as
    # a belt-and-suspenders tripwire that must never fire on the filtered set.
    publish_class_map = load_source_publish_class_map(project_root)
    series = [
        item for item in series
        if series_item_is_publishable(item, publish_class_map)
    ]
    assert_series_publishable(series, publish_class_map)

    summary = {
        "active_generation_sha256": pointer["generation_sha256"],
        "generated_at": status.get("generated_at"),
        "notice": (
            "Acquisition status and latest published observations only. The "
            "Stress Unit, National Index, chronology, Onset Watch, Damage "
            "Index and Forecaster shown on the site are a frozen scientific "
            "snapshot and are not recomputed from this feed."
        ),
        "pointer": pointer,
        "schema_version": BUNDLE_SCHEMA,
        "series_count": len(series),
        "source_count": len(snapshot.get("sources", [])),
        "source_health": status.get("current_source_health_counts", {}),
    }

    out_root = Path(out_root or (project_root / "live_data" / "public_deploy"))
    data_dir = out_root / "data" / "live"
    data_dir.mkdir(parents=True, exist_ok=True)

    written = {}
    for name, value in (
        ("pointer.json", pointer),
        ("status.json", status),
        ("coverage.json", coverage),
        ("manifest.json", generation["manifest"]),
        ("summary.json", summary),
        ("series_latest.json", {
            "generated_at": status.get("generated_at"),
            "generation_sha256": pointer["generation_sha256"],
            "schema_version": BUNDLE_SCHEMA,
            "series": series,
        }),
    ):
        data = canonical_json_bytes(value)
        atomic_write(data_dir / name, data, mode=0o644)
        written[name] = {"bytes": len(data), "sha256": sha256_bytes(data)}

    atomic_write(out_root / "_headers", CORS_HEADERS.encode("utf-8"), mode=0o644)

    receipt = {
        "files": written,
        "generation_sha256": pointer["generation_sha256"],
        "output_root": str(out_root),
        "schema_version": BUNDLE_SCHEMA,
        "scientific_effect": "none",
    }
    atomic_write(
        out_root / "publish_receipt.json",
        canonical_json_bytes(receipt),
        mode=0o644,
    )
    return receipt


def main(argv):
    root = argv[1] if len(argv) > 1 else str(Path(__file__).resolve().parents[1])
    out = argv[2] if len(argv) > 2 else None
    try:
        receipt = build(root, out)
    except (CanonicalDataError, OSError, KeyError, ValueError) as exc:
        print("PUBLISH FAILED: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 1
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
