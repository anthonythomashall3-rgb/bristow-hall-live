"""Real-time replay of the Sahm Rule (onset) and the Bristow Rule (end) on ALFRED vintages of UNRATE.
Every vintage column UNRATE_YYYYMMDD is the unemployment-rate series exactly as it stood on that release date.
Conventions follow Hall & Bristow (2026), Appendix A.2:
  S(t) = mean(u[t-2..t]) - min_{k=1..12} mean(u[t-k-2..t-k]);  signal when S(t) >= 0.50.
  Bristow end = month of the maximum of S after the crossing; confirmed when the first decline prints.
"""
import pandas as pd, numpy as np, json, sys, os
HOME=os.path.expanduser("~")
MNT = HOME+"/mnt" if os.path.isdir(HOME+"/mnt/Onset Detector Data") else HOME+"/Projects"
SRC = MNT+"/Onset Detector Data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/UNRATE_all_vintages.csv"
OUT = MNT+"/Recession Papers/Paper 2/data/"
df = pd.read_csv(SRC, index_col=0, parse_dates=True)
vintages = [c for c in df.columns]
vdates = pd.to_datetime([c.split("_")[1] for c in vintages], format="%Y%m%d")

def sahm(u):
    m3 = u.rolling(3).mean()
    prior_min = m3.shift(1).rolling(12).min()
    return m3 - prior_min

# For each vintage: latest published month and its S value (first print), plus S for the previous month within the same vintage
rows = []
for col, vd in zip(vintages, vdates):
    u = df[col].dropna()
    if len(u) < 16: continue
    s = sahm(u)
    t = u.index[-1]
    rows.append(dict(vintage=vd, latest_month=t, u_latest=u.iloc[-1], S_latest=s.iloc[-1], S_prev_same_vintage=s.iloc[-2],
                     month_prev=u.index[-2]))
rt = pd.DataFrame(rows).set_index("vintage")
rt["S_latest_r"] = rt["S_latest"].round(2)
rt.to_csv(OUT+"realtime_first_print_sahm_by_vintage.csv")

# --- cross-check against FRED SAHMREALTIME (first-print series) ---
fred = pd.read_csv(MNT+"/Onset Detector Data/22_recession_chronologies/rules/SAHMREALTIME.csv", parse_dates=[0]).set_index("date")["value"]
# keep the first vintage that publishes each month (some months have >1 vintage, e.g. re-releases)
first = rt.reset_index().sort_values("vintage").drop_duplicates("latest_month", keep="first").set_index("latest_month")
cmp = pd.concat([first["S_latest"].round(2).rename("replay"), fred.rename("fred")], axis=1).dropna()
diff = cmp[(cmp.replay - cmp.fred).abs() > 0.005]
print("Months compared vs FRED SAHMREALTIME:", len(cmp), " mismatches (>0.005):", len(diff))
print(diff.head(30))

# --- NBER chronology (verified from nber.org 2026-09-03) ---
nber = [("1960-04","1961-02"),("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
        ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
ann = {"1980-01":"1980-06-03","1980-07":"1981-07-08","1981-07":"1982-01-06","1982-11":"1983-07-08","1990-07":"1991-04-25",
       "1991-03":"1992-12-22","2001-03":"2001-11-26","2001-11":"2003-07-17","2007-12":"2008-12-01","2009-06":"2010-09-20",
       "2020-02":"2020-06-08","2020-04":"2021-07-19"}

first = first.sort_index()
res = []
for pk, tr in nber:
    pk_m = pd.Period(pk, "M"); tr_m = pd.Period(tr, "M")
    # window: from peak month through trough + 12 months (real-time; we look for the first crossing after the peak)
    win = first[(first.index.to_period("M") >= pk_m) & (first.index.to_period("M") <= (tr_m + 12))]
    cross = win[win["S_latest"] >= 0.50 - 1e-9]
    if cross.empty:
        res.append(dict(peak=pk, trough=tr, note="no real-time crossing")); continue
    c0 = cross.iloc[0]; c0_month = cross.index[0]
    # onset call: release date of first crossing
    onset_call = c0["vintage"]
    # Bristow: track running max of first-print S from crossing month; end call at first release where S_latest < running max
    seg = first[first.index >= c0_month]
    runmax = -9; peak_month = None; end_call = None; end_S = None; recalls = []
    for m, r in seg.iterrows():
        sv = r["S_latest"]
        if sv > runmax + 1e-12:
            if end_call is not None:
                recalls.append(dict(new_peak_month=str(m.to_period('M')), release=str(r['vintage'].date()), S=round(sv,2)))
            runmax = sv; peak_month = m; end_call = None
        elif end_call is None and sv < runmax - 1e-12:
            end_call = r["vintage"]; end_S = runmax
        # stop scanning 12 months after S has fallen back below 0.5 for good
        if end_call is not None and (m.to_period("M") - peak_month.to_period("M")).n >= 14: break
    # also the same-vintage confirmation: first release whose own series shows S(t) < S(t-1) after the crossing
    seg2 = first[first.index > c0_month]
    conf_same = None
    for m, r in seg2.iterrows():
        if r["S_latest"] < r["S_prev_same_vintage"] - 1e-12:
            conf_same = (m, r["vintage"]); break
    res.append(dict(peak=pk, trough=tr,
        first_cross_month=str(c0_month.to_period("M")), first_cross_S=round(c0["S_latest"],2), onset_call_date=str(onset_call.date()),
        onset_lag_days=(onset_call - pk_m.to_timestamp()).days, onset_lag_months=(onset_call.to_period("M") - pk_m).n,
        bristow_peak_month=str(peak_month.to_period("M")), bristow_peak_S=round(runmax,2),
        end_call_date=str(end_call.date()) if end_call is not None else None,
        end_lag_months_vs_trough=(end_call.to_period("M") - tr_m).n if end_call is not None else None,
        end_lag_days_vs_trough=(end_call - tr_m.to_timestamp()).days if end_call is not None else None,
        bristow_minus_nber_trough_months=(peak_month.to_period("M") - tr_m).n,
        same_vintage_first_decline_month=str(conf_same[0].to_period("M")) if conf_same else None,
        same_vintage_first_decline_release=str(conf_same[1].date()) if conf_same else None,
        recalls=recalls,
        nber_peak_announced=ann.get(pk), nber_trough_announced=ann.get(tr)))
out = pd.DataFrame(res)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
print(out.drop(columns=["recalls"]).to_string())
print("RECALLS:", [(r["peak"], r["recalls"]) for r in res if r.get("recalls")])
out.to_csv(OUT+"replay_results_sahm_onset_bristow_end.csv", index=False)
json.dump(res, open(OUT+"replay_results.json","w"), indent=1, default=str)
