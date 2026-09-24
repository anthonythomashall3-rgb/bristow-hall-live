"""Stage 31: v4 = v3 + the short-rate channel (6-month bill, 60-trading-day fall), threshold set by the maximum-margin rule
(midpoint between the largest gated quiet fall, 1.34 pp in July 1989, and the smallest onset-window fall among the recessions
the channel is meant to carry, 1.52 pp in 1973 and 2001). Current-vintage and first-print replays; days from end of peak month."""
exec(open("stage20b_confirm.py").read().split("chs=[SAHM[0.35], ICmix")[0])
DF=HOME+"/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/"
def loadfred(f):
    s=pd.read_csv(f); s=s[s.value!="."]; s.index=pd.to_datetime(s.date); return s.value.astype(float).sort_index()
tb6=loadfred(DF+"fred_daily/DTB6.csv")
def fall(s,w,th): x=(s-s.shift(w)); x.index=x.index+pd.Timedelta(days=1); return D(x<=-th)
V3=[SAHM[0.35], gapch(iur4,0.40), PAY, UM["um_d1_10"], persist2(h3,20)]
lastday=lambda pk: (P(pk)).to_timestamp(how="end").normalize()
for th in [1.40,1.43,1.45,1.50]:
    TB=fall(tb6,60,th)
    eps=replay3(V3+[TB], GATE[12], 120); res,false=score_eps(eps,T_P1)
    print(f"v4 TB6 60d fall>={th}: false {false} | lags {[r['lag'] for r in res]} | end {[r['end_lag'] for r in res]} | onsets {[r['onset'] for r in res]}")
    if th==1.43:
        print("   days from end of peak month:", [(r['peak'], (pd.Timestamp(r['onset'])-lastday(r['peak'])).days) for r in res])
        IUR40=gapch(iur4,0.40); IURF40=D(g4f>=0.40-1e-12); IURmix40=IUR40.copy(); IURmix40[cal>=cut]=IURF40[cal>=cut]
        epsF=replay3([SAHM[0.35], IURmix40, PAY, UM["um_d1_10"], persist2(h3,20), TB], GATE[12], 120); resF,falseF=score_eps(epsF,T_P1)
        print("   first-print replay (IUR first prints 2002->, bills unrevised): false", falseF, "| lags", [r['lag'] for r in resF], "| onsets", [r['onset'] for r in resF])
        names=["Sahm","IUR","payrolls","sentiment","housing","TB6"]; arrs=[fresh(a,120)&GATE[12] for a in V3+[TB]]
        for e in eps:
            i=int(np.where(cal==e["onset"])[0][0]); print("   ", e["onset"].date(), [n for n,a in zip(names,arrs) if a[i]])
# ungated behaviour of the channel alone and its near-misses
x=(tb6-tb6.shift(60)); x.index=x.index+pd.Timedelta(days=1)
allowed=np.zeros(N,bool)
for pk,tr in T_P1:
    lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(tr)+12).to_timestamp(how="end")); allowed[lo:hi+1]=True
v=x.reindex(cal).ffill().values; q=(~allowed)&(cal>=pd.Timestamp("1962-06-01"))
falls=pd.Series(v[q], index=cal[q]); big=falls[falls<=-1.0]
print("\nungated quiet 60-day falls >= 1.0 pp (episodes):", sorted(set(str(d.date())[:7] for d in big.index)))
gq=q&GATE[12]; fg=pd.Series(v[gq], index=cal[gq]); print("gated quiet 60-day falls >= 1.0 pp:", sorted(set(str(d.date())[:7] for d in fg[fg<=-1.0].index)))
