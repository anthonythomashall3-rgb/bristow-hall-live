"""2020 real-time comparison of three onset indicators on ALFRED vintages pulled through the FRED API
(key read from the lab's local.env; never printed). Writes data/replay_2020_three_indicators.csv.
Sahm: S >= 0.50 on UNRATE first prints. Michez (Michaillat & Saez 2025): m = min(u_hat, v_hat) > 0.29 with
u at basis-point precision (UNEMPLOY/CLF16OV) and openings assigned to the following month (their dashboard convention);
also reported on the published one-decimal rate and with same-month openings. SOS (O'Trakoun & Scavette 2025):
26-week mean of IURSA minus its minimum over the 52 preceding weeks, > 0.20, on IURSA vintages."""
import os,re,json,urllib.request,pandas as pd
HOME=os.path.expanduser("~"); MNT = HOME+"/mnt" if os.path.isdir(HOME+"/mnt/Recession Papers") else HOME+"/Projects"
env=open(MNT+"/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env").read()
key=re.search(r'FRED_API_KEY\s*=\s*"?([A-Za-z0-9]+)"?', env).group(1)
OUT=MNT+"/Recession Papers/Paper 2/data/"
def vint(sid, rt, start="2017-01-01"):
    url=f"https://api.stlouisfed.org/fred/series/observations?series_id={sid}&realtime_start={rt}&realtime_end={rt}&observation_start={start}&api_key={key}&file_type=json"
    d=json.load(urllib.request.urlopen(url,timeout=60))
    s=pd.Series({o["date"]:float(o["value"]) for o in d["observations"] if o["value"]!="."}); s.index=pd.to_datetime(s.index); return s
rows=[]
def uhat(u): m3=u.rolling(3).mean(); return m3-m3.shift(1).rolling(12).min()
def vhat(op,lf,shift):
    ops=op.shift(shift,freq="MS") if shift else op
    vr=(ops/lf.reindex(ops.index)*100).dropna(); v3=vr.rolling(3).mean(); return v3.shift(1).rolling(12).max()-v3
for rt in ["2020-03-06","2020-04-03","2020-04-07","2020-05-08","2020-05-15","2020-06-05","2020-06-09"]:
    ur,un,lf,op=[vint(s,rt) for s in ["UNRATE","UNEMPLOY","CLF16OV","JTSJOL"]]
    ubp=un/lf*100
    for month in ur.index[-2:]:
        r=dict(release=rt, indicator="Sahm/Michez inputs", month=str(month.date())[:7], latest_cps_month=str(ur.index[-1].date())[:7], latest_jolts_month=str(op.index[-1].date())[:7],
               u_published=ur.loc[month], sahm_S=round(uhat(ur).loc[month],3), u_hat_bp=round(uhat(ubp).loc[month],3))
        for sh,lab in [(1,"v_hat_lagged_openings"),(0,"v_hat_same_month_openings")]:
            vh=vhat(op,lf,sh); r[lab]=round(vh.loc[month],3) if month in vh.index and pd.notna(vh.loc[month]) else None
        r["michez_m_dashboard_convention"]=round(min(r["u_hat_bp"], r["v_hat_lagged_openings"]),3) if r["v_hat_lagged_openings"] is not None else None
        rows.append(r)
def sos(x): ma=x.rolling(26).mean(); return ma-ma.shift(1).rolling(52).min()
for rt in ["2020-03-26","2020-04-02","2020-04-09","2020-04-16","2020-04-23"]:
    s=vint("IURSA",rt); v=sos(s)
    rows.append(dict(release=rt, indicator="SOS", month=str(s.index[-1].date()), latest_week=str(s.index[-1].date()), iur_latest=s.iloc[-1], sos_latest=round(v.iloc[-1],3)))
df=pd.DataFrame(rows); df.to_csv(OUT+"replay_2020_three_indicators.csv", index=False)
pd.set_option("display.width",300); pd.set_option("display.max_columns",30); print(df.to_string())
