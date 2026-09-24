import pickle, pandas as pd, numpy as np
o=pickle.load(open('cache/objects.pkl','rb'))
s=o['iursa']; n=o['nat67']; rt=o['nat_sa_rt']; st=o['state_sa_rt']
iur_gap=s-s.rolling(52,min_periods=52).min().shift(1)
iur4=s.rolling(4).mean(); iur4_gap=iur4-iur4.rolling(52,min_periods=52).min().shift(1)
ic4=n['ic_sa'].rolling(4).mean(); ic4_rise=(ic4/ic4.rolling(52,min_periods=52).min().shift(1)-1)*100
ic4rt=rt['ic_sa_rt'].rolling(4).mean(); ic4rt_rise=(ic4rt/ic4rt.rolling(52,min_periods=52).min().shift(1)-1)*100
cc4=n['cc_sa'].rolling(4).mean(); cc4_rise=(cc4/cc4.rolling(52,min_periods=52).min().shift(1)-1)*100
cc4rt=rt['cc_sa_rt'].rolling(4).mean(); cc4rt_rise=(cc4rt/cc4rt.rolling(52,min_periods=52).min().shift(1)-1)*100
# leg C's breadth object: 13-wk mean of log SA state claims*100, >= 25 above its 104-wk min, share of states
K=st.rolling(13).mean()*100.0 if st.abs().max().max()<20 else np.log(st).rolling(13).mean()*100.0
print('state file sample values:',st.iloc[-1,:3].round(3).tolist())
S=K-K.rolling(104,min_periods=52).min()
breadth=((S>=25).sum(axis=1)/S.notna().sum(axis=1)*100.0)
df=pd.concat([iur_gap.rename('iur_gap'),iur4_gap.rename('iur4_gap'),ic4_rise.rename('ic4_rise%'),ic4rt_rise.rename('ic4rt_rise%'),cc4_rise.rename('cc4_rise%'),cc4rt_rise.rename('cc4rt_rise%'),breadth.rename('breadth%')],axis=1)
M=df.resample('MS').max()
def show(a,b): print(M[a:b].round(2).to_string())
print("== 2023-01 .. 2025-06 (monthly max of weekly objects) =="); show('2023-01','2025-06')
print("\n== Nov 1976 false alarm neighbourhood =="); show('1976-05','1977-04')
print("\n== 2003 false alarm neighbourhood =="); show('2002-12','2003-12')
print("\n== 1967 disturbance =="); show('1966-09','1967-12')
print("\n== peak windows: max of each object inside [peak-6, peak+6] ==")
PK=o['PK']+[pd.Timestamp('2024-04-01')]
rows=[]
for p in PK:
    seg=M[(M.index>=p-pd.DateOffset(months=6))&(M.index<=p+pd.DateOffset(months=6))]
    rows.append(pd.Series(seg.max(),name=p.strftime('%Y-%m')))
print(pd.DataFrame(rows).round(2).to_string())
pickle.dump(dict(M=M,df=df),open('cache/claims_objects.pkl','wb'))
