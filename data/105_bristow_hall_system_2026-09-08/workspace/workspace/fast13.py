"""The housing x rate pair's two halves: which half arrives last at each recession, and a lagged-housing form."""
from mini import *
lhs=(lh.rolling(12).max()-lh.rolling(2).mean())/35.0; rhs=(UR-UR.rolling(12).min())/0.20
lh1=(lh.rolling(12).max()-lh)/35.0   # one-month housing reading
print("pair halves (>=1 marks at line), months around each peak; housing half public the 18th of m+1, rate half the 5th of m+1")
for p in [pd.Timestamp('1973-11-01'),pd.Timestamp('1980-01-01'),pd.Timestamp('1981-07-01'),pd.Timestamp('1990-07-01'),pd.Timestamp('2001-03-01'),pd.Timestamp('2007-12-01'),pd.Timestamp('2020-02-01'),pd.Timestamp('2024-04-01')]:
    seg=pd.concat([lhs.rename('hous2m'),lh1.rename('hous1m'),rhs.rename('rate')],axis=1)[p-pd.DateOffset(months=3):p+pd.DateOffset(months=4)]
    print(f"\n{p:%Y-%m}:"); print(seg.round(2).T.to_string())
# lagged-housing pair: housing half from m-1 (already public on the 18th of m), rate half from m (public 5th of m+1) -> public 5th of m+1
PAIR_LAG=pd.concat([lhs.shift(1),rhs],axis=1).min(axis=1).dropna()
PAIR_1M=pd.concat([lh1,rhs],axis=1).min(axis=1).dropna()
def inwin(d,back=6,fwd=18): return any(pp-pd.DateOffset(months=back)<=d<=t+pd.DateOffset(months=fwd) for pp,t in zip(PK,TR))
for nm,ser in [('pair as shipped',PAIR),('lagged-housing pair',PAIR_LAG),('one-month-housing pair',PAIR_1M)]:
    q=[m.strftime('%Y-%m') for m,v in ser.items() if v>=1.0 and not inwin(m) and m>=pd.Timestamp('1960-01-01')]
    first=[]
    for pp,t in zip(PK,TR):
        seg=ser[(ser.index>=pp-pd.DateOffset(months=6))&(ser.index<=t)]; h=seg[seg>=1.0]; first.append(md(h.index[0],pp) if len(h) else None)
    print(f"\n{nm}: quiet firings {q}; first at-line month vs peak {first}")
pickle.dump(dict(PAIR_LAG=PAIR_LAG,PAIR_1M=PAIR_1M),open('cache/pairs_alt.pkl','wb'))
