"""Stage 22: trial by fire for v3 — leave-one-out and recursive (expanding-window) re-selection with the v3 channel menu
(Sahm threshold x IUR gap threshold x sentiment x housing x payrolls; initial claims as end channel only). Selection criteria on the
training set: zero false episodes (current vintage), fewest onsets outside +-1, then sum|lag|, then fewest channels."""
exec(open("stage19b_iur.py").read().split("base=[SAHM[0.35]")[0])
import itertools, time
UMx={8:UM["um_d1_8"],10:UM["um_d1_10"]}
HSx={18:persist2(h3,18),20:persist2(h3,20)}
grid=[]
for th in [0.30,0.35,0.40,0.50]:
  for g in [0.25,0.30,0.35,0.40,0.45,None]:
    for ux in [8,10,None]:
      for hx in [18,20,None]:
        for payon in [False,True]:
          grid.append((th,g,ux,hx,payon))
t0=time.time(); cache={}
for cfg in grid:
    th,g,ux,hx,payon=cfg
    chs=[SAHM[th]]+([gapch(iur4,g)] if g else [])+([PAY] if payon else [])+([UMx[ux]] if ux else [])+([HSx[hx]] if hx else [])
    cache[cfg]=replay3(chs, GATE[12], 120)
print("replays:", len(grid), "in", round(time.time()-t0,1), "s")
EPS=T_P1
def sc(cfg, folds, cutoff=None):
    res,false=score_eps(cache[cfg],EPS)
    if cutoff is not None: false=[f for f in false if pd.Timestamp(f)<cutoff]
    L=[res[i]["lag"] for i in folds]
    if any(l is None for l in L): return None
    nchan=1+sum(x is not None and x is not False for x in cfg[1:])
    return (len(false), sum(abs(l)>1 for l in L), sum(abs(l) for l in L), nchan)
print("\nLEAVE-ONE-OUT (v3 menu):")
for k in range(9):
    train=[i for i in range(9) if i!=k]; best=None
    for cfg in grid:
        s=sc(cfg,train)
        if s is None or s[0]>0: continue
        if best is None or s<best[0]: best=(s,cfg)
    cfg=best[1]; res,false=score_eps(cache[cfg],EPS); r=res[k]
    print(f"  hold out {EPS[k][0]}: chosen {cfg} -> onset {r['onset']} lag {r['lag']:+d} | end lag {r['end_lag']:+d} | false (whole sample) {len(false)}")
print("\nRECURSIVE (expanding window, v3 menu): choose on recessions before k using only false episodes before k's peak-2; apply to k")
for k in range(3,9):
    train=list(range(k)); cutoff=(P(EPS[k][0])-2).to_timestamp(); best=None
    for cfg in grid:
        s=sc(cfg,train,cutoff)
        if s is None: continue
        if best is None or s<best[0]: best=(s,cfg)
    cfg=best[1]; res,false=score_eps(cache[cfg],EPS); r=res[k]
    nf_after=len([f for f in false if pd.Timestamp(f)>=cutoff and pd.Timestamp(f)<=(P(EPS[k][1])+12).to_timestamp()])
    print(f"  {EPS[k][0]}: trained on {k} -> {cfg}; held-out onset {r['onset']} lag {r['lag']}, end lag {r['end_lag']}; false in its window {nf_after}")
# safety margins: how close each channel came to firing in gated quiet periods (current vintage)
print("\nSAFETY MARGINS (max gated reading outside [peak-2, trough+12] windows, 1968-2026):")
allowed=np.zeros(N,bool)
for pk,tr in EPS:
    lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(tr)+12).to_timestamp(how="end")); allowed[lo:hi+1]=True
quiet=(~allowed)&GATE[12]&(cal>=pd.Timestamp("1968-06-01"))
Sd=Srel.reindex(cal).ffill().values; print("  Sahm first print: max quiet gated =", np.nanmax(Sd[quiet]).round(3), "vs 0.35; dates >=0.30:", [str(d.date()) for d in cal[quiet&(Sd>=0.30-1e-9)]][:6])
g4=(iur4-iur4.shift(1).rolling(52).min()); g4d=pd.Series(g4.values,index=g4.index+pd.Timedelta(days=12)).reindex(cal).ffill().values
print("  IUR 4wk gap: max quiet gated =", np.nanmax(g4d[quiet]).round(3), "vs 0.40; dates >=0.25:", sorted(set(str(d.date())[:7] for d in cal[quiet&(g4d>=0.25-1e-9)]))[:8])
h3d=h3.reindex(cal).ffill().values; print("  housing starts 3-mo first print: min quiet gated =", np.nanmin(h3d[quiet]).round(3), "vs -0.20")
umd=(um-um.shift(1)).reindex(cal).ffill().values; print("  sentiment 1-mo change: min quiet gated =", np.nanmin(umd[quiet]).round(2), "vs -10")
payd=pd.Series(pay.d1.astype(float).values,index=pd.to_datetime(pay.rel.values)).reindex(cal).ffill().values; print("  payroll first print 1-mo %: min quiet gated =", np.nanmin(payd[quiet]).round(3), "vs -0.1")
