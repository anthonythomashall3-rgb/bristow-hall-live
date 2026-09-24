"""2007–09 real-time comparison of the three onset indicators.
SOS: first-print (advance, seasonally adjusted) national insured unemployment rate from the Department of Labor weekly news
releases (corpus file bristow-hall-harvest/data/dol_claims_press/national_iur_first_prints.csv, Oct 2002→); the indicator is
computed on the series of first prints (26-week mean less its minimum over the 52 preceding weeks, > 0.20).
Michez: JOLTS job openings as first published (corpus file Recession Papers/Claude RA/jolts_firstprints.csv, from the BLS
news-release archive, Feb 2004→), combined with UNRATE/UNEMPLOY/CLF16OV ALFRED vintages pulled through the FRED API at each
Employment Situation release date; openings assigned to the following month (authors' convention); u at basis-point precision.
Sahm: first-print S from the ALFRED UNRATE file. Writes data/replay_2008_three_indicators.csv and data/sos_first_print_series.csv."""
import os,re,json,urllib.request,pandas as pd,numpy as np
HOME=os.path.expanduser("~"); MNT = HOME+"/mnt" if os.path.isdir(HOME+"/mnt/Recession Papers") else HOME+"/Projects"
ODD=MNT+"/Onset Detector Data/"; RP=MNT+"/Recession Papers/"; OUT=RP+"Paper 2/data/"
env=open(ODD+"onset-detector-new-2026-08-23/live_data/config/local.env").read(); key=re.search(r'FRED_API_KEY\s*=\s*"?([A-Za-z0-9]+)"?', env).group(1)
def vint(sid, rt, start="2002-01-01"):
    url=f"https://api.stlouisfed.org/fred/series/observations?series_id={sid}&realtime_start={rt}&realtime_end={rt}&observation_start={start}&api_key={key}&file_type=json"
    d=json.load(urllib.request.urlopen(url,timeout=60)); s=pd.Series({o["date"]:float(o["value"]) for o in d["observations"] if o["value"]!="."}); s.index=pd.to_datetime(s.index); return s
# ---- SOS on first prints ----
d=pd.read_csv(ODD+"bristow-hall-harvest/data/dol_claims_press/national_iur_first_prints.csv", parse_dates=["obs_period","vintage_date"])
iur=d[d.series_id=="national_iur"].sort_values("obs_period").drop_duplicates("obs_period").set_index("obs_period")
s=iur["value"]; ma=s.rolling(26).mean(); sos=(ma-ma.shift(1).rolling(52).min())
S=pd.DataFrame(dict(iur_first_print=s, sos_first_print=sos.round(3), release=iur["vintage_date"])); S.to_csv(OUT+"sos_first_print_series.csv")
above=S[S.sos_first_print>0.20]
print("weeks with SOS>0.20 on first prints (first week of each run):")
prev=None
for w,r in above.iterrows():
    if prev is None or (w-prev).days>7: print("  ", w.date(), "SOS", r.sos_first_print, "IUR", r.iur_first_print, "released", r.release.date())
    prev=w
print("SOS first-print series starts", s.index.min().date(), "first computable SOS", sos.dropna().index.min().date())
print(S.loc["2007-11-01":"2008-06-30"].to_string())
# ---- Michez 2007-09 on JOLTS first prints + ALFRED labor-force vintages ----
j=pd.read_csv(RP+"Claude RA/jolts_firstprints.csv"); j["release_date"]=pd.to_datetime(j.release_date); j["ref"]=pd.to_datetime(j.ref_month)
jfp=j.set_index("ref")["openings_level_thousands"].sort_index()
ur_all=pd.read_csv(ODD+"onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/UNRATE_all_vintages.csv", index_col=0, parse_dates=True)
rel=[c for c in ur_all.columns if "2007" <= c[-8:-4] <= "2009"]
rows=[]
for c in rel:
    rt=pd.to_datetime(c[-8:]); ur=ur_all[c].dropna(); m=ur.index[-1]
    if m < pd.Timestamp("2007-06-01") or m > pd.Timestamp("2009-01-01"): continue
    un=vint("UNEMPLOY", rt.strftime("%Y-%m-%d")); lf=vint("CLF16OV", rt.strftime("%Y-%m-%d"))
    ubp=(un/lf*100); m3=ubp.rolling(3).mean(); uhat=(m3-m3.shift(1).rolling(12).min()).loc[m]
    m3p=ur.rolling(3).mean(); S_pub=(m3p-m3p.shift(1).rolling(12).min()).loc[m]
    # openings known on rt: first prints with release_date <= rt; month t uses openings of t-1
    jolts_rel=j[j.ref==(m-pd.DateOffset(months=1))].release_date.min()
    avail=max(rt, jolts_rel) if pd.notna(jolts_rel) else rt
    known=j[j.release_date<=avail].set_index("ref")["openings_level_thousands"].sort_index()
    ops=known.shift(1,freq="MS"); vr=(ops/lf.reindex(ops.index)*100).dropna(); v3=vr.rolling(3).mean(); vhat_s=v3.shift(1).rolling(12).max()-v3
    vhat=vhat_s.get(m, np.nan)
    rows.append(dict(cps_release=rt.date(), month=str(m.date())[:7], u_published=ur.loc[m], sahm_S=round(S_pub,3), u_hat_bp=round(uhat,3), v_hat_lagged=round(vhat,3) if pd.notna(vhat) else None,
                     michez_m=round(min(uhat,vhat),3) if pd.notna(vhat) else None, jolts_release_for_prev_month=jolts_rel.date() if pd.notna(jolts_rel) else None,
                     michez_available=avail.date()))
M=pd.DataFrame(rows); M.to_csv(OUT+"replay_2008_three_indicators.csv", index=False)
pd.set_option("display.width",250); print(M.to_string())
