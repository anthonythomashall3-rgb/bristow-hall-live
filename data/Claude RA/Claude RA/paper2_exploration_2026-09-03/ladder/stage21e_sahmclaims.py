"""Stage 21e: the Sahm channel with a layoff confirmation (Michez logic with claims instead of vacancies; answers Sahm's own
labor-supply objection): Sahm first print >= 0.35 AND, on the release day, the 4-week average of initial claims >= x above its
52-week minimum (claims known +5 days)."""
exec(open("stage19b_iur.py").read().split("base=[SAHM[0.35]")[0])
r4d=pd.Series(r4.values, index=r4.index+pd.Timedelta(days=5)).reindex(cal).ffill().values
r8d=pd.Series(r8.values, index=r8.index+pd.Timedelta(days=5)).reindex(cal).ffill().values
g4d=(iur4-iur4.shift(1).rolling(52).min()); g4d=pd.Series(g4d.values, index=g4d.index+pd.Timedelta(days=12)).reindex(cal).ffill().values
for rel in ["1969-10-06","1969-11-07","1969-12-05","2008-01-04","2024-05-03","2024-06-07","2024-07-05","1976-12-03","2003-05-02","1980-04-04","1990-11-02","2001-06-01","1974-04-05","1981-11-06","2020-04-03"]:
    i=int(np.where(cal==pd.Timestamp(rel))[0][0]); print(f"  {rel}: S={Srel.get(pd.Timestamp(rel),np.nan):.2f} r4={r4d[i]:.3f} r8={r8d[i]:.3f} IURgap={g4d[i]:.3f}")
def sahm_conf(th, conf, x):
    a=SAHM[th].copy(); c={"r4":r4d,"r8":r8d,"iur":g4d}[conf]
    return a & (c>=x)
rows=[]
for conf in ["r4","r8","iur"]:
    for x in ([0.05,0.08,0.10,0.12,0.15,0.20] if conf!="iur" else [0.05,0.10,0.15,0.20]):
        for th in [0.35,0.30]:
            chs=[sahm_conf(th,conf,x), gapch(iur4,0.35), IC["ic8_30_k1"], PAY, UM["um_d1_10"], HOU]
            eps=replay3(chs, GATE[12], 120); res,false=score_eps(eps,T_P1); L=[r["lag"] for r in res]
            rows.append(dict(rule=f"Sahm{th} & {conf}>={x} | IUR35 | claims | pay | sent | hou", n_false=len(false), false=false[:3], lags=L, out1=sum(1 for l in L if l is None or abs(l)>1), onsets=[r["onset"] for r in res]))
df=pd.DataFrame(rows); pd.set_option("display.width",330); pd.set_option("display.max_colwidth",150)
print(df.sort_values(["n_false","out1"]).drop(columns=["onsets"]).to_string())
for _,r in df.sort_values(["n_false","out1"]).head(6).iterrows(): print(r.rule, r.onsets)
# no-gate check for the best Sahm+claims channel alone: does the confirmation remove Sahm's own false alarms without the curve gate?
for x in [0.10,0.12,0.15]:
    a=sahm_conf(0.35,"r4",x); sc=score(pd.Series(a,index=cal), f"Sahm0.35 & r4>={x} NO GATE", start="1968-06-01"); print(sc["rule"], "false alarms", sc["n_fa"], sc["fa"], "lags", sc["lags"])
    a=sahm_conf(0.50,"r4",x) if 0.50 in SAHM else None
sc=score(pd.Series(SAHM[0.35],index=cal), "Sahm0.35 NO GATE", start="1968-06-01"); print(sc["rule"], "false alarms", sc["n_fa"], sc["fa"][:8])
sc=score(pd.Series(SAHM[0.50]&(r4d>=0.10),index=cal), "Sahm0.50 & r4>=0.10 NO GATE", start="1968-06-01"); print(sc["rule"], "false alarms", sc["n_fa"], sc["fa"][:8], "lags", sc["lags"])
