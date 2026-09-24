"""Stage 21a: the December-1973 hunt. Target now +-1 month at every onset with zero false alarms. 1974 is the binding case:
the call must come from a release dated Oct-Dec 1973. Scan every ALFRED-vintage series with vintages by Nov 1973 (first prints),
every simple deterioration statistic, and report any signal that (i) fires on a release in Oct-Dec 1973 and (ii) has zero false-alarm
runs 1968-2026 under the 12-month curve gate. Also the weekly claims/IUR family."""
from harness import *
import warnings; warnings.filterwarnings("ignore")
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
        out[m]=dict(rel=rel, d1=s.iloc[-1]/s.iloc[-2]-1, d2=s.iloc[-1]/s.iloc[-3]-1, d3=s.iloc[-1]/s.iloc[-4]-1, d6=s.iloc[-1]/s.iloc[-7]-1,
                    dd6=s.iloc[-1]/s.iloc[-7:].max()-1, dd12=s.iloc[-1]/s.iloc[-13:].max()-1, lvl1=s.iloc[-1]-s.iloc[-2], lvl3=s.iloc[-1]-s.iloc[-4], up12=s.iloc[-1]-s.iloc[-13:].min(), up6=s.iloc[-1]-s.iloc[-7:].min())
    return pd.DataFrame(out).T.sort_index()
SER="AWHMAN AWOTMAN CE16OV CLF16OV DMANEMP HOUST HOUST1F INDPRO MANEMP NDMANEMP PAYEMS PI UEMPMEAN UNRATE USCONS USFIRE USGOVT USMINE USPRIV USSERV USTPU USTRADE USWTRADE SRVPRD".split()
hits=[]
for sid in SER:
    try: t=fp(sid+"_all_vintages.csv")
    except Exception as e: print(sid,"skip",e); continue
    rel=pd.to_datetime(t.rel.values)
    for stat in ["d1","d2","d3","d6","dd6","dd12","lvl1","lvl3","up12","up6"]:
        x=t[stat].astype(float)
        qs=[-0.002,-0.003,-0.005,-0.0075,-0.01,-0.015,-0.02,-0.03,-0.05,-0.08,-0.12] if stat in ("d1","d2","d3","d6","dd6","dd12") else [-0.2,-0.3,-0.5,-1,-2,0.2,0.3,0.5,1,2,5,10]
        for q in qs:
            cond=(x<=q) if q<0 else (x>=q)
            if cond.sum()<3 or cond.mean()>0.5: continue
            s=pd.Series(cond.values, index=rel).sort_index()
            w=s[(s.index>="1973-10-01")&(s.index<="1973-12-31")]
            if not w.any(): continue
            sig=s & gate.reindex(s.index, method="ffill").fillna(False)
            r=score(sig, f"{sid} {stat} {'<=' if q<0 else '>='} {q} [gate12]", start="1968-06-01", gap_days=45)
            r["dec73_fire"]=str(w[w].index[0].date()); hits.append(r)
df=pd.DataFrame(hits); pd.set_option("display.width",330); pd.set_option("display.max_colwidth",100); pd.set_option("display.max_rows",400)
print("=== signals firing on a release in Oct-Dec 1973, sorted by false alarms then misses ===")
print(df.sort_values(["n_fa","misses"]).drop(columns=["calls","fa"]).head(60).to_string())
z=df[df.n_fa==0]
print("\nZERO false alarms among them:", len(z))
for _,r in z.iterrows(): print("  ", r.rule, "| fires", r.dec73_fire, "| lags", r.lags, "| misses", r.misses, "| calls", r.calls)
# ---- weekly family ----
ic=load(ODD+"01_labor_unemployment/weekly/ICSA.csv"); cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv"); iur=load(ODD+"01_labor_unemployment/weekly/IURSA.csv")
def wk(sig, lag): s=sig.copy(); s.index=s.index+pd.Timedelta(days=lag); return s
W={}
for n in [4,6,8,13]:
    m=ic.rolling(n).mean()
    for p in [0.10,0.15,0.20,0.25,0.30]: W[f"IC ma{n} vs 52wk min>={p}"]=wk(m/m.shift(1).rolling(52).min()-1>=p, 5)
    m=cc.rolling(n).mean()
    for p in [0.10,0.15,0.20,0.25,0.30]: W[f"CC ma{n} vs 52wk min>={p}"]=wk(m/m.shift(1).rolling(52).min()-1>=p, 12)
    m=iur.rolling(n).mean()
    for g in [0.10,0.15,0.20,0.25,0.30]: W[f"IUR ma{n} gap>={g}"]=wk(m-m.shift(1).rolling(52).min()>=g-1e-12, 12)
rows=[]
for nm,s in W.items():
    w=s[(s.index>="1973-10-01")&(s.index<="1973-12-31")]
    sig=s & gate.reindex(s.index, method="ffill").fillna(False)
    r=score(sig, nm, start="1968-06-01", gap_days=45); r["dec73_fire"]=str(w[w].index[0].date()) if w.any() else None; rows.append(r)
dw=pd.DataFrame(rows)
print("\n=== weekly family: fires by Dec 1973? / false alarms / lags ===")
print(dw.sort_values(["n_fa","misses"]).drop(columns=["calls","fa"]).to_string())
