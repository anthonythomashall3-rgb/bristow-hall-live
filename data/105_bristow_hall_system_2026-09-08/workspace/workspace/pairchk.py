from mini import *
lhs=(lh.rolling(12).max()-lh.rolling(2).mean())/35.0; rhs=(UR-UR.rolling(12).min())/0.20
df=pd.concat([UR.rename('UR'),UR.rolling(12).min().rename('min12'),rhs.rename('rate_half'),lhs.rename('hous_half'),PAIR.rename('pair')],axis=1)
with open('pairchk.out','w') as f:
    for m in ['1966-07','1966-08','1966-10','1973-11','1981-08','1995-11','1995-12','2007-01','1990-08','2008-01']:
        t=pd.Timestamp(m+'-01'); r=df.loc[t]
        f.write(f"{m} UR {r.UR} min {r.min12} rate_half {r.rate_half:.17f} hous {r.hous_half:.4f} pair {r.pair:.17f} {'FIRES' if r.pair>=1.0 else 'no'}\n")
