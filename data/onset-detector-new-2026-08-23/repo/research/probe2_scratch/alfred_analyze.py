import json
from pathlib import Path
H = Path("research/probe2_scratch")
alf = json.load(open(H/"alfred_depth.json"))
gap = json.load(open("model_authority/temporal/asof_surface_gap_map.v1.json"))

PIN = "2020-01-01"
# 13 blocking headline members (identical set across every blocked episode row)
BLOCK = ["ICSA","IURSA","SAHMREALTIME","UNRATE","INDPRO","CMRMTSPL","TCU",
         "GACDFSA066MSFRBPHI","NFCI","PERMIT","HOUST","UMCSENT","W875RX1"]

def ydelta(floor):
    from datetime import date
    fy = date.fromisoformat(floor); py = date.fromisoformat(PIN)
    return round((py - fy).days/365.25, 1)

print("=== §1.3 depth table: series | alfred_floor | vintages | vs 2020 pin | yrs_deeper ===")
rows=[]
for s in sorted(alf):
    r=alf[s]; f=r["alfred_floor"]
    dg = ydelta(f) if f else None
    deeper = f and f < PIN
    rows.append((s,f,r["vintage_count"],deeper,dg))
    print(f"{s:20} {str(f):12} n={r['vintage_count']:5} deeper={deeper} +{dg}y")

# composite reachability: max floor among the 13 blocking members
floors = {m: alf[m]["alfred_floor"] for m in BLOCK}
binding = max(floors.values())
binding_m = [m for m,v in floors.items() if v==binding]
print("\n=== composite ALFRED-alone floor = max over 13 members ===")
print("binding floor", binding, "set by", binding_m)
srt=sorted(floors.items(), key=lambda kv: kv[1], reverse=True)
print("shallowest 7 (the bottleneck):")
for m,v in srt[:7]: print(f"  {m:20} {v}")

print("\n=== §1.3 per-episode reachability (ALFRED alone, full 13-member composite) ===")
allep = ([("rec",e) for e in gap["coverage_grid_recessions"]] +
         [("dist",e) for e in gap["coverage_grid_disturbances"]])
reachable=[]
for kind,e in allep:
    if e.get("composite_fully_asof_replayable"): continue  # already replayable (2020+)
    cut=e["cutoff"]
    ok = all(floors[m] <= cut for m in BLOCK)
    if ok: reachable.append(e["episode_id"])
    # also count how many of 13 members individually reach this cutoff
    n_ok=sum(1 for m in BLOCK if floors[m] <= cut)
    print(f"{e['episode_id']:14} cutoff={cut}  ALFRED_composite_reach={ok}  members_reaching={n_ok}/13")
print("\nEPISODES ALFRED ALONE FULLY REACHES:", reachable or "NONE")

json.dump({"floors":floors,"binding_floor":binding,"binding_members":binding_m,
           "reachable_episodes":reachable,
           "depth_rows":[{"series":s,"floor":f,"vintages":n,"deeper_than_pin":d,"years_deeper":y} for s,f,n,d,y in rows]},
          open(H/"alfred_analysis.json","w"), indent=1)
print("WROTE alfred_analysis.json")
