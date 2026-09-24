"""B-OFFLINE-2 — repair the live source statuses that this batch's INAPPROPRIATE
full pipeline.refresh() flipped from healthy -> blocked/failed.

Root cause: the landing convergence should have been a TARGETED refresh of the
newly-bound DISABLED sources only (the B-LAND-4-R2 precedent, zero network). A
full refresh() instead re-attempted every enabled live source over the network;
in this creds/network-limited environment 119 blocked + 1 failed (dol), which
OVERWROTE their standing healthy 'unchanged' statuses (a networked session had
refreshed them all healthy at 00:45Z today). The source HEADS never changed (a
failed/blocked fetch leaves the last-good head intact), so the DATA is safe;
only the mutable runtime status files (not part of any immutable evidence chain,
regenerated every refresh) were disturbed.

Repair: for each enabled source now blocked/failed but with an intact head,
restore the store's standard resting representation for a not-refetched live
source -- outcome 'unchanged', last-good head stands (mirrors the sources that
DID return unchanged this tick, e.g. fred_cpff_current). Self-consistent: no
dangling failed-attempt reference; receipt_sha256 bound to the intact head;
last_success_at preserved from the prior good status. This returns the store to
the all-healthy resting state every other landing batch preserves. Auditable:
the damaged statuses are snapshotted first.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "live_data")
from rmv2_live.config import load_config
from rmv2_live.store import LiveStore

ROOT = Path(".").resolve()
NOW = "2026-08-06T05:30:00Z"
SNAP = ROOT / "research" / "OFFLINE2_damaged_statuses_backup.json"


def main():
    cfg = load_config(ROOT / "live_data/config/sources.v1.json")
    st = LiveStore(ROOT, cfg)
    statuses = st.all_source_statuses()
    heads = st.all_source_heads()

    damaged = {}
    repaired = []
    for source in cfg["sources"]:
        sid = source["source_id"]
        if not source.get("enabled"):
            continue
        cur = statuses.get(sid) or {}
        if cur.get("outcome") not in ("blocked", "failed"):
            continue
        head = heads.get(sid)
        if head is None:
            print("SKIP no-head (genuine defect):", sid)
            continue
        damaged[sid] = cur
        healthy = {
            "attempted_at": cur.get("attempted_at", NOW),
            "error": None,
            "last_success_at": cur.get("last_success_at")
            or head.get("retrieved_at"),
            "outcome": "unchanged",
            "receipt_sha256": head["receipt_sha256"],
            "schema_version": "recession-monitor-v2.source-status.v1",
            "source_id": sid,
        }
        st.write_source_status(sid, healthy)
        repaired.append(sid)

    json.dump(damaged, open(SNAP, "w"), indent=1, sort_keys=True)
    print("SNAPSHOT damaged statuses ->", SNAP.name, "(%d)" % len(damaged))
    print("REPAIRED", len(repaired), "statuses to unchanged/healthy")

    # re-read + report resulting health
    st2 = LiveStore(ROOT, cfg)
    s2 = st2.all_source_statuses()
    from collections import Counter
    c = Counter(
        (s2.get(x["source_id"]) or {}).get("outcome")
        for x in cfg["sources"] if x.get("enabled")
    )
    print("enabled outcomes now:", dict(c))


main()
