# asof_trough.py - THE TROUGH CLOSERS' MONTHLY OBJECTS ON THE RELEASE-DAY VINTAGE (Rule 23 clause 1, made uniform on
# 10 September 2026). walk39 to walk46 read the settling closers' monthly objects at each month's first print: the rise of
# housing starts and of factory hours from their twelve-month lows (the confirmations of closers R, S and Q), the settling
# test on housing starts (closer T's proposer) and the unemployment rate rolling over (closer T's guard). Here each is
# read, for each month, from the series as it stood on the day that month's print first appeared - every earlier month at
# the value then current - exactly as the peak side's monthly objects are read since walk45. The weekly closers (C, H, J,
# K and the weekly trigger of Q) read weekly first prints and are unchanged. Run after walk46's preamble (s2/asof_objects.py
# is already loaded there): exec(open('s2/asof_trough.py').read()); it rebuilds RC, TC, QC and TLH['S'] in place.
import numpy as np, pandas as pd
_TL_FIRSTPRINT=dict(RC=RC,TC=TC,QC=QC,S=list(TLH['S']))     # the first-print versions, kept for the comparison
def _rl_fn(log):
    if log: return lambda s:(lambda L:((L/L.rolling(12,min_periods=12).min()-1)*100))(np.log(s)*100)
    return lambda s:((s/s.rolling(12,min_periods=12).min()-1)*100)
RS_ASOF,_RS_PUB=asof_object('HOUST',_rl_fn(True)); RS_ASOF=RS_ASOF.dropna()      # starts: walk38's _rl(lh), lh=100*log(starts)
RH_ASOF,_RH_PUB=asof_object('AWHMAN',_rl_fn(False)); RH_ASOF=RH_ASOF.dropna()   # hours: walk38's _rl(AWH)
def _settle_starts_asof(band=0.02,n=3,L=12,stable=4,back=48):
    """walk38's _settle_starts, with the starts series taken, for each month m, as it stood on the release day of the
    print of m-1 (the latest print a user held in month m)"""
    M=VINT['HOUST']; vds=sorted(M); out_=[]; run=None; runlen=0; seen=set()
    for m in pd.date_range('1948-01-01',(pd.Timestamp(FD['HOUST'].index.max())+pd.DateOffset(months=1)).replace(day=1),freq='MS'):   # 17 Sep 2026: the months run to the month after the latest print in hand (a fixed '2026-08-01' would have silenced closer T from September 2026); a bound taken from the data, not the clock, so the memoised result depends on the data alone
        m1=m-pd.DateOffset(months=1)
        if m1 not in FD['HOUST'].index: continue
        d=pd.Timestamp(FD['HOUST'][m1]); js=[v for v in vds if v<=d]
        if not js: continue
        s=M[js[-1]]; lv=(np.log(s)*100).rolling(n).mean().dropna()
        avail=lv[lv.index<=m1]
        if len(avail)<8: continue
        w=avail[(avail.index>=m-pd.DateOffset(months=back))]
        if len(w)<8: continue
        dd=(w-w.rolling(L).mean()).dropna()
        if not len(dd): run=None; runlen=0; continue
        dp=dd.idxmax(); lo=float(w.min()); i=w.idxmin()
        if i==w.index[-1]: run=None; runlen=0; continue
        hi=float(w[:i].max()) if len(w[:i]) else float(w.max())
        amp=max(hi-lo,1e-9); on=w[w<=lo+band*amp]
        dt=max(dp,on.index[-1]) if len(on) else dp
        mm=pd.Timestamp(dt.year,dt.month,1)
        if run==mm: runlen+=1
        else: run=mm; runlen=1
        if runlen>=stable and mm not in seen:
            seen.add(mm); out_.append((pd.Timestamp(avail.index[-1].year,avail.index[-1].month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=16),mm))
    return out_
def _ur_rolled_asof(k=1):
    """walk38's _ur_rolled: the 3-month mean of the unemployment rate at or below its value k months before, both as they
    stood on the month's release day"""
    ind,_=asof_object('UNRATE',lambda s:(s.rolling(3).mean()<=s.rolling(3).mean().shift(k)).astype(float))
    o={}
    for m,v in ind.items():
        if v>=0.5: o[m]=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
    return o
def _guard_ur_asof(calls,k=1,fwd=6):
    RO=_ur_rolled_asof(k); out_=[]
    for pp,dd in calls:
        hits=[p_ for m,p_ in RO.items() if dd<=m<=dd+pd.DateOffset(months=fwd)]
        if hits: out_.append((max(pp,min(hits)),dd))
    return out_
# the confirmations of R, S and Q read the as-of objects from here on (walk39's _confirm_close reads the globals _RS, _RH)
_RS=RS_ASOF; _RH=RH_ASOF
RC={s_:_confirm_close(_settle_calls(stable=s_)) for s_ in (8,6,5,4)}
TC={s_:_guard_ur_asof(_settle_starts_asof(stable=s_)) for s_ in (6,5,4,3)}
QC={s_:_qleg(stable=s_) for s_ in (13,10,8,6)}
TLH=dict(TLH); TLH['S']=_confirm_close(TLC['S']); TLH['R']=RC[6]; TLH['T']=TC[4]; TLH['Q']=QC[8]
