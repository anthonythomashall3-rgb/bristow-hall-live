import csv, io, os, subprocess
BASE='https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_KEI@DF_KEI,4.0/'
OUT='/home/claude/lab/kei'
WANT={'BCICP':('C','PB','business confidence'),'CCICP':('_Z','PB','consumer confidence')}
AREAS=['USA','CAN','JPN','KOR','BRA','ESP','FRA','DEU','ITA','NLD','BEL','AUT','FIN','EA20','EA19']
for a in AREAS:
    url=f'{BASE}{a}.M.......?startPeriod=1950-01&format=csvfilewithlabels'
    p=subprocess.run(['curl','-sS','--max-time','180','-A','Mozilla/5.0',url],capture_output=True)
    raw=p.stdout.decode('utf-8','replace')
    if not raw or raw.lstrip().startswith('<'): print(a,'fail'); continue
    rows=list(csv.DictReader(io.StringIO(raw)))
    made=[]
    for meas,(act,unit,nm) in WANT.items():
        keep=[r for r in rows if r.get('MEASURE')==meas and r.get('ACTIVITY')==act
              and r.get('UNIT_MEASURE')==unit and r.get('ADJUSTMENT') in ('Y','AA')
              and r.get('TRANSFORMATION') in ('_Z','')]
        if len(keep)<120: continue
        ser=sorted((r['TIME_PERIOD'],r['OBS_VALUE']) for r in keep if r.get('OBS_VALUE'))
        with open(f'{OUT}/{a}_{meas}.csv','w') as g:
            g.write('date,value\n')
            for d,v in ser: g.write(f'{d}-01,{v}\n')
        made.append(f'{meas}:{ser[0][0]}..{ser[-1][0]}({len(ser)})')
    print(a,'  '.join(made) if made else 'nothing')
