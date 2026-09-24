#!/usr/bin/env python3
"""CH-R68 pass 1b — format-aware period parsing, real completeness, correct
future-date detection, format-heterogeneity census. Per-file bounded memory.
Read-only, offline."""
import json, glob, os, re, collections, calendar
from datetime import date

TODAY = date(2026,8,6)
GROUPS = "research/_ch_r68_groups2.jsonl"
FMT    = "research/_ch_r68_formats.json"

files = sorted(glob.glob("live_data/store/normalized/sha256/*/*.json"))
art_re = re.compile(r"\.\d*(9{5,}\d?|0{6,}\d?)$")

qend={1:(3,31),2:(6,30),3:(9,30),4:(12,31)}
def parse_period(p):
    """return (kind, sortkey_int, end_date) or None."""
    if not p: return None
    p=str(p)
    m=re.match(r"^(\d{4})-(\d{2})-(\d{2})$",p)
    if m:
        y,mo,d=int(m[1]),int(m[2]),int(m[3])
        try: return ("D", y*10000+mo*100+d, date(y,mo,d))
        except: return None
    m=re.match(r"^(\d{4})-(\d{2})$",p)
    if m:
        y,mo=int(m[1]),int(m[2])
        if 1<=mo<=12:
            return ("M", y*12+mo, date(y,mo,calendar.monthrange(y,mo)[1]))
        return None
    m=re.match(r"^(\d{4})[-]?Q([1-4])$",p)
    if m:
        y,q=int(m[1]),int(m[2]); mo,d=qend[q]
        return ("Q", y*4+q, date(y,mo,d))
    m=re.match(r"^(\d{4})$",p)
    if m:
        y=int(m[1]); return ("Y", y, date(y,12,31))
    return None

def ndec(s):
    return len(s.split(".",1)[1]) if "." in s else 0

fmt_counter=collections.Counter()      # kind -> count records
unparsed=collections.Counter()         # sample unparsed formats
mixed_series=collections.Counter()     # series with >1 period-kind

gf=open(GROUPS,"w")
series_kinds=collections.defaultdict(set)
for fp in files:
    try: d=json.load(open(fp))
    except Exception as e:
        gf.write(json.dumps({"file_error":fp,"err":str(e)})+"\n"); continue
    src=d.get("source_id")
    groups={}
    for r in d.get("records",[]):
        sid=r.get("series_id"); vin=r.get("vintage_id"); mode=r.get("information_set_mode")
        fc=r.get("forecast_horizon") is not None or r.get("forecast_origin") is not None
        pr=parse_period(r.get("observation_period") or r.get("observed_at"))
        val=r.get("value")
        k=(sid,vin,mode)
        g=groups.get(k)
        if g is None:
            g=groups[k]={"series":sid,"vintage":vin,"mode":mode,"source":src,"n":0,
                "keys":set(),"kinds":set(),"future":0,"unparsed":0,"maxdec":0,"nbad":0,
                "vmin":None,"vmax":None,"fc":False,"minkey":None,"maxkey":None,
                "minlbl":None,"maxlbl":None}
        g["n"]+=1
        if fc: g["fc"]=True
        if pr is None:
            g["unparsed"]+=1
            u=r.get("observation_period");
            if u and len(unparsed)<50: unparsed[str(u)[:12]]+=1
        else:
            kind,sk,ed=pr
            g["kinds"].add(kind); series_kinds[sid].add(kind); fmt_counter[kind]+=1
            g["keys"].add(sk)
            if g["minkey"] is None or sk<g["minkey"]: g["minkey"]=sk; g["minlbl"]=r.get("observation_period")
            if g["maxkey"] is None or sk>g["maxkey"]: g["maxkey"]=sk; g["maxlbl"]=r.get("observation_period")
            if ed>TODAY: g["future"]+=1
        if val is not None and val!="":
            dc=ndec(str(val))
            if dc>g["maxdec"]: g["maxdec"]=dc
            if art_re.search(str(val)): g["nbad"]+=1
            try:
                fv=float(val)
                if g["vmin"] is None or fv<g["vmin"]: g["vmin"]=fv
                if g["vmax"] is None or fv>g["vmax"]: g["vmax"]=fv
            except: pass
    for k,g in groups.items():
        keys=g.pop("keys")
        # completeness: distinct keys vs span
        ndist=len(keys)
        g["ndup"]=g["n"]-ndist-g["unparsed"] if g["n"]>=ndist else 0
        miss=0
        if ndist>=3:
            sk=sorted(keys); diffs=[b-a for a,b in zip(sk,sk[1:]) if b>a]
            if diffs:
                step=min(diffs)
                if step>0:
                    expected=(sk[-1]-sk[0])//step+1
                    miss=expected-ndist
        g["missing_est"]=miss if miss>0 else 0
        g["kinds"]=sorted(g["kinds"])
        gf.write(json.dumps(g)+"\n")
gf.close()

for sid,ks in series_kinds.items():
    if len(ks)>1: mixed_series[sid]=len(ks)
json.dump({"record_period_kinds":dict(fmt_counter),
           "unparsed_format_samples":dict(unparsed.most_common(50)),
           "series_with_mixed_period_kinds":len(mixed_series),
           "mixed_examples":dict(mixed_series.most_common(20))},
          open(FMT,"w"), indent=1)
print("done files",len(files),"fmt",dict(fmt_counter),"mixed_series",len(mixed_series))
