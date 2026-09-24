"""B-LAND-8-R2 resume: the 21 panels are bound + in config; the interrupted step
is ONLY the targeted zero-network republish. Re-run it for the 21 ids alone."""
import json, sys
from pathlib import Path
sys.path.insert(0, "live_data")
from rmv2_live.config import load_config
from rmv2_live.pipeline import RefreshPipeline
ROOT = Path(".").resolve()
cfg = load_config(ROOT / "live_data/config/sources.v1.json")
ids = [s["source_id"] for s in cfg["sources"]
       if s["source_id"].startswith("philadelphia_spf_individual_")]
assert len(ids) == 21, len(ids)
pipe = RefreshPipeline(ROOT, cfg)
res = pipe.refresh(source_ids=ids, due_only=False)
out = res if isinstance(res, dict) else {}
json.dump({"n_ids": len(ids), "outcomes": out.get("outcomes"),
           "pointer": (out.get("pointer") or {}).get("generation_sha256")},
          open("research/BLAND8R2_land_out.json", "w"), indent=1, default=str,
          sort_keys=True)
print("RESUME REFRESH done; pointer",
      (out.get("pointer") or {}).get("generation_sha256", "<none>"))
