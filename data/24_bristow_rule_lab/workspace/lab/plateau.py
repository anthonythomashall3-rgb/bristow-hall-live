"""Where in the within-band plateau should the turning point sit?

Both clauses currently take the LAST month inside the band, which cannot be earlier
than the extremum and is therefore biased late.  The alternatives are the first
month inside the band and the middle of it.  Nothing else changes.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
import pandas as pd, numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True

def pick(on, where):
    if len(on)==0: return None
    if where=='last': return on.index[-1]
    if where=='first': return on.index[0]
    return on.index[len(on)//2]

def ch_trough2(level,w0,w1,band,n,L,where='last',abstain=None):
    _ab = bench.ABSTAIN if abstain is None else abstain
    d=dev(level,L,n)[w0:w1].dropna()
    if len(d)==0: return None
    d_peak=d.idxmax()
    m=ma(level,n)[w0:w1].dropna()
    if len(m)<4: return d_peak
    lo=float(m.min()); i=m.idxmin()
    if _ab and i==m.index[-1]: return None
    hi=float(m[:i].max()) if len(m[:i]) else float(m.max())
    amp=max(hi-lo,1e-9)
    on=m[m<=lo+band*amp]
    p=pick(on,where)
    return max(d_peak,p) if p is not None else d_peak

def ch_peak2(level,w0,w1,band,n,where='last',abstain=None):
    _ab = bench.ABSTAIN if abstain is None else abstain
    m=ma(level,n)[w0:w1].dropna()
    if len(m)<4: return None
    hi=float(m.max()); i=m.idxmax()
    if _ab and i==m.index[-1]: return None
    lo=float(m[i:].min()) if len(m[i:]) else float(m.min())
    amp=max(hi-lo,1e-9)
    on=m[m>=hi-band*amp]
    return pick(on,where)

def run(where_t,where_p,band_t=0.03,band_p=0.01,n=3,L=12,peak_cap=18,min_depth=5.0,lam=500000.):
    tot=[]
    for c in ALL:
        cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
        cpt=CONCEPT.get(c,'level')
        for _e in cfg['chrono']:
            pk_off,tr_off,freq=ep3(_e,cfg['freq'])
            pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
            w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
            g=qgdp(c)
            if g is not None and g.index.min()<=w0 and g.index.max()>=trm:
                tr=ch_trough2(g,w0,w1,band_t,1,4,where_t,abstain=False)
                pk=ch_peak2(g,w0,tr if tr is not None else w1,band_p,1,where_p,abstain=False)
                a,ep=hit(pk,pk_off,freq); b,et=hit(tr,tr_off,freq)
                tot.append(dict(country=c,pk=pk,tr=tr,ep=ep,et=et,hp=a,ht=b,nch=1)); continue
            use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
            if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
            if not use: use=chs
            q=quantity(c,use) or use
            deepest=None
            for nm,s in q:
                m=ma(s,n)[w0:w1].dropna(); dd=maxdd(m)
                if dd is not None and (deepest is None or dd<deepest): deepest=dd
            growth = cpt=='growth' or deepest is None or deepest>-abs(min_depth)
            dt_a=[ch_trough2(s,w0,w1,band_t,n,L,where_t,abstain=True) for nm,s in use]
            dt_b=[ch_trough2(s,w0,w1,band_t,n,L,where_t,abstain=False) for nm,s in use]
            l_tr=med_fallback(dt_a,dt_b); end=l_tr if l_tr is not None else w1
            comp=composite_dev(use,L,n,1)[w0:end].dropna(); cross=None
            for d_,v in comp.items():
                if v>=2.0: cross=d_; break
            p0=w0 if cross is None else max(w0,cross-pd.DateOffset(months=peak_cap))
            dp_a=[ch_peak2(s,p0,end,band_p,n,where_p,abstain=True) for nm,s in use]
            dp_b=[ch_peak2(s,p0,end,band_p,n,where_p,abstain=False) for nm,s in use]
            l_pk=med_fallback(dp_a,dp_b)
            ref=next((s for nm,s in use if nm=='monthly reference GDP'),None)
            g_pk=g_tr=None
            if ref is not None and len(ma(ref,n)[w0:w1].dropna())>=6:
                g_tr=ch_trough2(ref,w0,w1,0.0,n,L,where_t,abstain=False)
                g_pk=ch_peak2(ref,w0,g_tr if g_tr is not None else w1,band_p,n,where_p,abstain=False)
            else:
                cy=cyc_hp(q,lam,n)
                if cy is not None and len(cy[w0:w1].dropna())>=6:
                    g_tr=ch_trough2(cy,w0,w1,0.0,1,L,where_t,abstain=False)
                    g_pk=ch_peak2(cy,w0,g_tr if g_tr is not None else w1,band_p,1,where_p,abstain=False)
            pk,tr=(g_pk,g_tr) if growth else (l_pk,l_tr)
            if pk is None: pk=l_pk if growth else g_pk
            if tr is None: tr=l_tr if growth else g_tr
            if cpt=='diffusion':
                d=date_diffusion_panel(use,w0,w1)
                if d['peak'] is not None: pk=d['peak']
                if d['trough'] is not None: tr=d['trough']
            if pk is None or tr is None:
                ci=composite_level(q); m=ma(ci,n)[w0:w1].dropna()
                if len(m)>=4:
                    if tr is None: tr=m.idxmin()
                    if pk is None:
                        pre=m[:tr] if tr is not None else m
                        pk=(pre.idxmax() if len(pre)>1 else m.idxmax())
            if pk is not None and tr is not None and pk>tr: pk,tr=tr,pk
            a,ep=hit(pk,pk_off,freq); b,et=hit(tr,tr_off,freq)
            tot.append(dict(country=c,pk=pk,tr=tr,ep=ep,et=et,hp=a,ht=b,nch=len(use)))
    return tot

if __name__=='__main__':
    for wt in ('last','mid','first'):
        for wp in ('last','mid','first'):
            tot=run(wt,wp)
            a,na,b,nb,ma_,mb,sa,sb=w2(tot)
            s=score(tot,'',show=False)
            print(f'trough={wt:5s} peak={wp:5s}  within2 {a}/{na} {b}/{nb}   hits {s["hp"]}/{s["ht"]}   '
                  f'MAE {ma_:.2f}/{mb:.2f}  bias {sa:+.2f}/{sb:+.2f}')
