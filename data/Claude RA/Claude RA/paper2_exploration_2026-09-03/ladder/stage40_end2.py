"""Stage 40: fast end + a second condition to block the mid-recession pauses. End = initial-claims 8wk avg falls x% below
its running peak AND a confirmer is also off its own peak. Confirmers: continued claims 4/8wk, IUR 4/8wk, share of states
whose 4wk claims are at a 26-week high, Sahm first print falling. Scored: withdrawn calls, trough error, lag in months/days."""
exec(open("stage39_ends.py").read().split("def peak_and_call")[0])
ic8=OBJ["IC ma8"]
CONF={"none":None,"CC ma4 off peak":OBJ["CC ma4"],"CC ma8 off peak":OBJ["CC ma8"],"IUR ma4 off peak":OBJ["IUR ma4"],"IUR ma8 off peak":OBJ["IUR ma8"],
      "state claims breadth off peak":OBJ["states claims at 26wk max"],"state IUR breadth off peak":OBJ["states IUR at 26wk max"]}
Sd=Srel.reindex(cal).ffill().values
def run_end(pct, conf, cpct, use_sahm=False):
    terr=[]; lagm=[]; lagd=[]; wd=0
    for e,tr in zip(V6eps,TR):
        i0=int(np.where(cal==e["onset"])[0][0]); i1=int(np.where(cal==e["close"])[0][0]) if e["close"] is not None else N-1
        runmax=-np.inf; pk=None; cmax=-np.inf; smax=-np.inf; called=None; calls=[]
        for i in range(i0,i1+1):
            v=ic8[i]
            if not np.isnan(v):
                if v>runmax:
                    if called is not None: calls.append([called,pk,True]); called=None
                    runmax=v; pk=i
            if conf is not None and not np.isnan(conf[i]): cmax=max(cmax,conf[i])
            if not np.isnan(Sd[i]): smax=max(smax,Sd[i])
            ok = (not np.isnan(v)) and pk is not None and v<=runmax*(1-pct)
            if conf is not None: ok = ok and (not np.isnan(conf[i])) and conf[i]<=cmax*(1-cpct)
            if use_sahm: ok = ok and (not np.isnan(Sd[i])) and Sd[i]<smax-1e-9
            if ok and called is None: called=i
        if called is not None: calls.append([called,pk,False])
        fin=[c for c in calls if not c[2]]; wd+=sum(1 for c in calls if c[2])
        c=fin[-1] if fin else (calls[-1] if calls else None)
        if c is None: terr.append(None); lagm.append(None); lagd.append(None); continue
        terr.append((cal[c[1]].to_period("M")-P(tr)).n); lagm.append((cal[c[0]].to_period("M")-P(tr)).n); lagd.append((cal[c[0]]-TE[tr]).days)
    L=[x for x in lagm if x is not None]
    return dict(exact=sum(1 for x in terr if x==0), tr_w1=sum(1 for x in terr if x is not None and abs(x)<=1), in_month=sum(1 for x in L if abs(x)<=1),
                in_week=sum(1 for x in lagd if x is not None and abs(x)<=7), withdrawn=wd, miss=sum(1 for x in lagm if x is None), trough_err=terr, lag_m=lagm, lag_d=lagd)
rows=[]
for pct in [0.005,0.01,0.02,0.03]:
    for cn,conf in CONF.items():
        for cpct in ([0.0] if conf is None else [0.0,0.01,0.02]):
            r=run_end(pct, conf, cpct); r.update(dict(ic_pct=pct, conf=cn, conf_pct=cpct)); rows.append(r)
    r=run_end(pct, None, 0, use_sahm=True); r.update(dict(ic_pct=pct, conf="Sahm falling", conf_pct=0)); rows.append(r)
df=pd.DataFrame(rows); pd.set_option("display.width",340); pd.set_option("display.max_colwidth",95); pd.set_option("display.max_rows",120)
df.to_csv("stage40_end2.csv", index=False)
print(df.sort_values(["withdrawn","miss","in_week"], ascending=[True,True,False])[["ic_pct","conf","conf_pct","exact","tr_w1","in_month","in_week","withdrawn","miss","lag_m","lag_d"]].head(28).to_string())
