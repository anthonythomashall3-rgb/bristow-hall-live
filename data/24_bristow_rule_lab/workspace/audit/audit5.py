import pandas as pd, numpy as np
def L(n):
    d=pd.read_csv(n+'.csv',parse_dates=['observation_date']); d.columns=['date','v']
    d['v']=pd.to_numeric(d.v,errors='coerce'); return d.dropna().reset_index(drop=True)
o=L('JTSJOL'); lf=L('CLF16OV'); u=L('UNRATE').set_index('date').v
m=o.merge(lf,on='date',suffixes=('_o','_l')); m['vr']=100*m.v_o/m.v_l; m=m.set_index('date')
mm=m.join(u.rename('u'),how='inner')
mm['u3']=mm.u.rolling(3).mean(); mm['v3']=mm.vr.rolling(3).mean()
mm['uh']=mm.u3-mm.u3.rolling(12).min(); mm['vh']=mm.v3.rolling(12).max()-mm.v3
s=mm.loc['2024-01-01':'2024-12-01',['uh','vh']].round(3)
s['binding']=np.where(s.uh<=s.vh,'unemployment','vacancy')
print(s.to_string())
print()
print("months in 2024 where unemployment is the binding (smaller) channel:", (s.binding=='unemployment').sum(), "of", len(s))
print("vh min 2024:", round(s.vh.min(),2), "  vh max 2024:", round(s.vh.max(),2))
print("vh min over Apr-Dec 2024:", round(s.loc['2024-04-01':'2024-12-01','vh'].min(),2))
print("vh range Jun-Sep 2024:", round(s.loc['2024-06-01':'2024-09-01','vh'].min(),2), "-", round(s.loc['2024-06-01':'2024-09-01','vh'].max(),2))
print("vh min 2024 as multiple of 0.29:", round(s.vh.min()/0.29,2))
# payrolls
p=L('PAYEMS').set_index('date').v
print()
print("PAYEMS 2021-12:",p['2021-12-01'],"2022-06:",p['2022-06-01'],"change %:",round(100*(p['2022-06-01']/p['2021-12-01']-1),2))
print("PAYEMS ever falls 2022-2024?", (p['2022-01-01':'2024-12-01'].diff()<0).sum(), "monthly declines")
