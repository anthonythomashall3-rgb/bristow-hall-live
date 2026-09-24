import json,sys,time
from pathlib import Path
ROOT=Path(".").resolve(); sys.path.insert(0,str(ROOT/"live_data"))
from rmv2_live.config import load_config
from rmv2_live.pipeline import RefreshPipeline
ids=["geo_metro_econ_current","geo_state_econ_current","geo_county_econ_current",
     "geo_state_metrics_current","geo_county_hist_current","geo_county_industry_current"]
t=time.time()
cfg=load_config(ROOT/"live_data/config/sources.v1.json")
res=RefreshPipeline(ROOT,cfg).refresh(source_ids=ids,due_only=False)
out=res.get("outcomes") if isinstance(res,dict) else None
ptr=res.get("pointer") if isinstance(res,dict) else None
print("REPUBLISH done in %.1fs" % (time.time()-t))
print("outcomes:",json.dumps(out))
print("generation:",(ptr or {}).get("generation_sha256","<none>"))
json.dump({"outcomes":out,"pointer":ptr},open(ROOT/"research/geo_land/republish_out.json","w"),indent=1,default=str)
