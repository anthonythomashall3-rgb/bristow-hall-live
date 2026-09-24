"""Download the OECD's short-term-statistics revisions database — every monthly edition of each
series from February 1999 to the present — for the economies in the memo's sample and the
held-out set.  Dataflow OECD.SDD.STES:DSD_STES_REVISIONS@DF_STES_REVISIONS, public SDMX
endpoint, no key.  One file per (economy, measure): every edition's full history, long format.
"""
import subprocess, os, sys, time, pandas as pd
BASE='https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES_REVISIONS@DF_STES_REVISIONS,/'
AREAS=['USA','CAN','EA19','EA20','EA','FRA','ESP','JPN','KOR','BRA','DEU','MEX','ZAF','GBR','ITA','AUT','AUS']
MEAS_M=['PRVM','TOVM','UNEMP','EMP','EX','IM','CP','H_EARN','MABM']
MEAS_Q=['B1GQ_Q']
os.chdir('/home/claude/lab/oecd_rt')
log=open('fetch.log','a')
for a in AREAS:
    for freq,meas in [('M',m) for m in MEAS_M]+[('Q',m) for m in MEAS_Q]:
        out=f'{a}_{meas}_{freq}.csv'
        if os.path.exists(out) and os.path.getsize(out)>200: continue
        url=f'{BASE}{a}.{freq}.{meas}...?format=csvfile'
        t=time.time()
        r=subprocess.run(['curl','-s','--max-time','900',url,'-o',out],capture_output=True,text=True)
        sz=os.path.getsize(out) if os.path.exists(out) else 0
        msg=f'{a} {meas} {freq}: {sz} bytes in {time.time()-t:.0f}s'
        if sz<200:
            msg+=' -- '+open(out,errors='ignore').read()[:120].replace('\n',' ')
            os.remove(out)
        print(msg); log.write(msg+'\n'); log.flush()
print('done')
