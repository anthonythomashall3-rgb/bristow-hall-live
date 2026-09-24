"""THE SPEED FRONTIER OF THE SETTLING TEST. The Bristow rule run in an expanding window closes an episode when it
returns the same trough month in a run of consecutive readings. The monthly insured rate settles it once a month;
the weekly insured rate and weekly initial claims settle it once a week, five days after the week ends. This script
lays the whole frontier out: for every trough, the first settle after the peak, its dated month and its lag."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('mc10.out','w')"))

TRs=[pd.Timestamp(x) for x in ['1949-10-01','1954-05-01','1958-04-01','1961-02-01','1970-11-01','1975-03-01','1980-07-01',
     '1982-11-01','1991-03-01','2001-11-01','2009-06-01','2020-04-01','2024-08-01']]
PKs=[pd.Timestamp(x) for x in ['1948-11-01','1953-07-01','1957-08-01','1960-04-01','1969-12-01','1973-11-01','1980-01-01',
     '1981-07-01','1990-07-01','2001-03-01','2007-12-01','2020-02-01','2024-04-01']]

own=pd.read_csv('cache/weekly_iur_prewar.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
frd=pd.read_csv(D+'/IURSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
IURW=pd.concat([own,frd[frd.index>own.index.max()]]).sort_index()
try:
    ICW=pd.read_csv(W+'/lab/data/fred_weekly/ICSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
except Exception as e:
    ICW=None; P(f"   ICSA weekly not loaded: {e}")
P(f"weekly insured rate {IURW.index.min():%Y-%m-%d} -> {IURW.index.max():%Y-%m-%d}  n={len(IURW)}")
if ICW is not None: P(f"weekly initial claims {ICW.index.min():%Y-%m-%d} -> {ICW.index.max():%Y-%m-%d}  n={len(ICW)}")

def settle(lv,band,L,stable,back,pubf,minw=8):
    """the expanding-window Bristow trough, closed when the same month comes back `stable` readings running"""
    out_=[];run=None;runlen=0;seen=set()
    for t in lv.index:
        w=lv[(lv.index>t-back)&(lv.index<=t)]
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
            seen.add(m); out_.append((pubf(t),m))
    return out_

def frontier(nm,calls):
    """for each trough, the first settle published after the peak month closes"""
    rows=[];lags=[];errs=[];bad=0
    for k in range(13):
        pk=PKs[k]+pd.DateOffset(months=2); tr=TRs[k]
        nxt=TRs[k+1] if k+1<13 else pd.Timestamp('2030-01-01')
        c=[(p_,d_) for p_,d_ in calls if p_>=pk and p_<PKs[k+1] + pd.DateOffset(months=2) if True] if k+1<13 else [(p_,d_) for p_,d_ in calls if p_>=pk]
        if not c: rows.append((tr,None,None,None)); continue
        p_,d_=sorted(c)[0]
        lag=(p_-(tr+pd.DateOffset(months=1))).days
        err=(d_.year-tr.year)*12+(d_.month-tr.month)
        rows.append((tr,p_,d_,lag)); lags.append(lag); errs.append(err)
        if abs(err)>1 or lag<0: bad+=1
    P(f"\n{nm}")
    for tr,p_,d_,lag in rows:
        if p_ is None: P(f"   {tr:%Y-%m}  no settle"); continue
        err=(d_.year-tr.year)*12+(d_.month-tr.month)
        P(f"   {tr:%Y-%m}  settled {p_:%Y-%m-%d}  dated {d_:%Y-%m}  lag {lag:+5d}  err {err:+d}")
    if lags:
        L2=sorted(lags); P(f"   n={len(lags)}  median {L2[len(L2)//2]}  mean {sum(lags)/len(lags):.0f}  worst {max(lags)}  within-month {sum(1 for x in lags if x<=31)}  off-month-dating {bad}  total calls {len(calls)}")

MPUB=lambda m: pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=11)
WPUB=lambda t: t+pd.Timedelta(days=5)
MI=(-spl.dropna())
P("\n======== MONTHLY INSURED RATE, 3-month mean (what R uses now) ========")
for stable in (2,3,4,6):
    for back in (36,48,60):
        frontier(f"monthly insured  stable={stable} back={back}m",
                 settle(MI.rolling(3).mean().dropna(),0.02,12,stable,pd.DateOffset(months=back),MPUB))
P("\n======== WEEKLY INSURED RATE, 4-week mean ========")
for stable in (3,4,6,8,12):
    for back in (104,156,208):
        frontier(f"weekly insured  stable={stable} back={back}w",
                 settle((-IURW).rolling(4).mean().dropna(),0.02,52,stable,pd.Timedelta(weeks=back),WPUB))
if ICW is not None:
    P("\n======== WEEKLY INITIAL CLAIMS, 4-week mean ========")
    for stable in (4,6,8,12):
        for back in (104,156,208):
            frontier(f"weekly claims  stable={stable} back={back}w",
                     settle((-ICW).rolling(4).mean().dropna(),0.02,52,stable,pd.Timedelta(weeks=back),WPUB))
out.close()
