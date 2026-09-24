"""Every number added in version 19, re-derived and checked against the memo."""
import sys; sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude')
import bench
from bench import *
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
M=open('/home/claude/Paper1.5_Bristow_Rule_Evidence_Memo.md').read()
ok=bad=0
def chk(l,c,d=''):
    global ok,bad
    if c: ok+=1; print(f'  OK   {l}')
    else: bad+=1; print(f'  FAIL {l}  {d}')
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
print('=== the shipped sample')
tp=tt=n=0; per={}
for c in ALL:
    r=run_country_concept(c,**K); cfg=PANELS[c]
    hp=ht=0
    for i,_e in enumerate(cfg['chrono']):
        pk,tr,f2=ep3(_e,cfg['freq'])
        a,_=hit(r[i]['pk'],pk,f2); b,_=hit(r[i]['tr'],tr,f2); hp+=a; ht+=b
    m=len(cfg['chrono']); n+=m; tp+=hp; tt+=ht; per[c]=(hp,ht,m)
print(f'   total {tp}/{n} peaks, {tt}/{n} troughs')
chk('78/83 peaks', tp==78 and '78/83' in M)
chk('80/83 troughs (79/83 before version 23)', tt==80 and '80/83' in M)
chk('Korea 10/11 peaks and 10/11 troughs (9/11 before version 23)', per['Korea'][:2]==(10,10))
chk('Spain 6/6 at both ends', per['Spain'][:2]==(6,6))
print('=== the Korean object')
co=load('/home/claude/lab/kor/KOR_coincident_cyclical.csv')
chk('Korea\'s coincident cyclical component is monthly from 1970-01',
    str(co.index.min().date())=='1970-01-01' and len(co)>=678)
print('=== the Spanish channels')
for nm,first in [('cement_production','1955-01-01'),('steel_production','1968-01-01'),
                 ('gasoline_consumption','1969-01-01'),('diesel_consumption','1969-01-01')]:
    s_=load(f'/home/claude/lab/esp/ESP_{nm}.csv')
    chk(f'{nm} begins {first}', str(s_.index.min().date())==first)
print('=== the German chronology, from the Council\'s own workbook')
import openpyxl
w=openpyxl.load_workbook('/home/claude/lab/deu/bcd.xlsx',data_only=True)['Business Cycles']
rows=[[c for c in r if c is not None] for r in w.iter_rows(values_only=True)]
dates=[r for r in rows if r and isinstance(r[0],str) and any(y in r[0] for y in ('19','20')) and '(' in r[0]]
chk('seven German contractions in the workbook', len(dates)==7, str(len(dates)))
chk('the first is March 1966 to May 1967', dates[0][0].startswith('March 1966') and dates[0][1].startswith('May 1967'))
print('=== the Mexican chronology, from the committee\'s own page')
import re as _re
h=open('/home/claude/lab/mex/923f78b4.html',encoding='utf-8',errors='replace').read()
h=_re.sub(r'<script.*?</script>','',h,flags=_re.S); h=_re.sub(r'<[^>]+>',' ',h)
h=h.replace('&nbsp;',' '); h=_re.sub(r'\s+',' ',h)
for tok in ['Diciembre 1981','Junio 1983','Septiembre 1985','Noviembre 1994','Septiembre 2000',
            'Junio 2008','Mayo 2019','Mayo 2020']:
    chk(f'"{tok}" is on the committee\'s page', tok in h)
print('=== the tool')
import bristow_rule_v3 as B3
n=B3.self_test(verbose=False)
chk(f'the tool self-test passes all {n} of its checks', n>=39)
import bench as _bench
chk('the benchmark panels match the channel manifest',
    _bench.manifest_check(strict=False, verbose=False)==[])
import subprocess as _sp, sys as _sys
_r=_sp.run([_sys.executable,'/home/claude/lab/reproduce.py'],capture_output=True,text=True,
           cwd='/home/claude/lab',timeout=3600)
chk('reproduce.py reproduces the whole record', _r.returncode==0)
print()
print(f'=== {ok} checks passed, {bad} failed')
