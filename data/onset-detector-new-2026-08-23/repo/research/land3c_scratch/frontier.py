import os,re,csv,collections,json
root="data_archive/additional_vintages/fred_md_official/extracted"
cur="data_archive/additional_vintages/fred_md_official/current/fred_md_2026-06.csv"
files=[]
for dp,_,fns in os.walk(root):
    for fn in fns:
        if fn.lower().endswith(".csv"): files.append(os.path.join(dp,fn))
if os.path.exists(cur): files.append(cur)
def vtag(p):
    m=re.search(r'(\d{4})[-_m](\d{2})', os.path.basename(p)); return f"{m.group(1)}-{m.group(2)}" if m else None
# schema drift: col count per vintage
sizes={}
cols_first=None; cols_last=None
tags=sorted(vtag(p) for p in files)
byt={vtag(p):p for p in files}
for t in [tags[0], tags[len(tags)//2], tags[-1]]:
    with open(byt[t]) as f: hdr=next(csv.reader(f))
    sizes[t]=len(hdr)
print("col_count_by_vintage(sample):", sizes)
# for W875RX1/CLAIMSx/CMRMTSPLx: earliest OBSERVATION date & value non-null in earliest vintage; and as-of stamp = vintage date
# 3B ALFRED deep lanes earliest as-of stamps (from receipt): W875RX1 2010-06-20, CMRMTSPL 2013-06-20, ICSA 2009-06-20
alfred_asof={"W875RX1":"2010-06","CMRMTSPL":"2013-06","ICSA":"2009-06"}
fredmd_col={"W875RX1":"W875RX1","CMRMTSPL":"CMRMTSPLx","ICSA":"CLAIMSx"}
# fredmd earliest AS-OF for each = earliest vintage tag where column present & has any non-null value
res={}
for mem,col in fredmd_col.items():
    earliest=None
    for t in tags:
        with open(byt[t]) as f:
            r=csv.reader(f); hdr=next(r); trow=next(r)
            if col not in hdr: continue
            idx=hdr.index(col)
            has=False
            for row in r:
                if len(row)>idx and row[idx].strip()!="":
                    has=True; break
        if has:
            earliest=t; break
    res[mem]={"fredmd_col":col,"fredmd_earliest_asof_vintage":earliest,"alfred_earliest_asof":alfred_asof[mem]}
print(json.dumps(res,indent=1))
json.dump({"schema_sizes":sizes,"frontier":res,"n_vintages":len(files),"tag_min":tags[0],"tag_max":tags[-1]}, open("research/land3c_scratch/frontier_out.json","w"), indent=1)
