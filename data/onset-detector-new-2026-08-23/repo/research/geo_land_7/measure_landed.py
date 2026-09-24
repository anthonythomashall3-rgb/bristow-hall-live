"""Measure landed counts for the 3 SQGDP1 heads from the store."""
import json
import sys
from pathlib import Path

REPO = Path("/Users/anthonyhall/Projects/bristow-hall/repo")
sys.path.insert(0, str(REPO))
from bh import produce as bhp

SOURCES = [
    "bea_sqgdp1_national_current_offline",
    "bea_sqgdp1_bearegion_current_offline",
    "bea_sqgdp1_state_current_offline",
]


def main():
    pipeline, _ = bhp.load_pipeline(REPO)
    out = {}
    tot = {"series": 0, "records": 0, "available": 0, "unavailable": 0}
    for sid in SOURCES:
        head = pipeline.store.read_source_head(sid)
        norm = pipeline.store.read_normalized(head["normalized_sha256"])
        recs = norm["records"] if isinstance(norm, dict) else norm
        series = set()
        avail = 0
        periods = []
        for r in recs:
            series.add(r["series_id"])
            if r.get("value") is not None:
                avail += 1
            periods.append(r["observation_period"])
        d = {
            "series": len(series),
            "records": len(recs),
            "available": avail,
            "unavailable": len(recs) - avail,
            "pmin": min(periods) if periods else None,
            "pmax": max(periods) if periods else None,
            "latest": head.get("latest_observation_period"),
            "head_record_count": head.get("record_count"),
        }
        out[sid] = d
        for k in tot:
            tot[k] += d[k]
        print("%s series=%d records=%d avail=%d unavail=%d %s..%s latest=%s"
              % (sid, d["series"], d["records"], d["available"], d["unavailable"],
                 d["pmin"], d["pmax"], d["latest"]))
    (REPO / "research/geo_land_7/landed_counts.json").write_text(
        json.dumps(out, indent=1))
    print("TOTALS", json.dumps(tot))


if __name__ == "__main__":
    main()
