"""The 1981 bug was a leg being SILENT at a peak its object had reached. Look
for the same shape everywhere else: which legs are silent at which peaks, and
which single leg is carrying each call."""
exec(open('frontier.py').read().split('def rep(')[0])
import numpy as np, pandas as pd
PKD=[pd.Timestamp(p+'-01') for p in PEAKS[:12]]
print(f"{'peak':10}" + ''.join(f"{k:>6}" for k in 'ABCMU') + "   earliest, and whether one leg alone carries it")
lone=0
for p in PKD:
    row=[]; best=None
    for k in 'ABCMU':
        c=[(pp,d) for pp,d in PLU[k] if p-pd.DateOffset(months=6)<=d<=p+pd.DateOffset(months=12)]
        if c:
            lag=(min(x[0] for x in c)-(p+pd.DateOffset(months=1)-pd.Timedelta(days=1))).days
            row.append(f"{lag:>6d}")
            if best is None or lag<best[0]: best=(lag,k)
        else: row.append(f"{'-':>6}")
    n=sum(1 for x in row if x.strip()!='-')
    tag=f"  {best[1]} at {best[0]:+d} d" + ("   <== ONLY LEG" if n==1 else f"   ({n} legs)")
    if n==1: lone+=1
    print(f"{p:%Y-%m}   " + ''.join(row) + tag)
print(f"\n{lone} of 12 peaks are carried by a single leg -- those are the calls with no redundancy.")
print("\nsilent legs whose object nonetheless moved: the 1981 test, applied to every leg and peak")
print("a leg counts as SILENT-BUT-LIVE if it makes no call in the window and its previous call")
print("was inside the preceding 365 days -- the exact shape of the leg U bug.")
for k in 'ABCMU':
    for p in PKD:
        c=[(pp,d) for pp,d in PLU[k] if p-pd.DateOffset(months=6)<=d<=p+pd.DateOffset(months=12)]
        if c: continue
        prev=[pp for pp,d in PLU[k] if pp<p]
        if prev and (p-max(prev)).days<=365:
            print(f"   leg {k} silent at {p:%Y-%m}; its previous call was {max(prev):%Y-%m-%d}, "
                  f"{(p-max(prev)).days} days earlier")
