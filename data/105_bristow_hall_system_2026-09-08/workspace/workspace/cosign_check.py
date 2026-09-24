import sys,pickle,io,contextlib
sys.argv=['cosign_check.py','1962','2026','mchk']
src=open('walk42.py').read().split('# ---- the walk itself')[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
import pandas as pd
p=pickle.load(open('cache/w42_carry.pkl','rb'))
# U leg: the insured rate's gap over its 52-week low, by release day
gap=(spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna()
for t,v in gap.items():
    d=rel_iu(t)
    if d is not None and pd.Timestamp('2001-02-15')<=d<=pd.Timestamp('2001-04-15'): print('U',t.date(),'rel',d.date(),'gap %.3f'%v,'line 0.45 band 0.2 strong 0.65','cosign',cosign(d))
m4=ICfp.dropna().rolling(4).mean(); rel_=((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()
for t,v in rel_.items():
    d=rel_ic(t)
    if d is not None and (pd.Timestamp('2001-02-15')<=d<=pd.Timestamp('2001-04-15') or pd.Timestamp('2020-03-01')<=d<=pd.Timestamp('2020-04-10')): print('I',t.date(),'rel',d.date(),'pct %.1f'%v,'line 40 band 15 strong 55','cosign',cosign(d))
print('gpub around 2001:',gpub[(gpub.index>='2000-12-01')&(gpub.index<='2001-05-01')].to_dict())
print('gpub around 1990:',gpub[(gpub.index>='1990-05-01')&(gpub.index<='1990-10-01')].to_dict())
print('gpub around 2020:',gpub[(gpub.index>='2020-02-01')&(gpub.index<='2020-05-15')].to_dict())
