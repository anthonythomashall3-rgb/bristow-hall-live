import json,os,re,csv,sys
R=os.path.expanduser("~/mnt/store/receipts"); N=os.path.expanduser("~/mnt/store/normalized/sha256")
OUT=os.path.expanduser("~/mnt/staging/_ra_audit/vintage_profile.csv")
rows=[]
pat_sid=re.compile(rb'"series_id":"([^"]+)"')
pat_op=re.compile(rb'"observation_period":"([0-9-]{10})"')
for sid in sorted(os.listdir(R)):
    d=os.path.join(R,sid)
    if not os.path.isdir(d): continue
    best=None
    for f in os.listdir(d):
        try: j=json.load(open(os.path.join(d,f)))
        except Exception: continue
        if j.get("information_set_mode")!="archive_snapshot_asof": continue
        if best is None or (j.get("clocks",{}).get("retrieved_at") or "")>(best.get("clocks",{}).get("retrieved_at") or ""): best=j
    if best is None: continue
    sha=best.get("normalized_sha256"); p=os.path.join(N,sha[:2],sha+".json")
    if not os.path.exists(p): rows.append([sid,"MISSING_PAYLOAD",0,0,"","","",""]); continue
    sz=os.path.getsize(p); nrec=0; vints=set(); ops_min=None; ops_max=None; base=set()
    with open(p,'rb') as fh:
        while True:
            chunk=fh.read(64*1024*1024)
            if not chunk: break
            # avoid splitting a match: read a small tail overlap
            tail=fh.read(400); chunk+=tail
            for m in pat_sid.finditer(chunk):
                s=m.group(1).decode(); nrec+=1
                if "." in s:
                    b,v=s.split(".",1); base.add(b); vints.add(v)
                else: base.add(s)
            for m in pat_op.finditer(chunk):
                o=m.group(1).decode()
                if ops_min is None or o<ops_min: ops_min=o
                if ops_max is None or o>ops_max: ops_max=o
    vs=sorted(vints)
    rows.append([sid,"OK",sz,nrec,len(base),len(vints),(vs[0] if vs else ""),(vs[-1] if vs else ""),ops_min or "",ops_max or "",";".join(sorted(base)[:3])])
    print(rows[-1],flush=True)
with open(OUT,"w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["source_id","status","payload_bytes","n_records","n_base_series","n_vintages","vintage_min","vintage_max","obs_min","obs_max","base_sample"]); w.writerows(rows)
print("DONE",len(rows))
