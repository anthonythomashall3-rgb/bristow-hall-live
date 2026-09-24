#!/usr/bin/env python3
"""CH-R46 SPF microdata parser (read-only). Fixed workbook -> tidy per-variable panels.
Per (YEAR,QUARTER) per forecast column: n, mean, median, sd, iqr(dispersion), p10, p90.
Output: research/spf_panels/panel__<SHEET>.csv + index + dispersion summary."""
import os, json, csv, math, statistics as st
import openpyxl

BASE=os.path.dirname(os.path.abspath(__file__))
FIXED=os.path.join(BASE,"_fixed.xlsx")
OUT=BASE
IDCOLS={"YEAR","QUARTER","ID","INDUSTRY"}

def num(v):
    if v is None: return None
    if isinstance(v,(int,float)):
        f=float(v)
        return None if math.isnan(f) else f
    s=str(v).strip()
    if s in ("","#N/A","NA","#N/A N/A","#DIV/0!","#VALUE!"): return None
    try: return float(s)
    except: return None

def pct(sorted_vals,p):
    if not sorted_vals: return None
    if len(sorted_vals)==1: return sorted_vals[0]
    k=(len(sorted_vals)-1)*p
    lo=math.floor(k); hi=math.ceil(k)
    if lo==hi: return sorted_vals[int(k)]
    return sorted_vals[lo]*(hi-k)+sorted_vals[hi]*(k-lo)

wb=openpyxl.load_workbook(FIXED, read_only=True, data_only=True)
index=[]
disp_rows=[]  # sheet, mean dispersion per era
for sheet in wb.sheetnames:
    ws=wb[sheet]
    it=ws.iter_rows(values_only=True)
    header=list(next(it))
    fcols=[(i,h) for i,h in enumerate(header) if h not in IDCOLS and h is not None]
    try:
        iy=header.index("YEAR"); iq=header.index("QUARTER")
    except ValueError:
        index.append({"sheet":sheet,"status":"NO_YEARQ","cols":";".join(map(str,header))}); continue
    # accumulate values per (year,quarter, colname)
    agg={}  # (y,q) -> col -> list
    nrows=0
    for row in it:
        if row is None: continue
        y=num(row[iy]); q=num(row[iq])
        if y is None or q is None: continue
        key=(int(y),int(q)); nrows+=1
        d=agg.setdefault(key,{})
        for ci,cn in fcols:
            v=num(row[ci]) if ci<len(row) else None
            if v is not None:
                d.setdefault(cn,[]).append(v)
    # write tidy panel
    path=os.path.join(OUT,f"panel__{sheet}.csv")
    with open(path,"w",newline="") as fh:
        w=csv.writer(fh)
        w.writerow(["year","quarter","variable","n","mean","median","sd","iqr","p10","p90"])
        for (y,q) in sorted(agg):
            for cn,vals in sorted(agg[(y,q)].items()):
                sv=sorted(vals); n=len(sv)
                mean=sum(sv)/n
                med=pct(sv,0.5)
                sd=st.pstdev(sv) if n>1 else 0.0
                p25=pct(sv,0.25); p75=pct(sv,0.75)
                iqr=(p75-p25) if (p25 is not None and p75 is not None) else 0.0
                w.writerow([y,q,cn,n,f"{mean:.4f}",f"{med:.4f}",f"{sd:.4f}",
                            f"{iqr:.4f}",f"{pct(sv,0.10):.4f}",f"{pct(sv,0.90):.4f}"])
    qtrs=sorted(agg);
    yr0=qtrs[0][0] if qtrs else None; yr1=qtrs[-1][0] if qtrs else None
    index.append({"sheet":sheet,"status":"OK","fcast_cols":";".join(c for _,c in fcols),
                  "n_forecaster_rows":nrows,"n_survey_qtrs":len(qtrs),
                  "first":f"{yr0}Q{qtrs[0][1]}" if qtrs else "",
                  "last":f"{yr1}Q{qtrs[-1][1]}" if qtrs else ""})

with open(os.path.join(OUT,"_index.json"),"w") as fh:
    json.dump(index,fh,indent=1)
print("SHEETS_DONE",len([i for i in index if i["status"]=="OK"]))
print("SKIPPED",[i["sheet"] for i in index if i["status"]!="OK"])
