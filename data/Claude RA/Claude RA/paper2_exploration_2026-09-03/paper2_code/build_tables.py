"""Paper 2 tables. Real-time protocol = Hall & Bristow (2026) App. A.2 read release by release on ALFRED first prints:
 * crossing episode = maximal run of first-print months with S >= 0.50; onset call = release of the run's first month;
 * Bristow end = month of the maximum first-print S inside the run's window (run + 12 months), confirmed at the first
   later release that prints below the running maximum; revised if a later print inside the window exceeds it.
No NBER date is an input to any call; NBER dates and announcement dates (nber.org, verified 3 Sep 2026) are comparators."""
import pandas as pd, numpy as np, json, os
HOME=os.path.expanduser("~"); MNT = HOME+"/mnt" if os.path.isdir(HOME+"/mnt/Recession Papers") else HOME+"/Projects"
D = MNT+"/Recession Papers/Paper 2/data/"
rt=pd.read_csv(D+"realtime_first_print_sahm_by_vintage.csv", parse_dates=["vintage","latest_month"])
first=rt.sort_values("vintage").drop_duplicates("latest_month", keep="first").set_index("latest_month").sort_index()
S=first["S_latest"]; V=first["vintage"]; THR=0.50-1e-9
P=lambda s: pd.Period(s,"M"); M=lambda ts: str(ts.to_period("M")); mdiff=lambda d,m:(pd.Timestamp(d).to_period("M")-P(m)).n
nber=[("1960-04","1961-02"),("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
      ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
ann={"1980-01":"1980-06-03","1980-07":"1981-07-08","1981-07":"1982-01-06","1982-11":"1983-07-08","1990-07":"1991-04-25",
     "1991-03":"1992-12-22","2001-03":"2001-11-26","2001-11":"2003-07-17","2007-12":"2008-12-01","2009-06":"2010-09-20",
     "2020-02":"2020-06-08","2020-04":"2021-07-19"}
# maximal runs
above=S>=THR; idx=list(S.index); runs=[]; i=0
while i<len(idx):
    if above.iloc[i]:
        j=i
        while j+1<len(idx) and above.iloc[j+1]: j+=1
        runs.append((idx[i],idx[j])); i=j+1
    else: i+=1
eps=[]
for k,(a,b) in enumerate(runs):
    win_end=b.to_period("M")+12
    if k+1<len(runs): win_end=min(win_end, runs[k+1][0].to_period("M")-1)   # a window closes when the next run begins
    seg=first[(first.index>=a)&(first.index.to_period("M")<=win_end)]
    runmax=-9; pk=None; calls=[]; opn=None
    for m,r in seg.iterrows():
        sv=r.S_latest
        if sv>runmax+1e-12:
            runmax=sv; pk=m
            if opn is not None: calls[-1]["superseded_release"]=str(r.vintage.date()); calls[-1]["superseded_by"]=M(m); opn=None
        elif opn is None and sv<runmax-1e-12:
            opn=dict(end_month=M(pk), end_S=round(runmax,2), call_release=str(r.vintage.date()), first_decline_month=M(m)); calls.append(opn)
    eps.append(dict(run_start=M(a), run_end=M(b), run_len=(b.to_period("M")-a.to_period("M")).n+1, first_S=round(S.loc[a],2),
                    onset_call=str(V.loc[a].date()), dated_peak=str(a.to_period("M")-4), calls=calls,
                    final_end_month=calls[-1]["end_month"] if calls else None, final_end_S=calls[-1]["end_S"] if calls else None,
                    final_end_call=calls[-1]["call_release"] if calls else None, revisions=len(calls)-1 if calls else 0))
json.dump(eps, open(D+"protocolA_episodes.json","w"), indent=1)
E=pd.DataFrame([{k:v for k,v in e.items() if k!="calls"} for e in eps]); E.to_csv(D+"table_protocolA_episodes.csv", index=False)
print(E.to_string())
print("\nREVISED END CALLS:"); [print(" ",e["run_start"], c) for e in eps for c in e["calls"][:-1]]
# comparator table: one row per NBER recession, matching runs that begin between peak-2 and trough+12
rows=[]
for pk,tr in nber:
    match=[e for e in eps if P(pk)-2<=P(e["run_start"])<=P(tr)+12 and not (P(e["run_start"])>P(tr)+3 and e["run_len"]<=2)]
    f=match[0]; main=max(match,key=lambda e:e["run_len"])
    rows.append(dict(nber_peak=pk, nber_trough=tr, nber_peak_announced=ann.get(pk), nber_peak_months=mdiff(ann[pk],pk) if pk in ann else None,
        nber_trough_announced=ann.get(tr), nber_trough_months=mdiff(ann[tr],tr) if tr in ann else None,
        first_onset_call=f["onset_call"], first_onset_months=mdiff(f["onset_call"],pk), first_cross_month=f["run_start"], first_cross_S=f["first_S"],
        sustained_onset_call=main["onset_call"], sustained_onset_months=mdiff(main["onset_call"],pk), sustained_cross_month=main["run_start"],
        dated_peak_rt=main["dated_peak"], dated_peak_err=(P(main["dated_peak"])-P(pk)).n,
        bristow_end_month=main["final_end_month"], bristow_end_S=main["final_end_S"], end_call=main["final_end_call"], end_call_months=mdiff(main["final_end_call"],tr),
        dated_trough_err=(P(main["final_end_month"])-P(tr)).n, end_revisions=main["revisions"], n_runs_matched=len(match),
        false_end_call=(f["final_end_call"] if f is not main else None), false_end_month=(f["final_end_month"] if f is not main else None)))
C=pd.DataFrame(rows); C.to_csv(D+"table_comparison_nber_vs_rules.csv", index=False)
pd.set_option("display.width",320); pd.set_option("display.max_columns",60)
print("\n"+C.to_string())
six=C.dropna(subset=["nber_peak_months"])
print("\nSIX: peaks NBER", six.nber_peak_months.tolist(), "median",six.nber_peak_months.median(),"mean",round(six.nber_peak_months.mean(),2),
      "| rule first", six.first_onset_months.tolist(), "median", six.first_onset_months.median(), "mean", round(six.first_onset_months.mean(),2))
print("SIX: troughs NBER", six.nber_trough_months.tolist(), "median",six.nber_trough_months.median(),"mean",round(six.nber_trough_months.mean(),2),
      "| rule", six.end_call_months.tolist(), "median", six.end_call_months.median(), "mean", round(six.end_call_months.mean(),2))
print("NINE: first onset", C.first_onset_months.tolist(), "median", C.first_onset_months.median(), "| sustained", C.sustained_onset_months.tolist(), "median", C.sustained_onset_months.median())
print("NINE: end call", C.end_call_months.tolist(), "median", C.end_call_months.median(), "| dated peak err", C.dated_peak_err.tolist(), "| dated trough err", C.dated_trough_err.tolist())
un=[e for e in eps if not any(P(pk)-2<=P(e["run_start"])<=P(tr)+12 for pk,tr in nber)]
print("\nRUNS OUTSIDE ANY NBER RECESSION (+12m):", [(e["run_start"],e["run_end"],e["first_S"],e["onset_call"],e["final_end_month"],e["final_end_call"]) for e in un])
