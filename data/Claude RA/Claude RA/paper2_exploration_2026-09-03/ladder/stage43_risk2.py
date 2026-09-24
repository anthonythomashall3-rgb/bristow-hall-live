"""Stage 43: corrected risk arithmetic. The quiet set is what the machine actually sees: outside every recession window AND
outside every open episode (the close rule), with the channel as implemented (persistence, freshness, gate)."""
exec(open("stage38_v6.py").read().split("T={pk:(P(pk)+1)")[0])
import warnings; warnings.filterwarnings("ignore")
rng=np.random.default_rng(20260904)
eps6,_=run(["VIX 20d change>=17.4 (1990->)","Baa-10y rise from 250d min>=1.5 (1987->)"])
openmask=np.zeros(N,bool)
for e in eps6:
    a=int(np.where(cal==e["onset"])[0][0]); b=int(np.where(cal==e["close"])[0][0]) if e["close"] is not None else N-1
    openmask[a:b+1]=True
allowed=np.zeros(N,bool)
for pk,tr in T_P1:
    lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(tr)+12).to_timestamp(how="end")); allowed[lo:hi+1]=True
def dl(s,lag): x=s.dropna().copy(); x.index=x.index+pd.Timedelta(days=lag); return x
s4=iur4-iur4.shift(1).rolling(52).min(); pay1=pd.Series(pay.d1.astype(float).values, index=pd.to_datetime(pay.rel.values)); ip3=fpch3("INDPRO_all_vintages.csv")
CH=[("Sahm fast",Srel,0,0.35,True,1),("IUR gap fast",s4,12,0.40,True,1),("payrolls fast",-pay1,0,0.10,True,1),("sentiment fast",-(um-um.shift(1)),0,10.0,True,1),
    ("housing fast",-h3,0,0.20,True,2),("bill fast",-(tb6-tb6.shift(60)),1,1.43,True,1),
    ("Sahm backstop",Srel,0,0.55,False,1),("IUR backstop",s4,12,0.50,False,1),("claims backstop",r8,5,0.40,False,1),("bill backstop",-(tb6-tb6.shift(60)),1,2.50,False,1),
    ("sentiment backstop",-(um-um.shift(1)),0,15.0,False,1),("housing backstop",-h3,0,0.25,False,2),("IP backstop",-ip3,0,0.02,False,2),
    ("VIX lane",vix-vix.shift(20),1,17.425,True,1),("Baa lane",baa-baa.rolling(250).min(),1,1.50,True,1)]
print("=== EXPOSURE on the quiet set the machine sees (no episode open, outside recession windows) ===")
print(f"{'channel':20s} {'thresh':>7s} {'k':>2s} {'quiet max':>10s} {'margin':>8s} {'m/sd':>6s} {'quiet obs':>9s} {'>90% line':>10s}")
SER={}
for nm,st,lag,thr,gated,k in CH:
    x=dl(st,lag)
    if k>1: x=pd.Series(np.minimum(x.values, np.r_[np.nan, x.values[:-1]]), index=x.index)  # two consecutive prints: the weaker of the pair
    v=x.reindex(cal).ffill().values
    q=(~allowed)&(~openmask)&(cal>=pd.Timestamp("1968-06-01"))&(GATE[12] if gated else np.ones(N,bool))
    vals=v[q]; vals=vals[~np.isnan(vals)]
    if len(vals)<200: print(f"{nm:20s} insufficient"); continue
    mx=vals.max(); sd=vals.std(); SER[nm]=(vals,thr)
    print(f"{nm:20s} {thr:7.3f} {k:2d} {mx:10.3f} {thr-mx:8.3f} {(thr-mx)/sd:6.2f} {len(vals):9d} {100*np.mean(vals>0.9*thr):9.2f}%")
print("\n=== BLOCK BOOTSTRAP over that quiet set (2,000 synthetic 58-year quiet histories) ===")
for bw in [65,130,260]:
    anyfa=np.zeros(2000,bool); cnt=np.zeros(2000)
    for nm,(q,thr) in SER.items():
        n=len(q); nb=int(np.ceil(n/bw)); mx=np.full(2000,-np.inf)
        for b in range(nb):
            s=rng.integers(0,max(1,n-bw),size=2000)
            mx=np.maximum(mx, np.stack([q[i:i+bw] for i in s]).max(axis=1))
        hit=mx>=thr; anyfa|=hit; cnt+=hit
    p=anyfa.mean(); print(f"  {bw//5}-week blocks: P(>=1 false alarm in 58 quiet years) = {p:.4f} | per-year {1-(1-p)**(1/58) if p<1 else float('nan'):.5f} | mean channels crossing {cnt.mean():.2f}")
print("\n=== per-channel bootstrap crossing probability (58 quiet years, 26-week blocks) ===")
bw=130
for nm,(q,thr) in SER.items():
    n=len(q); nb=int(np.ceil(n/bw)); mx=np.full(2000,-np.inf)
    for b in range(nb):
        s=rng.integers(0,max(1,n-bw),size=2000); mx=np.maximum(mx, np.stack([q[i:i+bw] for i in s]).max(axis=1))
    print(f"  {nm:20s} P(cross) = {(mx>=thr).mean():.4f}")
