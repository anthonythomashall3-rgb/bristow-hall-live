"""The United Kingdom on national series (ONS via DBnomics, lab/nat/gbr), against ECRI's
chronology — the panel §8e's 'Every chronology' paragraph said the next pass would fill.
Level route at the shipped configuration; nothing about the United Kingdom entered any choice.
Channels: ONS Index of Production B-E (1948) and manufacturing (1948), retail sales volume
(ONS from 1996; the OECD's longer series from 1957 beside it), LFS employment 16+ (1971),
monthly GVA (1997).  Unemployment and claimant counts are rate channels the level route does
not read (the shipped SKIP), and are shown only as a diagnostic."""
import sys, json, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/cmp')
import pandas as pd, numpy as np
import bristow_rule_v3 as B, bench
from bench import date_any, pro
from ecri_countries import contractions, run, cnt, K, ecri
NAT='/home/claude/lab/nat/gbr'
def load(f): return pd.read_csv(f,index_col=0,parse_dates=True).iloc[:,0].dropna().astype(float)
bench.PANELS.setdefault('United Kingdom',{'ch':[],'chrono':[],'freq':'M'}); bench.CONCEPT['United Kingdom']='level'
chron=contractions(ecri['United Kingdom'])   # ECRI's July 2021 table: 1974-75, 1979-81, 1990-92, 2008-10 (trough January 2010), 2019-20
oecd=[(nm,pro(p,kind)) for nm,p,kind in bench.kei('GBR') if nm in ('industrial production','manufacturing production','retail volume')]
nat=[('industrial production (ONS)',load(f'{NAT}/GBR_industrial_production.csv')),
     ('manufacturing production (ONS)',load(f'{NAT}/GBR_manufacturing_production.csv')),
     ('retail volume (ONS)',load(f'{NAT}/GBR_retail_volume.csv')),
     ('employment (ONS LFS)',load(f'{NAT}/GBR_employment.csv')),
     ('monthly GVA (ONS)',load(f'{NAT}/GBR_monthly_gva.csv'))]
panels={'OECD channels, as in §8e':oecd,
        'ONS national panel':nat,
        'ONS national panel with the OECD retail series (1957)':nat+[('retail volume (OECD)',dict(oecd)['retail volume'])]}
for label,chs in panels.items():
    print(f'\n### {label}: {[(nm,str(s.index.min().date())[:7]) for nm,s in chs]}')
    rows,ep,et=run('GBR','United Kingdom',chron,chs)
    print(f"ECRI, {len(chron)} contractions: peaks {cnt(ep)} | troughs {cnt(et)}")
    for r in rows: print('   ',r)
