"""Channel zoo: every monthly ALFRED-vintage series in the corpus, first prints, simple deterioration signals, scored standalone
(with and without the 12-month curve gate). Purpose: find which channels are fast in 1980 and 1981 without false alarms."""
from harness import *
import warnings, sys; warnings.filterwarnings("ignore")
A=ODD+"onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/"
d10=load(ODD+"06_interest_rates_yield_curve/daily/DGS10.csv"); d1=load(ODD+"06_interest_rates_yield_curve/daily/DGS1.csv")
curve=(d10-d1.reindex(d10.index)).dropna(); gate=((curve<0).rolling(12*21).max()==1)
def fp(fn):
    df=pd.read_csv(A+fn, index_col=0, parse_dates=True); out={}
    for c in df.columns:
        s=df[c].dropna()
        if len(s)<14: continue
        m=s.index[-1]
        if m in out: continue
        rel=pd.to_datetime(c[-8:])
        out[m]=dict(rel=rel, d1=s.iloc[-1]/s.iloc[-2]-1, d3=s.iloc[-1]/s.iloc[-4]-1, d6=s.iloc[-1]/s.iloc[-7]-1,
                    dd12=s.iloc[-1]/s.iloc[-13:].max()-1, lvl1=s.iloc[-1]-s.iloc[-2], lvl3=s.iloc[-1]-s.iloc[-4], up12=s.iloc[-1]-s.iloc[-13:].min())
    return pd.DataFrame(out).T.sort_index()
series=sys.argv[1].split(",")
R=[]
for sid in series:
    try: t=fp(sid+"_all_vintages.csv")
    except Exception as e: print(sid,"skip",e); continue
    rel=pd.to_datetime(t.rel.values)
    for stat in ["d1","d3","d6","dd12","lvl1","lvl3","up12"]:
        x=t[stat].astype(float)
        qs=[-0.003,-0.005,-0.01,-0.02,-0.03,-0.05,-0.08] if stat in ("d1","d3","d6","dd12") else [-0.3,-0.5,-1,-2,0.3,0.5,1,2,5,10]
        for q in qs:
            cond=(x<=q) if q<0 else (x>=q)
            if cond.sum()<5 or cond.mean()>0.5: continue
            s=pd.Series(cond.values, index=rel).sort_index()
            for gname,sig in [("nogate",s),("gate12", s & gate.reindex(s.index, method="ffill").fillna(False))]:
                r=score(sig, f"{sid} {stat} {'<=' if q<0 else '>='} {q} [{gname}]", gap_days=45)
                r["sid"]=sid; R.append(r)
df=pd.DataFrame(R); df.to_csv(f"stage10_zoo_{series[0]}.csv", index=False)
d=df[df.misses<=1].copy()
pd.set_option("display.width",330); pd.set_option("display.max_colwidth",120)
best=d.sort_values(["n_fa","max_lag"]).groupby("sid").head(2)
print(best[["rule","n_episodes_covered","misses","lags","max_lag","n_fa","fa"]].to_string())
# 1980 and 1981 fast catchers: lags index positions depend on coverage; print calls for rules with any lag<=2 at 1980/1981
for r in R:
    c=r["calls"]
    try:
        i80=[i for i,(pk,tr) in enumerate(EP) if pk=="1980-01"][0]; i81=i80+1
        if r["n_fa"]<=2 and c[i80] not in ("-","MISS") and c[i81] not in ("-","MISS"):
            l80=(pd.Timestamp(c[i80]).to_period("M")-P("1980-01")).n; l81=(pd.Timestamp(c[i81]).to_period("M")-P("1981-07")).n
            if l80<=2 or l81<=2: print("FAST 80/81:", r["rule"], "1980:", c[i80], l80, "1981:", c[i81], l81, "fa", r["n_fa"], "misses", r["misses"])
    except Exception: pass
