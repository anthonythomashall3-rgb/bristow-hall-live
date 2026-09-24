import json, copy, hashlib, sys
STAMP="20260808T173444Z"
RULING="OWNER_RULING_20260808T171959Z_EFFN_ONLY"
BATCH="B-RETIRE-INHERITED"
P="model_authority/parameters/parameter_registry.v1.json"
raw=open(P,encoding="utf-8").read()
d=json.loads(raw)
# 1. snapshot BEFORE touching
snap="model_authority/parameters/retired/registry_pre_retire_%s.v1.json"%STAMP
open(snap,"w",encoding="utf-8").write(raw)
before_sha=hashlib.sha256(raw.encode()).hexdigest()
params=d["parameters"]
keys=sorted(params.keys())
# capture values before
vbefore={k:copy.deepcopy(v.get("value")) for k,v in params.items()}
# 2. retire every row — change ONLY provenance metadata
for k in keys:
    row=params[k]
    prior=row.get("provenance")
    assert prior=="inherited", "unexpected prior provenance %s on %s"%(prior,k)
    row["provenance"]="retired"
    row["prior_provenance"]=prior
    row["retired_by"]=RULING
    row["retired_at"]=STAMP
# provenance_classes gains 'retired'
if "retired" not in d["provenance_classes"]:
    d["provenance_classes"]=list(d["provenance_classes"])+["retired"]
# grandfather baseline: the retired constants allowed to remain in code (reproducibility)
d["retired_citation_baseline"]=keys
d["retirement_note"]=("37 inherited params RETIRED per %s (cited as sanction, batch %s, %s). "
  "inherited->0 by RETIREMENT not measurement. Values byte-unchanged; provenance authority removed."
  %(RULING,BATCH,STAMP))
out=json.dumps(d,indent=2,ensure_ascii=False)+"\n"
open(P,"w",encoding="utf-8").write(out)
# 3. verify NO value changed
d2=json.loads(open(P,encoding="utf-8").read())
changed=[k for k in keys if d2["parameters"][k].get("value")!=vbefore[k]]
print("rows_retired",len(keys))
print("values_changed",len(changed),changed)
print("provenance_classes",d2["provenance_classes"])
print("baseline_len",len(d2["retired_citation_baseline"]))
print("snapshot",snap)
print("before_sha",before_sha)
print("alias_preserved",all("alias_of" in d2["parameters"][k] for k in ("method_source/alfred_replay.py::CH","method_source/energy_build.py::BAR_E","method_source/forecaster_site.py::BAR")))
