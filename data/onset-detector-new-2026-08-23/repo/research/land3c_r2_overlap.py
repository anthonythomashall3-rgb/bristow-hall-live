import json,sys,os,csv
sys.path.insert(0,"live_data")
from rmv2_live.config import load_config
from rmv2_live.store import LiveStore
from pathlib import Path
root=Path(".").resolve()
cfg=load_config(root/"live_data/config/sources.v1.json")
store=LiveStore(root,cfg); store.initialize()

def store_series(sid):
    head=store.read_source_head(sid)
    if not head: return None,None
    norm=store.read_normalized(head["normalized_sha256"])
    recs=norm["records"] if isinstance(norm,dict) and "records" in norm else norm
    out={}
    for r in recs:
        out[r.get("observation_period")]=r.get("value")
    return out,head.get("normalized_sha256")

def fredmd_col(path,col):
    lines=open(path,encoding="utf-8").read().splitlines()
    hdr=lines[0].split(",")
    if col not in hdr: return {}
    ci=hdr.index(col)
    di=hdr.index("sasdate")
    out={}
    for ln in lines[2:]:  # skip transform row
        p=ln.split(",")
        if len(p)<=ci or not p[di].strip(): continue
        v=p[ci].strip()
        if v in("","."): continue
        # sasdate like 1/1/1959 or 1959-01-01
        d=p[di].strip()
        out[d]=v
    return out

def norm_date(d):
    # to YYYY-MM
    d=d.strip()
    if "/" in d:
        m,day,y=d.split("/"); return f"{int(y):04d}-{int(m):02d}"
    if "-" in d:
        parts=d.split("-"); return f"{int(parts[0]):04d}-{int(parts[1]):02d}"
    return d

for sid_store,fmcol in [("fred_w875rx1_api_current","W875RX1")]:
    sv,sha=store_series(sid_store)
    cur="data_archive/additional_vintages/fred_md_official/current/fred_md_2026-06.csv"
    fv=fredmd_col(cur,fmcol)
    print(f"== {fmcol}: store {sid_store} n={len(sv) if sv else 0} sha={sha[:12] if sha else None}; fredmd n={len(fv)}")
    if not sv: continue
    svn={norm_date(k):float(v) for k,v in sv.items()}
    fvn={norm_date(k):float(v) for k,v in fv.items()}
    common=sorted(set(svn)&set(fvn))
    print("   common_months",len(common), common[0] if common else None, common[-1] if common else None)
    if common:
        import statistics
        divs=[abs(svn[m]-fvn[m]) for m in common]
        rel=[abs(svn[m]-fvn[m])/abs(svn[m]) if svn[m] else 0 for m in common]
        xs=[svn[m] for m in common]; ys=[fvn[m] for m in common]
        mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
        cov=sum((x-mx)*(y-my) for x,y in zip(xs,ys))
        sx=sum((x-mx)**2 for x in xs)**.5; sy=sum((y-my)**2 for y in ys)**.5
        corr=cov/(sx*sy) if sx and sy else float('nan')
        print(f"   corr={corr:.10f} max_abs_div={max(divs):.6f} max_rel_div={max(rel):.2e} mean_abs_div={statistics.mean(divs):.6f}")
        # show the worst
        worst=max(common,key=lambda m:abs(svn[m]-fvn[m]))
        print(f"   worst_month={worst} store={svn[worst]} fredmd={fvn[worst]}")
