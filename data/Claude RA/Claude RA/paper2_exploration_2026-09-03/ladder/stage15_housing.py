exec(open("stage14_sent_autos.py").read().split("base=[")[0])
A=ODD+"onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/"
def fpch(fn, h):
    df=pd.read_csv(A+fn, index_col=0, parse_dates=True); out={}
    for c in df.columns:
        s=df[c].dropna(); m=s.index[-1]
        if m in out or len(s)<h+1: continue
        out[m]=(pd.to_datetime(c[-8:]), s.iloc[-1]/s.iloc[-1-h]-1)
    idx=[v[0] for v in out.values()]; val=[v[1] for v in out.values()]
    return pd.Series(val, index=pd.to_datetime(idx)).sort_index()
h3=fpch("HOUST_all_vintages.csv",3); p3=fpch("PERMIT_all_vintages.csv",3); ip1=fpch("INDPRO_all_vintages.csv",1); ip2=fpch("INDPRO_all_vintages.csv",2)
CH={f"houst_d3_{x}": D(h3<=-x/100) for x in [15,20,25,30]}
CH.update({f"permit_d3_{x}": D(p3<=-x/100) for x in [15,20,25,30]})
CH.update({f"ip_d2_{x}": D(ip2<=-x/100) for x in [1.0,1.5,2.0]})
base=[SAHM[0.35], IC["ic8_30_k1"], PAY, UM["um_d1_10"]]
rows=[]
for nm,ch in list(CH.items())+[("none",None)]:
    eps=replay3(base+([ch] if ch is not None else []), GATE[12], 120)
    res,false=score_eps(eps,T_P1); L=[r["lag"] for r in res]
    rows.append(dict(extra=nm, misses=sum(l is None for l in L), n_false=len(false), false=false[:5], lags=L, onsets=[r["onset"] for r in res]))
df=pd.DataFrame(rows); pd.set_option("display.width",330); pd.set_option("display.max_colwidth",140); print(df.drop(columns=["onsets"]).to_string())
print("\n=== housing with 2-month persistence ===")
def persist2(s, x):
    c=(s<=-x/100); return D(c & c.shift(1).fillna(False))
CH2={f"houst_d3_{x}_k2": persist2(h3,x) for x in [15,20,25]}
CH2.update({f"houst_d3_{x}_k2_and_ip": persist2(h3,x) for x in [20]})
rows=[]
for nm,ch in CH2.items():
    eps=replay3(base+[ch], GATE[12], 120); res,false=score_eps(eps,T_P1); L=[r["lag"] for r in res]
    rows.append(dict(extra=nm, misses=sum(l is None for l in L), n_false=len(false), false=false[:5], lags=L, onsets=[r["onset"] for r in res], end=[r["end_lag"] for r in res], tr=[r["tr_err"] for r in res]))
df=pd.DataFrame(rows); print(df.drop(columns=["onsets"]).to_string()); 
for _,r in df.iterrows(): print(r.extra, r.onsets)
print("housing d3 first prints 1979:", {str(k.date()):round(v,3) for k,v in h3.loc["1979-01":"1979-06"].items()})
print("housing d3 first prints 1981:", {str(k.date()):round(v,3) for k,v in h3.loc["1981-05":"1981-11"].items()})
print("housing d3 first prints 1980:", {str(k.date()):round(v,3) for k,v in h3.loc["1980-02":"1980-07"].items()})
