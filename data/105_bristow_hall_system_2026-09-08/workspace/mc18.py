"""Q WITH A DIFFERENT OBJECT DOING THE DATING. The weekly claims settle says when. The month can be named by any
monthly object that has a dating record: the insured rate (public on the twelfth of the following month), aggregate
weekly hours (public with the employment report on the fifth) or housing starts (public on the seventeenth). Hours
is the fastest of the three to publish. A guard is added throughout: the month named must be within a year of the
month the weekly series settled on, so that the two objects are talking about the same episode."""
import sys
sys.argv=['x','1962','2026']
src=open('mc14.py').read().split('def build_with(')[0].replace("out=open('mc14.out','w')","out=open('mc18.out','w')")
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
_IC4=(-ICW).rolling(4).mean().dropna()
report("the shipped menu, v3.18 (no Q)",TLH)
for dater in ('insured','hours','starts'):
    for st in (6,8,10,13):
        TL=dict(TLH); TL['Q']=qleg2(_IC4,st,156,5,dater)
        report(f"Q: weekly claims stable={st}, dated by {dater}",TL)
for dater in ('insured','hours','starts'):
    for d2 in ('insured','hours','starts'):
        if d2==dater: continue
        TL=dict(TLH); TL['Q']=qleg2(_IC4,8,156,5,dater); TL['Y']=qleg2(_IC4,8,156,5,d2)
        report(f"Q dated by {dater} together with Y dated by {d2}, both stable=8",TL)
out.close()
