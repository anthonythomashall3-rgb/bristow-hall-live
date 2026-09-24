import os, hashlib, csv, json, re, glob
root="data_archive/additional_vintages/fred_md_official/extracted"
files=[]
for dp,_,fns in os.walk(root):
    for fn in fns:
        if fn.lower().endswith(".csv"):
            files.append(os.path.join(dp,fn))
cur="data_archive/additional_vintages/fred_md_official/current/fred_md_2026-06.csv"
if os.path.exists(cur): files.append(cur)
# vintage tag from filename e.g. 2003-06.csv
def vtag(p):
    m=re.search(r'(\d{4})-(\d{2})', os.path.basename(p))
    return f"{m.group(1)}-{m.group(2)}" if m else None
rows=[]
shas={}
for p in files:
    b=open(p,'rb').read()
    sha=hashlib.sha256(b).hexdigest()
    rows.append((vtag(p), sha, len(b), p))
    shas.setdefault(sha,[]).append(p)
tags=sorted(set(r[0] for r in rows if r[0]))
print("total_files", len(files))
print("distinct_sha", len(shas))
print("distinct_vintage_tags", len(tags))
print("tag_min", tags[0], "tag_max", tags[-1])
# duplicate shas across different tags?
dupe=[ (s,ps) for s,ps in shas.items() if len(ps)>1]
print("sha_collisions", len(dupe))
json.dump({"tags":tags}, open("research/land3c_scratch/tags.json","w"))
