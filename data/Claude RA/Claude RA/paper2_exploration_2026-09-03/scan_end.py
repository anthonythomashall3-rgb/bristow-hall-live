import pandas as pd, numpy as np, os
HOME=os.path.expanduser("~")
stats=pd.read_pickle("/tmp/explore/stats.pkl")
rt=pd.read_csv(HOME+"/mnt/Recession Papers/Paper 2/data/realtime_first_print_sahm_by_vintage.csv", parse_dates=["vintage","latest_month"])
first=rt.sort_values("vintage").drop_duplicates("latest_month", keep="first").set_index("latest_month").sort_index()
V=first.vintage; P=lambda s: pd.Period(s,"M")
nber=[("1960-04","1961-02"),("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
starts={"1960-04":"1960-08","1969-12":"1970-02","1973-11":"1974-07","1980-01":"1980-04","1981-07":"1981-11","1990-07":"1990-11","2001-03":"2001-06","2007-12":"2008-04","2020-02":"2020-04"}  # sustained Sahm crossing months
def run_end(ser, start, tr, mode, tol=0.0, k=1):
    """Track first-print ser from start; end call at first k consecutive prints below running max by > tol. Returns (dated month, call date, revisions, first_call_month, first_call_date)."""
    seg=ser[(ser.index.to_period("M")>=P(start))&(ser.index.to_period("M")<=P(tr)+14)]
    runmax=-9; pk=None; below=0; call=None; calls=[]
    for m,v in seg.items():
        if v>runmax+1e-12:
            if call is not None: calls[-1]["superseded"]=True
            runmax=v; pk=m; below=0; call=None
        else:
            if v<runmax-tol-1e-12: below+=1
            else: below=0
            if below>=k and call is None:
                call=dict(dated=str(pk.to_period("M")), call=V.loc[m], superseded=False); calls.append(call)
    if not calls: return None
    f=calls[0]; l=calls[-1]
    return dict(dated=l["dated"], err=(P(l["dated"])-P(tr)).n, call_lag=(l["call"].to_period("M")-P(tr)).n, call=str(l["call"].date()), revisions=len(calls)-1, first_call=str(f["call"].date()), first_dated=f["dated"])
rules={"Bristow: first decline of S":("S12",0.0,1),"S: two consecutive declines":("S12",0.0,2),"S: decline > 0.10 below max":("S12",0.10,1),"S: decline > 0.05 below max":("S12",0.05,1),
       "dS3 (3-mo change of S): first decline":("dS3",0.0,1),"dS3: two declines":("dS3",0.0,2),"du3 (3-mo change of u3): first decline":("du3",0.0,1),"du3: two declines":("du3",0.0,2),
       "S6 (6-mo lookback): first decline":("S6",0.0,1)}
out=[]
for name,(st,tol,k) in rules.items():
    rows=[run_end(stats[st], starts[pk], tr, None, tol, k) for pk,tr in nber]
    errs=[r["err"] for r in rows]; lags=[r["call_lag"] for r in rows]; rev=sum(r["revisions"] for r in rows)
    out.append(dict(rule=name, errors=errs, abs_err_mean=round(np.mean(np.abs(errs)),2), within2=sum(abs(e)<=2 for e in errs), exact=sum(e==0 for e in errs), call_lags=lags, lag_median=np.median(lags), lag_mean=round(np.mean(lags),2), revisions=rev))
R=pd.DataFrame(out); pd.set_option("display.width",300); pd.set_option("display.max_colwidth",80)
print(R.to_string())
# detail for dS3 first decline
print("\nDetail dS3 first decline:"); [print(pk, run_end(stats["dS3"], starts[pk], tr, None, 0.0, 1)) for pk,tr in nber]
print("\nDetail S two declines:"); [print(pk, run_end(stats["S12"], starts[pk], tr, None, 0.0, 2)) for pk,tr in nber]
