import pickle, pandas as pd, numpy as np
o=pickle.load(open('cache/objects.pkl','rb'))
PK=o['PK']+[pd.Timestamp('2024-04-01')]; TR=o['TR']+[pd.Timestamp('2024-08-01')]
def inwin(d,back=6,fwd=3):
    for p,t in zip(PK,TR):
        if p-pd.DateOffset(months=back)<=d<=t+pd.DateOffset(months=fwd): return p
    return None
g=o['sahm']; 
print("== Sahm first prints >= 0.50, by month (window: peak-6 .. trough+3 of 12 NBER + Paper 1's 2024-04..2024-08) ==")
hits=g[g>=0.5]
rows=[]
for d,v in hits.items():
    rows.append((d.strftime('%Y-%m'),round(v,3),(inwin(d).strftime('%Y-%m') if inwin(d) else 'QUIET')))
# compress runs
runs=[];cur=None
for m,v,w in rows:
    if cur and cur[2]==w and (pd.Timestamp(m+'-01')-pd.Timestamp(cur[1]+'-01')).days<=62: cur[1]=m; cur[3]=max(cur[3],v)
    else:
        if cur: runs.append(cur)
        cur=[m,m,w,v]
runs.append(cur)
for r in runs: print(f"  {r[0]}..{r[1]}  max {r[3]:.3f}  -> {r[2]}")
print("\n== Sahm first prints: first month >= 0.50 after each peak (lag in months from peak) ==")
for p,t in zip(PK,TR):
    seg=g[(g.index>=p-pd.DateOffset(months=6))&(g.index<=t+pd.DateOffset(months=3))]
    f=seg[seg>=0.5]
    print(f"  peak {p:%Y-%m}: first >=0.50 at {f.index[0]:%Y-%m} (+{(f.index[0].year-p.year)*12+f.index[0].month-p.month} mo), max in window {seg.max():.2f}" if len(f) else f"  peak {p:%Y-%m}: never (max {seg.max():.2f})")
print("\n== quiet-period maxima of Sahm first prints (outside all windows), top 8 ==")
q=g[[inwin(d) is None for d in g.index]]
print(q.sort_values(ascending=False).head(8).round(3).to_string())
print("\n== leg calls (published > dated) ==")
for k,v in o['PL'].items(): print(' peak',k,[(p.strftime('%Y-%m-%d'),(d.strftime('%Y-%m') if d is not None else None)) for p,d in v])
for k in ['K','J','H','T','S']: print(' trough',k,[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in o['TLG'][k]])
