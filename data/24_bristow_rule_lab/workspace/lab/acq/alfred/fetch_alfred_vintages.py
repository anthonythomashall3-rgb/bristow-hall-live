"""ALFRED, every vintage of a series, through the keyless download form (Rule 12.7b).

usage: python fetch_alfred_vintages.py ID [ID ...]
Writes lab/acq/alfred/<ID>_alfred_<date>.zip, unpacks the wide CSV to lab/rt/vint/<ID>_all_vintages.csv
(observation_date, <ID>_YYYYMMDD ...), and appends SHA-256 lines to MANIFEST_alfred_<date>.sha256.
The vintage dates are read from the GET page's <option value="YYYY-MM-DD"> tags; nothing is guessed.
Transport is curl with its default User-Agent: a custom UA string draws an empty reply from ALFRED's front end (measured 3 September).
"""
import sys, re, io, os, zipfile, hashlib, datetime, subprocess, urllib.parse, pandas as pd
HERE='/home/claude/lab/acq/alfred'; VINT='/home/claude/lab/rt/vint'
today=datetime.date.today().isoformat()
UA='Mozilla/5.0 (research; Bristow-Hall program)'
def curl(args, tries=8):
    for a in range(tries):
        r=subprocess.run(['curl','-sS','-L','-m','900']+args,capture_output=True)
        if r.returncode==0 and r.stdout: return r.stdout
        import time; time.sleep(8*(a+1))
    raise SystemExit(f'curl failed {tries} times: {r.stderr.decode()[:200]}')
def fetch(seid):
    url=f'https://alfred.stlouisfed.org/series/downloaddata?seid={seid}'
    page=curl([url]).decode('utf8','ignore')
    dates=sorted(set(re.findall(r'option value="(\d{4}-\d{2}-\d{2})"',page)))
    m0=re.search(r'name="form\[obs_start_date\]"[^>]*value="([^"]+)"',page); m1=re.search(r'name="form\[obs_end_date\]"[^>]*value="([^"]+)"',page)
    obs0=m0.group(1) if m0 else '1776-07-04'; obs1=m1.group(1) if m1 else '9999-12-31'
    if not dates: raise SystemExit(f'{seid}: no vintage dates on the page')
    form=[('form[units]','lin'),('form[obs_start_date]',obs0),('form[obs_end_date]',obs1),('form[entered_vintage_dates]',''),
          ('form[file_type]','2'),('form[file_format]','csv'),('form[download_data]','')]+[('form[selected_vintage_dates][]',d) for d in dates]
    body=urllib.parse.urlencode(form)
    bf=f'/tmp/alfred_form_{seid}.txt'; open(bf,'w').write(body)
    content=curl(['-X','POST','-H','Content-Type: application/x-www-form-urlencoded','--data-binary',f'@{bf}',url])
    if not content.startswith(b'PK'): raise SystemExit(f'{seid}: response is not a zip ({len(content)} bytes): {content[:120]!r}')
    zp=f'{HERE}/{seid}_alfred_{today}.zip'; open(zp,'wb').write(content)
    z=zipfile.ZipFile(io.BytesIO(content)); csvs=[n for n in z.namelist() if n.endswith('.csv')]
    df=pd.read_csv(z.open(csvs[0]))
    out=f'{VINT}/{seid}_all_vintages.csv'; df.to_csv(out,index=False)
    sha=hashlib.sha256(content).hexdigest()
    with open(f'{HERE}/MANIFEST_alfred_{today}.sha256','a') as f: f.write(f'{sha}  {os.path.basename(zp)}\n')
    print(f'{seid}: {len(dates)} vintages {dates[0]} -> {dates[-1]}; {df.shape[0]} rows x {df.shape[1]-1} vintage columns -> {out}; zip sha256 {sha[:12]}')
if __name__=='__main__':
    for seid in sys.argv[1:]: fetch(seid)
