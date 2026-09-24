"""THE MONEY-MARKET SPREAD, EXAMINED PROPERLY. The one-month commercial paper rate over the three-month Treasury bill,
read as its rise above its lowest value of the previous six months, buys 1969, 1980, 2001 and 2007 at its
construction-grade line. Before it can be adopted it needs what every other object in this rule needed: the full
distribution of quiet readings (not just the maximum), the plateau of each gain, the 2025-26 reading, and a causal
replay that re-chooses the line from the record before each turn."""
exec(open('daily13.py').read().split('P("SPREADS BUILT AND SCREENED')[0].replace("out=open('daily13.out','w')","out=open('daily14.out','w')"))
def spread(a,b):
    aa=L25(a); bb=L25(b); idx=aa.index.union(bb.index)
    S=(aa.reindex(idx).ffill()-bb.reindex(idx).ffill()).dropna(); return S[S.index>=max(aa.index.min(),bb.index.min())]
SP={'CP1m-bill3m':spread('H0RIFSPPFM01NWF','WTB3MS'),'BA3m-bill3m':spread('H1RIFSPABM03NWF','WTB3MS'),
    'CP3m-bill3m':spread('H0RIFSPPFM03NWF','WTB3MS'),'CP3m-funds':spread('H0RIFSPPFM03NWF','FF')}
for nm,S in SP.items():
    per=max(1,int(round(float(np.median(np.diff(S.index.values).astype('timedelta64[D]').astype(int))))))
    win=max(4,int(6*30/per)); GG=(S-S.rolling(win).min()).dropna()
    qs=sorted([(float(wseg(GG,dd).max()),dd.strftime('%Y-%m')) for dd in QP if len(wseg(GG,dd))],reverse=True)
    P(f"\n{nm}: {S.index.min().date()} -> {S.index.max().date()}, weekly, published the next day; six-month rise")
    P(f"   quiet readings, highest first: {[(round(a,2),b) for a,b in qs[:8]]}")
    P(f"   covers {len(qs)} of {len(QP)} quiet proposal windows")
    P(f"   recession-window maxima: {[(PK[i].strftime('%Y-%m'),round(float(wseg(GG,PK[i]).max()),2) if len(wseg(GG,PK[i])) else None) for i in range(13)]}")
    P(f"   2025-26 maximum {float(GG[GG.index>=pd.Timestamp('2025-01-01')].max()):.3f}; share of all weeks at or above the construction line {(GG>=qs[0][0]*1.02).mean()*100:.2f} per cent")
P("\n=== fine line sweep, CP1m-bill3m six-month rise (where each gain lives) ===")
S=SP['CP1m-bill3m']; per=max(1,int(round(float(np.median(np.diff(S.index.values).astype('timedelta64[D]').astype(int))))))
G6=(S-S.rolling(max(4,int(6*30/per))).min()).dropna()
for ln in [1.40,1.50,1.54,1.56,1.60,1.65,1.70,1.75,1.80,1.85,1.90,1.95,2.00]:
    go9(f'CP1m-bill3m 6m >= {ln}',[CRED,dict(name='cpb',gap=G6,line=ln,pub_lag_days=1)])
P("\n=== the same object over other windows, at each window's own construction-grade line ===")
for wmon in [3,9,12,18,26]:
    win=max(4,int(wmon*30/per)); Gw=(S-S.rolling(win).min()).dropna()
    qm_=max([float(wseg(Gw,dd).max()) for dd in QP if len(wseg(Gw,dd))])
    for mult in [1.02,1.10,1.25]:
        go9(f'CP1m-bill3m {wmon}m >= {qm_*mult:.3f}',[CRED,dict(name='cpb',gap=Gw,line=qm_*mult,pub_lag_days=1)])
P("\n=== the bankers-acceptance spread (data from 1954, so it reaches 1957 and 1960) ===")
S2=SP['BA3m-bill3m']; per2=max(1,int(round(float(np.median(np.diff(S2.index.values).astype('timedelta64[D]').astype(int))))))
G62=(S2-S2.rolling(max(4,int(6*30/per2))).min()).dropna()
for ln in [1.70,1.76,1.80,1.90,2.00,2.10,2.20]:
    go9(f'BA3m-bill3m 6m >= {ln}',[CRED,dict(name='bab',gap=G62,line=ln,pub_lag_days=1)])
out.close()
