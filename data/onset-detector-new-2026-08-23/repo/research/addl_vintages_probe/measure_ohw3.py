import os, glob, hashlib, csv, json, re
base="data_archive/additional_vintages/ohw3"
files=sorted(glob.glob(base+"/*.csv"))
series={}
for f in files:
    fn=os.path.basename(f)
    m=re.match(r"(.+)_(\d{4}-\d{2}-\d{2})\.csv$",fn)
    s,cap=m.group(1),m.group(2)
    with open(f,'rb') as fh: raw=fh.read()
    lines=raw.split(b"\n")
    payload=b"\n".join(lines[1:])            # drop header (embeds date token)
    h=hashlib.sha1(payload).hexdigest()
    # last observation date = last non-empty data row's first field
    lastobs=None; firstobs=None; nrows=0
    for ln in lines[1:]:
        if not ln.strip(): continue
        d=ln.split(b",")[0].decode()
        if firstobs is None: firstobs=d
        lastobs=d; nrows+=1
    d=series.setdefault(s,{"files":0,"payloads":set(),"caps":[],"lastobs":set(),"firstobs":set(),"bytes":0})
    d["files"]+=1; d["payloads"].add(h); d["caps"].append(cap)
    d["lastobs"].add(lastobs); d["firstobs"].add(firstobs); d["bytes"]+=len(raw)
out={}
for s,d in series.items():
    caps=sorted(d["caps"]); los=sorted(x for x in d["lastobs"] if x)
    out[s]={"files":d["files"],"distinct_payloads":len(d["payloads"]),
            "cap_first":caps[0],"cap_last":caps[-1],
            "series_start":sorted(x for x in d["firstobs"] if x)[0],
            "lastobs_min":los[0],"lastobs_max":los[-1],"lastobs_distinct":len(los),
            "bytes":d["bytes"]}
json.dump(out,open("research/addl_vintages_probe/ohw3_measured.json","w"),indent=1)
for s in sorted(out,key=lambda k:-out[k]["distinct_payloads"]):
    o=out[s]
    print(f"{s:22s} files={o['files']:4d} realVint={o['distinct_payloads']:3d} lastobsSpan={o['lastobs_min']}..{o['lastobs_max']} cap={o['cap_first']}..{o['cap_last']} start={o['series_start']}")
