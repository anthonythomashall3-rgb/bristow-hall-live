"""Rule 4: independent rulings on the US turning points, from published methods that are not the committee.
  CP  Chauvet-Piger smoothed recession probabilities (RECPROUSM156N, Piger's series): a recession month is
      p >= 50; the peak is the last month before the run, the trough the last month of the run (their own convention:
      a month is classified recession when the smoothed probability exceeds 50 percent).
  HAM Hamilton's GDP-based recession indicator (JHDUSRGDPBR, quarterly): recession quarter = 1; peak = last quarter
      before the run, trough = last quarter of the run; quarters mapped to their middle month.
  PHI Bry-Boschan on the Philadelphia Fed coincident index (USPHCI, 1979-), the tool's own bry_boschan().
  BB  Bry-Boschan on the tool's US panel (bench channels), the median of channel dates.
The rule's date is then scored against the committee AND against the median of the independent rulings."""
import sys, pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.argv=['x']
import bristow_rule_v3 as B, bench
NBER=[('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04')]
def fred(s):
    d=pd.read_csv(f'{s}.csv'); d.columns=['d','v']; d['d']=pd.to_datetime(d.d); d['v']=pd.to_numeric(d.v,errors='coerce'); return d.dropna().set_index('d')['v']
def runs(flag):
    """peak = last month before each run of 1s, trough = last month of the run"""
    out=[]; on=False; start=None
    idx=flag.index; v=flag.values
    for i in range(len(v)):
        if v[i] and not on: on=True; start=i
        elif not v[i] and on:
            on=False; out.append((idx[start-1] if start>0 else idx[start], idx[i-1]))
    if on: out.append((idx[start-1], idx[-1]))
    return out
cp=fred('RECPROUSM156N'); cp_runs=runs(cp>=50.0)
ham=fred('JHDUSRGDPBR'); ham_runs=[(pd.Timestamp(p.year,p.month+1,1),pd.Timestamp(t.year,t.month+1,1)) for p,t in runs(ham>=1)]  # quarter start -> middle month
phi=fred('USPHCI')
tp=B.bry_boschan(phi.astype(float),smooth=3)   # returns list? check
print('bry_boschan output type:', type(tp))

def nearest(pairs, ref, tol=9):
    """closest (peak,trough) pair to the NBER pair, by peak distance; None if none within tol months"""
    best=None
    for p,t in pairs:
        e=B._md(p,ref[0])
        if abs(e)<=tol and (best is None or abs(e)<abs(best[0])): best=(e,B._md(t,ref[1]),p,t)
    return best
phi_tp=B.bry_boschan(phi.astype(float),smooth=3)
phi_pairs=[]
for i in range(len(phi_tp)-1):
    if phi_tp[i][1]=='P' and phi_tp[i+1][1]=='T': phi_pairs.append((phi_tp[i][0],phi_tp[i+1][0]))
# BB on the tool's US panel (each channel; median of channel dates, as the memo's §9 benchmark does)
chs=[(nm,s) for nm,s in bench.channels('United States')]
def bb_panel(pk,tr,smooth=3):
    pkm=B.pd.Timestamp(pk+'-01'); trm=B.pd.Timestamp(tr+'-01')
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    ps=[];ts=[]
    for nm,s in chs:
        if s.index.min()>w0 or s.index.max()<w1: continue
        tp=B.bry_boschan(s[w0-pd.DateOffset(months=24):w1+pd.DateOffset(months=24)].astype(float),smooth=smooth)
        pp=[d for d,k in tp if k=='P' and w0<=d<=w1]; tt=[d for d,k in tp if k=='T' and w0<=d<=w1]
        if pp: ps.append(min(pp,key=lambda d:abs(B._md(d,pkm))))
        if tt: ts.append(min(tt,key=lambda d:abs(B._md(d,trm))))
    return (B._median(ps) if ps else None, B._median(ts) if ts else None)
# the rule itself (shipped, and no smoothing)
def rule(pk,tr,smooth):
    pkm=pd.Timestamp(pk+'-01'); trm=pd.Timestamp(tr+'-01')
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm and nm not in ('exports','imports','car registrations','construction production')]
    vol=bench.quantity('United States',use) or use
    r=B.date_turning_points(use,w0,w1,volume_channels=vol,concept='level',lam=500000.0,band_trough=0.12,band_peak=0.01,peak_cap=18,smooth=smooth,lookback=12)
    return r['peak'], r['trough']
print(f"{'NBER':14s} {'CP':>9s} {'Hamilton':>9s} {'PhilaFed BB':>12s} {'panel BB':>9s} | {'indep. median':>14s} | {'rule s3':>9s} {'rule s1':>9s} | rule vs NBER (s3,s1) | rule vs median (s3,s1)")
rows=[]
for pk,tr in NBER:
    ref=(pd.Timestamp(pk+'-01'),pd.Timestamp(tr+'-01'))
    c=nearest(cp_runs,ref); h=nearest(ham_runs,ref); ph=nearest(phi_pairs,ref); bbp,bbt=bb_panel(pk,tr)
    bb=(B._md(bbp,ref[0]) if bbp is not None else None, B._md(bbt,ref[1]) if bbt is not None else None)
    r3=rule(pk,tr,3); r1=rule(pk,tr,1)
    e3=(B._md(r3[0],ref[0]),B._md(r3[1],ref[1])); e1=(B._md(r1[0],ref[0]),B._md(r1[1],ref[1]))
    pe=[x[0] for x in (c,h,ph) if x]+([bb[0]] if bb[0] is not None else []); te=[x[1] for x in (c,h,ph) if x]+([bb[1]] if bb[1] is not None else [])
    medp=float(np.median(pe)) if pe else None; medt=float(np.median(te)) if te else None
    f=lambda x: '   -' if x is None else f'{x[0]:+d}/{x[1]:+d}'
    print(f"{pk}/{tr[2:]}  {f(c):>9s} {f(h):>9s} {f(ph):>12s} {f(bb):>9s} | {'-' if medp is None else f'{medp:+.1f}/{medt:+.1f}':>14s} | {e3[0]:+d}/{e3[1]:+d}   {e1[0]:+d}/{e1[1]:+d}   | "
          f"{e3[0]:+d}/{e3[1]:+d}, {e1[0]:+d}/{e1[1]:+d} | " + ('-' if medp is None else f"{e3[0]-medp:+.1f}/{e3[1]-medt:+.1f}, {e1[0]-medp:+.1f}/{e1[1]-medt:+.1f}"))
    rows.append(dict(pk=pk,tr=tr,cp=c,ham=h,phi=ph,bb=bb,medp=medp,medt=medt,e3=e3,e1=e1))
import json; json.dump([{k:(None if v is None else (list(v) if isinstance(v,tuple) else v)) for k,v in r.items()} for r in rows],open('rulings_us.json','w'),default=str)
