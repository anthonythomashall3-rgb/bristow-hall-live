import json,os,csv,sys
R=os.path.expanduser("~/mnt/store/receipts")
out=os.path.expanduser("~/mnt/staging/_ra_audit/receipt_catalog.csv")
rows=[]
for sid in sorted(os.listdir(R)):
    d=os.path.join(R,sid)
    if not os.path.isdir(d): continue
    fs=[f for f in os.listdir(d) if f.endswith(".json")]
    best=None
    for f in fs:
        try:
            j=json.load(open(os.path.join(d,f)))
        except Exception as e:
            continue
        if best is None or (j.get("clocks",{}).get("retrieved_at") or "")>(best.get("clocks",{}).get("retrieved_at") or ""):
            best=j
    if best is None:
        rows.append([sid,len(fs),"","","","","",""]); continue
    c=best.get("clocks",{})
    rows.append([sid,len(fs),best.get("information_set_mode",""),best.get("outcome",""),
        best.get("response",{}).get("status",""),best.get("response",{}).get("content_length",""),
        best.get("request",{}).get("url","")[:300], c.get("retrieved_at",""),
        best.get("normalized_sha256","")])
with open(out,"w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["source_id","n_receipts","information_set_mode","outcome","http_status","content_length","url","retrieved_at","normalized_sha256"]); w.writerows(rows)
print("rows",len(rows))
from collections import Counter
print("MODES",Counter(r[2] for r in rows))
print("OUTCOMES",Counter(r[3] for r in rows))
