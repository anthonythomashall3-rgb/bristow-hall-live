#!/usr/bin/env python3
"""CH-R68 accuracy/precision reconciliation — pass 1 (read-only, offline).
Streams every normalized file, emits compact per-(series,vintage,mode) group stats
to a JSONL, plus a series->sources map for cross-source reconciliation candidates.
No store writes."""
import json, glob, os, re, collections
from datetime import date

OUT_DIR = "research"
GROUPS = os.path.join(OUT_DIR, "_ch_r68_groups.jsonl")
CAND   = os.path.join(OUT_DIR, "_ch_r68_srcmap.json")
ART    = os.path.join(OUT_DIR, "_ch_r68_artifacts.jsonl")
TODAY  = "2026-08-06"

from datetime import datetime
def _gap(a,b):
    try:
        da=datetime.strptime(a[:10],"%Y-%m-%d"); db=datetime.strptime(b[:10],"%Y-%m-%d")
        return (db-da).days
    except Exception:
        return -1

files = sorted(glob.glob("live_data/store/normalized/sha256/*/*.json"))

# float round-trip artifact: >=12 decimal digits AND ends in run of >=4 nines or zeros
art_re = re.compile(r"\.\d*(9{5,}\d?|0{6,}\d?)$")

def ndecimals(s):
    if "." in s:
        return len(s.split(".",1)[1])
    return 0

# series_id -> {mode -> set(source_id)}  (for reconciliation candidates)
srcmap = collections.defaultdict(lambda: collections.defaultdict(set))
n_art = 0
gf = open(GROUPS, "w"); af = open(ART, "w")
for fi, fp in enumerate(files):
    try:
        d = json.load(open(fp))
    except Exception as e:
        gf.write(json.dumps({"file_error": fp, "err": str(e)})+"\n"); continue
    src = d.get("source_id"); parser = d.get("parser_id")
    recs = d.get("records", [])
    groups = {}  # (series,vintage,mode) -> stats
    for r in recs:
        sid = r.get("series_id"); vin = r.get("vintage_id"); mode = r.get("information_set_mode")
        per = r.get("observation_period") or r.get("observed_at") or ""
        val = r.get("value"); unit = r.get("unit")
        srcmap[sid][mode].add(src)
        k = (sid, vin, mode)
        g = groups.get(k)
        if g is None:
            g = groups[k] = {"series":sid,"vintage":vin,"mode":mode,"source":src,"parser":parser,
                "n":0,"min":None,"max":None,"dup":0,"nonmono":0,"future":0,
                "prev":None,"seen":set(),"maxdec":0,"units":set(),
                "vmin":None,"vmax":None,"nnum":0,"nbad":0,"gaps":collections.Counter()}
        g["n"]+=1
        # date checks
        if per:
            if per in g["seen"]: g["dup"]+=1
            else: g["seen"].add(per)
            if g["prev"] is not None:
                if per < g["prev"]: g["nonmono"]+=1
                else:
                    g["gaps"][_gap(g["prev"],per)]+=1
            g["prev"]=per
            if g["min"] is None or per<g["min"]: g["min"]=per
            if g["max"] is None or per>g["max"]: g["max"]=per
            if per > TODAY: g["future"]+=1
        if unit: g["units"].add(unit)
        # value / precision
        if val is not None and val != "":
            dc = ndecimals(str(val))
            if dc>g["maxdec"]: g["maxdec"]=dc
            if art_re.search(str(val)):
                g["nbad"]+=1
                if n_art < 4000:
                    af.write(json.dumps({"series":sid,"mode":mode,"source":src,"period":per,"value":str(val)})+"\n")
                    n_art+=1
            try:
                fv=float(val); g["nnum"]+=1
                if g["vmin"] is None or fv<g["vmin"]: g["vmin"]=fv
                if g["vmax"] is None or fv>g["vmax"]: g["vmax"]=fv
            except: pass
    # flush groups (drop heavy sets)
    for k,g in groups.items():
        g.pop("prev",None); g.pop("seen",None)
        g["units"]=sorted(g["units"])[:5]
        # keep top-2 gap sizes
        g["gaps"]=g["gaps"].most_common(3)
        gf.write(json.dumps(g)+"\n")
gf.close(); af.close()

# serialize srcmap
out={}
for sid,mm in srcmap.items():
    out[sid]={m:sorted(s) for m,s in mm.items()}
json.dump(out, open(CAND,"w"))
print("files",len(files),"artifacts",n_art,"series",len(out))
