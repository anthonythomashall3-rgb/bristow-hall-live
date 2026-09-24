"""South Africa: OECD Key Economic Indicators, and the OECD's ratio-to-trend reference
series, for the SARB's growth-cycle chronology."""
import csv, io, os, subprocess
OUT='/home/claude/lab/kei'
BASE='https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_KEI@DF_KEI,4.0/'
raw=open('/tmp/zaf_kei.csv').read()
rows=list(csv.DictReader(io.StringIO(raw)))
print('rows',len(rows))
def write(sel, name):
    ser=sorted((r['TIME_PERIOD'], r['OBS_VALUE']) for r in sel if r.get('OBS_VALUE'))
    if len(ser)<120: print(f'{name}: only {len(ser)}'); return
    p=f'{OUT}/ZAF_{name}.csv'
    with open(p,'w') as g:
        g.write('date,value\n')
        for d,v in ser: g.write(f'{d}-01,{v}\n')
    print(f'{name}: {ser[0][0]} .. {ser[-1][0]}  n={len(ser)} -> {p}')
JOBS=[('PRVM','C','Y','_Z','IX','PRVM_C'),
      ('PRVM','BTE','Y','_Z','IX','PRVM_BTE'),
      ('PRVM','B_TO_E','Y','_Z','IX','PRVM_BTE'),
      ('TOVM','G47','Y','_Z','IX','TOVM_G47'),
      ('EMP','_T','Y','_Z','IX','EMP__T'),
      ('UNEMP','_T','Y','_Z','PT_LF_SUB','UNEMP__T'),
      ('TOCAPA','G45','Y','_Z','IX','TOCAPA_G45'),
      ('EX','_T','Y','_Z','IX','EX__T'),
      ('IM','_T','Y','_Z','IX','IM__T'),
      ('RS','_T','RT','_Z','IX','RS__T'),
      ('RS','_T','NOR','_Z','IX','RSNOR'),
      ('RS','_T','T','_Z','IX','RSTREND')]
for meas,act,adj,tr,um,name in JOBS:
    sel=[r for r in rows if r.get('MEASURE')==meas and r.get('ACTIVITY')==act
         and r.get('ADJUSTMENT')==adj and r.get('TRANSFORMATION')==tr]
    if um: sel=[r for r in sel if r.get('UNIT_MEASURE')==um] or sel
    if sel: write(sel,name)
    else: print(f'{name}: nothing')
