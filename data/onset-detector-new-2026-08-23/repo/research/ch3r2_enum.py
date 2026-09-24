#!/usr/bin/env python3
"""CH3-R2 enum builder: scan live store, list current_revised bases + archive_snapshot_asof
(vintage-lane) bases. Read-only. Writes research/ch3_bases_enum.json (rebuilt for the
now-complete store incl B-OFFLINE-2's 18 never-revised current lanes)."""
import glob, json
REPO="/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
NORM=REPO+"/live_data/store/normalized"
cr=set(); vint=set(); modes={}
for f in glob.glob(NORM+"/sha256/*/*.json"):
    try: d=json.load(open(f))
    except: continue
    for r in d.get("records",[]):
        sid=r.get("series_id")
        if not sid: continue
        base=sid.split(".")[0]
        m=r.get("information_set_mode")
        modes[m]=modes.get(m,0)+1
        if m=="current_revised": cr.add(base)
        elif m=="archive_snapshot_asof": vint.add(base)
out={"cr_bases":sorted(cr),"vint_bases":sorted(vint)}
json.dump(out,open(REPO+"/research/ch3_bases_enum.json","w"),indent=0)
print("cr_bases:",len(cr)," vint_bases:",len(vint))
print("modes:",modes)
print("vint:",sorted(vint))
