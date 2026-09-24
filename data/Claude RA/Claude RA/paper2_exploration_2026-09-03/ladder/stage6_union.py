from harness import *
import warnings; warnings.filterwarnings("ignore")
# --- inputs ---
d10=load(ODD+"06_interest_rates_yield_curve/daily/DGS10.csv"); d1=load(ODD+"06_interest_rates_yield_curve/daily/DGS1.csv")
curve=(d10-d1.reindex(d10.index)).dropna(); gate_d=((curve<0).rolling(18*21).max()==1)
rt=pd.read_csv(HOME+"/mnt/Recession Papers/Paper 2/data/realtime_first_print_sahm_by_vintage.csv", parse_dates=["vintage","latest_month"])
f=rt.sort_values("vintage").drop_duplicates("latest_month", keep="first").set_index("latest_month").sort_index(); S=f.S_latest; V=f.vintage
ic=load(ODD+"01_labor_unemployment/weekly/ICSA.csv"); icr=ic.rolling(4).mean()/ic.rolling(4).mean().shift(1).rolling(52).min()-1
d=pd.read_csv(ODD+"onset-detector-new-2026-08-23/26_ui_claims_admin/eta_ar539.csv", usecols=["st","c2","c8"], parse_dates=["c2"]); d=d[~d.st.isin(["PR","VI"])]
cw=d.pivot_table(index="c2", columns="st", values="c8", aggfunc="sum").sort_index(); s8=cw.rolling(8).sum(); br=((s8/s8.shift(52)-1)>=0.10).sum(axis=1); breadth=(br>=25).rolling(4).sum()==4
# daily calendar
cal=pd.date_range("1963-01-01","2026-08-31",freq="D")
def daily(sig, lagdays=0):   # weekly/monthly signal known at date + lag
    s=sig.copy(); s.index=s.index+pd.Timedelta(days=lagdays); return s.reindex(cal).ffill().fillna(False).astype(bool)
G=gate_d.reindex(cal).ffill().fillna(False).astype(bool)
# monthly sahm signal must be re-evaluated each release: build as a series over release dates
def sahm_daily(th):
    s=pd.Series((S>=th-1e-9).values, index=pd.to_datetime(V.values)); return s.reindex(cal).ffill().fillna(False).astype(bool)
IC={p: daily(icr>=p, 5) for p in [0.15,0.20,0.25,0.30]}
BR=daily(breadth, 9)  # ETA 539 published ~9 days after week end
def evalsig(sig, name, start):
    start=pd.Timestamp(start); sig=sig[sig.index>=start]
    # new-signal rule: count as onset only if signal was off for >= 28 days before (kills tails of the previous episode)
    off28=(~sig).rolling(28).sum()==28
    new=sig & off28.shift(1).fillna(True)
    rows=[]; ok=True; lags=[]
    for pk,tr in EP:
        if P(pk).to_timestamp()<start: continue
        lo=(P(pk)-2).to_timestamp(); hi=(P(tr)+6).to_timestamp(how="end")
        w=new[(new.index>=lo)&(new.index<=hi)]; h=w[w].index
        # allow an already-on signal that started within the window too
        if len(h)==0:
            w2=sig[(sig.index>=lo)&(sig.index<=hi)]; h=w2[w2].index
        if len(h)==0: rows.append("MISS"); ok=False; continue
        lag=(h[0].to_period("M")-P(pk)).n; lags.append(lag); rows.append(f"{h[0].date()} ({lag:+d})")
        if abs(lag)>2: ok=False
    fa=[]
    for a in new[new].index:
        if not any((P(pk)-2).to_timestamp()<=a<=(P(tr)+12).to_timestamp(how="end") for pk,tr in EP): fa.append(str(a.date()))
    # merge fa dates into runs (45 days)
    fr=[]
    for x in fa:
        x=pd.Timestamp(x)
        if fr and (x-fr[-1][1]).days<=45: fr[-1][1]=x
        else: fr.append([x,x])
    return dict(rule=name, lags=lags, max_abs_lag=max(abs(l) for l in lags) if lags else None, n_fa=len(fr), fa=[(str(a.date()),str(b.date())) for a,b in fr][:6], calls=rows)
R=[]
for th in [0.30,0.35,0.40,0.45,0.50]:
    R.append(evalsig(G & sahm_daily(th), f"gate18 & Sahm>={th}", "1963-06-01"))
    for p in [0.20,0.25,0.30]:
        R.append(evalsig(G & (sahm_daily(th) | IC[p]), f"gate18 & (Sahm>={th} | IC4wk>={int(p*100)}%)", "1968-06-01"))
        R.append(evalsig(G & (sahm_daily(th) | IC[p] | BR), f"gate18 & (Sahm>={th} | IC4wk>={int(p*100)}% | stateCC breadth>=25)", "1987-06-01"))
    R.append(evalsig(G & (sahm_daily(th) | BR), f"gate18 & (Sahm>={th} | stateCC breadth>=25)", "1987-06-01"))
R.append(evalsig(G & BR, "gate18 & stateCC breadth>=25", "1987-06-01"))
R.append(evalsig(BR, "stateCC breadth>=25 (no gate)", "1987-06-01"))
for p in [0.20,0.30]: R.append(evalsig(G & IC[p], f"gate18 & IC4wk>={int(p*100)}%", "1968-06-01"))
df=pd.DataFrame(R); pd.set_option("display.width",340); pd.set_option("display.max_colwidth",150); pd.set_option("display.max_rows",200)
print(df.drop(columns=["calls"]).to_string())
print("\nCALLS for selected:")
for r in R:
    if r["n_fa"]<=1: print(r["rule"], r["calls"])
df.to_csv("stage6_union.csv", index=False)
