"""Stage 42: how likely is a false alarm, and how likely is a miss.
(A) exposure: for each frozen channel, the distribution of gated quiet readings against its threshold (margin, and the share of
quiet weeks within 10/25/50% of the line).
(B) block bootstrap: resample the gated quiet record of each channel statistic in blocks (13/26/52 weeks), build 2,000 synthetic
58-year quiet histories, apply the frozen thresholds, count crossings -> P(>=1 false alarm in 58 yrs) and a per-year rate.
(C) redundancy: how many of the 13 frozen channels fire inside [peak-1, peak+2] of each recession -> what has to fail for a miss.
(D) coverage bounds: exact binomial bounds from 9/9 in sample and from the recursive out-of-sample record."""
exec(open("stage38_v6.py").read().split("T={pk:(P(pk)+1)")[0])
import warnings; warnings.filterwarnings("ignore")
rng=np.random.default_rng(20260904)
allowed=np.zeros(N,bool)
for pk,tr in T_P1:
    lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(tr)+12).to_timestamp(how="end")); allowed[lo:hi+1]=True
QG=(~allowed)&GATE[12]&(cal>=pd.Timestamp("1968-06-01")); QU=(~allowed)&(cal>=pd.Timestamp("1968-06-01"))
def dl(s,lag): x=s.dropna().copy(); x.index=x.index+pd.Timedelta(days=lag); return x
s4=iur4-iur4.shift(1).rolling(52).min()
h3s=h3.copy(); pay1=pd.Series(pay.d1.astype(float).values, index=pd.to_datetime(pay.rel.values))
ip3=fpch3("INDPRO_all_vintages.csv")
CH=[  # name, statistic (larger = worse), publication lag days, threshold, gated?
 ("Sahm first print", Srel, 0, 0.35, True),
 ("IUR 4wk gap", s4, 12, 0.40, True),
 ("payrolls 1m fall", -pay1, 0, 0.10, True),
 ("sentiment 1m fall", -(um-um.shift(1)), 0, 10.0, True),
 ("housing 3m fall", -h3s, 0, 0.20, True),
 ("6mo bill 60d fall", -(tb6-tb6.shift(60)), 1, 1.43, True),
 ("Sahm backstop", Srel, 0, 0.55, False),
 ("IUR gap backstop", s4, 12, 0.50, False),
 ("claims 8wk backstop", r8, 5, 0.40, False),
 ("bill fall backstop", -(tb6-tb6.shift(60)), 1, 2.50, False),
 ("sentiment backstop", -(um-um.shift(1)), 0, 15.0, False),
 ("housing backstop", -h3s, 0, 0.25, False),
 ("IP 3m fall backstop", -ip3, 0, 0.02, False),
 ("VIX 20d change (lane)", vix-vix.shift(20), 1, 17.425, True),
 ("Baa-10y rise (lane)", baa-baa.rolling(250).min(), 1, 1.50, True),
]
print("=== (A) EXPOSURE: gated quiet readings vs the frozen line ===")
print(f"{'channel':26s} {'thresh':>8s} {'quiet max':>10s} {'margin':>8s} {'sd':>7s} {'m/sd':>6s} {'>90% of line':>13s} {'>75%':>7s}")
BOOT={}
for nm,st,lag,thr,gated in CH:
    v=dl(st,lag).reindex(cal).ffill().values
    q=v[QG if gated else QU]; q=q[~np.isnan(q)]
    if len(q)<200: print(f"{nm:26s} insufficient quiet data"); continue
    mx=np.nanmax(q); sd=np.nanstd(q); marg=thr-mx
    print(f"{nm:26s} {thr:8.3f} {mx:10.3f} {marg:8.3f} {sd:7.3f} {marg/sd:6.2f} {100*np.mean(q>0.9*thr):12.2f}% {100*np.mean(q>0.75*thr):6.2f}%")
    BOOT[nm]=(q, thr)
print("\n=== (B) BLOCK BOOTSTRAP: synthetic 58-year quiet histories, frozen thresholds ===")
YRS=58
for bw in [65,130,260]:   # ~13, 26, 52 weeks of daily observations
    anyfa=np.zeros(2000,bool); per=np.zeros(2000)
    for nm,(q,thr) in BOOT.items():
        n=len(q); nb=int(np.ceil(n/bw))
        idx=rng.integers(0,max(1,n-bw),size=(2000,nb))
        for b in range(nb):
            pass
        # vectorised: build each synthetic path's max
        mx=np.full(2000,-np.inf)
        for b in range(nb):
            starts=idx[:,b]
            seg=np.stack([q[s:s+bw] for s in starts]) if bw<=n else None
            mx=np.maximum(mx, seg.max(axis=1))
        hit=mx>=thr
        anyfa|=hit; per+=hit.astype(float)
    p=anyfa.mean()
    print(f"  block {bw//5} weeks: P(at least one false alarm in {YRS} synthetic quiet years) = {p:.4f}"
          f" -> implied per-year rate {1-(1-p)**(1/YRS):.5f}; mean channels crossing {per.mean():.3f}")
print("\n=== (C) REDUNDANCY: frozen channels firing inside [peak-1, peak+2] ===")
for pk,tr in T_P1:
    lo=cal.searchsorted((P(pk)-1).to_timestamp()); hi=cal.searchsorted((P(pk)+2).to_timestamp(how="end"))
    on=[]
    for nm,st,lag,thr,gated in CH:
        v=dl(st,lag).reindex(cal).ffill().values; g=GATE[12] if gated else np.ones(N,bool)
        seg=(v[lo:hi+1]>=thr)&g[lo:hi+1]
        if np.nansum(seg)>0: on.append(nm)
    print(f"  {pk}: {len(on)} of 15 fire -> {on}")
print("\n=== (D) COVERAGE BOUNDS ===")
from math import comb
def lower(k,n,a=0.05):
    lo,hi=0.0,1.0
    for _ in range(200):
        m=(lo+hi)/2
        if sum(comb(n,i)*m**i*(1-m)**(n-i) for i in range(k,n+1))<a: lo=m
        else: hi=m
    return lo
print(f"  in-sample 9/9 detected: 95% lower bound on per-recession detection = {lower(9,9):.3f}")
print(f"  leave-one-out 9/9 detected (8/9 within a month): lower bound {lower(9,9):.3f}")
print(f"  recursive out-of-sample 5/6 detected: lower bound {lower(5,6):.3f}; point estimate {5/6:.3f}")
print(f"  false alarms 0 in 58 gated quiet years: 95% upper bound on the annual rate = {3/58:.4f}; P(clean decade) >= {(1-3/58)**10:.3f}")
