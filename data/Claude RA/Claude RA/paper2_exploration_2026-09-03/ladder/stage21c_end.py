"""Stage 21c: end-rule variants for the +-1 month target with no withdrawn (false) end calls.
Within each v2 episode (onset -> close), an end rule proposes a trough week and calls the end; a call that is later overturned by a new
high (before the episode closes) counts as a withdrawn call. Variants: claims MA length x decline threshold x minimum peak age;
IUR 4wk decline; claims MA cross (4wk below 8wk for k weeks); Sahm first-print decline; earliest-of combinations."""
exec(open("stage19b_iur.py").read().split("base=[SAHM[0.35]")[0])
IUR4=gapch(iur4,0.30)
V2=[SAHM[0.35], IC["ic8_30_k1"], IUR4, PAY, UM["um_d1_10"], HOU]
eps=replay3(V2, GATE[12], 120)
TR=[t for p,t in T_P1]
def series_daily(s, lag): x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values
ma_d={n: series_daily(ic.rolling(n).mean(),5) for n in [3,4,6,8]}
iur_d={n: series_daily(iur.rolling(n).mean(),12) for n in [2,4,8]}
def end_rule(vals, i0, i1, pct=None, minage=0, absdrop=None):
    """track vals from i0 to i1: running max -> provisional trough; call when value <= max*(1-pct) (or max-absdrop) and peak age>=minage.
    Returns list of (call_i, peak_i, withdrawn_bool) for every provisional call, plus final."""
    runmax=-np.inf; pk=None; calls=[]; called=False
    for i in range(i0,i1+1):
        v=vals[i]
        if np.isnan(v): continue
        if v>runmax:
            if called: calls[-1][2]=True; called=False
            runmax=v; pk=i
        elif not called and pk is not None and (i-pk)>=minage and ((pct is not None and v<=runmax*(1-pct)) or (absdrop is not None and v<=runmax-absdrop)):
            calls.append([i,pk,False]); called=True
    return calls
rows=[]
variants=[]
for n in [3,4,6,8]:
    for pct in [0.01,0.02,0.03,0.05,0.08]:
        for age in [0,28,56]:
            variants.append((f"claims ma{n} drop {int(pct*100)}% age>={age}d", ma_d[n], dict(pct=pct, minage=age)))
for n in [2,4,8]:
    for ad in [0.05,0.1,0.2,0.3]:
        for age in [0,28]:
            variants.append((f"IUR ma{n} drop {ad}pp age>={age}d", iur_d[n], dict(absdrop=ad, minage=age)))
for nm,vals,kw in variants:
    lags=[]; terr=[]; wd=0; ncalls=0
    for e,tr in zip(eps,TR):
        i0=int(np.where(cal==e["onset"])[0][0]); i1=int(np.where(cal==e["close"])[0][0]) if e["close"] is not None else N-1
        calls=end_rule(vals,i0,i1,**kw)
        if not calls: lags.append(None); terr.append(None); continue
        wd+=sum(1 for c in calls if c[2]); ncalls+=len(calls)
        fin=[c for c in calls if not c[2]]
        c=fin[-1] if fin else calls[-1]
        lags.append((cal[c[0]].to_period("M")-P(tr)).n); terr.append((cal[c[1]].to_period("M")-P(tr)).n)
    L=[l for l in lags if l is not None]
    rows.append(dict(rule=nm, end_lags=lags, trough_err=terr, n_out1=sum(abs(l)>1 for l in L), max_abs=max(abs(l) for l in L) if L else None, withdrawn=wd, misses=sum(l is None for l in lags)))
df=pd.DataFrame(rows); pd.set_option("display.width",330); pd.set_option("display.max_colwidth",120); pd.set_option("display.max_rows",300)
print("=== END RULE VARIANTS (v2 episodes; lags = end-call month minus NBER trough month; withdrawn = provisional calls overturned) ===")
print(df.sort_values(["withdrawn","n_out1","max_abs"]).to_string())
df.to_csv("stage21c_end.csv", index=False)
