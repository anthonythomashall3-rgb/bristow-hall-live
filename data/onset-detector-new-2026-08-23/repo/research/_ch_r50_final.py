import os,re,glob,json,csv
D="research/prefetch/nber_macrohistory"; docdir=f"{D}/docs"
NUM=re.compile(r'^-?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$')
def is_missing(v): return v=="" or v=="." 
def clean(l): return l.strip().strip('"').lstrip('c').strip()
def parse_doc(p):
    info={k:"" for k in("title","units","area","md","ann","qtr","mon","sa","source","docvar")}
    if not os.path.exists(p): return info
    lines=open(p,encoding="latin-1").readlines(); txt="".join(lines)
    g=lambda pat:(re.search(pat,txt,re.I).group(1).strip() if re.search(pat,txt,re.I) else "")
    info["md"]=g(r"MD=\s*([0-9.eE+-]+)"); info["units"]=g(r"UNITS:\s*([^\n\"]*)")
    info["area"]=g(r"AREA COVERED:\s*([^\n\"]*)"); info["ann"]=g(r"ANNUAL COVERAGE:\s*([^\n\"]*)")
    info["qtr"]=g(r"QUARTERLY COVERAGE:\s*([^\n\"]*)"); info["mon"]=g(r"MONTHLY COVERAGE:\s*([^\n\"]*)")
    info["sa"]=g(r"SEASONAL ADJUSTMENT:\s*([^\n\"]*)"); info["source"]=g(r"SOURCE:\s*([^\n\"]*)")
    has_div="-----" in txt
    info["docvar"]="full" if has_div else "compact"
    cl=[clean(l) for l in lines]
    for i in range(0,len(cl)-1):
        nxt=cl[i+1]
        if nxt and set(nxt)<=set('- ') and '-' in nxt and cl[i] and not cl[i].upper().startswith('NBER SERIES'):
            info["title"]=cl[i]; break
    return info
# NBER reference recession peak years within cache era
PEAKS=[1857,1860,1865,1869,1873,1882,1887,1890,1893,1895,1899,1902,1907,1910,1913,1918,1920,1923,1926,1929,1937,1945,1948,1953,1957,1960]
rows=[]; missconv={"blank":set(),"dot":set()}
for dp in sorted(glob.glob(f"{D}/data/*/*.dat")):
    fid=os.path.splitext(os.path.basename(dp))[0]; ch=os.path.basename(os.path.dirname(dp))
    info=parse_doc(os.path.join(docdir,ch,fid+".txt"))
    ymin=ymax=None; nobs=nmiss=pmax=nlines=0; corrupt=False
    for ln in open(dp,encoding="latin-1"):
        nlines+=1; raw=ln.rstrip("\n")
        if len(raw) not in (39,42): corrupt=True
        yr=raw[0:4].strip(); per=raw[4:10].strip(); val=raw[10:].strip()
        if yr.isdigit(): y=int(yr); ymin=y if ymin is None else min(ymin,y); ymax=max(ymax or y,y)
        if per.isdigit(): pmax=max(pmax,int(per))
        if is_missing(val):
            nmiss+=1
            if val=="": missconv["blank"].add(fid)
            else: missconv["dot"].add(fid)
        elif NUM.match(val): nobs+=1
    freq="EMPTY" if fid=="m08217" else ("A" if pmax==0 and nobs>0 else "M")
    span=[y for y in PEAKS if ymin and ymin<=y<=ymax]
    rows.append({"id":fid,"chapter":ch,"freq":freq,"docvar":info["docvar"],"title":info["title"][:75],
                 "units":info["units"][:26],"sa":info["sa"][:8],"ymin":ymin,"ymax":ymax,
                 "nobs":nobs,"nmiss":nmiss,"episodes":len(span),"corrupt":int(corrupt),
                 "source":info["source"][:40]})
with open("research/nber_catalog_scan.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("dot-missing files:",len(missconv["dot"]),"| blank-missing files:",len(missconv["blank"]))
print("docvar:",{v:sum(1 for r in rows if r['docvar']==v) for v in set(r['docvar'] for r in rows)})
print("corrupt files:",[r["id"] for r in rows if r["corrupt"]])
open("research/_ch_r50_missconv.json","w").write(json.dumps({k:sorted(v) for k,v in missconv.items()}))
