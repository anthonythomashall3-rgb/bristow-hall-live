"""Rule 4 (independent rulings) across the nine chronologies: ECRI (classical, July 2021 table; ECRI_TABLE=2010 selects the 2010 one), OECD growth-cycle
turning points (FRED xxxRECM), Bry-Boschan on the tool's own panel; US adds Chauvet-Piger, Hamilton, Philadelphia BB.
The rule's own errors come from rule17_sweep.json (smoothing 3 shipped; smoothing 1)."""
import sys, json, pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.argv=['x']
import bristow_rule_v3 as B, bench
import os
ECRI_TABLE=os.environ.get('ECRI_TABLE','2021')   # ECRI's July 2021 table (1948-2020) by default; '2010' for the September 2010 table
ecri=json.load(open(f'ecri_chronology_{ECRI_TABLE}.json'))
ECRI_NAME={'United States':None,   # ECRI's American dates are the NBER's by construction; excluded from the agreement counts
           'Canada':'Canada','Japan':'Japan','Korea':'Korea','Brazil':'Brazil','Spain':'Spain','France':'France','Euro area':None,'United States (interwar)':None}
OECD_FILE={'United States':'USARECM','Canada':'CANRECM','Japan':'JPNRECM','Korea':'KORRECM','Brazil':'BRARECM','Spain':'ESPRECM','France':'FRARECM','Euro area':'EURORECM','United States (interwar)':None}
def pairs_from_list(lst):
    ps=[];ts=[]
    for k,d in lst: (ps if k=='P' else ts).append(pd.Timestamp(d+'-01'))
    return sorted(ps), sorted(ts)
def oecd_pairs(f):
    u=pd.read_csv(f+'.csv'); u.columns=['d','v']; u['d']=pd.to_datetime(u.d); v=u.v.values; idx=list(u.d)
    ps=[];ts=[]; on=False; st=0
    for i in range(len(v)):
        if v[i]==1 and not on: on=True; st=i
        elif v[i]==0 and on:
            on=False
            if st>0: ps.append(idx[st-1])
            ts.append(idx[i-1])
    return ps,ts
def near(cands, ref, tol=9):
    if not cands: return None
    e=[B._md(c,ref) for c in cands]; k=int(np.argmin([abs(x) for x in e]))
    return e[k] if abs(e[k])<=tol else None
sweep=json.load(open('/home/claude/lab/rule17_sweep.json'))
per3={c:v for c,v in [r for r in sweep if r[0]=='smooth 3 | later | US all | no-unemp'][0][2].items()}
per1={c:v for c,v in [r for r in sweep if r[0]=='smooth 1 | later | US all | no-unemp'][0][2].items()}
# the shipped rule of version 23 (refinement clause on), computed live
bench.SKIP={'exports','imports','car registrations','unemployment','construction production','construction output',
            'capital goods production','intermediate goods production','consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
_K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
perR={}
for _c in bench.ALL:
    _r=bench.run_country_concept(_c,**_K)
    perR[_c]=([x['ep'] for x in _r],[x['et'] for x in _r])
tot={'n':0,'ecri_n':0,'ecri_cm':[], 'rule3_ecri':[], 'rule1_ecri':[], 'ruleR_ecri':[], 'rule3_cm':[], 'rule1_cm':[], 'ruleR_cm':[], 'bb_cm':[], 'oecd_cm':[]}
lines=[]
for c in bench.ALL:
    cfg=bench.PANELS[c]
    if cfg['freq']!='M' and not any(len(e)>2 and e[2]=='M' for e in cfg['chrono']): continue
    ep=ecri.get(ECRI_NAME.get(c)) if ECRI_NAME.get(c) else None
    eP,eT=pairs_from_list(ep) if ep else ([],[])
    oP,oT=oecd_pairs(OECD_FILE[c]) if OECD_FILE.get(c) else ([],[])
    chs=[(nm,s) for nm,s in bench.channels(c)]
    lines.append(f'\n### {c}\n\n| official peak / trough | ECRI peak / trough (err) | OECD growth-cycle (err) | Bry–Boschan on the panel (err) | rule, smoothing 3, before v23 (err) | rule, no smoothing (err) | **rule as shipped, v23** (err) |\n|---|---|---|---|---|---|---|')
    for i,_e in enumerate(cfg['chrono']):
        pk,tr,freq=bench.ep3(_e,cfg['freq'])
        if freq!='M': continue
        pkm=bench.ts(pk); trm=bench.ts(tr)
        ecp=near(eP,pkm); ect=near(eT,trm); ocp=near(oP,pkm); oct_=near(oT,trm)
        # BB on the panel
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12); bps=[];bts=[]
        for nm,s in chs:
            if s.index.min()>w0-pd.DateOffset(months=24) or s.index.max()<w1: continue
            try: tp=B.bry_boschan(s[w0-pd.DateOffset(months=24):w1+pd.DateOffset(months=24)].astype(float),smooth=3)
            except Exception: continue
            pp=[d for d,k in tp if k=='P' and w0<=d<=w1]; tt=[d for d,k in tp if k=='T' and w0<=d<=w1]
            if pp: bps.append(min(pp,key=lambda d:abs(B._md(d,pkm))))
            if tt: bts.append(min(tt,key=lambda d:abs(B._md(d,trm))))
        bbp=B._median(bps) if bps else None; bbt=B._median(bts) if bts else None
        bbe=(None if bbp is None else B._md(bbp,pkm), None if bbt is None else B._md(bbt,trm))
        r3=(per3[c][0][i],per3[c][1][i]); r1=(per1[c][0][i],per1[c][1][i]); rR=(perR[c][0][i],perR[c][1][i])
        f=lambda x: '—' if x is None else f'{x:+d}'
        lines.append(f'| {pk} / {tr} | {f(ecp)} / {f(ect)} | {f(ocp)} / {f(oct_)} | {f(bbe[0])} / {f(bbe[1])} | {f(r3[0])} / {f(r3[1])} | {f(r1[0])} / {f(r1[1])} | **{f(rR[0])} / {f(rR[1])}** |')
        tot['n']+=1
        if ecp is not None and ect is not None:
            tot['ecri_n']+=1; tot['ecri_cm']+=[abs(ecp),abs(ect)]
            if r3[0] is not None and r3[1] is not None: tot['rule3_ecri']+=[abs(r3[0]-ecp),abs(r3[1]-ect)]
            if r1[0] is not None and r1[1] is not None: tot['rule1_ecri']+=[abs(r1[0]-ecp),abs(r1[1]-ect)]
            if rR[0] is not None and rR[1] is not None: tot['ruleR_ecri']+=[abs(rR[0]-ecp),abs(rR[1]-ect)]
            if rR[0] is not None and rR[1] is not None: tot.setdefault('ruleR_cm_e',[]).extend([abs(rR[0]),abs(rR[1])])
            if r3[0] is not None and r3[1] is not None: tot.setdefault('rule3_cm_e',[]).extend([abs(r3[0]),abs(r3[1])])
        for k,v in (('rule3_cm',r3),('rule1_cm',r1),('ruleR_cm',rR),('bb_cm',bbe),('oecd_cm',(ocp,oct_))):
            tot[k]+=[abs(x) for x in v if x is not None]
open('rulings_all.md','w').write('\n'.join(lines))
def summ(v): 
    v=np.array(v); return f'n={len(v)} exact {int((v==0).sum())} within1 {int((v<=1).sum())} within3 {int((v<=3).sum())} mean {v.mean():.2f}' if len(v) else 'n=0'
print('contractions',tot['n'],'with an ECRI date at both ends',tot['ecri_n'])
print('ECRI vs committee     ', summ(tot['ecri_cm']))
print('OECD vs committee     ', summ(tot['oecd_cm']))
print('BB-panel vs committee ', summ(tot['bb_cm']))
print('rule s3 vs committee  ', summ(tot['rule3_cm']))
print('rule s1 vs committee  ', summ(tot['rule1_cm']))
print('rule v23 vs committee ', summ(tot['ruleR_cm']))
print('rule s3 vs ECRI       ', summ(tot['rule3_ecri']))
print('rule s1 vs ECRI       ', summ(tot['rule1_ecri']))
print('rule v23 vs ECRI      ', summ(tot['ruleR_ecri']))
print('rule v23 vs committee, ECRI-dated ends only', summ(tot['ruleR_cm_e']))
print('rule s3 vs committee, ECRI-dated ends only ', summ(tot['rule3_cm_e']))
