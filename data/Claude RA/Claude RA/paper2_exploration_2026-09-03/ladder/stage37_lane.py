"""Stage 37: the live lane on short-history data. Rule: a lane channel is scored only on the years it covers; threshold by the
maximum-margin rule on that window (gated); zero false alarms within the window required; it may ADVANCE a v5 call that follows
within 120 days. Report: for each recession the lane channel covers, the lane's first crossing vs v5's call (days advanced)."""
exec(open("stage32_backstops.py").read().split("rows=[]")[0])
DF=HOME+"/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/"
def loadfred(f):
    s=pd.read_csv(f); s=s[s.value!="."]; s.index=pd.to_datetime(s.date); return s.value.astype(float).sort_index()
def dl(s, lagd): x=s.dropna().copy(); x.index=x.index+pd.Timedelta(days=lagd); return x
V5calls={"1969-12":"1969-10-06","1973-11":"1973-10-25","1980-01":"1980-01-03","1981-07":"1981-08-18","1990-07":"1990-08-03","2001-03":"2001-02-02","2007-12":"2008-01-04","2020-02":"2020-03-19","2024-04":"2024-05-03"}
allowed=np.zeros(N,bool)
for pk,tr in T_P1:
    lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(tr)+12).to_timestamp(how="end")); allowed[lo:hi+1]=True
def lane(name, series, lagd, hold=5, sign=1):
    """series: larger = worse after sign. Threshold = midpoint of gated quiet max (in window) and the smallest onset-window
    max among recessions it must carry (those where it exceeds the quiet max). Returns per-recession first crossing."""
    x=dl(sign*series, lagd); v=x.reindex(cal).ffill().values; start=x.index.min()
    q=(~allowed)&(cal>=start)&GATE[12]; 
    if q.sum()<250: return None
    Q=np.nanmax(v[q]); Qd=str(cal[q][np.nanargmax(v[q])].date())
    covered=[(pk,tr) for pk,tr in T_P1 if (P(pk)-2).to_timestamp()>=start]
    R={}
    for pk,tr in covered:
        lo=cal.searchsorted((P(pk)-1).to_timestamp()); hi=cal.searchsorted((P(pk)+2).to_timestamp(how="end")); w=v[lo:hi+1]; R[pk]=np.nanmax(w) if len(w) else np.nan
    carried=[pk for pk in R if R[pk]>Q]
    if not carried: return dict(stat=name, start=str(start.date())[:7], Q=round(Q,3), Qdate=Qd, carried=[], note="never separates")
    t=(Q+min(R[pk] for pk in carried))/2
    on=(v>=t)&GATE[12]
    out=[]
    for pk,tr in covered:
        lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(tr)).to_timestamp(how="end")); seg=on[lo:hi+1]
        if seg.any():
            d=cal[lo+int(np.argmax(seg))]; adv=(pd.Timestamp(V5calls[pk])-d).days; out.append((pk, str(d.date()), adv))
    # false alarms of the lane alone within its window (gated, thresholded): runs starting outside windows
    d=np.diff(on.astype(np.int8)); starts=np.flatnonzero(d==1)+1; fa=[str(cal[i].date()) for i in starts if not allowed[i] and cal[i]>=start]
    return dict(stat=name, start=str(start.date())[:7], Q=round(Q,3), Qdate=Qd, thr=round(t,3), carried=carried, calls=out, lane_fa=fa[:4])
res=[]
of=pd.read_csv(DF+"other/ofr_fsi.csv", parse_dates=["Date"]).set_index("Date")
for c in ["OFR FSI","Credit","Equity valuation","Funding","Volatility","Safe assets"]:
    for w in [1,5,20]: res.append(lane(f"OFR {c} {w}d mean", of[c].rolling(w).mean(), 1))
vix=loadfred(DF+"fred_daily/VIXCLS.csv"); res.append(lane("VIX 20d mean", vix.rolling(20).mean(), 1)); res.append(lane("VIX 20d change", vix-vix.shift(20), 1)); res.append(lane("VIX rise from 250d min", vix-vix.rolling(250).min(), 1))
baa=loadfred(DF+"fred_daily/BAA10Y.csv"); res.append(lane("Baa-10y 20d mean", baa.rolling(20).mean(), 1)); res.append(lane("Baa-10y rise from 250d min", baa-baa.rolling(250).min(), 1)); res.append(lane("Baa-10y 60d change", baa-baa.shift(60), 1))
nfci=loadfred(DF+"extra/NFCI.csv"); res.append(lane("NFCI level", nfci, 6, 10)); res.append(lane("NFCI 13w change", nfci-nfci.shift(13), 6, 10))
ind=pd.read_csv(ODD+"onset-detector-new-2026-08-23/35_alt_and_stability/indeed/aggregate_job_postings_US.csv", parse_dates=["date"]); ind=ind[ind.variable=="total postings"].set_index("date").indeed_job_postings_index_SA
for w in [10,20,40]: res.append(lane(f"Indeed postings {w}d log fall", -np.log(ind/ind.shift(w)), 3))
res.append(lane("Indeed postings drawdown from 250d max", -np.log(ind/ind.rolling(250).max()), 3))
ui=pd.read_csv(DF+"other/dts_daily_ui_withheld.csv", parse_dates=["record_date"]).groupby("record_date").transaction_today_amt.sum().sort_index(); ui28=ui.rolling("28D").sum()
res.append(lane("DTS UI benefits 28d sum, log rise vs 90d earlier", np.log(ui28/ui28.shift(90, freq="D").reindex(ui28.index, method="nearest")), 3))
wt=pd.read_csv(DF+"other/dts_daily_withheld.csv", parse_dates=["record_date"]).groupby("record_date").transaction_today_amt.sum().sort_index(); wt28=wt.rolling("28D").sum()
res.append(lane("DTS withheld taxes 28d sum, log fall vs 365d earlier", -np.log(wt28/wt28.shift(365, freq="D").reindex(wt28.index, method="nearest")), 3))
ns=pd.read_csv(DF+"other/sffed_news_sentiment.csv", parse_dates=["date"]).set_index("date")["News Sentiment"]
res.append(lane("news sentiment 20d mean (low=bad)", -ns.rolling(20).mean(), 1)); res.append(lane("news sentiment 20d change down", -(ns.rolling(20).mean()-ns.rolling(20).mean().shift(20)), 1))
# state initial-claims breadth from FRED weekly state files (1987->)
import glob
st={}
for f in glob.glob(DF+"fred_weekly/??ICLAIMS.csv"):
    sid=os.path.basename(f)[:2]
    try: st[sid]=loadfred(f)
    except Exception: pass
if len(st)>40:
    W=pd.DataFrame(st); m4=W.rolling(4).mean(); g=m4/m4.shift(52)-1
    for p in [0.2,0.3,0.5]: res.append(lane(f"states with initial claims 4wk yoy>={int(p*100)}% (count)", (g>=p).sum(axis=1), 9, 10))
res=[r for r in res if r]
for r in res: print(r)
