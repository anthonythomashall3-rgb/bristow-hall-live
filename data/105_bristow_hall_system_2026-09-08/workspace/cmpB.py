"""THE OLD BRISTOW RULE AGAINST THE BRISTOW HALL RULE. Two things are run here. First the old rule as Paper 1 uses
it: the seven-channel American panel, each episode dated by the median of the channels' own turning points, on the
current vintage of every series - a retrospective dating tool. Second the old rule run in real time, which is the
lab's own real_time_trough_calls and its mirror for peaks: at every month the composite deviation statistic is
recomputed from what was in hand, an episode opens when the statistic reaches two per cent and closes when it has
fallen for four months and by half a point from its maximum. The month named is the month the statistic peaked for
a trough and the median of the channels' own peaks for a peak. The publication convention is the fifteenth of the
following month, the day industrial production and retail sales for a month are out; four of the seven channels
have reported by then. The real-time run reads the CURRENT vintage of every channel, which flatters the old rule,
because its channels are all heavily revised. Stated, not hidden."""
import sys
sys.argv=['x','1962','2026']
src=open('walk25.py').read().split('BASE15=dict(BASE)')[0].replace("out=open('walk25_%s.out'%sys.argv[1],'w')","out=open('cmpB.out','w')")
exec(src)
sys.path.insert(0,W+'/lab'); sys.path.insert(0,W)
import bench
from bench import PANELS, channels, ep3, ts, quantity, dating_series, md
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
CH=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
NB=[('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
    ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
    ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04'),('2024-04','2024-08')]
PKn=[pd.Timestamp(a+'-01') for a,b in NB]; TRn=[pd.Timestamp(b+'-01') for a,b in NB]
def mm(a,b): return (a.year-b.year)*12+(a.month-b.month)

P("="*100); P("ONE. THE OLD BRISTOW RULE AS PAPER 1 USES IT: retrospective dating, current vintage, whole record seen")
P("="*100)
FR={}
for i,(a,b) in enumerate(NB):
    pkm,trm=PKn[i],TRn[i]
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in CH if s.index.min()<=w0 and s.index.max()>=trm]
    if not use: use=[(nm,s) for nm,s in CH if s.index.min()<=trm and s.index.max()>=trm]
    if not use: use=CH
    vol=quantity('United States',use) or use
    try:
        r=B.date_turning_points(use,w0,w1,volume_channels=vol,concept='level',lam=500000.0,
                                band_trough=0.12,band_peak=0.01,peak_cap=18,smooth=3,lookback=12,
                                dating_series=dating_series('United States',w0,trm))
    except Exception as e:
        P(f"   {a}/{b}: FAILED {e}"); continue
    pe=mm(r['peak'],pkm) if r['peak'] is not None else None
    te=mm(r['trough'],trm) if r['trough'] is not None else None
    FR[i]=(pe,te)
    P(f"   {a} / {b}   channels {len(use):2d}   rule peak {r['peak']:%Y-%m} err {pe:+d}   rule trough {r['trough']:%Y-%m} err {te:+d}")
pe=[v[0] for v in FR.values() if v[0] is not None]; te=[v[1] for v in FR.values() if v[1] is not None]
P(f"   PEAKS  n={len(pe)} exact {sum(1 for x in pe if x==0)} within one {sum(1 for x in pe if abs(x)<=1)} worst {max(abs(x) for x in pe)} months")
P(f"   TROUGHS n={len(te)} exact {sum(1 for x in te if x==0)} within one {sum(1 for x in te if abs(x)<=1)} worst {max(abs(x) for x in te)} months")

P(""); P("="*100); P("TWO. THE OLD BRISTOW RULE RUN IN REAL TIME: expanding window, current vintage, published on the fifteenth")
P("="*100)
def pub(m): return pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=14)
Dv=B.composite_deviation(CH,12,3,2).dropna()
P(f"   composite deviation runs {Dv.index.min():%Y-%m} to {Dv.index.max():%Y-%m}, {len(Dv)} months")
def rt_calls(threshold=2.0,fall=4,drop=0.5,mincycle=15,warm=24):
    calls=[];start=Dv.index[0];state='closed';last=None;onset=None
    for i in range(warm,len(Dv)):
        t=Dv.index[i]; seg=Dv[start:t]
        if state=='closed':
            if float(Dv.iloc[i])>=threshold:
                if last is not None and mm(t,last)<mincycle: continue
                w0=t-pd.DateOffset(months=24)
                dates=[B.channel_peak(s[s.index<=t],w0,t) for nm,s in CH if s.index.min()<=w0 and (s[s.index<=t].index.max() if len(s[s.index<=t]) else pd.Timestamp.min)>=t-pd.DateOffset(months=2)]
                dates=[d for d in dates if d is not None]
                if not dates: continue
                dt=B._median(dates)
                calls.append((pub(t),pd.Timestamp(dt.year,dt.month,1),'peak')); onset=dt; state='open'; start=Dv.index[0]
        else:
            at=seg.idxmax(); hi=float(seg.max())
            if hi<threshold: continue
            after=seg[seg.index>at]
            if len(after)<fall: continue
            tail=list(after.iloc[-fall:]); prev=float(after.iloc[-fall-1]) if len(after)>fall else hi
            fal=all(tail[k]<(tail[k-1] if k>0 else prev) for k in range(fall))
            if fal and (hi-float(after.iloc[-1]))>=drop:
                calls.append((pub(t),pd.Timestamp(at.year,at.month,1),'trough')); last=at; state='closed'; start=t+pd.DateOffset(months=1)
    return calls
CL=rt_calls()
for p_,d_,k in CL: P(f"   {p_:%Y-%m-%d}  {k.upper():6s} dated {d_:%Y-%m}")
P(""); P("   scored against the thirteen episodes")
pl=[];tl=[];perr=[];terr=[];fa=[]
for i in range(13):
    c=[x for x in CL if x[2]=='peak' and PKn[i]-pd.DateOffset(months=9)<=x[1]<=PKn[i]+pd.DateOffset(months=9)]
    if c:
        p_,d_,_=c[0]; lg=(p_-(PKn[i]+pd.DateOffset(months=1))).days; er=mm(d_,PKn[i]); pl.append(lg); perr.append(er)
        P(f"   peak   {PKn[i]:%Y-%m}  called {p_:%Y-%m-%d} dated {d_:%Y-%m}  lag {lg:+5d}  err {er:+d}")
    else: P(f"   peak   {PKn[i]:%Y-%m}  NOT CALLED")
    c=[x for x in CL if x[2]=='trough' and TRn[i]-pd.DateOffset(months=9)<=x[1]<=TRn[i]+pd.DateOffset(months=12)]
    if c:
        p_,d_,_=c[0]; lg=(p_-(TRn[i]+pd.DateOffset(months=1))).days; er=mm(d_,TRn[i]); tl.append(lg); terr.append(er)
        P(f"   trough {TRn[i]:%Y-%m}  called {p_:%Y-%m-%d} dated {d_:%Y-%m}  lag {lg:+5d}  err {er:+d}")
    else: P(f"   trough {TRn[i]:%Y-%m}  NOT CLOSED")
fa=[x for x in CL if x[2]=='peak' and not any(PKn[i]-pd.DateOffset(months=9)<=x[1]<=PKn[i]+pd.DateOffset(months=9) for i in range(13))]
P(f"\n   PEAKS  detected {len(pl)}/13  FALSE ALARMS {len(fa)} {[f'{x[0]:%Y-%m-%d}' for x in fa]}")
if pl:
    s=sorted(pl); P(f"   lags {s}  median {s[len(s)//2]}  mean {sum(pl)/len(pl):.1f}  within the month {sum(1 for x in pl if x<=31)}/{len(pl)}  dates exact {sum(1 for e in perr if e==0)} within one {sum(1 for e in perr if abs(e)<=1)}")
P(f"   TROUGHS closed {len(tl)}/13")
if tl:
    s=sorted(tl); P(f"   lags {s}  median {s[len(s)//2]}  mean {sum(tl)/len(tl):.1f}  within the month {sum(1 for x in tl if x<=31)}/{len(tl)}  dates exact {sum(1 for e in terr if e==0)} within one {sum(1 for e in terr if abs(e)<=1)}")
P("\n   the same, restricted to the nine peaks from November 1961 and the nine troughs from 1970")
p9=[(PKn[i],pl,perr) for i in range(4,13)]
pl9=[];pe9=[];tl9=[];te9=[]
for i in range(4,13):
    c=[x for x in CL if x[2]=='peak' and PKn[i]-pd.DateOffset(months=9)<=x[1]<=PKn[i]+pd.DateOffset(months=9)]
    if c: pl9.append((c[0][0]-(PKn[i]+pd.DateOffset(months=1))).days); pe9.append(mm(c[0][1],PKn[i]))
    c=[x for x in CL if x[2]=='trough' and TRn[i]-pd.DateOffset(months=9)<=x[1]<=TRn[i]+pd.DateOffset(months=12)]
    if c: tl9.append((c[0][0]-(TRn[i]+pd.DateOffset(months=1))).days); te9.append(mm(c[0][1],TRn[i]))
for nm,L,E in [('peaks',pl9,pe9),('troughs',tl9,te9)]:
    if L:
        s=sorted(L); P(f"   {nm}: n={len(L)}/9  lags {s}  median {s[len(s)//2]}  mean {sum(L)/len(L):.1f}  within the month {sum(1 for x in L if x<=31)}  exact {sum(1 for e in E if e==0)} within one {sum(1 for e in E if abs(e)<=1)}")
    else: P(f"   {nm}: none")
out.close()
