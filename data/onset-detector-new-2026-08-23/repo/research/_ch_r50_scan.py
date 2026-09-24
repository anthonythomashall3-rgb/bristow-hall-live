import os, re, glob, json, csv
D="research/prefetch/nber_macrohistory"
data_files=sorted(glob.glob(f"{D}/data/*/*.dat"))
docdir=f"{D}/docs"
def clean(l): return l.strip().strip('"').lstrip('c').strip()
def parse_doc(docpath):
    info={k:"" for k in("title","units","area","md","ann","qtr","mon","sa","source")}
    if not os.path.exists(docpath): return info
    lines=open(docpath,encoding="latin-1").readlines()
    txt="".join(lines)
    def grab(pat):
        m=re.search(pat,txt,re.I); return m.group(1).strip() if m else ""
    info["md"]=grab(r"MD=\s*([0-9.eE+-]+)"); info["units"]=grab(r"UNITS:\s*([^\n\"]*)")
    info["area"]=grab(r"AREA COVERED:\s*([^\n\"]*)"); info["ann"]=grab(r"ANNUAL COVERAGE:\s*([^\n\"]*)")
    info["qtr"]=grab(r"QUARTERLY COVERAGE:\s*([^\n\"]*)"); info["mon"]=grab(r"MONTHLY COVERAGE:\s*([^\n\"]*)")
    info["sa"]=grab(r"SEASONAL ADJUSTMENT:\s*([^\n\"]*)"); info["source"]=grab(r"SOURCE:\s*([^\n\"]*)")
    cl=[clean(l) for l in lines]
    # title = line immediately before a dashes-only line
    for i in range(1,len(cl)-1):
        nxt=cl[i+1]
        if nxt and set(nxt)<=set('- ') and '-' in nxt and cl[i] and not cl[i].upper().startswith('NBER SERIES'):
            info["title"]=cl[i]; break
    return info
rows=[]
for dp in data_files:
    fid=os.path.splitext(os.path.basename(dp))[0]; ch=os.path.basename(os.path.dirname(dp))
    info=parse_doc(os.path.join(docdir,ch,fid+".txt"))
    ymin=ymax=None; nobs=nblank=pmax=nlines=0
    for ln in open(dp,encoding="latin-1"):
        nlines+=1; raw=ln.rstrip("\n")
        yr=raw[0:4].strip(); per=raw[4:10].strip(); val=raw[10:].strip()
        if yr.isdigit(): y=int(yr); ymin=y if ymin is None else min(ymin,y); ymax=max(ymax or y,y)
        if per.isdigit(): pmax=max(pmax,int(per))
        if val=="": nblank+=1
        elif re.match(r'^-?[0-9.]+([eE][+-]?\d+)?$',val): nobs+=1
    freq="A" if pmax==0 and nlines>1 and any(c for c in open(dp,encoding="latin-1").read().split()) else ("M" if pmax==12 else ("Q" if pmax in(3,4) else "?"))
    if fid=="m08217": freq="EMPTY"
    rows.append({"id":fid,"chapter":ch,"freq":freq,"title":info["title"][:75],"units":info["units"][:26],
                 "sa":info["sa"][:10],"ymin":ymin,"ymax":ymax,"nobs":nobs,"nblank":nblank,
                 "period_max":pmax,"nlines":nlines,"source":info["source"][:44]})
csv.DictWriter(open("research/nber_catalog_scan.csv","w",newline=""),fieldnames=list(rows[0].keys())).writerows([dict(zip(rows[0].keys(),rows[0].keys()))]) if False else None
with open("research/nber_catalog_scan.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("scanned",len(rows),"| freq dist:",{k:sum(1 for r in rows if r['freq']==k) for k in set(r['freq'] for r in rows)})
print("n_missing_title",sum(1 for r in rows if not r["title"]))
