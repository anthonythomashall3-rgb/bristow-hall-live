"""THE WEEKLY SETTLING TEST. The insured rate and initial claims are published every week, so the Bristow rule run in
an expanding window can settle a trough weeks before the same test on a monthly series. Initial claims for the week
ending Saturday t are public the following Thursday, five days later; the insured rate for that week is public with
the next week's release, twelve days later. This lays out the frontier for both."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('mc11.out','w')"))
TR9=[pd.Timestamp(x) for x in ['1970-11-01','1975-03-01','1980-07-01','1982-11-01','1991-03-01','2001-11-01','2009-06-01','2020-04-01','2024-08-01']]
PK9=[pd.Timestamp(x) for x in ['1969-12-01','1973-11-01','1980-01-01','1981-07-01','1990-07-01','2001-03-01','2007-12-01','2020-02-01','2024-04-01']]
own=pd.read_csv('cache/weekly_iur_prewar.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
frd=pd.read_csv(D+'/IURSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
IURW=pd.concat([own,frd[frd.index>own.index.max()]]).sort_index()
ICW=pd.read_csv(W+'/lab/data/fred_weekly/ICSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
CCW=None
import glob as _g
for c in _g.glob(W+'/lab/data/fred_weekly/CCSA.csv'):
    CCW=pd.read_csv(c,index_col=0,parse_dates=True).iloc[:,0].dropna()
P(f"insured weekly {IURW.index.min():%Y-%m-%d}->{IURW.index.max():%Y-%m-%d} n={len(IURW)} | claims weekly {ICW.index.min():%Y-%m-%d}->{ICW.index.max():%Y-%m-%d} n={len(ICW)}"+(f" | continued {CCW.index.min():%Y-%m-%d} n={len(CCW)}" if CCW is not None else " | continued NOT FOUND"))
def settle(lv,band,L,stable,back,pub,minw=8):
    out_=[];run=None;runlen=0;seen=set()
    idx=lv.index; vals=lv
    for t in idx:
        w=vals[(idx>t-back)&(idx<=t)]
        if len(w)<minw: continue
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
def score(nm,calls,show=False):
    lags=[];errs=[];miss=0;pre=0;rows=[]
    for k in range(9):
        lo=PK9[k]+pd.DateOffset(months=2); hi=(PK9[k+1]+pd.DateOffset(months=2)) if k+1<9 else pd.Timestamp('2030-01-01')
        c=sorted([(p_,d_) for p_,d_ in calls if lo<=p_<hi])
        if not c: rows.append((TR9[k],None,None,None,None)); miss+=1; continue
        p_,d_=c[0]; lag=(p_-(TR9[k]+pd.DateOffset(months=1))).days
        err=(d_.year-TR9[k].year)*12+(d_.month-TR9[k].month)
        rows.append((TR9[k],p_,d_,lag,err)); lags.append(lag); errs.append(err)
        if lag<0 or err<-1: pre+=1
    if show:
        for tr,p_,d_,lag,err in rows:
            P(f"      {tr:%Y-%m}  "+("no settle" if p_ is None else f"{p_:%Y-%m-%d} dated {d_:%Y-%m} lag {lag:+5d} err {err:+d}"))
    if not lags: P(f"   {nm}: nothing"); return None
    L2=sorted(lags)
    P(f"   {nm}: n={len(lags)} miss={miss} median {L2[len(L2)//2]} mean {sum(lags)/len(lags):.0f} worst {max(lags)} within-month {sum(1 for x in lags if x<=31)} exact {sum(1 for e in errs if e==0)} within-one {sum(1 for e in errs if abs(e)<=1)} PREMATURE/BADDATE {pre} calls {len(calls)}")
    return (pre,max(lags),L2[len(L2)//2],nm,calls)
best=[]
P("\n==== WEEKLY INSURED RATE, 4-week mean, published 12 days after the week ====")
for stable in (4,6,8,10,13):
    for back in (104,156,208):
        r=score(f"insured stable={stable} back={back}w",settle((-IURW).rolling(4).mean().dropna(),0.02,52,stable,pd.Timedelta(weeks=back),12))
        if r: best.append(r)
P("\n==== WEEKLY INITIAL CLAIMS, 4-week mean, published 5 days after the week ====")
for stable in (6,8,10,13,17):
    for back in (104,156,208):
        r=score(f"claims stable={stable} back={back}w",settle((-ICW).rolling(4).mean().dropna(),0.02,52,stable,pd.Timedelta(weeks=back),5))
        if r: best.append(r)
P("\n==== the clean ones, fastest first ====")
for pre,worst,med,nm,calls in sorted([b for b in best if b[0]==0],key=lambda z:(z[2],z[1]))[:6]:
    P(f"\n   {nm}"); score(nm,calls,show=True)
out.close()
