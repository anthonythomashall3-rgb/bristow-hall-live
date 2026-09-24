"""Build a real-time vintage record for Japan from ESRI's own monthly releases.

Each monthly release PDF carries the coincident CI back to 1997 as published that
month.  Collecting them gives what no public archive supplies for Japan: the index
as it stood at each date, so the recognition lag can be measured in real time
rather than on the final vintage.
"""
import os, re, subprocess, json
OUT='/home/claude/lab/esri_vint'; os.makedirs(OUT,exist_ok=True)
BASE='https://www.esri.cao.go.jp/jp/stat/di/'
got=[]
for y in range(2022,2027):
    for m in range(1,13):
        ym=f'{y}{m:02d}'
        pdf=f'{OUT}/{ym}.pdf'
        if not os.path.exists(pdf):
            r=subprocess.run(['curl','-sS','-A','Mozilla/5.0','--max-time','90','-o',pdf,'-w','%{http_code}',
                              f'{BASE}{ym}report.pdf'],capture_output=True,text=True)
            if r.stdout.strip()!='200' or os.path.getsize(pdf)<50000:
                os.remove(pdf); continue
        got.append(ym)
print('downloaded',len(got),got[:6],'...',got[-3:] if got else '')
# extract the coincident CI table from each
vint={}
for ym in got:
    txt=f'{OUT}/{ym}.txt'
    if not os.path.exists(txt):
        subprocess.run(['pdftotext','-layout',f'{OUT}/{ym}.pdf',txt],capture_output=True)
    t=open(txt,encoding='utf-8',errors='replace').read()
    # The CI time-series table: '(2) 一 致 指 数  Coincident Index', then one row per
    # year labelled with the Japanese era year and the last two digits of the
    # Western year, and twelve monthly values.
    js=[m.start() for m in re.finditer(r'\(2\)\s*一\s*致\s*指\s*数',t)]
    rows={}
    for j in js:
        seg2=t[j:j+6000]
        if 'Coincident Index' not in seg2[:200]: continue
        got={}
        for m in re.finditer(r'^\s*(?:[HRS]?\d+/)?(\d{2})\s+((?:\d+\.\d+\s+){5,11}\d+\.\d+)\s*$',seg2,re.M):
            yy=int(m.group(1)); yr=1900+yy if yy>=90 else 2000+yy
            for k,v in enumerate(m.group(2).split()):
                got[f'{yr}-{k+1:02d}']=float(v)
        if len(got)>len(rows): rows=got
    if rows: vint[ym]=rows
json.dump(vint,open(f'{OUT}/vintages.json','w'))
print('vintages with a coincident table:',len(vint))
for k in list(vint)[:3]:
    r=vint[k]; ks=sorted(r)
    print(' ',k,'n=',len(r),ks[0],ks[-1])
