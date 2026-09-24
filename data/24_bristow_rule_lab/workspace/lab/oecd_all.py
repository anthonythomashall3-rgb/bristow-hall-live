import csv, io, os, subprocess, sys, collections
BASE='https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_KEI@DF_KEI,4.0/'
OUT='/home/claude/lab/kei'
os.makedirs(OUT, exist_ok=True)

WANT = {          # measure -> (unit, list of activities to keep separately)
 'EMP':   ('PS',    ['_T']),
 'UNEMP': ('PT_LF', ['_T']),
 'PRVM':  ('IX',    ['BTE','B_TO_E','C','F','_T']),
 'TOVM':  ('IX',    ['G47','_T']),
 'EX':    ('USD',   ['_T']),
 'IM':    ('USD',   ['_T']),
 'TOCAPA':('IX',    ['G45','_T']),
 'RS':    ('IX',    ['_T']),
}

def pull_area(area, start='1950-01'):
    url=f'{BASE}{area}.M.......?startPeriod={start}&format=csvfilewithlabels'
    p=subprocess.run(['curl','-sS','--max-time','180','-A','Mozilla/5.0','-H','Accept: text/csv',url],
                     capture_output=True)
    raw=p.stdout.decode('utf-8','replace')
    if not raw or raw.lstrip().startswith('<'):
        print(f'{area}: fetch failed ({len(raw)} bytes)'); return
    rows=list(csv.DictReader(io.StringIO(raw)))
    made=[]
    for meas,(unit,acts) in WANT.items():
        for act in acts:
            keep=[r for r in rows if r.get('MEASURE')==meas
                  and r.get('UNIT_MEASURE')==unit
                  and r.get('ACTIVITY','')==act
                  and r.get('ADJUSTMENT') in ('Y','AA','RT')
                  and r.get('TRANSFORMATION') in ('_Z','')]
            if len(keep)<120: continue
            ser=sorted((r['TIME_PERIOD'], r['OBS_VALUE']) for r in keep if r.get('OBS_VALUE'))
            fn=f'{OUT}/{area}_{meas}_{act}.csv'
            with open(fn,'w') as g:
                g.write('date,value\n')
                for d,v in ser: g.write(f'{d}-01,{v}\n')
            made.append(f'{meas}/{act}:{ser[0][0]}-{ser[-1][0]}({len(ser)})')
    print(f'{area}: ' + '  '.join(made) if made else f'{area}: nothing usable')

if __name__=='__main__':
    areas = sys.argv[1:] or ['USA','CAN','JPN','KOR','MEX','BRA','ESP','FRA','EA20','DEU','ITA','GBR','AUS','ZAF']
    for a in areas: pull_area(a)
