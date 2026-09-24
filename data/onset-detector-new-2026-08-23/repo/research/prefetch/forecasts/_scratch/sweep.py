#!/usr/bin/env python3
# Integrity sweep: verify magic bytes, quarantine decoys, rebuild manifests. Keep exact bytes.
import os, json, hashlib, shutil, glob, datetime, collections
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
QUAR=os.path.join(ROOT,"_scratch","quarantine")
os.makedirs(QUAR,exist_ok=True)
def utc(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def kind(path):
    with open(path,"rb") as f: h=f.read(8)
    if h[:4]==b"PK\x03\x04": return "zipxlsx"   # xlsx & zip both PK
    if h[:4]==b"%PDF": return "pdf"
    if h[:5] in (b"<!DOC",b"<!doc",b"<html",b"<HTML") or h[:1]==b"<": return "html"
    if h[:2]==b"\xd0\xcf": return "ole"  # legacy xls
    return "other"

def expected(name):
    n=name.lower()
    if n.endswith((".xlsx",".zip",".xls")): return {"zipxlsx","ole"}
    if n.endswith(".pdf"): return {"pdf"}
    if n.endswith((".csv",".htm",".html")): return {"other","html"}
    return {"zipxlsx","pdf","other","ole"}

report={"generated_utc":utc(),"sources":{}}
for src in sorted(os.listdir(ROOT)):
    d=os.path.join(ROOT,src)
    if not os.path.isdir(d) or src=="_scratch": continue
    kept=[]; dropped=[]
    for fp in glob.glob(os.path.join(d,"**","*"),recursive=True):
        if not os.path.isfile(fp) or fp.endswith("MANIFEST.sha256.json"): continue
        b=open(fp,"rb").read(); sha=hashlib.sha256(b).hexdigest(); k=kind(fp)
        name=os.path.relpath(fp,d)
        bad = (k not in expected(name)) or (k=="html")
        rec={"path":os.path.relpath(fp,ROOT),"bytes":len(b),"sha256":sha,"kind":k}
        if bad:
            qp=os.path.join(QUAR,src+"__"+name.replace("/","__"))
            os.makedirs(os.path.dirname(qp) if os.path.dirname(qp) else QUAR,exist_ok=True)
            shutil.move(fp,qp); rec["reason"]=f"{k} not valid for {name}"; dropped.append(rec)
        else: kept.append(rec)
    # sha-dedup within kept: flag placeholders (same sha appearing many times)
    shac=collections.Counter(r["sha256"] for r in kept)
    dupsha={s for s,c in shac.items() if c>=3}  # 3+ identical = placeholder family
    kept2=[]
    for r in kept:
        if r["sha256"] in dupsha:
            fp=os.path.join(ROOT,r["path"]); qp=os.path.join(QUAR,src+"__"+os.path.basename(r["path"]))
            if os.path.exists(fp): shutil.move(fp,qp)
            r["reason"]="sha-dup placeholder (>=3 identical)"; dropped.append(r)
        else: kept2.append(r)
    report["sources"][src]={"kept":len(kept2),"dropped":len(dropped),
                            "kept_bytes":sum(r["bytes"] for r in kept2),
                            "dropped_detail":[{"path":r["path"],"bytes":r["bytes"],"reason":r.get("reason")} for r in dropped]}
    json.dump({"source":src,"generated_utc":utc(),"files":kept2},
              open(os.path.join(d,"MANIFEST.sha256.json"),"w"),indent=2)
json.dump(report,open(os.path.join(ROOT,"SWEEP_REPORT.json"),"w"),indent=2)
for s,v in report["sources"].items():
    print(f"{s:20} kept={v['kept']:3} dropped={v['dropped']:3} kept_bytes={v['kept_bytes']}")
