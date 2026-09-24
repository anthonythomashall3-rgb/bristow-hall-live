"""Reconcile operational_status.json to the current healthy generation.

B-GEO-LAND-3: commit-staged admitted the four bea_cainc1 heads and extended
config to 538, but its O(store) publish was killed by a 2-minute wall.
finish_publish.py then re-published ONE generation over all 538 heads (pointer
188425ad), but operational_status.json was still naming the pre-landing
generation and a health source-id set missing the four new archival heads
(launcher no-arg: overall_state DEGRADED, recovery_required=true, errors
'operational status generation differs from pointer' +
'operational health source IDs are not the exact enabled set; missing=
bea_cainc1_bearegion/county/national/state_current_offline'). Same
interrupted-publish class geo_land_1 / geo_land_2 (reconcile_opstatus.py) and
STATE-CLAIMS db4d3b45 hit.

This replicates the pipeline's own no-change happy path: rebuild
operational_status for the CURRENT generation with
generation_recovery_required=False, AFTER asserting runtime heads == the
generation binding AND == the recovery-head set. No refetch, no data change, no
code/test edit (section 18.1 clean — the store is genuinely healthy; the
launcher correctly flags a stale health file, which this rewrites).
"""
import sys
from pathlib import Path

REPO = Path("/Users/anthonyhall/Projects/bristow-hall/repo")
sys.path.insert(0, str(REPO))

from datetime import datetime, timezone
from bh import produce as bhp, writer_lock
from live_data.rmv2_live.canonical import atomic_write_json


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pipeline, cfg = bhp.load_pipeline(REPO)
    with writer_lock.writer_lock("reconcile operational_status geo-land-3", REPO):
        cp, cs, active_bindings = pipeline._current_generation_binding()
        heads = pipeline.store.all_source_heads()
        rt = pipeline._runtime_head_binding_map(heads)
        assert rt == active_bindings, "heads diverge from generation; abort reconcile"
        pipeline._validate_generation_recovery_heads(heads)
        coverage = pipeline.build_coverage(stamp)
        status = dict(cs)
        status["coverage_counts"] = coverage["counts"]
        status["generated_at"] = stamp
        status["last_refresh_outcomes"] = []
        status["last_refresh_state_counts"] = {}
        operational = pipeline._operational_status(
            status, cp, stamp, [], generation_recovery_required=False)
        assert operational["active_generation_sha256"] == cp["generation_sha256"]
        atomic_write_json(
            pipeline.store.public / "operational_status.json", operational)
        print("reconciled operational_status ->",
              operational["active_generation_sha256"][:12],
              "service_state=", operational.get("service_state"),
              "recovery=", operational.get("generation_recovery_required"))


if __name__ == "__main__":
    main()
