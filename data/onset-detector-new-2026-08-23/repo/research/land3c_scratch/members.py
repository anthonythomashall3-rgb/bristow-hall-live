import os, re, csv, json, collections
root="data_archive/additional_vintages/fred_md_official/extracted"
files=[]
for dp,_,fns in os.walk(root):
    for fn in fns:
        if fn.lower().endswith(".csv"): files.append(os.path.join(dp,fn))
def vtag(p):
    m=re.search(r'(\d{4})[-_m](\d{2})', os.path.basename(p)); return f"{m.group(1)}-{m.group(2)}" if m else None
notag=[p for p in files if vtag(p) is None]
print("files_without_parseable_tag:", len(notag))
for p in notag[:15]: print("   ", os.path.basename(p))
targets=["W875RX1","CMRMTSPLx","CLAIMSx","CMRMTSPL","ICSA","PAYEMS","INDPRO","RETAILx"]
earliest={t:None for t in targets}
freq_ok=0
for p in files:
    t=vtag(p)
    if t is None: continue
    with open(p, newline='') as f:
        r=csv.reader(f); hdr=next(r)
    for col in targets:
        if col in hdr and (earliest[col] is None or t<earliest[col]): earliest[col]=t
print("earliest_vintage_with_column:")
for c in targets: print(" ", c, earliest[c])
