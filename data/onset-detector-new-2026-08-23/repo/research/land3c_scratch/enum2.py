import os, re, hashlib, collections, csv
root="data_archive/additional_vintages/fred_md_official/extracted"
cur="data_archive/additional_vintages/fred_md_official/current/fred_md_2026-06.csv"
files=[]
for dp,_,fns in os.walk(root):
    for fn in fns:
        if fn.lower().endswith(".csv"): files.append(os.path.join(dp,fn))
if os.path.exists(cur): files.append(cur)
def vtag(p):
    m=re.search(r'(\d{4})[-_m](\d{2})', os.path.basename(p)); return f"{m.group(1)}-{m.group(2)}" if m else None
by=collections.defaultdict(list)
for p in files: by[vtag(p)].append(p)
dups={t:len(ps) for t,ps in by.items() if len(ps)>1}
tags=sorted(by)
print("files",len(files),"distinct_tags",len(tags),"tag_min",tags[0],"tag_max",tags[-1])
print("dup_tags",dups)
# freq check: sasdate spacing in one file (monthly?)
p=files[len(files)//2]
with open(p) as f:
    rows=list(csv.reader(f))
dates=[r[0] for r in rows[2:6]]
print("sample vintage",vtag(p),"first dates",dates)
