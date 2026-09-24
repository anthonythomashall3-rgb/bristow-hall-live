import sys,re,json,time
sys.path.insert(0,"live_data")
from pathlib import Path
from collections import defaultdict
from datetime import date
import statistics as sx
from rmv2_live.config import load_config, load_env_file
from rmv2_live.store import LiveStore
PR=Path(".").resolve()
cfgp=PR/"live_data/config/sources.v1.json"
load_env_file(cfgp.parent/"local.env"); cfg=load_config(cfgp)
st=LiveStore(PR,cfg); st.initialize()
heads=st.all_source_heads()
uni=json.load(open("research/chr43_signed_universe.json"))
uni=[u for u in uni if u["series_id"]!="PCEPILFE"]   # stray price index
want={u["series_id"]:u for u in uni}
srcset={u["src"] for u in uni}
def pdate(s):
    s=str(s).strip()
    m=re.match(r"^(\d{4})-Q([1-4])$",s)
    if m: return date(int(m.group(1)),(int(m.group(2))-1)*3+1,1)
    for pat,f in [(r"^(\d{4})-(\d{2})-(\d{2})$",lambda g:date(int(g[0]),int(g[1]),int(g[2]))),
                  (r"^(\d{4})-(\d{2})$",lambda g:date(int(g[0]),int(g[1]),1)),
                  (r"^(\d{4})$",lambda g:date(int(g[0]),1,1))]:
        m=re.match(pat,s)
        if m: return f(m.groups())
    return None
def ym(d): return d.year*12+(d.month-1)
# read only needed sources; per series monthly level (last obs in month)
lvl=defaultdict(dict)  # sid -> ym -> value
for src in srcset:
    try: norm=st.read_normalized(heads[src]["normalized_sha256"])
    except: continue
    for r in norm.get("records",[]):
        if r.get("information_set_mode")!="current_revised": continue
        si=r.get("series_id")
        if si not in want or want[si]["src"]!=src: continue
        try: v=float(r.get("value"))
        except: continue
        d=pdate(r.get("observation_period"))
        if d is None: continue
        lvl[si][ym(d)]=v
# global month range
allm=[m for s in lvl.values() for m in s]
m0,m1=min(allm),max(allm)
def mlabel(m): return f"{m//12:04d}-{m%12+1:02d}"
# diffusion at horizon h: economic change = sign*(level[t]-level[t-h]); deteriorating if <0
def diffusion(h):
    out={}
    for m in range(m0+h,m1+1):
        det=tot=0
        for si,ser in lvl.items():
            if m in ser and (m-h) in ser:
                c=ser[m]-ser[m-h]; g=want[si]["sign"]
                if g*c<0: det+=1
                tot+=1
        if tot>0: out[m]=(det/tot,tot)
    return out
D={h:diffusion(h) for h in (1,3,6)}
# NBER recession months (peak..trough inclusive), external comparator only
NBER=[("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),("1960-04","1961-02"),
 ("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
 ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
def mm(s): y,mo=s.split("-"); return int(y)*12+int(mo)-1
recset=set()
for a,b in NBER:
    for m in range(mm(a),mm(b)+1): recset.add(m)
# write CSV
import csv
w=csv.writer(open("research/diffusion_evidence_v1.csv","w",newline=""))
w.writerow(["month","n_reporting_6m","diff_1m","diff_3m","diff_6m","nber_recession"])
for m in range(m0,m1+1):
    r6=D[6].get(m); 
    row=[mlabel(m),(r6[1] if r6 else ""),
         round(D[1][m][0],4) if m in D[1] else "",
         round(D[3][m][0],4) if m in D[3] else "",
         round(r6[0],4) if r6 else "",
         1 if m in recset else 0]
    w.writerow(row)
# ---- threshold analysis on 6m diffusion, full sample where n>=10 ----
series6=[(m,v) for m,(v,t) in D[6].items() if t>=10]
vals=[v for _,v in series6]
rec_v=[v for m,v in series6 if m in recset]
exp_v=[v for m,v in series6 if m not in recset]
def q(xs,p): xs=sorted(xs); return round(xs[min(len(xs)-1,int(p*(len(xs)-1)))],3)
def roc(thr):
    tp=sum(1 for v in rec_v if v>=thr); fn=len(rec_v)-tp
    fp=sum(1 for v in exp_v if v>=thr); tn=len(exp_v)-fp
    tpr=tp/max(len(rec_v),1); fpr=fp/max(len(exp_v),1)
    return dict(thr=thr,tpr=round(tpr,3),fpr=round(fpr,3),youden=round(tpr-fpr,3))
cand=[roc(t) for t in [0.5,0.55,0.6,0.65,0.7,0.75,0.8]]
best=max(cand,key=lambda c:c["youden"])
# per-episode behavior (6m)
def episode_stats(a,b,pad=6):
    lo,hi=mm(a)-pad,mm(b)+pad
    seg=[(m,D[6][m][0]) for m in range(lo,hi+1) if m in D[6] and D[6][m][1]>=8]
    if not seg: return None
    peak=mm(a)
    mx=max(seg,key=lambda x:x[1])
    # first month diff crosses best threshold within window
    cross=next((mlabel(m) for m,v in seg if v>=best["thr"]),None)
    lead=(mm(cross.split('-')[0]+'-'+cross.split('-')[1]) if False else None)
    return dict(peak=a,trough=b,max_diff=round(mx[1],3),max_month=mlabel(mx[0]),
                first_cross=cross,diff_at_peak=round(next((v for m,v in seg if m==peak),float('nan')),3) if any(m==peak for m,_ in seg) else None,
                n_members_at_peak=(D[6][peak][1] if peak in D[6] else None))
eps=[episode_stats(a,b) for a,b in NBER]
# non-episodes (slowdowns w/o recession)
NON=[("1966 slowdown","1966-01","1967-06"),("1995 soft landing","1995-01","1996-06"),
     ("2015-16 industrial","2015-06","2016-12")]
def window_stats(a,b):
    seg=[(m,D[6][m][0]) for m in range(mm(a),mm(b)+1) if m in D[6] and D[6][m][1]>=8]
    if not seg: return None
    mx=max(seg,key=lambda x:x[1])
    crossed=any(v>=best["thr"] for _,v in seg)
    return dict(max_diff=round(mx[1],3),max_month=mlabel(mx[0]),crossed_best_thr=crossed,n=len(seg))
non=[dict(name=n,start=a,end=b,**(window_stats(a,b) or {})) for n,a,b in NON]
summary=dict(
 schema_version="rmv2.ch43_diffusion.v1", batch_id="CH-R43_DIFFUSION_PROTOTYPE",
 writes_store=False, network=False, adoption="NONE",
 universe_note="de-polluted signable MONTHLY current_revised universe: excluded state/regional "
   "disaggregations, forecast/expectation (FUTURE) series, earnings, prices/rates/money (ambiguous "
   "direction). Regional-Fed survey sub-indices (Philly 10 / Dallas 8 / NYFed 6) retained but are "
   "within-district correlated -> flagged, not de-twinned (that is CH-R42's job).",
 n_members=len(want), sign_convention="deteriorating := economic_direction*(level[t]-level[t-h])<0; "
   "sign=+1 higher-is-better(down_bad), -1 higher-is-worse(up_bad).",
 month_range=[mlabel(m0),mlabel(m1)],
 member_ramp={y:sum(1 for u in want.values() if int(u['first'][:4])<=y) for y in [1948,1960,1970,1980,1990,2000,2010,2020]},
 nber_note="NBER dates are EXTERNAL comparator only (per CLAUDE.md), not a construction input.",
 diff6_full_dist=dict(n=len(vals),min=round(min(vals),3),p25=q(vals,.25),median=round(sx.median(vals),3),
   p75=q(vals,.75),p90=q(vals,.90),max=round(max(vals),3)),
 diff6_recession_months=dict(n=len(rec_v),median=round(sx.median(rec_v),3),p25=q(rec_v,.25),p75=q(rec_v,.75)),
 diff6_expansion_months=dict(n=len(exp_v),median=round(sx.median(exp_v),3),p75=q(exp_v,.75),p90=q(exp_v,.90)),
 threshold_candidates=cand, best_threshold_youden=best,
 per_episode=eps, non_episodes=non,
)
json.dump(summary,open("research/CH-R43_DIFFUSION.v1.json","w"),indent=1,default=str)
print("members",len(want),"months",mlabel(m0),"->",mlabel(m1))
print("diff6 median rec/exp:",summary["diff6_recession_months"]["median"],summary["diff6_expansion_months"]["median"])
print("best thr",best)
print("episodes:")
for e in eps: 
    if e: print("  ",e["peak"],"max",e["max_diff"],"@",e["max_month"],"cross",e["first_cross"],"n@peak",e["n_members_at_peak"])
print("non-episodes:")
for n in non: print("  ",n["name"],"max",n.get("max_diff"),"crossed",n.get("crossed_best_thr"))
