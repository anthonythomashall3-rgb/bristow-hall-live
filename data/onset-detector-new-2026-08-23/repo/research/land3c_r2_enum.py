import os,re,csv,hashlib,json,glob
roots=["data_archive/additional_vintages/fred_md_official/extracted",
       "data_archive/additional_vintages/fred_md_official/current"]
files=[]
for r in roots:
    for dp,_,fns in os.walk(r):
        for fn in fns:
            if fn.lower().endswith(".csv"): files.append(os.path.join(dp,fn))
def vtag(p):
    b=os.path.basename(p)
    m=re.search(r'(\d{4})[-_]?m?(\d{2})',b)
    return f"{m.group(1)}-{m.group(2)}" if m else None
targets=["W875RX1","CLAIMSx","CMRMTSPLx"]
rows=[]; shas={}
for p in files:
    raw=open(p,'rb').read()
    sha=hashlib.sha256(raw).hexdigest()
    shas.setdefault(sha,[]).append(p)
    txt=raw.decode('utf-8',errors='replace').splitlines()
    hdr=txt[0].split(',')
    present={t:(t in hdr) for t in targets}
    rows.append({"tag":vtag(p),"sha":sha[:12],"cols":len(hdr),"present":present,"path":p})
tags=sorted(set(r["tag"] for r in rows if r["tag"]))
# column presence summary
summ={t:sum(1 for r in rows if r["present"][t]) for t in targets}
print("total_files",len(files),"distinct_sha",len(shas),"distinct_tags",len(tags))
print("tag_min",tags[0],"tag_max",tags[-1])
print("present_counts",summ)
# any vintage missing any target?
miss=[(r["tag"],[t for t in targets if not r["present"][t]]) for r in rows if not all(r["present"].values())]
print("vintages_missing_a_target",len(miss))
for m in miss[:10]: print("  MISS",m)
# duplicate tags (multiple files same vintage)?
from collections import Counter
tc=Counter(r["tag"] for r in rows if r["tag"])
dups={k:v for k,v in tc.items() if v>1}
print("dup_tags",len(dups),dict(list(dups.items())[:10]))
json.dump({"rows":rows,"tags":tags,"summ":summ,"n_sha":len(shas)},open("research/land3c_r2_enum.json","w"))
