"""THE CONJUNCTION ON THE TROUGH SIDE. The settling test is slow only because the run length does all the work of
telling a settled date from a wandering one. A second settling test on an independent series can do that work
instead: two objects that settle on the same month, or on months a month apart, agree; the close is published at
the later of the two publications and dated by the insured rate, the object with the dating record. That lets the
run length come down from six months to three or four."""
import sys
sys.argv=['x','1962','2026']
src=open('walk24.py').read().split('BASE15=dict(BASE)')[0].replace("out=open('walk24_%s.out'%sys.argv[1],'w')","out=open('mc13.out','w')")
exec(src)
TR9=[pd.Timestamp(x) for x in ['1970-11-01','1975-03-01','1980-07-01','1982-11-01','1991-03-01','2001-11-01','2009-06-01','2020-04-01','2024-08-01']]
PK9=[pd.Timestamp(x) for x in ['1969-12-01','1973-11-01','1980-01-01','1981-07-01','1990-07-01','2001-03-01','2007-12-01','2020-02-01','2024-04-01']]
def settleM(lv,stable,band=0.02,n=3,L=12,back=48,pubday=11,pubm=1):
    """the Bristow rule in an expanding window on a monthly series read only through the month before the reading"""
    lvv=lv.rolling(n).mean().dropna(); out_=[];run=None;runlen=0;seen=set()
    for m in lvv.index:
        w=lvv[(lvv.index>=m-pd.DateOffset(months=back))&(lvv.index<=m)]
        if len(w)<8: continue
        d=(w-w.rolling(L).mean()).dropna()
        if not len(d): run=None;runlen=0;continue
        dp=d.idxmax(); lo=float(w.min()); i=w.idxmin()
        if i==w.index[-1]: run=None;runlen=0;continue
        hi=float(w[:i].max()) if len(w[:i]) else float(w.max())
        amp=max(hi-lo,1e-9); on=w[w<=lo+band*amp]
        dt=max(dp,on.index[-1]) if len(on) else dp
        mm=pd.Timestamp(dt.year,dt.month,1)
        if run==mm: runlen+=1
        else: run=mm;runlen=1
        if runlen>=stable and mm not in seen:
            seen.add(mm); out_.append((pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=pubm)+pd.Timedelta(days=pubday),mm))
    return out_
MI=(-spl.dropna()); HR=AWH.dropna(); ST=lh.dropna(); UI=(-UR.dropna())
SER={'insured':(MI,11,1),'hours':(HR,4,1),'starts':(ST,17,1),'rate':(UI,4,1)}
def pair(a,b,sa,sb,tol=1):
    """two settling tests agree when their dated months are within `tol`; the close is dated by the first named"""
    A=settleM(SER[a][0],sa,pubday=SER[a][1],pubm=SER[a][2]); Bc=settleM(SER[b][0],sb,pubday=SER[b][1],pubm=SER[b][2])
    out_=[]
    for pa,da in A:
        cand=[(pb,db) for pb,db in Bc if abs((db.year-da.year)*12+(db.month-da.month))<=tol]
        if not cand: continue
        pb,db=min(cand); out_.append((max(pa,pb),da))
    seen=set(); res=[]
    for p_,d_ in sorted(out_):
        if d_ in seen: continue
        seen.add(d_); res.append((p_,d_))
    return res
def score(nm,calls,show=False):
    lags=[];errs=[];miss=0;pre=0;rows=[]
    for k in range(9):
        lo=PK9[k]+pd.DateOffset(months=2); hi=(PK9[k+1]+pd.DateOffset(months=2)) if k+1<9 else pd.Timestamp('2030-01-01')
        c=sorted([(p_,d_) for p_,d_ in calls if lo<=p_<hi])
        if not c: rows.append((TR9[k],None,None,None,None)); miss+=1; continue
        p_,d_=c[0]; lg=(p_-(TR9[k]+pd.DateOffset(months=1))).days
        er=(d_.year-TR9[k].year)*12+(d_.month-TR9[k].month)
        rows.append((TR9[k],p_,d_,lg,er)); lags.append(lg); errs.append(er)
        if lg<0 or abs(er)>1: pre+=1
    if show:
        for tr,p_,d_,lg,er in rows: P(f"      {tr:%Y-%m}  "+("no call" if p_ is None else f"{p_:%Y-%m-%d} dated {d_:%Y-%m} lag {lg:+5d} err {er:+d}"))
    if not lags: return None
    L2=sorted(lags)
    P(f"   {nm}: n={len(lags)} miss={miss} median {L2[len(L2)//2]} mean {sum(lags)/len(lags):.0f} worst {max(lags)} within-month {sum(1 for x in lags if x<=31)} exact {sum(1 for e in errs if e==0)} BAD {pre} calls {len(calls)}")
    return (pre,miss,L2[len(L2)//2],max(lags),nm,calls)
res=[]
P("==== one object alone, for reference ====")
for a in SER:
    for s in (3,4,5,6):
        r=score(f"{a} alone stable={s}",settleM(SER[a][0],s,pubday=SER[a][1],pubm=SER[a][2]))
        if r: res.append(r)
P("\n==== two objects agreeing within one month, dated by the first ====")
for a in SER:
    for b in SER:
        if a==b: continue
        for sa in (3,4):
            for sb in (3,4):
                r=score(f"{a}(s={sa}) + {b}(s={sb})",pair(a,b,sa,sb))
                if r: res.append(r)
P("\n==== the clean ones, fastest first ====")
for pre,miss,med,worst,nm,calls in sorted([r for r in res if r[0]==0 and r[1]==0],key=lambda z:(z[2],z[3]))[:8]:
    P(f"\n   {nm}"); score(nm,calls,show=True)
out.close()
