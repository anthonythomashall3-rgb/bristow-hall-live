"""Aggregate-then-date at the trough (and peak), priced against the shipped median-of-dates.

Why: Stock and Watson (2010, Tables 2-3) date 7 of 8 American troughs 1960-2009 to the month by
running Bry-Boschan on ONE weighted coincident index (ISD inverse-standard-deviation weights or a
DFM), where the shipped rule, dating every channel and taking the median, gets 5 of those 8.
Memo section 7 rejected composite-then-date as the general architecture (60/83 peaks against 74,
72/83 troughs against 73, at three months, before routing and before the refinement clause).
The question here is the exact month, at the trough, on the level chronologies, with the shipped
clause and refinement applied to the composite exactly as to a channel.

Variants, each on the same channel set the shipped rule uses for the episode:
  shipped      median of the channel dates (the tool, refinement clause in force)
  comp-eq      the tool's equal-weight chain-linked composite, dated with channel_trough / channel_peak
  comp-sd      bench's standardized composite (each channel's log change over its own sd - Stock-Watson's
               inverse-sd weighting), dated the same way
  comp-eq BB   Bry-Boschan (the tool's, smooth 3) on comp-eq, nearest turn inside the window
  US only: comp-ISD  the four NBER series at Stock-Watson's ISD weights (IP .14, payrolls .49,
               manufacturing-and-trade sales .11, real income less transfers .26), dated the same way
Scored exact / within one / within three against the committee; nothing here is adopted on its score.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.argv=['x']
import numpy as np, pandas as pd
import bristow_rule_v3 as B
import bench
from bench import PANELS, channels, ep3, ts, quantity, dating_series, md
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
LEVEL=['United States','United States (interwar)','Brazil']
def weighted_composite(chs, w):
    """chain-linked composite of log changes with fixed weights (renormalised over channels present)"""
    D=pd.DataFrame({nm:np.log(s.clip(lower=1e-9)).diff() for nm,s in chs})
    W=pd.Series({nm:w.get(nm,0.0) for nm,_ in chs})
    num=(D*W).sum(axis=1,skipna=True); den=D.notna().mul(W,axis=1).sum(axis=1)
    g=(num/den).where(den>0)
    first=g.first_valid_index(); g=g.loc[first:].fillna(0.0)
    return pd.Series(100*np.exp(g.cumsum()),index=g.index)
ISD={'industrial production (Federal Reserve)':0.14,'payroll employment':0.49,
     'real manufacturing and trade sales':0.11,'real income less transfers':0.26}
def bb_nearest(x,w0,w1,ref,kind):
    tp=B.bry_boschan(x[w0-pd.DateOffset(months=24):w1+pd.DateOffset(months=24)].astype(float),smooth=3)
    c=[d for d,k in tp if k==kind and w0<=d<=w1]
    return min(c,key=lambda d:abs(md(d,ref))) if c else None
def run(country):
    cfg=PANELS[country]; chs=[(nm,s) for nm,s in channels(country) if nm not in bench.SKIP]
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        if freq!='M': continue
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
        if not use: use=chs
        vol=quantity(country,use) or use
        r=B.date_turning_points(use,w0,w1,volume_channels=vol,concept='level',lam=500000.0,
                                band_trough=0.12,band_peak=0.01,peak_cap=18,smooth=3,lookback=12,
                                dating_series=dating_series(country,w0,trm))
        out={'ep':pk_off[:7],'n':len(vol),'shipped':(md(r['peak'],pkm) if r['peak'] is not None else None,
                                                    md(r['trough'],trm) if r['trough'] is not None else None)}
        comps={'comp-eq':B.composite_level(vol),'comp-sd':bench.composite_level(vol,1,True,1)}
        if country=='United States':
            four=[(nm,s) for nm,s in vol if nm in ISD]
            if len(four)==4: comps['comp-ISD']=weighted_composite(four,ISD)
        for k,ci in comps.items():
            ci=ci.dropna()
            t=B.channel_trough(ci,w0,w1)
            ends=t if t is not None else w1
            d=B.deviation(ci,12,3)[w0:ends].dropna(); cross=None
            for dt,v in d.items():
                if v>=2.0: cross=dt; break
            p0=w0 if cross is None else max(w0,cross-pd.DateOffset(months=18))
            p=B.channel_peak(ci,p0,ends)
            out[k]=(md(p,pkm) if p is not None else None, md(t,trm) if t is not None else None)
        ce=comps['comp-eq'].dropna()
        pb=bb_nearest(ce,w0,w1,pkm,'P'); tb=bb_nearest(ce,w0,w1,trm,'T')
        out['comp-eq BB']=(md(pb,pkm) if pb is not None else None, md(tb,trm) if tb is not None else None)
        rows.append(out)
    return rows
def stat(errs):
    e=np.array([x for x in errs if x is not None],dtype=float); n=len(errs)
    f=lambda k: int((np.abs(e)<=k).sum())
    return f'{f(0):2d}/{f(1):2d}/{f(3):2d} of {n:2d} mae {np.abs(e).mean() if len(e) else float("nan"):.2f}'
if __name__=='__main__':
    for c in LEVEL:
        rows=run(c)
        keys=[]
        for r in rows:
            for k in r:
                if k not in ('ep','n') and k not in keys: keys.append(k)
        print(f'\n== {c} (exact/within one/within three) ==')
        for k in keys:
            if any(k in r for r in rows):
                print(f'{k:12s} peaks {stat([r.get(k,(None,None))[0] for r in rows])}   troughs {stat([r.get(k,(None,None))[1] for r in rows])}')
        f=lambda x: '  -' if x is None else f'{x:+d}'
        print('   episode   n  '+'  '.join(f'{k:>12s}' for k in keys))
        for r in rows:
            print(f"   {r['ep']}  {r['n']:2d} "+'  '.join(f"{f(r.get(k,(None,None))[0]):>5s}/{f(r.get(k,(None,None))[1]):<5s}" for k in keys))
