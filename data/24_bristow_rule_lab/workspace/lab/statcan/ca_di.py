"""The diffusion index the C.D. Howe Council names: "a diffusion index for GDP, which
Statistics Canada formerly calculated, that shows the percentage of industries that expand
output in a particular month."  Built from Statistics Canada's own monthly GDP by industry:
table 36-10-0378 (SIC 1980 divisions, 1961-1997) chained to 36-10-0434 (NAICS two-digit
sectors, 1997-present)."""
import pandas as pd, numpy as np, json
SIC={1:'Agriculture',4:'Fishing and trapping',7:'Logging and forestry',
     10:'Mining, quarrying and oil wells',25:'Manufacturing',127:'Construction',
     130:'Transportation and storage',142:'Communication',146:'Other utilities',
     151:'Wholesale trade',154:'Retail trade',157:'Finance, insurance and real estate',
     167:'Community, business and personal services',200:'Government services'}
m=pd.read_csv('36100378/36100378_MetaData.csv',low_memory=False,on_bad_lines='skip',header=None,dtype=str)
mem=m[(m[0]=='2')&(m[3].notna())]
name_by_mid={int(r[3]):r[1] for _,r in mem.iterrows()}
want={name_by_mid[k] for k in SIC}
print('SIC divisions:',len(want))
d=pd.read_csv('36100378/36100378.csv',low_memory=False)
d=d[(d['Seasonal adjustments']=='Seasonally adjusted at annual rates')&
    (d['Prices']=='1986 constant prices')&
    (d['Gross domestic product (GDP)'].isin(want))][['REF_DATE','Gross domestic product (GDP)','VALUE']]
A=d.pivot_table(index='REF_DATE',columns='Gross domestic product (GDP)',values='VALUE')
A.index=pd.to_datetime(A.index+'-01'); A=A.sort_index()
print('SIC panel',A.shape,A.index.min().date(),A.index.max().date())

sec=json.load(open('naics2.json')); wn={s['name'] for s in sec}
d2=pd.read_csv('36100434/36100434.csv',low_memory=False)
col=[c for c in d2.columns if c.startswith('North American')][0]
d2=d2[(d2['Seasonal adjustment']=='Seasonally adjusted at annual rates')&
      (d2['Prices']=='Chained (2017) dollars')]
d2['nm']=d2[col].str.replace(r'\s*\[.*\]$','',regex=True)
d2=d2[d2['nm'].isin(wn)][['REF_DATE','nm','VALUE']]
B=d2.pivot_table(index='REF_DATE',columns='nm',values='VALUE')
B.index=pd.to_datetime(B.index+'-01'); B=B.sort_index()
print('NAICS panel',B.shape,B.index.min().date(),B.index.max().date())

def di(P):
    g=P.diff()
    up=(g>0).sum(axis=1); n=g.notna().sum(axis=1)
    return (up/n*100.0).where(n>=5)
dA=di(A).dropna(); dB=di(B).dropna()
cut=dB.index.min()
CA_DI=pd.concat([dA[dA.index<cut],dB]).sort_index()
CA_DI.to_csv('/home/claude/lab/statcan/CA_gdp_diffusion.csv',header=['value'])
print('diffusion index',CA_DI.index.min().date(),CA_DI.index.max().date(),len(CA_DI))
print(CA_DI['1990-06':'1992-12'].round(1).to_string())
