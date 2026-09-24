#!/usr/bin/env python3
"""CH-R46: forecaster-disagreement (dispersion) as a stress-signal candidate.
For near-term horizon h=2 (next quarter): cross-forecaster dispersion per survey quarter.
RGDP/EMP: transform each forecaster's level pair (col1->col2) to annualized growth first,
so dispersion is scale-free. UNEMP: rate units already. RECESS2: aggregate recession prob.
Then per-NBER-episode vs expansion mean. Read-only."""
import os, math, csv, json, statistics as st
import openpyxl
BASE=os.path.dirname(os.path.abspath(__file__))
wb=openpyxl.load_workbook(os.path.join(BASE,"_fixed.xlsx"), read_only=True, data_only=True)

def num(v):
    if v is None: return None
    if isinstance(v,(int,float)):
        f=float(v); return None if math.isnan(f) else f
    s=str(v).strip()
    try: return float(s)
    except: return None

def sheet_rows(name):
    ws=wb[name]; it=ws.iter_rows(values_only=True); hdr=list(next(it))
    idx={h:i for i,h in enumerate(hdr)}
    for row in it:
        if row: yield row, idx

# NBER recession quarters (survey-quarter basis)
def qkey(y,q): return y*4+(q-1)
REC=set()
for (ys,qs),(ye,qe) in [((1969,4),(1970,4)),((1973,4),(1975,1)),((1980,1),(1980,3)),
    ((1981,3),(1982,4)),((1990,3),(1991,1)),((2001,1),(2001,4)),
    ((2007,4),(2009,2)),((2020,1),(2020,2))]:
    a=qkey(ys,qs); b=qkey(ye,qe)
    for k in range(a,b+1): REC.add(k)
EP_NAMES={qkey(1969,4):"1969-70",qkey(1973,4):"1973-75",qkey(1980,1):"1980",
    qkey(1981,3):"1981-82",qkey(1990,3):"1990-91",qkey(2001,1):"2001",
    qkey(2007,4):"2007-09",qkey(2020,1):"2020"}

def disagreement_series(sheet, mode):
    """returns dict (y,q)->dispersion(iqr). mode: 'growth' uses col1->col2 annualized; 'level' uses col2."""
    c1=f"{sheet}1"; c2=f"{sheet}2"
    out={}
    cur=None; buf=[]
    def flush(k):
        sv=sorted(buf)
        if len(sv)>=5:
            p25=sv[int((len(sv)-1)*.25)]; p75=sv[int((len(sv)-1)*.75)]
            out[k]=(p75-p25, len(sv), st.pstdev(sv))
    for row,idx in sheet_rows(sheet):
        y=num(row[idx["YEAR"]]); q=num(row[idx["QUARTER"]])
        if y is None or q is None: continue
        k=(int(y),int(q))
        if k!=cur:
            if cur is not None: flush(cur)
            cur=k; buf=[]
        v1=num(row[idx[c1]]); v2=num(row[idx[c2]])
        if mode=="growth":
            if v1 not in (None,0) and v2 is not None:
                buf.append(((v2/v1)**4-1)*100 if v1>0 else None)
                if buf[-1] is None: buf.pop()
        else:
            if v2 is not None: buf.append(v2)
    if cur is not None: flush(cur)
    return out

def recess_prob():
    """RECESS2 mean recession probability (Anxious-Index precursor) per quarter."""
    out={}; cur=None; buf=[]
    for row,idx in sheet_rows("RECESS"):
        y=num(row[idx["YEAR"]]); q=num(row[idx["QUARTER"]]); v=num(row[idx["RECESS2"]])
        if y is None or q is None: continue
        k=(int(y),int(q))
        if k!=cur:
            if cur is not None and buf: out[cur]=sum(buf)/len(buf)
            cur=k; buf=[]
        if v is not None: buf.append(v)
    if cur is not None and buf: out[cur]=sum(buf)/len(buf)
    return out

specs={"RGDP_growth_disagreement":("RGDP","growth"),
       "EMP_growth_disagreement":("EMP","growth"),
       "UNEMP_level_disagreement":("UNEMP","level")}
series={n:disagreement_series(s,m) for n,(s,m) in specs.items()}
rp=recess_prob()

# write timelines
with open(os.path.join(BASE,"disagreement_timeline.csv"),"w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["year","quarter","recession_qtr","recess_prob_RECESS2",
        "RGDP_growth_disp_iqr","EMP_growth_disp_iqr","UNEMP_level_disp_iqr"])
    allk=sorted(set(rp)|set().union(*[set(s) for s in series.values()]))
    for (y,q) in allk:
        k=qkey(y,q)
        row=[y,q,1 if k in REC else 0, f"{rp.get((y,q),''):.3f}" if (y,q) in rp else ""]
        for n in ["RGDP_growth_disagreement","EMP_growth_disagreement","UNEMP_level_disagreement"]:
            v=series[n].get((y,q)); row.append(f"{v[0]:.4f}" if v else "")
        w.writerow(row)

# per-episode vs expansion
def episode_stats(ser, valfn):
    exp=[]; ep={}
    for (y,q),v in ser.items():
        val=valfn(v)
        if val is None: continue
        k=qkey(y,q)
        if k in REC:
            # find episode label = nearest start
            lab=None
            for sk,nm in sorted(EP_NAMES.items()):
                if sk<=k: lab=nm
            ep.setdefault(lab,[]).append(val)
        else:
            exp.append(val)
    em=sum(exp)/len(exp) if exp else float("nan")
    rows=[("EXPANSION_mean",f"{em:.4f}",len(exp))]
    for nm,vs in sorted(ep.items()):
        m=sum(vs)/len(vs); rows.append((nm,f"{m:.4f} (x{m/em:.2f})" if em else f"{m:.4f}",len(vs)))
    return rows,em

summary={}
summary["recess_prob_RECESS2"],_=episode_stats(rp, lambda v:v)
for n in series:
    summary[n],_=episode_stats(series[n], lambda v:v[0])
with open(os.path.join(BASE,"episode_dispersion_summary.json"),"w") as fh:
    json.dump(summary,fh,indent=1)

print("=== per-episode (mean; x = ratio to expansion mean) ===")
for sig,rows in summary.items():
    print(f"\n[{sig}]")
    for nm,val,n in rows: print(f"  {nm:16s} {val:>18s}  n={n}")
