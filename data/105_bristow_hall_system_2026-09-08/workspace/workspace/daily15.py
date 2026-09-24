"""SMOOTHING THE SPREAD. The binding quiet reading for the commercial-paper spread is August and December 1978 (1.53),
which is a tightening episode, not a contraction, and it is what forces the line up against the 1969 and 1980 gains.
A spread read as a multi-week MEAN before the rise is taken should separate a sustained widening from a spike. Every
smoothing length and window is swept, and the quantity that decides is the RATIO of the lowest recession reading the
object needs to the highest quiet reading anywhere on the record — the margin, not the record."""
exec(open('daily13.py').read().split('P("SPREADS BUILT AND SCREENED')[0].replace("out=open('daily13.out','w')","out=open('daily15.out','w')"))
def spread(a,b):
    aa=L25(a); bb=L25(b); idx=aa.index.union(bb.index)
    S=(aa.reindex(idx).ffill()-bb.reindex(idx).ffill()).dropna(); return S[S.index>=max(aa.index.min(),bb.index.min())]
SP={'CP1m-bill3m':spread('H0RIFSPPFM01NWF','WTB3MS'),'BA3m-bill3m':spread('H1RIFSPABM03NWF','WTB3MS'),
    'CP3m-bill3m':spread('H0RIFSPPFM03NWF','WTB3MS'),'CP6m-bill3m':spread('H0RIFSPPFM06NWF','WTB3MS')}
P(f"{'object':16s} {'sm':>3s} {'win':>4s} {'quiet max':>9s} {'when':>8s} {'2nd':>6s} | recessions cleared at 1.10x and the margin")
BEST=[]
for nm,S in SP.items():
    per=max(1,int(round(float(np.median(np.diff(S.index.values).astype('timedelta64[D]').astype(int))))))
    for sm in [1,2,4,8,13]:
        Sm=S.rolling(sm).mean().dropna() if sm>1 else S
        for wmon in [3,6,9,12]:
            win=max(4,int(wmon*30/per)); GG=(Sm-Sm.rolling(win).min()).dropna()
            qs=sorted([(float(wseg(GG,dd).max()),dd.strftime('%Y-%m')) for dd in QP if len(wseg(GG,dd))],reverse=True)
            if len(qs)<20: continue
            qmax=qs[0][0]
            rec=sorted([(float(wseg(GG,PK[i]).max()),PK[i].strftime('%Y-%m')) for i in range(13) if len(wseg(GG,PK[i]))],reverse=True)
            rec=[r for r in rec if r[0]<9000]
            n10=sum(1 for v,_ in rec if v>=qmax*1.10); n25=sum(1 for v,_ in rec if v>=qmax*1.25); n50=sum(1 for v,_ in rec if v>=qmax*1.50)
            P(f"{nm:16s} {sm:3d} {wmon:4d} {qmax:9.2f} {qs[0][1]:>8s} {qs[1][0]:6.2f} | 1.10x {n10}/13  1.25x {n25}/13  1.50x {n50}/13")
            if n25>=2: BEST.append((nm,sm,wmon,win,qmax,n25))
P(f"\n{len(BEST)} configurations fire in two or more recessions at a line 25 per cent clear of every quiet reading — through the machine:")
seen=set()
for nm,sm,wmon,win,qmax,n25 in BEST:
    S=SP[nm]; Sm=S.rolling(sm).mean().dropna() if sm>1 else S; GG=(Sm-Sm.rolling(win).min()).dropna()
    for mult in [1.25,1.5,1.75]:
        k=(nm,sm,wmon,round(qmax*mult,3))
        if k in seen: continue
        seen.add(k); go9(f'{nm} sm{sm} {wmon}m >= {qmax*mult:.3f} ({mult}x)',[CRED,dict(name=nm,gap=GG,line=qmax*mult,pub_lag_days=1)])
out.close()
