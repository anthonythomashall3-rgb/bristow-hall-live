#!/usr/bin/env python3
"""CH-R21 Part 2 — per-member persistence vs site window (read-only).
Imports the live site build (method_source/index_v1.py, NOWCAST_DISABLE=1) exactly as
CH1 did, and measures the autocorrelation of each member's TRANSFORMED current_revised
series (the transform the site feeds), reporting 1/e decay length, half-life, and
first-zero crossing in days, plus window/persistence ratio. No writes anywhere but
research/. Transform-window params reused from CH1 §6B (transform_window_days)."""
import os,sys,json,math,statistics as st

REPO="/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
WORK=REPO+"/research/channel_structure_ch1/scratch/work"     # holds raw/ -> current_revised
os.environ["NOWCAST_DISABLE"]="1"
os.environ["INDEX_OUT"]=REPO+"/research/ch_r21_index_out.scratch.json"
os.chdir(WORK); sys.path.insert(0,REPO+"/method_source")
import index_v1 as m

CHAN=m.CHANNELS; MEMBERS=[]
for c in CHAN: MEMBERS+=CHAN[c][1]
assert len(MEMBERS)==17,MEMBERS
T=m.T   # name -> {date: transformed_value}

# transform look-back windows (days) the site uses, from CH1 §6B; None = level/composite (no window)
WIN={"ICSA":365,"IURSA":370,"SAHM":None,"UNRATEv":120,"INDPRO":365,"CMRMT":365,"TCU":365,
     "PHILLY":None,"NASDAQ":370,"BAAAAA":None,"BAA10Y":None,"VIX":None,"NFCI":None,
     "PERMIT":365,"HOUST":365,"UMCSENT":370,"W875":365}

def acf(x,maxlag):
    n=len(x); mu=sum(x)/n
    d=[v-mu for v in x]
    c0=sum(v*v for v in d)/n
    out=[]
    for k in range(1,maxlag+1):
        ck=sum(d[i]*d[i+k] for i in range(n-k))/n
        out.append(ck/c0 if c0>0 else 0.0)
    return out

rows=[]; log=open(REPO+"/research/CH-R21_part2.log","w")
INV_E=1.0/math.e
for name in MEMBERS:
    ks=sorted(T[name]); vals=[float(T[name][k]) for k in ks]
    # obs spacing = median day-gap between consecutive transformed obs
    gaps=[(ks[i+1]-ks[i]).days for i in range(len(ks)-1) if (ks[i+1]-ks[i]).days>0]
    spacing=st.median(gaps) if gaps else None
    n=len(vals)
    maxlag=min(n-2, 800)
    r=acf(vals,maxlag)
    def cross(thr, strict_below=True):
        for k,rk in enumerate(r,1):
            if (rk<thr) if strict_below else (rk<=thr):
                return k
        return None
    lag_1e=cross(INV_E); lag_half=cross(0.5); lag_zero=cross(0.0,strict_below=False)
    def days(l): return None if (l is None or spacing is None) else l*spacing
    p1e=days(lag_1e); phalf=days(lag_half); pzero=days(lag_zero)
    w=WIN[name]
    ratio=(w/p1e) if (w and p1e) else None
    rows.append(dict(member=name,channel=[c for c in CHAN if name in CHAN[c][1]][0],
        transform_window_days=w,obs_spacing_days=spacing,n_transformed_obs=n,
        acf_1e_lag_obs=lag_1e,persistence_1e_days=p1e,
        acf_half_lag_obs=lag_half,half_life_days=phalf,
        acf_firstzero_lag_obs=lag_zero,first_zero_days=pzero,
        window_over_persistence=(round(ratio,4) if ratio else None)))
    log.write(f"{name:9s} win={w} spacing={spacing} n={n} 1e={p1e} half={phalf} zero={pzero} ratio={ratio}\n")
    print(f"done {name} 1e_days={p1e} half={phalf} zero={pzero} ratio={ratio}",flush=True)
log.close()
# merge CH1 §6B raw-series persistence for side-by-side (CH1 measured RAW underlying;
# this probe measures the TRANSFORMED signal the site feeds). Both feed S6.
ch1=json.load(open(REPO+"/research/channel_structure_ch1/CH1_CHANNEL_STRUCTURE_PROBE.v1.json"))
rawmap={e['m']:e['persistence_days'] for e in ch1['s6B_windows']['persistence_vs_window']}
for rr in rows:
    rawp=rawmap.get(rr['member'])
    rr['raw_persistence_1e_days_ch1']=rawp
    w=rr['transform_window_days']
    rr['window_over_raw_persistence_ch1']=(round(w/rawp,4) if (w and rawp) else None)
import csv
cols=['member','channel','transform_window_days','obs_spacing_days','n_transformed_obs',
      'acf_1e_lag_obs','persistence_1e_days','acf_half_lag_obs','half_life_days',
      'acf_firstzero_lag_obs','first_zero_days','window_over_persistence',
      'raw_persistence_1e_days_ch1','window_over_raw_persistence_ch1']
with open(REPO+"/research/member_persistence_v1.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
    for rr in rows: w.writerow({k:rr.get(k) for k in cols})
print("WROTE research/member_persistence_v1.csv rows=",len(rows))
