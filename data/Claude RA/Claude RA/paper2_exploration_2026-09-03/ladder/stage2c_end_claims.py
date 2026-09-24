from harness import *
ic=load(ODD+"01_labor_unemployment/weekly/ICSA.csv"); cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv"); iur=load(ODD+"01_labor_unemployment/weekly/IURSA.csv")
EPS=[e for e in EP if e[0]>="1969"]
rows=[]
for nm,s in [("initial claims",ic),("continued claims",cc),("insured unemp. rate",iur)]:
    for w in [4,8,13]:
        ma=s.rolling(w).mean().dropna()
        for x in [0.03,0.05,0.10,0.15]:
            errs=[]; lags=[]; revs=0; detail=[]
            for pk,tr in EPS:
                start=(P(pk)-1).to_timestamp()   # track from a month before the peak (onset side handled elsewhere)
                seg=ma[(ma.index>=start)&(ma.index<=(P(tr)+18).to_timestamp(how="end"))]
                runmax=-1e18; pkd=None; call=None; calls=0
                for d,v in seg.items():
                    if v>runmax:
                        if call is not None: calls+=1; call=None   # superseded
                        runmax=v; pkd=d
                    elif call is None and v<=runmax*(1-x):
                        call=d
                if call is None: errs.append(None); lags.append(None); continue
                errs.append((pkd.to_period("M")-P(tr)).n); lags.append((call.to_period("M")-P(tr)).n); revs+=calls
                detail.append(f"{tr}: peak {pkd.date()} call {call.date()}")
            ok=all(e is not None and abs(e)<=3 for e in errs) and all(l is not None and abs(l)<=2 for l in lags)
            rows.append(dict(rule=f"{nm} {w}wk avg peak, confirm when {int(x*100)}% below peak", dated_err=errs, call_lag=lags, revisions=revs, passes=ok, n=len(EPS)))
df=pd.DataFrame(rows); pd.set_option("display.width",300); pd.set_option("display.max_colwidth",120); pd.set_option("display.max_rows",200)
print(df.to_string())
