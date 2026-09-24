import csv, io, os, subprocess
BASE='https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_CLI,4.0/'
OUT='/home/claude/lab/kei'
AREAS=['KOR','JPN','USA','CAN','BRA','ESP','FRA','MEX','EA20','DEU','ITA','GBR']
for a in AREAS:
    url=f'{BASE}{a}.M.......?startPeriod=1950-01&format=csvfilewithlabels'
    p=subprocess.run(['curl','-sS','--max-time','180','-A','Mozilla/5.0',url],capture_output=True)
    raw=p.stdout.decode('utf-8','replace')
    if not raw or raw.lstrip().startswith('<'): print(a,'fail'); continue
    rows=list(csv.DictReader(io.StringIO(raw)))
    made=[]
    for adj,tag in (('NOR','RSNOR'),('T','RSTREND'),('RT','RSRT')):
        keep=[r for r in rows if r.get('MEASURE')=='RS' and r.get('ADJUSTMENT')==adj
              and r.get('TRANSFORMATION')=='IX']
        if len(keep)<120: continue
        ser=sorted((r['TIME_PERIOD'],r['OBS_VALUE']) for r in keep if r.get('OBS_VALUE'))
        with open(f'{OUT}/{a}_{tag}.csv','w') as g:
            g.write('date,value\n')
            for d,v in ser: g.write(f'{d}-01,{v}\n')
        made.append(f'{tag}:{ser[0][0]}..{ser[-1][0]}({len(ser)})')
    print(a,'  '.join(made) if made else 'nothing')
