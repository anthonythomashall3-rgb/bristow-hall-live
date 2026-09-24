"""Euro-area aggregates for the years before the OECD publishes an EA series.

Each aggregate is a weighted geometric mean of the member-state indices, weights
being 2019 shares of euro-area GDP (Eurostat nama_10_gdp).  Members enter as their
data begin; the chain-linked construction means an entry causes no jump.
"""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/claude/lab')
KEI='/home/claude/lab/kei'
W={'DEU':0.293,'FRA':0.205,'ITA':0.153,'ESP':0.104,'NLD':0.070,'BEL':0.041,
   'AUT':0.034,'IRL':0.031,'FIN':0.021,'PRT':0.018,'GRC':0.016}

def load(p):
    d=pd.read_csv(p); d.columns=['d','v']
    d['d']=pd.to_datetime(d.d); d['v']=pd.to_numeric(d.v,errors='coerce')
    return d.dropna().set_index('d')['v'].astype(float).sort_index()

def agg(field):
    cols={}; wts={}
    for a,w in W.items():
        p=f'{KEI}/{a}_{field}.csv'
        if os.path.exists(p):
            cols[a]=np.log(load(p)).diff(); wts[a]=w
    if len(cols)<3: return None
    D=pd.DataFrame(cols)
    Wm=pd.DataFrame({a:np.where(D[a].notna(), wts[a], np.nan) for a in D}, index=D.index)
    num=(D*Wm).sum(axis=1, skipna=True); den=Wm.sum(axis=1, skipna=True)
    g=(num/den).where(den>0.30)                      # members covering at least 30% of the area
    g=g[g.first_valid_index():]
    s=np.exp(g.fillna(0.0).cumsum())*100.0
    return s

if __name__=='__main__':
    for field in ['PRVM_BTE','PRVM_C','PRVM_F','TOVM_G47','TOCAPA_G45','IM__T','EX__T','UNEMP__T']:
        s=agg(field)
        if s is None: print(field,'skipped'); continue
        fn=f'{KEI}/EAAGG_{field}.csv'
        with open(fn,'w') as g:
            g.write('date,value\n')
            for d,v in s.items(): g.write(f'{d.strftime("%Y-%m-%d")},{v:.4f}\n')
        print(f'EAAGG {field}: {s.index.min():%Y-%m} .. {s.index.max():%Y-%m}  n={len(s)}')
