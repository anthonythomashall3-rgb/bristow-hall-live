#!/usr/bin/env python3
"""CH-R47 — never-revised daily edge simulation (read-only, research/ only, §20-class).
Build RESEARCH-ONLY stress-oriented daily composites (equal-weight + ERC) from the
never-revised daily block; measure per-episode lead/lag, noise, false signals.
NO adoption. Standardization is expanding-window causal (min 504 obs). ERC weights are
full-sample (hindsight) — flagged as upper-bound. Writes research/ only."""
import sys,re,json,math
from pathlib import Path
from collections import defaultdict
from datetime import date,timedelta
import numpy as np
sys.path.insert(0,"live_data")
from rmv2_live.config import load_config, load_env_file
from rmv2_live.store import LiveStore

PR=Path(".").resolve()
cfgp=PR/"live_data/config/sources.v1.json"
load_env_file(cfgp.parent/"local.env"); cfg=load_config(cfgp)
st=LiveStore(PR,cfg); st.initialize()
heads=st.all_source_heads()

def pdate(s):
    m=re.match(r"^(\d{4})-(\d{2})-(\d{2})$",str(s).strip())
    return date(int(m.group(1)),int(m.group(2)),int(m.group(3))) if m else None

# series_id -> chosen source (prefer non-offline live head, else any)
NEED={'T10Y2Y':'fred_t10y2y_api_current','T10Y3M':'fred_t10y3m_api_current',
      'DCPF3M':'fred_dcpf3m_api_current_offline','DFF':'fred_dff_api_current',
      'DCOILWTICO':'fred_dcoilwtico_api_current','DTWEXBGS':'fred_dtwexbgs_api_current'}
raw={}
for si,src in NEED.items():
    h=heads[src]; norm=st.read_normalized(h["normalized_sha256"])
    d={}
    for r in norm.get("records",[]):
        if r.get("information_set_mode")!="current_revised": continue
        if r.get("series_id")!=si: continue
        dt=pdate(r.get("observation_period"))
        try: v=float(r.get("value"))
        except: continue
        if dt is not None: d[dt]=v
    raw[si]=d
    print("loaded",si,len(d),min(d) if d else "-",max(d) if d else "-")

# master business-day calendar: union of all dates, sorted
alldates=sorted(set().union(*[set(d.keys()) for d in raw.values()]))
di={dt:i for i,dt in enumerate(alldates)}
N=len(alldates)

def ffill(series):
    """align to alldates, forward-fill last value (cap 7d gap)."""
    out=np.full(N,np.nan); last=None; lastdt=None
    for i,dt in enumerate(alldates):
        if dt in series: last=series[dt]; lastdt=dt
        if last is not None and lastdt is not None and (dt-lastdt).days<=7:
            out[i]=last
    return out

lvl={si:ffill(d) for si,d in raw.items()}

def mom(arr,win):
    """log-change over ~win business days."""
    out=np.full(N,np.nan)
    for i in range(win,N):
        a,b=arr[i-win],arr[i]
        if a and b and a>0 and b>0: out[i]=math.log(b/a)
    return out

def chg(arr,win):
    out=np.full(N,np.nan)
    for i in range(win,N):
        if not np.isnan(arr[i-win]) and not np.isnan(arr[i]): out[i]=arr[i]-arr[i-win]
    return out

# stress-oriented members (higher = more recession stress)
mem={}
mem['TERM2']  = -lvl['T10Y2Y']                       # inversion -> +stress ; 1976+
mem['TERM3M'] = -lvl['T10Y3M']                       # 1982+
mem['CPFF']   = lvl['DCPF3M'] - lvl['DFF']           # money-mkt spread ; 1997+
mem['OILMOM'] = mom(lvl['DCOILWTICO'],250)           # oil shock ; 1987+
mem['DOLMOM'] = chg(lvl['DTWEXBGS'],60)              # broad-$ surge ; 2006+

MEMS=list(mem.keys())

# expanding causal z-score, min 504 obs
def expz(arr,minobs=504):
    out=np.full(N,np.nan); s=0.0; s2=0.0; c=0
    for i in range(N):
        x=arr[i]
        if not np.isnan(x):
            c+=1; s+=x; s2+=x*x
            if c>=minobs:
                mu=s/c; var=max(s2/c-mu*mu,1e-9); out[i]=(x-mu)/math.sqrt(var)
    return out
z={m:expz(mem[m]) for m in MEMS}
Z=np.vstack([z[m] for m in MEMS])   # (M,N)

# equal-weight composite = mean of available member-z
def compose(weights=None):
    out=np.full(N,np.nan)
    for i in range(N):
        col=Z[:,i]; ok=~np.isnan(col)
        if ok.sum()==0: continue
        if weights is None:
            out[i]=col[ok].mean()
        else:
            w=np.array(weights)[ok]; w=w/w.sum(); out[i]=float((col[ok]*w).sum())
    return out
EW=compose()

# ERC weights (full-sample hindsight; flagged). Use member-z overlap covariance.
def erc_weights():
    M=len(MEMS)
    # common-overlap matrix (drop rows w/ any nan)
    ok=~np.isnan(Z).any(axis=0)
    X=Z[:,ok]
    if X.shape[1]<252: return [1.0/M]*M
    C=np.cov(X)
    w=np.ones(M)/M
    for _ in range(500):
        mrc=C@w                      # marginal risk
        rc=w*mrc                     # risk contribution
        tgt=(w*mrc).sum()/M
        grad=rc-tgt
        w=w-0.01*grad/ (np.abs(mrc)+1e-9)
        w=np.clip(w,1e-4,None); w=w/w.sum()
    return list(w)
ERCw=erc_weights()
ERC=compose(ERCw)
print("ERC weights:",{m:round(w,3) for m,w in zip(MEMS,ERCw)})

# ---- episodes & NBER windows ----
ONSET={'2001':date(2001,3,1),'2008':date(2007,12,1),'2020':date(2020,2,1)}
RECWIN={'2001':(date(2001,3,1),date(2001,11,30)),
        '2008':(date(2007,12,1),date(2009,6,30)),
        '2020':(date(2020,2,1),date(2020,4,30))}
# 2022: no recession (false-positive stress test window)
def in_any_rec(dt):
    for a,b in RECWIN.values():
        if a<=dt<=b: return True
    return False

# monthly-resampled composite (month-end last value) to test daily lead
def monthly_resample(comp):
    by=defaultdict(list)
    for i,dt in enumerate(alldates):
        if not np.isnan(comp[i]): by[(dt.year,dt.month)].append((dt,comp[i]))
    m={}
    for k,vs in by.items():
        vs.sort(); m[k]=vs[-1][1]     # month-end value
    return m

def first_cross(comp,thr,lo,hi):
    """first date comp>=thr within [lo,hi]."""
    for i,dt in enumerate(alldates):
        if lo<=dt<=hi and not np.isnan(comp[i]) and comp[i]>=thr: return dt
    return None

def metrics_for(comp,label):
    rows=[]
    for thr in (1.0,1.5):
        for ep,onset in ONSET.items():
            lo=onset-timedelta(days=730)
            xd=first_cross(comp,thr,lo,onset)
            lead=(onset-xd).days if xd else None
            rows.append((label,thr,ep,xd.isoformat() if xd else "NONE",lead))
    # noise: daily std of first-diff over full sample (defined region)
    d=np.diff(comp[~np.isnan(comp)]); noise=float(np.nanstd(d))
    # lag-1 autocorr of level
    v=comp[~np.isnan(comp)]; ac1=float(np.corrcoef(v[:-1],v[1:])[0,1]) if len(v)>2 else float('nan')
    # false signals: threshold-cross onsets (rising edge) in expansion not followed by recession within 18mo
    def false_count(thr):
        fp=0; prev=False; edges=[]
        for i,dt in enumerate(alldates):
            if np.isnan(comp[i]): continue
            cur=comp[i]>=thr
            if cur and not prev: edges.append(dt)  # rising edge
            prev=cur
        for e in edges:
            if in_any_rec(e): continue
            # recession within next 18 months?
            precedes=any(0<=(a-e).days<=548 for a,b in RECWIN.values())
            if not precedes: fp+=1
        return fp,len(edges)
    fp10=false_count(1.0); fp15=false_count(1.5)
    return rows,noise,ac1,fp10,fp15

# ---- write composite CSV ----
import csv
with open("research/daily_edge_sim_v1.csv","w",newline="") as f:
    w=csv.writer(f)
    w.writerow(["date"]+[f"z_{m}" for m in MEMS]+["ew_composite","erc_composite","in_nber_recession"])
    for i,dt in enumerate(alldates):
        w.writerow([dt.isoformat()]+
                   [("" if np.isnan(z[m][i]) else round(float(z[m][i]),4)) for m in MEMS]+
                   [("" if np.isnan(EW[i]) else round(float(EW[i]),4)),
                    ("" if np.isnan(ERC[i]) else round(float(ERC[i]),4)),
                    1 if in_any_rec(dt) else 0])

# ---- metrics file ----
allrows=[]; summary={}
for comp,lab in ((EW,"EW"),(ERC,"ERC")):
    rows,noise,ac1,fp10,fp15=metrics_for(comp,lab)
    allrows+=rows
    summary[lab]={"noise_dstd":round(noise,4),"ac1":round(ac1,4),
                  "false_pos@1.0":fp10[0],"edges@1.0":fp10[1],
                  "false_pos@1.5":fp15[0],"edges@1.5":fp15[1]}
with open("research/ch_r47_metrics.txt","w") as f:
    f.write("=== per-episode lead (days before NBER onset; threshold-cross in [onset-24mo, onset]) ===\n")
    f.write(f"{'comp':5}{'thr':>5} {'episode':8} {'cross_date':12} {'lead_days':>10}\n")
    for r in allrows:
        f.write(f"{r[0]:5}{r[1]:>5} {r[2]:8} {r[3]:12} {str(r[4]):>10}\n")
    f.write("\n=== noise / autocorr / false-signal counts (full sample) ===\n")
    f.write(json.dumps(summary,indent=2)+"\n")
    f.write("\nERC weights (full-sample, HINDSIGHT upper-bound):\n")
    f.write(json.dumps({m:round(w,4) for m,w in zip(MEMS,ERCw)},indent=2)+"\n")
    # member coverage starts
    f.write("\nmember effective z-start (post-warmup):\n")
    for m in MEMS:
        idx=np.where(~np.isnan(z[m]))[0]
        f.write(f"  {m}: {alldates[idx[0]].isoformat() if len(idx) else 'NONE'}\n")

# ---- 2022 false-positive probe: max composite Jan2022-Dec2022 ----
def episode_stat(comp,lo,hi):
    seg=[comp[i] for i,dt in enumerate(alldates) if lo<=dt<=hi and not np.isnan(comp[i])]
    return (round(max(seg),3),round(min(seg),3),round(float(np.mean(seg)),3)) if seg else None
with open("research/ch_r47_metrics.txt","a") as f:
    f.write("\n=== 2022 window (no NBER recession) composite max/min/mean ===\n")
    for comp,lab in ((EW,"EW"),(ERC,"ERC")):
        s=episode_stat(comp,date(2022,1,1),date(2022,12,31))
        f.write(f"  {lab} 2022 (max,min,mean)= {s}\n")
    f.write("\n=== per-episode composite max/min/mean (in-window) ===\n")
    for ep,(a,b) in RECWIN.items():
        for comp,lab in ((EW,"EW"),(ERC,"ERC")):
            f.write(f"  {lab} {ep} {episode_stat(comp,a,b)}\n")
print("DONE; rows in csv:",N)
