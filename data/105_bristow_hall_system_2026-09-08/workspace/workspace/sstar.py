from mini import *
u=o['unrate_fp']; cur=o['unrate_cur']; rt=pd.concat([cur[cur.index<u.index.min()],u]).sort_index()
m3=rt.rolling(3).mean(); m6=rt.rolling(6).mean()
Sstar=(m3-m6.shift(1).rolling(15).min()).dropna()
def inwin(d): return any(p-pd.DateOffset(months=6)<=d<=t+pd.DateOffset(months=18) for p,t in zip(PK,TR))
for line in [0.45,0.46,0.50]:
    q=[d.strftime('%Y-%m') for d,x in Sstar.items() if x>=line and not inwin(d) and d>=pd.Timestamp('1949-01-01')]
    first=[]
    for p,t in zip(PK,TR):
        seg=Sstar[(Sstar.index>=p-pd.DateOffset(months=6))&(Sstar.index<=t)]; h=seg[seg>=line]
        first.append(md(h.index[0],p) if len(h) else None)
    print(f"S* line {line}: quiet months {q}; first crossing lags (months) {first}")
g2=g
q=[d.strftime('%Y-%m') for d,x in g2.items() if x>=0.5 and not inwin(d) and d>=pd.Timestamp('1949-01-01')]
print("Sahm 0.50 fp quiet months (same exclusion):",q)
