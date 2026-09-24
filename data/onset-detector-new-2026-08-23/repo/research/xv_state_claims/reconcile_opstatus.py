"""Reconcile operational_status.json to the current healthy generation.

The interrupted commit-staged published generation db4d3b45 (pointer advanced)
but did not rewrite operational_status.json, which still names the pre-landing
generation. This replicates the pipeline's own no-change happy path
(pipeline.refresh lines ~849-869): rebuild operational_status for the CURRENT
generation with generation_recovery_required=False. No refetch; scope stays the
51-state landing. Heads==generation verified separately (diverged=False).
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
    with writer_lock.writer_lock("reconcile operational_status state-claims", REPO):
        cp, cs, active_bindings = pipeline._current_generation_binding()
        heads = pipeline.store.all_source_heads()
        rt = pipeline._runtime_head_binding_map(heads)
        assert rt == active_bindings, "heads diverge from generation; abort reconcile"
        # guard: runtime heads == enabled/archival exact set (recovery invariant)
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
        atomic_write_json(pipeline.store.public / "operational_status.json", operational)
        print("reconciled operational_status ->",
              operational["active_generation_sha256"][:12],
              "service_state=", operational.get("service_state"),
              "recovery=", operational.get("generation_recovery_required"))


if __name__ == "__main__":
    main()
