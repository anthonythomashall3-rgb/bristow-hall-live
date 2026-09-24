"""B-ACQ-RTDSM-GDI refresh-only: the 24 GDI vars were already bound + config-
appended by bland_rtdsm_gdi_land.py before it hit the 2m timeout. This does ONLY
the targeted zero-network refresh over the 24 disabled sids (writes
operational_status + pointer). No re-bind, no config append -> idempotent."""
import json
import sys
from pathlib import Path

sys.path.insert(0, "live_data")
from rmv2_live.config import load_config
from rmv2_live.pipeline import RefreshPipeline

ROOT = Path(".").resolve()
CFG_PATH = ROOT / "live_data/config/sources.v1.json"

VARS = ["yngdi", "yrgdi", "ypdgdp", "yncompep", "ynws", "ynsws", "ynsd",
        "yntaxr", "ynctax", "yngsub", "ynos", "ynosg", "ynosp", "yncfc",
        "yncfcg", "yncfcp", "yncprfw", "yncprfatw", "ynucprfw", "ynipaid",
        "yndpaid", "ynpincw", "ynrinc", "yntrpay"]
sids = ["philadelphia_rtdsm_%s_vintages_deep" % v for v in VARS]

cfg = load_config(CFG_PATH)
pipe = RefreshPipeline(ROOT, cfg)
result = pipe.refresh(source_ids=sids, due_only=False)
outcomes = result.get("outcomes") if isinstance(result, dict) else None
pointer = result.get("pointer") if isinstance(result, dict) else None
print("TARGETED REFRESH outcomes:", json.dumps(outcomes))
print("POINTER generation:", (pointer or {}).get("generation_sha256", "<none>"))
json.dump({"refresh": {"outcomes": outcomes, "pointer": pointer}},
          open("research/BLAND_RTDSM_GDI_out.json", "w"), indent=1)
print("DONE refresh-only")
