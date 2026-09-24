"""The SARB's documented trend (Quarterly Bulletin, March 2023, 'The South African business
cycle from 2013 to 2022'): the growth cycle is the deviation of the composite coincident
indicator from a Hodrick-Prescott trend with lambda = 108,000 (Zarnowitz and Ozyildirim's
monthly approximation to the phase-average trend), with a two-step COVID treatment (an
HP(500) proxy substituted for March-June 2020 before the HP(108,000) trend).  The held-out
South African route is rerun with that trend beside the shipped lambda of 500,000 (chosen on
the nine chronologies, never on South Africa).  Rule 18: a committee's documented object,
tried; not adopted unless it holds."""
import sys; sys.path.insert(0,'/home/claude/lab'); sys.argv=['x']
import numpy as np, pandas as pd, io, contextlib
with contextlib.redirect_stdout(io.StringIO()): import zaf_full as Z
from bench import ts, hit, ch_trough, ch_peak, hp_filter
def run_lam(lam, covid_fix=False):
    co=Z.co; y=np.log(co.dropna()); y=y[np.isfinite(y)]
    if covid_fix:
        t500=pd.Series(hp_filter(y.values,500.0),index=y.index); ya=y.copy()
        m=(ya.index>=pd.Timestamp('2020-03-01'))&(ya.index<=pd.Timestamp('2020-06-01')); ya[m]=t500[m]
        t=pd.Series(hp_filter(ya.values,lam),index=y.index)
    else: t=pd.Series(hp_filter(y.values,lam),index=y.index)
    cc=np.exp(y-t)*100.0; hp_=ht=0; rows=[]; n=0
    for pk_off,tr_off in Z.ZA:
        pkm=ts(pk_off); trm=ts(tr_off); w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if co.index.min()>w0: continue
        n+=1
        tr=ch_trough(cc,w0,w1,0.0,3,12,abstain=False); _u=ch_trough(cc,w0,w1,0.0,3,12,abstain=False,refine=False)
        pk=ch_peak(cc,w0,_u if _u is not None else w1,0.0,3,abstain=False,refine=False)
        a,e1=hit(pk,pk_off,'M'); b,e2=hit(tr,tr_off,'M'); hp_+=a; ht+=b; rows.append((pk_off,e1,tr_off,e2,pk,tr))
    return hp_,ht,n,rows
for lam,fix in ((500000.,False),(108000.,False),(108000.,True)):
    hp_,ht,n,rows=run_lam(lam,fix)
    print(f'lambda {lam:>9.0f} {"with the COVID two-step" if fix else "":24s} peaks {hp_}/{n} troughs {ht}/{n}')
    for r in rows: print(f'    {r[0]} {str(r[1]):>5s} ({r[4]:%Y-%m})   {r[2]} {str(r[3]):>5s} ({r[5]:%Y-%m})')
