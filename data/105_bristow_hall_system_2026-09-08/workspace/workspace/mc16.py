"""THE FAST TRIGGER WITH THE SLOW DATE. Initial claims are public five days after the week they cover, so a settling
test on the weekly series recognises that the fall has stopped weeks before any monthly series can. It dates the
trough badly, because a weekly series wanders. So let the weekly series say WHEN and the monthly insured rate say
WHICH MONTH: at the moment the weekly test settles, the Bristow rule is applied to the monthly insured rate as
published to that date, and the month it returns is the date of the close. The close still has to clear the two
confirmations. Nothing here is read after the publication date of the call."""
import sys
sys.argv=['x','1962','2026']
src=open('walk24.py').read().split('BASE15=dict(BASE)')[0].replace("out=open('walk24_%s.out'%sys.argv[1],'w')","out=open('mc16.out','w')")
exec(src)
BASE15=dict(BASE); BASE15.update(deep=999,wline=None,wline2=None,bshare=None,hline=1.00,spr=round(LINE,3),sahm=0.43,vl=0.20,hback=6)
TRt=[pd.Timestamp(x) for x in ['1949-10-01','1954-05-01','1958-04-01','1961-02-01','1970-11-01','1975-03-01','1980-07-01','1982-11-01','1991-03-01','2001-11-01','2009-06-01','2020-04-01','2024-08-01']]
PKt=[pd.Timestamp(x) for x in ['1948-11-01','1953-07-01','1957-08-01','1960-04-01','1969-12-01','1973-11-01','1980-01-01','1981-07-01','1990-07-01','2001-03-01','2007-12-01','2020-02-01','2024-04-01']]
ICW=pd.read_csv(W+'/lab/data/fred_weekly/ICSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
own=pd.read_csv('cache/weekly_iur_prewar.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
frd=pd.read_csv(D+'/IURSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
IURW=pd.concat([own,frd[frd.index>own.index.max()]]).sort_index()
_MI=(-spl.dropna()).rolling(3).mean().dropna()
_MIP=pd.Series([pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=11) for m in _MI.index],index=_MI.index)
def bris_date(asof,back=48,L=12,band=0.02):
    """the Bristow trough on the monthly insured rate, read only through the months public at `asof`"""
    k=int(_MIP.searchsorted(asof,side='right'))
    av=_MI.iloc[:k]
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
def wsettle(lv,stable,back_w,pub,band=0.02,n=4,L=52):
    out_=[];run=None;runlen=0;seen=set()
    for t in lv.index:
        w=lv[(lv.index>t-pd.Timedelta(weeks=back_w))&(lv.index<=t)]
        if len(w)<8: continue
        d=(w-w.rolling(L).mean()).dropna()
        if not len(d): run=None;runlen=0;continue
        dp=d.idxmax(); lo=float(w.min()); i=w.idxmin()
        if i==w.index[-1]: run=None;runlen=0;continue
        hi=float(w[:i].max()) if len(w[:i]) else float(w.max())
        amp=max(hi-lo,1e-9); on=w[w<=lo+band*amp]
        dt=max(dp,on.index[-1]) if len(on) else dp
        m=pd.Timestamp(dt.year,dt.month,1)
        if run==m: runlen+=1
        else: run=m;runlen=1
        if runlen>=stable and m not in seen:
            seen.add(m); out_.append((t+pd.Timedelta(days=pub),m))
    return out_
def qleg(series,stable,back_w,pub):
    raw=wsettle(series,stable,back_w,pub); out_=[];seen=set()
    for p_,_w in raw:
        dd=bris_date(p_)
        if dd is None: continue
        if dd>=pd.Timestamp(p_.year,p_.month,1): continue      # never date the month the call is made in
        if dd in seen: continue
        seen.add(dd); out_.append((p_,dd))
    return _confirm_close(out_)

def q2leg(series,stable,back_w,pub):
    """THE WEEKLY TRIGGER, THE MONTHLY DATE. The weekly series settles first; the call waits for the next publication
    of the monthly insured rate and is dated by the Bristow rule run on that, so the month named is a month the tool
    has actually seen. A conjunction: the fast object says when, the object with the dating record says which month."""
    raw=wsettle(series,stable,back_w,pub); out_=[];seen=set()
    for p_,_w in raw:
        k=int(_MIP.searchsorted(p_,side='left'))
        if k>=len(_MIP): continue
        pp=_MIP.iloc[k]
        dd=bris_date(pp)
        if dd is None or dd>=pd.Timestamp(pp.year,pp.month,1) or dd in seen: continue
        seen.add(dd); out_.append((pp,dd))
    return _confirm_close(out_)
def build_with(TL,p=None):
    p=dict(BASE15) if p is None else p
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hc=dict(Hc); Hc['line']=p['hline']; Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1)
    def hubv(sl,back):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=back))&(G.index<=m)]; hit=w[w>=p['vl']]
                if len(hit)>=2:
                    kk=hit.index[1]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')]}
    with contextlib.redirect_stdout(io.StringIO()): return B.american_chronology(legs,TL)
def report(nm,TL):
    t=build_with(TL); P(f"\n{nm}")
    lags=[];errs=[];bad=[];closed=0
    tro=[x for x in t if x['kind']=='trough']; pks=[x for x in t if x['kind']=='peak']
    fa=[x for x in pks if not any(pk-pd.DateOffset(months=6)<=x['date']<=tr for pk,tr in zip(PKt,TRt))]
    for i in range(13):
        c=[x for x in tro if TRt[i]-pd.DateOffset(months=6)<=x['date']<=TRt[i]+pd.DateOffset(months=12)]
        if not c: P(f"   {TRt[i]:%Y-%m}  not closed"); continue
        x=c[0]; lg=(x['published']-(TRt[i]+pd.DateOffset(months=1))).days; er=(x['date'].year-TRt[i].year)*12+(x['date'].month-TRt[i].month)
        closed+=1; lags.append(lg); errs.append(er)
        P(f"   {TRt[i]:%Y-%m}  closed {x['published']:%Y-%m-%d}  dated {x['date']:%Y-%m}  lag {lg:+5d}  err {er:+d}  by {x['leg']}")
    un=[x for x in tro if not any(TRt[i]-pd.DateOffset(months=1)<=x['date']<=TRt[i]+pd.DateOffset(months=1) for i in range(13))]
    L2=sorted(lags); unlist=[u["published"].strftime("%Y-%m-%d") for u in un][:6]
    P(f"   closed {closed}/13  median {L2[len(L2)//2] if L2 else '-'}  mean {sum(lags)/len(lags):.0f}  worst {max(lags)}  within-month {sum(1 for x in lags if x<=31)}  exact {sum(1 for e in errs if e==0)}  within-one {sum(1 for e in errs if abs(e)<=1)}  UNMATCHED {len(un)} {unlist}  peaks {len(pks)} FALSE {len(fa)}")
report("the shipped menu, v3.18",TLH)
_IC4=(-ICW).rolling(4).mean().dropna(); _IU4=(-IURW).rolling(4).mean().dropna()
for st in (6,8,10,13,17):
    for bw in (156,208):
        TL=dict(TLH); TL['Q']=q2leg(_IC4,st,bw,5)
        report(f"Q on a weekly CLAIMS trigger stable={st} back={bw}w, monthly date",TL)
for st in (6,8,10,13,17):
    for bw in (156,208):
        TL=dict(TLH); TL['Q']=q2leg(_IU4,st,bw,12)
        report(f"Q on a weekly INSURED trigger stable={st} back={bw}w, monthly date",TL)
out.close()
