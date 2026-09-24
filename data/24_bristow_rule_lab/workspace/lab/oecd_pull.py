import urllib.request, csv, io, os, sys
BASE='https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_KEI@DF_KEI,4.0/'
def pull(area, measure, out, start='1960-01'):
    url=f'{BASE}{area}.M.{measure}......?startPeriod={start}&format=csvfilewithlabels'
    import subprocess
    p=subprocess.run(['curl','-sS','--max-time','90','-A','Mozilla/5.0','-H','Accept: text/csv',url],capture_output=True)
    raw=p.stdout.decode('utf-8','replace')
    if not raw or raw.lstrip().startswith('<'):
        print(f'{area} {measure}: fetch failed'); return None
    rows=list(csv.DictReader(io.StringIO(raw)))
    keep=[r for r in rows if r.get('UNIT_MEASURE')=='IX' and r.get('ADJUSTMENT')=='Y' and r.get('TRANSFORMATION') in ('_Z','')]
    if not keep:
        keep=[r for r in rows if r.get('ADJUSTMENT')=='Y' and r.get('TRANSFORMATION') in ('_Z','')]
    if not keep: print(f'{area} {measure}: no seasonally adjusted index rows'); return None
    acts=sorted(set(r.get('ACTIVITY','') for r in keep))
    act=acts[0]
    if measure=='TOVM' and 'G47' in acts: act='G47'
    if measure=='PRVM':
        for c in ('B_TO_E','BTE','C','_T'):
            if c in acts: act=c; break
    keep=[r for r in keep if r.get('ACTIVITY','')==act]
    ser=sorted((r['TIME_PERIOD'], r['OBS_VALUE']) for r in keep if r.get('OBS_VALUE'))
    if len(ser)<120: print(f'{area} {measure}: only {len(ser)} observations (activity {act})'); return None
    with open(out,'w') as g:
        g.write('date,value\n')
        for d,v in ser: g.write(f'{d}-01,{v}\n')
    print(f'{area} {measure} [{act}]: {ser[0][0]} .. {ser[-1][0]}  n={len(ser)}  -> {out}')
    return out
if __name__=='__main__':
    jobs=[('MEX','PRVM'),('MEX','TOVM'),('MEX','UNEMP'),
          ('KOR','TOVM'),('KOR','PRVM'),
          ('BRA','TOVM'),('BRA','PRVM'),
          ('CAN','TOVM'),('JPN','TOVM'),('ESP','TOVM'),('FRA','TOVM'),('EA20','TOVM')]
    os.makedirs('cand',exist_ok=True)
    for a,m in jobs:
        pull(a,m,f'cand/OECD_{a}_{m}.csv')
