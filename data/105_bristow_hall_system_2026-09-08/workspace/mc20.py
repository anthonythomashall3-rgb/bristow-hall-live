"""Q WITH A DIFFERENT OBJECT DOING THE DATING. The weekly claims settle says when. The month can be named by any
monthly object that has a dating record: the insured rate (public on the twelfth of the following month), aggregate
weekly hours (public with the employment report on the fifth) or housing starts (public on the seventeenth). Hours
is the fastest of the three to publish. A guard is added throughout: the month named must be within a year of the
month the weekly series settled on, so that the two objects are talking about the same episode."""
import sys
sys.argv=['x','1962','2026']
src=open('mc14.py').read().split('def build_with(')[0].replace("out=open('mc14.out','w')","out=open('mc20.out','w')")
exec(src)
exec("def build_with("+open('mc14.py').read().split('def build_with(')[1].split('report("the shipped menu')[0])
DAT={'insured':((-spl.dropna()).rolling(3).mean().dropna(),11,1),
     'hours':(AWH.dropna().rolling(3).mean().dropna(),4,1),
     'starts':(lh.dropna().rolling(3).mean().dropna(),17,1)}
def mkdate(nm,back=48,L=12,band=0.02):
    ser,pdy,pm=DAT[nm]
    PUB=pd.Series([pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=pm)+pd.Timedelta(days=pdy) for m in ser.index],index=ser.index)
    def f(asof):
        k=int(PUB.searchsorted(asof,side='right')); av=ser.iloc[:k]
        if len(av)<8: return None
        w=av[av.index>=av.index[-1]-pd.DateOffset(months=back)]
        if len(w)<8: return None
        d=(w-w.rolling(L).mean()).dropna()
        if not len(d): return None
        dp=d.idxmax(); lo=float(w.min()); i=w.idxmin()
        if i==w.index[-1]: return None
        hi=float(w[:i].max()) if len(w[:i]) else float(w.max())
        amp=max(hi-lo,1e-9); on=w[w<=lo+band*amp]
        dt=max(dp,on.index[-1]) if len(on) else dp
        return pd.Timestamp(dt.year,dt.month,1)
    return f
def qleg2(trig,stable,back_w,pub,dater,gap=12):
    raw=wsettle(trig,stable,back_w,pub); f=mkdate(dater); out_=[];seen=set()
    for p_,wm in raw:
        dd=f(p_)
        if dd is None or dd>=pd.Timestamp(p_.year,p_.month,1) or dd in seen: continue
        if abs((wm.year-dd.year)*12+(wm.month-dd.month))>gap: continue   # the two objects must mean the same episode
        seen.add(dd); out_.append((p_,dd))
    return _confirm_close(out_)
def qleg3(trig,stable,back_w,pub,dater,other,tol=1,gap=12):
    """A DATE NAMED BY ONE OBJECT ALONE IS NOT A DATE. The weekly claims settle says when; the month is named by
    `dater` and has to be corroborated by `other` within `tol` months. Both are read as published at that moment."""
    raw=wsettle(trig,stable,back_w,pub); f=mkdate(dater); h=mkdate(other); out_=[];seen=set()
    for p_,wm in raw:
        dd=f(p_); ee=h(p_)
        if dd is None or ee is None: continue
        if dd>=pd.Timestamp(p_.year,p_.month,1) or dd in seen: continue
        if abs((wm.year-dd.year)*12+(wm.month-dd.month))>gap: continue
        if abs((ee.year-dd.year)*12+(ee.month-dd.month))>tol: continue
        seen.add(dd); out_.append((p_,dd))
    return _confirm_close(out_)
_IC4=(-ICW).rolling(4).mean().dropna()
report("the shipped menu, v3.18 (no Q)",TLH)
for tol in (1,2,3):
    for st in (8,10,13):
        TL=dict(TLH); TL['Q']=qleg3(_IC4,st,156,5,'starts','insured',tol=tol)
        report(f"Q: weekly claims stable={st}, dated by starts, corroborated by the insured rate within {tol} month(s)",TL)
out.close()
