exec(open("stage29_fed.py").read().split("rows=[]")[0])
V3=[SAHM[0.35], gapch(iur4,0.40), PAY, UM["um_d1_10"], persist2(h3,20)]
print("=== short-rate fall channel: threshold x window grid, added to v3 (2024 = Apr-Aug) ===")
for nm,s in [("TB6",tb6),("TB3",tb3),("FF",ff)]:
    for w in [40,60,80,120]:
        for th in [1.0,1.25,1.5,1.75,2.0,2.5]:
            ch=D(dch(s,w)<=-th)
            eps=replay3(V3+[ch], GATE[12], 120); res,false=score_eps(eps,T_P1); L=[r["lag"] for r in res]
            alone=score(pd.Series(ch&GATE[12], index=cal), "x", start="1968-06-01")
            print(f"  {nm} fall>={th:4.2f} in {w:3d}d: v3+ false {len(false)} {false[:2]} lags {L} out1 {sum(1 for l in L if l is None or abs(l)>1)} | alone: fa {alone['n_fa']} misses {alone['misses']} lags {alone['lags']}")
# quiet-period margin for TB6 60-day fall under the gate
x=dch(tb6,60); v=x.reindex(cal).ffill().values
allowed=np.zeros(N,bool)
for pk,tr in T_P1:
    lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(tr)+12).to_timestamp(how="end")); allowed[lo:hi+1]=True
quiet=(~allowed)&GATE[12]&(cal>=pd.Timestamp("1968-06-01"))
q=v[quiet]; print("\nTB6 60-day fall: largest gated quiet fall =", np.nanmin(q).round(3), "on", str(cal[quiet][np.nanargmin(q)].date()))
qq=v[(~allowed)&(cal>=pd.Timestamp("1968-06-01"))]; print("   ungated largest quiet fall =", np.nanmin(qq).round(3), "on", str(cal[(~allowed)&(cal>=pd.Timestamp('1968-06-01'))][np.nanargmin(qq)].date()))
for pk,tr in T_P1:
    lo=cal.searchsorted((P(pk)-1).to_timestamp()); hi=cal.searchsorted((P(pk)+1).to_timestamp(how="end")); w=v[lo:hi+1]
    print(f"   {pk}: largest 60-day fall inside [peak-1, peak+1] = {np.nanmin(w):.2f}")
print("TB6 around Oct 1973 - Jan 1974:", {str(k.date()):round(val,2) for k,val in tb6.loc['1973-09-01':'1974-01-15'].resample('W').last().items()})
