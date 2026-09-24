"""Does the diffusion index the C.D. Howe Council names date Canada's turning points?"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd, json
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
DI=pd.read_csv('/home/claude/lab/statcan/CA_gdp_diffusion.csv',index_col=0,parse_dates=True)['value']
# the industry panels themselves, for a historical DI
def build_panels():
    SICN=None
    d=pd.read_csv('/home/claude/lab/statcan/36100378/36100378.csv',low_memory=False)
    m=pd.read_csv('/home/claude/lab/statcan/36100378/36100378_MetaData.csv',low_memory=False,
                  on_bad_lines='skip',header=None,dtype=str)
    mem=m[(m[0]=='2')&(m[3].notna())]
    nb={int(r[3]):r[1] for _,r in mem.iterrows()}
    keep={nb[k] for k in (1,4,7,10,25,127,130,142,146,151,154,157,167,200)}
    d=d[(d['Seasonal adjustments']=='Seasonally adjusted at annual rates')&
        (d['Prices']=='1986 constant prices')&(d['Gross domestic product (GDP)'].isin(keep))]
    A=d.pivot_table(index='REF_DATE',columns='Gross domestic product (GDP)',values='VALUE')
    A.index=pd.to_datetime(A.index+'-01'); A=A.sort_index()
    sec=json.load(open('/home/claude/lab/statcan/naics2.json')); wn={s['name'] for s in sec}
    d2=pd.read_csv('/home/claude/lab/statcan/36100434/36100434.csv',low_memory=False)
    col=[c for c in d2.columns if c.startswith('North American')][0]
    d2=d2[(d2['Seasonal adjustment']=='Seasonally adjusted at annual rates')&
          (d2['Prices']=='Chained (2017) dollars')]
    d2['nm']=d2[col].str.replace(r'\s*\[.*\]$','',regex=True)
    d2=d2[d2['nm'].isin(wn)]
    B=d2.pivot_table(index='REF_DATE',columns='nm',values='VALUE')
    B.index=pd.to_datetime(B.index+'-01'); B=B.sort_index()
    return A,B
A,B=build_panels()
CH_A=[(c,A[c].dropna()) for c in A.columns]
CH_B=[(c,B[c].dropna()) for c in B.columns]
print('panels', len(CH_A), len(CH_B))
for _e in PANELS['Canada']['chrono']:
    pk_off,tr_off,freq=ep3(_e,'M')
    pkm=ts(pk_off); trm=ts(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    if DI.index.min()>w0: print(f'{pk_off}/{tr_off}  before 1961'); continue
    chs = CH_A if trm < pd.Timestamp('1997-01-01') else CH_B
    hdi = hist_di([(n,s) for n,s in chs if s.index.min()<=w0 and s.index.max()>=trm], 3)
    out=[]
    for n_s in (3,6,9,12):
        d=ma(DI,n_s)
        tr=ch_trough(d,w0,w1,0.30,1,12,abstain=False,where='last')
        _,e=hit(tr,tr_off,'M'); out.append(f'mom{n_s}:{e}')
    if hdi is not None:
        tr=ch_trough(hdi+1.0,w0,w1,0.30,3,12,abstain=False,where='last')
        _,e=hit(tr,tr_off,'M'); out.append(f'histDI:{e}')
        pk=di_peak_first(hdi,w0,tr if tr is not None else w1,45.,4)
        _,e2=hit(pk,pk_off,'M'); out.append(f'histDIpeak:{e2}')
    print(f'{pk_off}/{tr_off}  trough errors: '+'  '.join(out))
