"""Q WITH A DIFFERENT OBJECT DOING THE DATING. The weekly claims settle says when. The month can be named by any
monthly object that has a dating record: the insured rate (public on the twelfth of the following month), aggregate
weekly hours (public with the employment report on the fifth) or housing starts (public on the seventeenth). Hours
is the fastest of the three to publish. A guard is added throughout: the month named must be within a year of the
month the weekly series settled on, so that the two objects are talking about the same episode."""
import sys
sys.argv=['x','1962','2026']
src=open('mc14.py').read().split('def build_with(')[0].replace("out=open('mc14.out','w')","out=open('mc21.out','w')")
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

P("the weekly claims settles around 1970, 1975 and 1991, with what each monthly object would date them to")
fs={k:mkdate(k) for k in DAT}
for st in (8,10):
    P(f"\n  stable={st}")
    for p_,wm in wsettle(_IC4,st,156,5):
        if not (pd.Timestamp('1969-06-01')<=p_<=pd.Timestamp('1976-06-01') or pd.Timestamp('1990-06-01')<=p_<=pd.Timestamp('1992-06-01')): continue
        P(f"    settled {p_:%Y-%m-%d} weekly {wm:%Y-%m} | "+", ".join(f"{k}={fs[k](p_)}" for k in DAT))
P("\nthe two confirmations, when each is public, for the months a close might be dated to")
for dd in [pd.Timestamp(x) for x in ['1970-11-01','1971-01-01','1975-01-01','1975-02-01','1975-03-01','1991-03-01','1991-04-01']]:
    hits=[]
    seg=_BELOW[(_BELOW.index>=dd)&(_BELOW.index<=dd+pd.DateOffset(months=6))]; h=seg[seg>=0.15]
    if len(h): hits.append(("claims",h.index[0]+pd.Timedelta(days=5)))
    for n2,rl_,pdy in [('starts',_RS,18),('hours',_RH,5)]:
        s2=rl_[(rl_.index>=dd)&(rl_.index<=dd+pd.DateOffset(months=6))]; h2=s2[s2>=2.0]
        if len(h2): hits.append((n2,pd.Timestamp(h2.index[0].year,h2.index[0].month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pdy-1)))
    hits.sort(key=lambda z:z[1])
    P(f"   dated {dd:%Y-%m}: "+", ".join(f"{a} {b:%Y-%m-%d}" for a,b in hits)+(f"  SECOND {hits[1][1]:%Y-%m-%d}" if len(hits)>1 else "  never two"))
out.close()
