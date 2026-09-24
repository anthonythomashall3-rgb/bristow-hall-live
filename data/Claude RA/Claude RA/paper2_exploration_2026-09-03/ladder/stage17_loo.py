"""Leave-one-recession-out: select the best zero-false-alarm config on 8 episodes, test on the 9th. Also days-from-peak speed for v1."""
exec(open("stage16_finegrid.py").read().split("rows=[]")[0])
import itertools, time
IC["ic8_35_k1"]=wk(r8>=0.35)
grid=[]
for th in [0.30,0.35,0.40,0.50]:
  for icn in ["ic8_25_k1","ic8_30_k1","ic8_35_k1","ic4_30_k2",None]:
    for ux in [8,10,None]:
      for hx in [18,20,None]:
        for payon in [False,True]:
          grid.append((th,icn,ux,hx,payon))
t0=time.time(); cache={}
for cfg in grid:
    th,icn,ux,hx,payon=cfg
    chs=[SAHM[th]]+([IC[icn]] if icn else [])+([PAY] if payon else [])+([UMx[ux]] if ux else [])+([HSx[hx]] if hx else [])
    cache[cfg]=replay3(chs, GATE[12], 120)
print("replays:", len(grid), "in", round(time.time()-t0,1), "s")
def per_episode(eps, targets):
    res,false=score_eps(eps,targets); return res, false
EPS=T_P1
def cfg_score(cfg, folds):
    res,false=per_episode(cache[cfg], EPS)
    # false episodes counted over the whole sample (they are not attributable to a fold)
    L=[res[i]["lag"] for i in folds]
    if any(l is None for l in L): return None
    return dict(n_false=len(false), n_out2=sum(abs(l)>2 for l in L), sum_abs=sum(abs(l) for l in L))
print("\nLEAVE-ONE-OUT (select on 8 by: zero false episodes, then fewest lags outside ±2, then sum|lag|; test on held-out):")
loo=[]
for k in range(9):
    train=[i for i in range(9) if i!=k]
    best=None
    for cfg in grid:
        s=cfg_score(cfg, train)
        if s is None or s["n_false"]>0: continue
        key=(s["n_out2"], s["sum_abs"])
        if best is None or key<best[0]: best=(key,cfg)
    if best is None: loo.append((EPS[k][0],None)); continue
    cfg=best[1]; res,false=per_episode(cache[cfg], EPS); r=res[k]
    loo.append((EPS[k][0], cfg, r["lag"], r["end_lag"], r["tr_err"], len(false)))
    print(f"  held out {EPS[k][0]}: selected {cfg} -> onset lag {r['lag']:+d}, end lag {r['end_lag']:+d}, trough err {r['tr_err']:+d}; false episodes (full sample) {len(false)}")
# robustness band: which single-threshold moves keep zero false and all within 2
print("\nROBUSTNESS of v1 (0.35, ic8_30, um10, hs20, pay on): neighbors")
base=(0.35,"ic8_30_k1",10,20,True)
for cfg in grid:
    diff=[i for i in range(5) if cfg[i]!=base[i]]
    if len(diff)==1:
        s=cfg_score(cfg, list(range(9))); print("  ", cfg, s)
# speed in days for v1
res,false=per_episode(cache[base], EPS)
print("\nSPEED IN DAYS (v1): onset call minus last day of NBER peak month; end call minus last day of trough month")
for (pk,tr),r in zip(EPS,res):
    on=pd.Timestamp(r["onset"]); pe=P(pk).to_timestamp(how="end").normalize(); print(f"  {pk}: onset {on.date()} = {(on-pe).days:+d} days after peak month end")
