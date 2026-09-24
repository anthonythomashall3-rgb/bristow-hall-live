import json,sys
sys.path.insert(0,"live_data")
from pathlib import Path
from rmv2_live.config import load_config
from rmv2_live.pipeline import RefreshPipeline
ROOT=Path(".").resolve()
cfg=load_config(ROOT/"live_data/config/sources.v1.json")
print("config sources",len(cfg["sources"]),"enabled",sum(1 for s in cfg["sources"] if s.get("enabled")),
      "archival",sum(1 for s in cfg["sources"] if s.get("archival")))
pl=RefreshPipeline(ROOT,cfg); pl.store.initialize()
ATT="2026-08-05T21:45:00Z"
snap=pl.build_snapshot(ATT); cov=pl.build_coverage(ATT)
st=pl.build_status(ATT,[],snap,cov)
ptr=pl.store.publish_generation(snap, st, cov)
print("PUBLISHED", ptr.get("generation_sha256"))
json.dump(ptr,open("research/land3c_r2_pointer.json","w"),indent=1)
