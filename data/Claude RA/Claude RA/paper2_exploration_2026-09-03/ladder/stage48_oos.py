"""Stage 48: leave-one-out and recursive (expanding-window) re-selection on the v7 menu — the first time the bill channel and the
backstop layer are inside the out-of-sample test. Selection on the training recessions: zero false episodes, fewest onsets outside
one month, then sum|lag|, then fewest channels."""
exec(open("stage47_perturb.py").read().split('print("\\n=== (c) PERTURBATION')[0])
import itertools, time, warnings; warnings.filterwarnings("ignore")
grid=[]
for sahm in [0.30,0.35,0.40,0.50]:
  for iurg in [0.35,0.40,0.45,None]:
    for billx in [1.33,1.43,1.53,None]:
      for houx in [18,20,25,None]:
        for payon in [True,False]:
          grid.append((sahm,iurg,billx,houx,payon))
t0=time.time(); cache={}
BSarr=[D(Srel>=0.55-1e-9), gapch(iur4,0.50), wk(r8>=0.40), fall(tb6,60,2.50), persist2(h3,25), D((ip3c<=-0.02)&(ip3c.shift(1)<=-0.02))]
lanefull=np.zeros(N,bool)
for a in [lane_arr(vix-vix.shift(20),1,17.425), lane_arr(baa-baa.rolling(250).min(),1,1.50)]: lanefull|=fresh(a,120)
for cfg in grid:
    sahm,iurg,billx,houx,payon=cfg
    fast=[SAHM[sahm] if sahm in SAHM else D(Srel>=sahm-1e-9)]
    if iurg: fast.append(gapch(iur4,iurg))
    if billx: fast.append(fall(tb6,60,billx))
    if houx: fast.append(persist2(h3,houx))
    if payon: fast.append(PAY)
    frozen=np.zeros(N,bool)
    for c in fast: frozen|=fresh(c,120)&GATE[12]
    for c in BSarr: frozen|=fresh(c,120)
    valid=lanefull.copy()
    for i in np.flatnonzero(np.diff(lanefull.astype(np.int8))==1)+1:
        if not frozen[i:i+121].any():
            j=i
            while j<N and lanefull[j]: valid[j]=False; j+=1
    cache[cfg]=replay(frozen|valid)
print("replays:", len(grid), "in", round(time.time()-t0,1),"s")
EPS=T_P1
def sc(cfg, folds, cutoff=None):
    res,false=score_eps(cache[cfg],EPS)
    if cutoff is not None: false=[f for f in false if pd.Timestamp(f)<cutoff]
    L=[res[i]["lag"] for i in folds]
    if any(l is None for l in L): return None
    nch=1+sum(1 for x in cfg[1:4] if x is not None)+(1 if cfg[4] else 0)
    return (len(false), sum(abs(l)>1 for l in L), sum(abs(l) for l in L), nch)
print("\nLEAVE-ONE-OUT (v7 menu):")
same=0
for k in range(9):
    train=[i for i in range(9) if i!=k]; best=None
    for cfg in grid:
        s=sc(cfg,train)
        if s is None or s[0]>0: continue
        if best is None or s<best[0]: best=(s,cfg)
    cfg=best[1]; res,false=score_eps(cache[cfg],EPS); r=res[k]
    if cfg==(0.35,0.40,1.43,20,False) or cfg==(0.35,0.40,1.43,20,True): same+=1
    print(f"  hold out {EPS[k][0]}: chosen {cfg} -> onset {r['onset']} lag {r['lag']} | end {r['end_lag']} | false {len(false)}")
print(f"  folds choosing the shipped configuration: {same} of 9")
print("\nRECURSIVE (expanding window, v7 menu):")
for k in range(3,9):
    train=list(range(k)); cutoff=(P(EPS[k][0])-2).to_timestamp(); best=None
    for cfg in grid:
        s=sc(cfg,train,cutoff)
        if s is None: continue
        if best is None or s<best[0]: best=(s,cfg)
    cfg=best[1]; res,false=score_eps(cache[cfg],EPS); r=res[k]
    nf=len([f for f in false if pd.Timestamp(f)>=cutoff and pd.Timestamp(f)<=(P(EPS[k][1])+12).to_timestamp()])
    print(f"  {EPS[k][0]}: trained on {k} -> {cfg}; held-out onset {r['onset']} lag {r['lag']} | end {r['end_lag']} | false in window {nf}")
