"""Stage 39: speed and exactness at the END. v6 episodes fixed; only the end rule varies.
Objects: initial claims (8/4-wk), continued claims, insured-unemployment rate, state breadth of claims turning down
(ETA 539, 1986->), state breadth of IUR turning down, Sahm first-print peak, industrial production first-print trough,
and the earliest-of combinations. Scored: trough-month error vs NBER, end-call lag in months AND days from the
expansion's first day, and withdrawn (false) end calls."""
exec(open("stage38_v6.py").read().split("T={pk:(P(pk)+1)")[0])
V6eps,_=run(["VIX 20d change>=17.4 (1990->)","Baa-10y rise from 250d min>=1.5 (1987->)"])
TR=[t for p,t in T_P1]; TE={t:(P(t)+1).to_timestamp() for t in TR}
def sd(s, lag): x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values
cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv")
OBJ={}
for n in [4,8]: OBJ[f"IC ma{n}"]=sd(ic.rolling(n).mean(),5)
for n in [4,8]: OBJ[f"CC ma{n}"]=sd(cc.rolling(n).mean(),12)
for n in [4,8]: OBJ[f"IUR ma{n}"]=sd(iur.rolling(n).mean(),12)
d=pd.read_csv(ODD+"onset-detector-new-2026-08-23/26_ui_claims_admin/eta_ar539.csv", usecols=["st","c2","c3","c8","c19"], parse_dates=["c2"]); d=d[~d.st.isin(["PR","VI"])]
stc=d.pivot_table(index="c2", columns="st", values="c3", aggfunc="sum").sort_index().rolling(4).mean()
sti=d.pivot_table(index="c2", columns="st", values="c19", aggfunc="max").sort_index().rolling(4).mean()
# breadth of states still rising: share whose 4wk mean is at its own 26-week max
for nm,X in [("states claims at 26wk max",stc),("states IUR at 26wk max",sti)]:
    sh=(X>=X.rolling(26).max()-1e-9).sum(axis=1)/X.notna().sum(axis=1)
    OBJ[nm]=sd(sh,9)
def peak_and_call(vals, i0, i1, pct, minage=0):
    runmax=-np.inf; pk=None; calls=[]; called=False
    for i in range(i0,i1+1):
        v=vals[i]
        if np.isnan(v): continue
        if v>runmax:
            if called: calls[-1][2]=True; called=False
            runmax=v; pk=i
        elif not called and pk is not None and (i-pk)>=minage and v<=runmax*(1-pct) if runmax>0 else False: calls.append([i,pk,False]); called=True
    return calls
rows=[]
for nm,vals in OBJ.items():
    for pct in [0.01,0.02,0.03,0.05]:
        terr=[]; lagm=[]; lagd=[]; wd=0
        for e,tr in zip(V6eps,TR):
            i0=int(np.where(cal==e["onset"])[0][0]); i1=int(np.where(cal==e["close"])[0][0]) if e["close"] is not None else N-1
            calls=peak_and_call(vals,i0,i1,pct)
            if not calls: terr.append(None); lagm.append(None); lagd.append(None); continue
            wd+=sum(1 for c in calls if c[2]); fin=[c for c in calls if not c[2]]; c=fin[-1] if fin else calls[-1]
            terr.append((cal[c[1]].to_period("M")-P(tr)).n); lagm.append((cal[c[0]].to_period("M")-P(tr)).n); lagd.append((cal[c[0]]-TE[tr]).days)
        L=[x for x in lagm if x is not None]; TT=[x for x in terr if x is not None]
        rows.append(dict(obj=nm, pct=pct, trough_err=terr, exact=sum(1 for x in TT if x==0), tr_w1=sum(1 for x in TT if abs(x)<=1),
                         end_lag_m=lagm, in_month=sum(1 for x in L if abs(x)<=1), lag_days=lagd, in_week=sum(1 for x in lagd if x is not None and abs(x)<=7), withdrawn=wd, miss=sum(1 for x in lagm if x is None)))
df=pd.DataFrame(rows); pd.set_option("display.width",340); pd.set_option("display.max_colwidth",95); pd.set_option("display.max_rows",100)
df.to_csv("stage39_ends.csv", index=False)
print(df.sort_values(["withdrawn","miss"], ascending=[True,True])[["obj","pct","exact","tr_w1","in_month","in_week","withdrawn","miss","trough_err","end_lag_m"]].to_string())
