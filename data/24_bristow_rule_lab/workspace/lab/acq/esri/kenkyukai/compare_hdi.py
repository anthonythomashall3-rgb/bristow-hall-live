"""Pass A.4: ESRI's own per-component phases (parsed from the committee materials,
esri_hdi_components.csv, 2009-01 .. 2021-12) against the tool's Bry-Boschan phases on the
same components (lab/esri/JPN_*.csv, the series the bench's Japanese route reads).
Reports, per component, the months on which the two disagree and each side's turning
points; then the two diffusion indexes and the dates each gives by ESRI's own rule."""
import sys, pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bench, bristow_rule_v3 as B
E=pd.read_csv('esri_hdi_components.csv',parse_dates=['month'])
# one sign per (code, month): the latest file wins (later materials carry revised phases)
E['file_order']=E.file.str.extract(r'^(\d+)')[0].str[:6].astype(int)
E=E.sort_values(['code','month','file_order']).drop_duplicates(['code','month'],keep='last')
# ESRI code -> tool file (C4 is overtime hours before the 2020 revision, labor input after;
# C9 is the small-business shipments index in the 2015-2020 set and the job-offer rate before/after)
MAP={'C1':'industrial_production','C2':'producer_goods_shipments','C3':'durable_consumer_goods_shipments',
     'C5':'investment_goods_shipments','C6':'retail_sales_yoy','C7':'wholesale_sales_yoy','C8':'operating_profits'}
NAME_MAP={'有効求人倍率(除学卒)':'effective_job_offer_rate','労働投入量指数(調査産業計)':'labor_input','輸出数量指数':'exports_volume'}
def tool_phase(f, n=3):
    s=pd.read_csv(f'/home/claude/lab/esri/JPN_{f}.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
    tp=B.bry_boschan(s, n)
    idx=s.rolling(n,center=True).mean().dropna().index
    ph=pd.Series(np.nan,index=idx)
    for d,k in tp: ph[d]=0.0 if k=='P' else 1.0
    ph=ph.ffill(); ph[:tp[0][0]]=1.0 if tp[0][1]=='P' else 0.0
    return ph, tp
def esri_tp(sig):
    """turning points implied by ESRI's signs: last '+' before a '-' is a peak, last '-' before '+' a trough"""
    out=[]; s=sig.sort_index()
    for a,b in zip(s.index[:-1],s.index[1:]):
        if s[a]=='+' and s[b]=='-': out.append((a,'P'))
        if s[a]=='-' and s[b]=='+': out.append((a,'T'))
    return out
rows=[]
codes=sorted(E.code.unique(), key=lambda c:int(c[1:]))
for code in codes:
    sub=E[E.code==code]
    names=sub.name.unique()
    f=MAP.get(code)
    if f is None:
        for nm in names:
            for k,v in NAME_MAP.items():
                if k in nm: f=v
    if f is None: print(f'{code} {list(names)}: no tool series'); continue
    ph,tp=tool_phase(f)
    sig=sub.set_index('month').sign
    both=sig.index.intersection(ph.index)
    tool_sig=ph[both].map(lambda v:'+' if v==1.0 else '-')
    agree=(tool_sig==sig[both]).mean()*100
    etp=esri_tp(sig)
    ttp=[(d,k) for d,k in tp if sig.index.min()<=d<=sig.index.max()]
    print(f'\n== {code} {list(names)} -> {f}: agreement on {len(both)} months {agree:.0f}%')
    print('   ESRI turning points:', [(d.strftime("%Y-%m"),k) for d,k in etp])
    print('   tool turning points:', [(d.strftime("%Y-%m"),k) for d,k in ttp])
    dis=[d.strftime('%Y-%m') for d in both if tool_sig[d]!=sig[d]]
    if dis: print('   disagreeing months:', dis[:40], '...' if len(dis)>40 else '')
    rows.append((code,f,len(both),agree))
# the two indexes side by side at ESRI's reference months
print('\n== the diffusion index, ESRI (from its tables) vs the tool (same components where they exist)')
piv=E.pivot(index='month',columns='code',values='sign')
esri_di=(piv=='+').sum(axis=1)/piv.notna().sum(axis=1)*100
cols=[]
for code in codes:
    f=MAP.get(code)
    if f is None:
        for nm in E[E.code==code].name.unique():
            for k,v in NAME_MAP.items():
                if k in nm: f=v
    if f: cols.append(tool_phase(f)[0].rename(code))
tool_di=(pd.concat(cols,axis=1).mean(axis=1)*100)[esri_di.index.min():esri_di.index.max()]
for m in ['2009-01','2009-03','2009-05','2012-02','2012-03','2012-04','2012-05','2012-10','2012-11','2012-12','2014-03','2014-04','2018-09','2018-10','2018-11','2018-12','2019-06','2020-04','2020-05','2020-06','2020-07']:
    t=pd.Timestamp(m+'-01')
    print(f'   {m}: ESRI {esri_di.get(t,np.nan):5.1f}%  tool {tool_di.get(t,np.nan):5.1f}%')
