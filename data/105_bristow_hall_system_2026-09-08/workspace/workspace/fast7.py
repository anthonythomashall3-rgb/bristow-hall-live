from mini import *
from hub import leg_X2
from legu_min import s_cur, spl, iur_fp
exec(open('fast6.py').read().split("KJHS={k:TLG[k] for k in 'KJHS'}")[0].split("out=open('fast6.out','w')")[1].replace("P(","(lambda *a: None)(") if False else "")
# rebuild the objects (breadth, gaps) quietly
d=pd.read_csv(W+'/lab/dol/ar539.csv',low_memory=False); d['week']=pd.to_datetime(d['c2'],errors='coerce'); d=d[d['week'].notna()&d['st'].notna()]; d=d[~d['st'].isin(['PR','VI'])]
CW=d.pivot_table(index='week',columns='st',values='c8',aggfunc='first').sort_index().apply(pd.to_numeric,errors='coerce').resample('W-SAT').last()
S8=CW.rolling(8).sum(); Y=np.log(S8)-np.log(S8.shift(52)); BR=((Y>=0.10).sum(axis=1)/Y.notna().sum(axis=1)*100.0).dropna()
def gapof(s): return (s-s.rolling(52,min_periods=52).min().shift(1)).dropna()
gap_cur=gapof(s_cur); gap_fp=gapof(spl)
print("IUR gap, first-print splice vs current file, 2023-01..2024-12 monthly max:")
print(pd.concat([gap_cur.rename('current'),gap_fp.rename('first print')],axis=1)['2022-10':'2024-12'].resample('MS').max().round(2).T.to_string())
print("\nweeks where the FIRST-PRINT gap >= 0.25 outside the recession windows, 2002 on:")
q=[(t.strftime('%Y-%m-%d'),round(v,2)) for t,v in gap_fp['2002-11':].items() if v>=0.25 and not any(p-pd.DateOffset(months=6)<=t<=tt+pd.DateOffset(months=18) for p,tt in zip(PK,TR))]
print(q)
print("\nyoy breadth 2023 monthly max:",BR['2023-01':'2024-06'].resample('MS').max().round(0).tolist())
print("housing pair 2023-01..2024-06:",PAIR['2023-01':'2024-06'].round(2).tolist())
