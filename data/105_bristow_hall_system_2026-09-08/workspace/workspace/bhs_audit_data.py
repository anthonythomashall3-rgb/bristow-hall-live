"""THE BRISTOW HALL SYSTEM - the data audit (8 September 2026). Every series the rule reads is checked against its
source as served today: the weekly claims files and the two rates against FRED's current print, the four vintage
tables against ALFRED's initial releases (output_type=4), the vacancy composite against JOLTS openings over the
labour force, the S&P 500 closes against FRED's SP500, the Sahm object against FRED's SAHMREALTIME, the first-print
file of collection 45 against ALFRED's initial releases. The FRED key is read from local.env in this process and never
printed (Rule 12.6). Writes out/audit/data_audit.md and returns the findings as PASS / DEFECT lines."""
import os,sys,json,subprocess,glob,pickle,datetime
import pandas as pd,numpy as np
HOME=os.path.expanduser('~'); MNT=os.path.join(HOME,'mnt','Onset Detector Data')
ENV=os.path.join(MNT,'onset-detector-new-2026-08-23','live_data','config','local.env')
K=[l.split('=',1)[1].strip().strip('"').strip("'") for l in open(ENV) if l.startswith('FRED_API_KEY=')][0]
W=os.path.join(MNT,'24_bristow_rule_lab','workspace'); D=os.path.join(W,'lab','data','fred_weekly'); C25=os.path.join(MNT,'25_fred_daily_weekly')
AL=os.path.join(MNT,'onset-detector-new-2026-08-23','27_realtime_vintages','alfred_all_vintages')
OUT=[]; today=datetime.date.today().isoformat()
def say(s): print(s); OUT.append(s)
def fred(sid,**q):
    url=f'https://api.stlouisfed.org/fred/series/observations?series_id={sid}&api_key={K}&file_type=json&'+'&'.join(f'{a}={b}' for a,b in q.items())
    r=subprocess.run(['curl','-sS','-m','60',url],capture_output=True,text=True); d=json.loads(r.stdout)
    if 'observations' not in d: raise RuntimeError(('FRED: '+str(d)[:120]).replace(K,'***'))
    obs=d['observations']; s=pd.Series({o['date']:(np.nan if o['value']=='.' else float(o['value'])) for o in obs}); s.index=pd.to_datetime(s.index)
    rt=pd.Series({o['date']:o['realtime_start'] for o in obs}); rt.index=pd.to_datetime(rt.index)
    return s.sort_index(),rt.sort_index()
def csv2(path):
    x=pd.read_csv(path).iloc[:,:2]; x.columns=['d','v']; x['d']=pd.to_datetime(x['d'],errors='coerce'); return pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna()
def cmp(name,ours,theirs,tol=1e-9):
    common=ours.index.intersection(theirs.dropna().index); d=(ours[common]-theirs[common]).abs()
    bad=d[d>tol]; missing=theirs.dropna().index.difference(ours.index); extra=ours.index.difference(theirs.dropna().index)
    status='PASS' if len(bad)==0 and len(missing)==0 else 'DEFECT'
    say(f'- {status} {name}: {len(common)} dates compared, {len(bad)} values differ'+(f' (first: {[(t.date().isoformat(),float(ours[t]),float(theirs[t])) for t in bad.index[:3]]})' if len(bad) else '')+f'; in source not in file: {len(missing)}'+(f' {[t.date().isoformat() for t in missing[:4]]}' if len(missing) else '')+f'; in file not in source: {len(extra)}'+(f' {[t.date().isoformat() for t in extra[:4]]}' if len(extra) else '')+f'; file ends {ours.index.max().date()}, source ends {theirs.dropna().index.max().date()}')
    return status
say(f'# Data audit, {today}\n\n## A1. Weekly and daily files against FRED today (current print)')
for sid,path in [('ICSA',f'{D}/ICSA.csv'),('CCSA',f'{D}/CCSA.csv'),('IURSA',f'{D}/IURSA.csv'),('WTB3MS',f'{C25}/fred_weekly/WTB3MS.csv'),('DCPN30',f'{C25}/fred_daily/DCPN30.csv'),('H0RIFSPPFM01NWF',f'{C25}/fred_weekly/H0RIFSPPFM01NWF.csv')]:
    s,_=fred(sid); cmp(sid,csv2(path),s)
nbad=0; nst=0
for f in sorted(glob.glob(f'{D}/*INSUREDUR.csv')):
    sid=os.path.basename(f)[:-4]; s,_=fred(sid); ours=csv2(f); common=ours.index.intersection(s.dropna().index); d=(ours[common]-s[common]).abs(); nst+=1
    if (d>1e-9).sum() or len(s.dropna().index.difference(ours.index)): nbad+=1; say(f'- DEFECT {sid}: {(d>1e-9).sum()} values differ, {len(s.dropna().index.difference(ours.index))} dates missing (file ends {ours.index.max().date()}, source {s.dropna().index.max().date()})')
say(f'- {"PASS" if nbad==0 else "DEFECT"} state insured-unemployment-rate files: {nst} series compared with FRED, {nbad} with differences')
say('\n## A2. The four vintage tables: first prints against ALFRED initial releases (output_type=4)')
sys.path.insert(0,os.getcwd()); import shim
from mini import first_prints
for sid in ['UNRATE','HOUST','AWHMAN','NDMANEMP']:
    fp=first_prints(sid); a,rt=fred(sid,output_type=4,realtime_start='1776-07-04',realtime_end='9999-12-31')
    common=fp.index.intersection(a.dropna().index); d=(fp[common]-a[common]).abs(); bad=d[d>1e-9]
    # dates: our relcal first_release vs ALFRED realtime_start
    rc=pd.read_csv(f'cache/relcal_{sid}.csv',index_col=0,parse_dates=[0,'first_release']) if os.path.exists(f'cache/relcal_{sid}.csv') else None
    dd=''
    if rc is not None:
        rc.index=pd.to_datetime(rc.index); fr=pd.to_datetime(rc['first_release']); c2=fr.index.intersection(rt.index); mism=[(m.strftime('%Y-%m'),fr[m].date().isoformat(),rt[m]) for m in c2 if fr[m].date().isoformat()!=rt[m]]
        dd=f'; release dates: {len(c2)} compared, {len(mism)} differ'+(f' {mism[:5]}' if mism else '')
    say(f'- {"PASS" if len(bad)==0 and not (rc is not None and mism) else "DEFECT"} {sid}: {len(common)} months compared, {len(bad)} first prints differ'+(f' {[(t.strftime("%Y-%m"),float(fp[t]),float(a[t])) for t in bad.index[:5]]}' if len(bad) else '')+f'; table through {fp.index.max().strftime("%Y-%m")}, ALFRED through {a.dropna().index.max().strftime("%Y-%m")}'+dd)
say('\n## A3. JOLTS and the vacancy composite')
jl,_=fred('JTSJOL'); cl,_=fred('CLF16OV'); vt=csv2(os.path.join(W,'lab','vac','vacancy_rate_PNZ_JOLTS.csv'))
jo=(jl/cl*100).dropna(); common=vt.index.intersection(jo.index); common=common[common>=pd.Timestamp('2001-01-01')]
d=(vt[common]-jo[common]).abs(); say(f'- {"PASS" if d.max()<1e-6 else "DEFECT"} vacancy composite after December 2000 = JTSJOL/CLF16OV*100 (current print): {len(common)} months, max |diff| {d.max():.2e}; level file through {vt.index.max().strftime("%Y-%m")}, JOLTS through {jl.dropna().index.max().strftime("%Y-%m")}')
say('\n## A4. The S&P 500 daily closes against FRED SP500 (the last ten years FRED serves)')
spx=csv2(os.path.join(W,'lab','speed2','data','sp500_daily_yahoo.csv')); sp,_=fred('SP500')
common=spx.index.intersection(sp.dropna().index); d=(spx[common]-sp[common]).abs(); bad=d[d>0.02]
say(f'- {"PASS" if len(bad)==0 else "DEFECT"} S&P 500 closes: {len(common)} days compared, {len(bad)} differ by more than 0.02'+(f' {[(t.date().isoformat(),float(spx[t]),float(sp[t])) for t in bad.index[:5]]}' if len(bad) else '')+f'; file through {spx.index.max().date()}, FRED through {sp.dropna().index.max().date()}; weekdays only: {bool((spx.index.weekday<5).all())}')
say('\n## A5. The Sahm object against FRED SAHMREALTIME')
o=pickle.load(open('cache/objects.pkl','rb')); g=o['sahm']; S,_=fred('SAHMREALTIME')
def crossings(s):
    out=[];armed=True
    for t,v in s.items():
        if armed and v>=0.5: out.append(t.strftime('%Y-%m')); armed=False
        elif not armed and v<0.5: armed=True
    return out
cf=crossings(S[S.index>='1960-01-01']); co=crossings(g[g.index>='1960-01-01'])
say(f'- FRED SAHMREALTIME crossings of 0.50 since 1960: {cf}')
say(f'- the rule\'s Sahm gap on first prints, crossings: {co}')
say(f'- {"PASS" if set(cf)==set(co) else "DEFECT"} the two agree on every crossing month: {set(cf)==set(co)}; only in ours: {sorted(set(co)-set(cf))}; only in FRED: {sorted(set(cf)-set(co))}. Last three months FRED {S.tail(3).round(2).to_dict()} vs ours {g.tail(3).round(3).to_dict()}')
open('out/audit/data_audit.md','w').write('\n'.join(OUT)+'\n')
