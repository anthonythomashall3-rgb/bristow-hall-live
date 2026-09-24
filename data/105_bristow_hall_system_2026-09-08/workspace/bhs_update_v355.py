"""THE BRISTOW HALL SYSTEM — the refresh (collection 105). v3.55 copy (16 September 2026): also refreshes every carried-leg channel, confirmer and first-print file, and runs bhs_build_v355.py against the staged version file. Pulls the current print of every series the rule reads,
writes it where the lab reads it (keeping a dated copy of what it replaces), appends today's vintage to the six
ALFRED tables where it carries something new, extends the first-print files, rebuilds the release calendars and the
two objects that live in cache/objects.pkl, then runs bhs_build.py unless told not to. The FRED key is read from
local.env inside this process and is never printed (Rule 12.6). Run from the collection's workspace:
    python3 bhs_update.py [--no-build]
Transport is curl, as in collection 25's fetcher.

Audit of 8 September 2026 (Rule Zero): until then the refresh left three things behind. The first-print file of the
weekly claims (collection 45) was never extended, so a new week entered the current file and not the rule's
first-print objects; the insured-rate base series in cache/objects.pkl stopped at its cached end; the JOLTS and
labour-force vintage tables and the three release calendars (relcal_*.csv) were not refreshed. All four are done here
now. The first prints of new claims weeks come from ALFRED's initial releases (output_type=4), which on the release
day are the advance figures just published; the release day is ALFRED's realtime_start."""
import sys
import os, sys, json, subprocess, datetime, glob, shutil, io, pickle, csv
import pandas as pd, numpy as np
HOME=os.path.expanduser('~'); MNT=os.path.join(HOME,'mnt','Onset Detector Data')
ENV=os.path.join(MNT,'onset-detector-new-2026-08-23','live_data','config','local.env')
KEY=None
for line in open(ENV):
    if line.startswith('FRED_API_KEY='): KEY=line.strip().split('=',1)[1].strip().strip('"').strip("'")
assert KEY and len(KEY)==32, 'no FRED key in local.env'
W=os.path.join(MNT,'24_bristow_rule_lab','workspace'); D=os.path.join(W,'lab','data','fred_weekly')
C25=os.path.join(MNT,'25_fred_daily_weekly'); AL=os.path.join(MNT,'onset-detector-new-2026-08-23','27_realtime_vintages','alfred_all_vintages')
C45=os.path.join(MNT,'45_dol_first_prints_2026-09','national_first_prints.csv')
COL=os.path.join(MNT,'105_bristow_hall_system_2026-09-08'); today=datetime.date.today().isoformat()
BK=os.path.join(COL,'live','backup_'+today); os.makedirs(BK,exist_ok=True); os.makedirs('cache',exist_ok=True)
REPORT=[]
def say(*a):
    t=' '.join(str(x) for x in a); print(t); REPORT.append(t)
def fred(series,**params):
    q='&'.join(f'{k}={v}' for k,v in params.items())
    url=f'https://api.stlouisfed.org/fred/series/observations?series_id={series}&api_key={KEY}&file_type=json&{q}'
    for _try in range(4):   # v3.55: FRED answers 429 when the standing collector is also drawing on the key; wait and retry
        r=subprocess.run(['curl','-sS','-m','40',url],capture_output=True,text=True)
        if r.returncode!=0: raise RuntimeError(f'curl failed for {series}')
        d=json.loads(r.stdout)
        if 'observations' in d or str(d.get('error_code'))!='429': break
        import time as _t; _t.sleep(15*(_try+1))
    if 'observations' not in d: raise RuntimeError(f'FRED error for {series}: {str(d)[:80].replace(KEY,"***")}')
    s=pd.Series({o['date']:(np.nan if o['value']=='.' else float(o['value'])) for o in d['observations']})
    s.index=pd.to_datetime(s.index); return s.sort_index()
def alfred_first(series,start='2000-01-01'):
    """ALFRED's initial release of every observation from `start`: value and the day it was released"""
    q=f'output_type=4&realtime_start=1776-07-04&realtime_end=9999-12-31&observation_start={start}'
    url=f'https://api.stlouisfed.org/fred/series/observations?series_id={series}&api_key={KEY}&file_type=json&{q}'
    for _try in range(4):   # v3.55: FRED answers 429 when the standing collector is also drawing on the key; wait and retry
        r=subprocess.run(['curl','-sS','-m','40',url],capture_output=True,text=True)
        if r.returncode!=0: raise RuntimeError(f'curl failed for {series}')
        d=json.loads(r.stdout)
        if 'observations' in d or str(d.get('error_code'))!='429': break
        import time as _t; _t.sleep(15*(_try+1))
    if 'observations' not in d: raise RuntimeError(f'ALFRED error for {series}: {str(d)[:80].replace(KEY,"***")}')
    obs=[o for o in d['observations'] if o['value']!='.']
    return pd.DataFrame({'first':[float(o['value']) for o in obs],'release':[o['realtime_start'] for o in obs]},index=pd.to_datetime([o['date'] for o in obs])).sort_index()
def backup(path):
    if os.path.exists(path): shutil.copy2(path,os.path.join(BK,os.path.basename(path)))
def refresh_series(series,path,start='1900-01-01'):
    """replace a date,value csv with the current print of the whole series; report what moved"""
    new=fred(series,observation_start=start)
    old=None
    if os.path.exists(path):
        try: old=pd.read_csv(path).iloc[:,:2]; old.columns=['date','value']; old['date']=pd.to_datetime(old['date'],errors='coerce'); old=old.set_index('date')['value']
        except Exception: old=None
    backup(path)
    out=new.dropna().rename('value').to_frame(); out.index.name='date'; out.to_csv(path)
    o_last=None if old is None or old.dropna().empty else old.dropna().index[-1].date()
    say(f'{series:14s} {str(o_last):>10s} -> {new.dropna().index[-1].date()}  ({len(new.dropna())} obs)')
    return new
# ---- weekly claims objects (current print) ----
for s in ['ICSA','CCSA','IURSA']: refresh_series(s,os.path.join(D,f'{s}.csv'))
for f in sorted(glob.glob(os.path.join(D,'*INSUREDUR.csv'))):
    sid=os.path.basename(f)[:-4]
    try: refresh_series(sid,f)
    except Exception as e: say(f'{sid}: {e}')
# ---- the weekly claims FIRST PRINTS: collection 45, extended from ALFRED's initial releases ----
try:
    N=pd.read_csv(C45,dtype=str)
    have_ic=set(N[N.icsa.notna()&(N.icsa!='')].ic_week_ended); have_iu=set(N[N.iur_sa.notna()&(N.iur_sa!='')].iu_week_ended)
    A=alfred_first('ICSA',start='2026-01-01'); U=alfred_first('IURSA',start='2026-01-01'); C=alfred_first('CCSA',start='2026-01-01')
    rows={}                                    # one row per release day: the initial-claims week and the insured week it carried
    def row(rel):
        if rel not in rows: rows[rel]=dict(release=pd.Timestamp(rel).strftime('%m%d%y'),ic_week='',icsa='',icsa_prev_rev='',icnsa='',iu_week='',iur_sa='',iusa='',iunsa='',kind='alfred',release_date=rel,ic_week_ended='',iu_week_ended='')
        return rows[rel]
    for w,r in A.iterrows():
        wk=w.strftime('%Y-%m-%d')
        if wk in have_ic:
            e=N[(N.ic_week_ended==wk)&(N.kind=='dol_pdf')]
            if len(e):
                same=abs(float(e.icsa.iloc[0])-float(r['first']))<0.5; say(f"first prints: ALFRED initial release for the week ending {wk} ({float(r['first']):.0f}) {'agrees with' if same else 'DIFFERS FROM'} the Department's release ({float(e.icsa.iloc[0]):.0f}) filed earlier"+('' if same else ' - kept as filed; check'))
                N.loc[e.index,'kind']='dol_pdf+alfred'; N.to_csv(C45,index=False)
            continue
        x=row(r['release']); x.update(ic_week=w.strftime('%B %-d'),icsa=str(float(r['first'])),ic_week_ended=wk)
    for w,r in U.iterrows():
        wk=w.strftime('%Y-%m-%d')
        if wk in have_iu: continue
        x=row(r['release']); x.update(iu_week=w.strftime('%B %-d'),iur_sa=str(float(r['first'])),iu_week_ended=wk,iusa=(str(float(C.loc[w,'first'])) if w in C.index else ''))
    for x in rows.values():                    # a release carries the insured week seven days before its claims week
        if not x['iu_week_ended'] and x['ic_week_ended']: x['iu_week_ended']=(pd.Timestamp(x['ic_week_ended'])-pd.Timedelta(days=7)).strftime('%Y-%m-%d')
        if not x['ic_week_ended'] and x['iu_week_ended']: x['ic_week_ended']=(pd.Timestamp(x['iu_week_ended'])+pd.Timedelta(days=7)).strftime('%Y-%m-%d')
    rows=list(rows.values())
    if rows:
        backup(C45); N=pd.concat([N,pd.DataFrame(rows)],ignore_index=True); N['_rd']=pd.to_datetime(N.release_date); N=N.sort_values(['_rd','release']).drop(columns='_rd'); N.to_csv(C45,index=False)
        say(f'first prints: {len(rows)} release(s) appended to collection 45 from ALFRED initial releases: {[(x["release_date"],x["ic_week_ended"],x["icsa"],x["iu_week_ended"],x["iur_sa"]) for x in rows]}')
    else: say(f'first prints: collection 45 already carries every week ALFRED has (through {A.index.max().date()}, released {A["release"].iloc[-1]})')
except Exception as e: say(f'first prints: NOT extended ({e})')
# ---- the same first prints from the Department's own release on the release day (bhs_dol_press.py), when FRED/ALFRED lag ----
try:
    from bhs_dol_press import dol_press_extend
    dol_press_extend(C45,say)
except Exception as e: say(f'DOL release: NOT read ({e})')
# ---- the search week (v3.27): Google searches for unemployment, daily, stitched onto the history (collection 108) ----
try:
    import subprocess
    _c108=os.path.join(MNT,'108_high_frequency_speed_2026-09-10')
    _r=subprocess.run([os.path.join(_c108,'.venv','bin','python'),os.path.join(_c108,'scripts','trends_live.py')],capture_output=True,text=True,timeout=600)
    for _ln in (_r.stdout.strip().splitlines() or [_r.stderr.strip()[-120:] or 'search week: no output']): say(_ln)   # one line per term (v3.29); 'appended' on any of them is new data
except Exception as e: say(f'search week: NOT refreshed ({e})')
# the Department's ETA 539 state file (the breadth object's data; collection 37's panel). Found stale on 11 September
# 2026 - built once on 4 September and never refreshed - so the panel is now extended at every run, weeks after its last
# only (the weeks in hand keep their first-published values).
try:
    _r=subprocess.run([sys.executable,os.path.join('s2','state539_live.py')],capture_output=True,text=True,timeout=600)
    for _ln in (_r.stdout.strip().splitlines() or [(_r.stderr.strip()[-120:] or 'state 539: no output')]): say(_ln)
except Exception as e: say(f'state 539: NOT refreshed ({e})')
# the state FIRST PRINTS the breadth proposer reads (collection 45's wide file): parsed from the weekly press release
# PDF this system already downloads, because the Department's page-8 archive runs about two weeks behind (11 Sep 2026).
try:
    _r=subprocess.run([sys.executable,os.path.join('s2','state_press_live.py')],capture_output=True,text=True,timeout=600)
    for _ln in (_r.stdout.strip().splitlines() or [(_r.stderr.strip()[-120:] or 'state first prints: no output')]): say(_ln)
except Exception as e: say(f'state first prints: NOT refreshed ({e})')
# the home page's current readings (collection 109): the published series the programme shows beside its own indicator
try:
    _r=subprocess.run([sys.executable,os.path.join('s2','home_tiles.py')],capture_output=True,text=True,timeout=300)
    for _ln in (_r.stdout.strip().splitlines() or [(_r.stderr.strip()[-120:] or 'home tiles: no output')]): say(_ln)
except Exception as e: say(f'home tiles: NOT refreshed ({e})')
# ---- the spread's two rates ----
refresh_series('WTB3MS',os.path.join(C25,'fred_weekly','WTB3MS.csv'))
refresh_series('DCPN30',os.path.join(C25,'fred_daily','DCPN30.csv'))
refresh_series('DCPF1M',os.path.join(C25,'fred_daily','DCPF1M.csv'))   # the financial paper rate: the spread reads the wider of the two markets (v3.26)
refresh_series('PERMIT','cache/surveys/PERMIT.csv')   # the current file of building permits (v3.27): the permits half runs over its months; the vintage table gives each month's reading as of its day
# ---- the Sahm rule as FRED publishes it in real time (the page's comparator) ----
try:
    sr=fred('SAHMREALTIME'); backup('cache/SAHMREALTIME.csv'); o_=sr.dropna().rename('SAHMREALTIME').to_frame(); o_.index.name='date'; o_.to_csv('cache/SAHMREALTIME.csv'); say(f'SAHMREALTIME    through {sr.dropna().index[-1].strftime("%Y-%m")}: {sr.dropna().iloc[-1]:.2f}')
except Exception as e: say(f'SAHMREALTIME: fetch failed ({e})')
# ---- the monthly first-print objects: append today's vintage where it carries something new ----
for s in ['UNRATE','HOUST','AWHMAN','NDMANEMP','JTSJOL','CLF16OV','PERMIT']:   # PERMIT from v3.27 (walk51): the housing x rate pair reads starts or permits
    path=os.path.join(AL,f'{s}_all_vintages.csv')
    if not os.path.exists(path): say(f'{s:14s} no vintage table at {path}'); continue
    tab=pd.read_csv(path,index_col=0); tab.index=pd.to_datetime(tab.index)
    cur=fred(s,realtime_start=today,realtime_end=today,observation_start='1940-01-01')
    lastcol=tab.columns[-1]; lastdate=tab.index[-1]; newdate=cur.dropna().index[-1]
    changed=(newdate>lastdate) or (abs(float(cur.get(lastdate,np.nan))-float(pd.to_numeric(tab[lastcol],errors='coerce').get(lastdate,np.nan)))>1e-9 if lastdate in cur.index else False)
    if changed:
        # the vintage is named by the day this print was PUBLISHED (ALFRED's realtime_start of the newest observation),
        # not by the day the refresh ran: the release calendars (relcal_*.csv) are read off these column names
        try: vday=alfred_first(s,start=newdate.strftime('%Y-%m-%d'))['release'].iloc[-1]
        except Exception: vday=today
        backup(path); col=f'{s}_{vday.replace("-","")}'
        if col in tab.columns: tab=tab.drop(columns=[col])
        tab=tab.reindex(tab.index.union(cur.index)).sort_index(); tab=pd.concat([tab,cur.reindex(tab.index).rename(col)],axis=1)
        tab.index.name='date'; tab.to_csv(path,na_rep='')
        say(f'{s:14s} vintage {col} appended: data through {newdate.date()} (was {lastdate.date()}); published {vday}')
    else: say(f'{s:14s} no new print (through {lastdate.date()}, last vintage {lastcol})')
# ---- the vacancy rate's two first-print series, straight from ALFRED's initial releases (the CLF16OV vintage table of
# collection 27 stops in 1996; output_type=4 gives every month's first print and its release day in one call) ----
for s in ['JTSJOL','CLF16OV']:
    try:
        a=alfred_first(s,start='1940-01-01'); p_=f'cache/alfred_first_{s}.csv'
        old=pd.read_csv(p_,index_col=0) if os.path.exists(p_) else None
        if old is None or len(old)!=len(a): backup(p_); a.index.name='date'; a.to_csv(p_); say(f'alfred_first_{s}: {len(a)} months, through {a.index[-1].strftime("%Y-%m")} (released {a["release"].iloc[-1]})')
        else: say(f'alfred_first_{s}: unchanged (through {a.index[-1].strftime("%Y-%m")})')
    except Exception as e: say(f'alfred_first_{s}: NOT refreshed ({e})')
# ---- the release calendars from the vintage tables (the first vintage carrying each month) ----
def release_calendar(series):
    rows=list(csv.reader(open(os.path.join(AL,series+'_all_vintages.csv')))); h=rows[0]
    vd=[pd.Timestamp(c.split('_')[-1]) for c in h[1:]]; dates=[pd.Timestamp(r[0]) for r in rows[1:]]
    out={}
    for i,m in enumerate(dates):
        for j in range(1,len(h)):
            v=rows[1+i][j]
            if v not in ('','.'): out[m]=(vd[j-1],float(v)); break
    return pd.DataFrame({'first_release':{m:a for m,(a,b) in out.items()},'first_print':{m:b for m,(a,b) in out.items()}}).sort_index()
for s in ['HOUST','UNRATE','JTSJOL']:
    c=release_calendar(s); p_=f'cache/relcal_{s}.csv'
    old=pd.read_csv(p_,index_col=0) if os.path.exists(p_) else None
    if old is None or len(old)!=len(c) or str(old.index[-1])[:10]!=c.index[-1].strftime('%Y-%m-%d'):
        backup(p_); c.to_csv(p_); say(f'relcal_{s}: {len(c)} months, through {c.index[-1].strftime("%Y-%m")} (released {c["first_release"].iloc[-1].date()})')
    else: say(f'relcal_{s}: unchanged (through {c.index[-1].strftime("%Y-%m")})')
# ---- the vacancy rate: after December 2000 the composite is JOLTS openings over the civilian labour force ----
vp=os.path.join(W,'lab','vac','vacancy_rate_PNZ_JOLTS.csv')
vt=pd.read_csv(vp,index_col=0,parse_dates=True).iloc[:,0]
jl=refresh_series('JTSJOL',os.path.join(W,'lab','vac','JTSJOL.csv'),start='2000-12-01'); cl=refresh_series('CLF16OV',os.path.join(W,'lab','vac','CLF16OV.csv'),start='1948-01-01')
jo=(jl/cl*100).dropna()
ov=[(m,float(vt[m]),float(jo[m])) for m in vt.index[-3:] if m in jo.index]
if ov and max(abs(a-b) for _,a,b in ov)<=1e-6:
    newm=jo[jo.index>vt.index[-1]].dropna()
    if len(newm):
        backup(vp); vt=pd.concat([vt,newm]).sort_index(); vt.rename('0').to_frame().to_csv(vp)
        say(f'vacancy: {len(newm)} JOLTS month(s) appended, through {vt.index[-1].date()}')
    else: say(f'vacancy: no new JOLTS month (through {vt.index[-1].date()})')
else: say(f'vacancy: openings/labour force does not reproduce the level file on recent months {ov}; NOT appended')
# ---- the S&P 500, daily closes ----
sp_path=os.path.join(W,'lab','speed2','data','sp500_daily_yahoo.csv')
sp=pd.read_csv(sp_path,index_col=0,parse_dates=True).iloc[:,0]
r=subprocess.run(['curl','-sS','-m','40','-A','Mozilla/5.0','https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?range=3mo&interval=1d'],capture_output=True,text=True)
try:
    ch=json.loads(r.stdout)['chart']['result'][0]; ts=ch['timestamp']; cl=ch['indicators']['quote'][0]['close']
    ys=pd.Series({pd.Timestamp(datetime.datetime.fromtimestamp(t,datetime.timezone.utc).date()):c for t,c in zip(ts,cl) if c is not None}).sort_index()
    # only settled closes: today's row is a live price until the market has closed (4:00 ET; the feed settles by 4:15)
    from zoneinfo import ZoneInfo
    _ny=datetime.datetime.now(ZoneInfo('America/New_York')); _cut=pd.Timestamp(_ny.date() if (_ny.hour,_ny.minute)>=(16,15) else _ny.date()-datetime.timedelta(days=1))
    ys=ys[ys.index<=_cut]
    if sp.index[-1]>_cut: backup(sp_path); _dropped=sp.index[-1].date(); sp=sp[sp.index<=_cut]; sp.rename('close').to_frame().to_csv(sp_path); say(f'S&P 500: dropped the intraday row for {_dropped} (not a close)')
    # the official close (S&P Dow Jones Indices, FRED SP500, posted the next morning) replaces the feed's figure once it
    # exists; the feed's own later value replaces a preliminary print. Audit of 8 September 2026: a run at 4:20 PM had
    # kept a preliminary 7753.74 for 3 September 2026 where the close was 7747.71.
    fixed=[]
    try:
        off=fred('SP500',observation_start=(datetime.date.today()-datetime.timedelta(days=45)).isoformat()).dropna()
        for t,v in off.items():
            if t in sp.index and abs(float(sp[t])-float(v))>0.005: fixed.append((t.date().isoformat(),round(float(sp[t]),2),round(float(v),2))); sp[t]=float(v)
    except Exception as e: say(f'S&P 500: FRED SP500 not read ({e})'); off=pd.Series(dtype=float)
    for t,v in ys.items():
        if t in sp.index and t not in off.index and abs(float(sp[t])-float(v))>0.005: fixed.append((t.date().isoformat(),round(float(sp[t]),2),round(float(v),2))); sp[t]=float(v)
    if fixed: backup(sp_path); sp.rename('close').to_frame().to_csv(sp_path); say(f'S&P 500: {len(fixed)} close(s) corrected to the settled figure: {fixed}')
    add=ys[ys.index>sp.index[-1]]
    if len(add):
        backup(sp_path); sp=pd.concat([sp,add]); sp.rename('close').to_frame().to_csv(sp_path); say(f'S&P 500: {len(add)} day(s) appended, through {sp.index[-1].date()}')
    else: say(f'S&P 500: nothing new (through {sp.index[-1].date()})')
except Exception as e: say(f'S&P 500: fetch failed ({e})')
# ---- cache/objects.pkl: the Sahm gap on first prints rebuilt from the refreshed vintages; the insured-rate base extended ----
sys.path.insert(0,os.getcwd()); import shim
import bristow_rule_v3 as B
from mini import first_prints
o=pickle.load(open('cache/objects.pkl','rb')); g_old=o['sahm']; changed=False
g_new=B.sahm_gap(first_prints('UNRATE'))
common=g_old.index.intersection(g_new.index); dev=float((g_old[common]-g_new[common]).abs().max()) if len(common) else 0.0
# the stored series begins in 1949 (the reconstruction before ALFRED's vintages); only months after its end are added
if dev<=1e-6 and g_new.index[-1]>g_old.index[-1]:
    o['sahm']=pd.concat([g_old,g_new[g_new.index>g_old.index[-1]]]).sort_index(); changed=True; say(f'Sahm gap: extended to {o["sahm"].index[-1].date()} (history kept from {o["sahm"].index[0].date()})')
elif dev<=1e-6: say(f'Sahm gap: unchanged (through {g_old.index[-1].date()})')
else: say(f'Sahm gap: rebuilt series differs from the stored one by {dev:.4f} on the overlap; NOT replaced')
# the insured rate (current file) that the first prints overwrite: extend it with the weeks after its cached end, so a
# new week reaches the rule's insured-rate objects (the first-print file supplies the advance figure for those weeks)
iu_cur=pd.read_csv(os.path.join(D,'IURSA.csv')).iloc[:,:2]; iu_cur.columns=['d','v']; iu_cur['d']=pd.to_datetime(iu_cur['d']); iu_cur=iu_cur.set_index('d')['v'].astype(float).dropna()
base=o['iursa']; add=iu_cur[iu_cur.index>base.index.max()]
if len(add): o['iursa']=pd.concat([base,add]).sort_index(); changed=True; say(f'insured rate base: {len(add)} week(s) appended, through {o["iursa"].index.max().date()}')
else: say(f'insured rate base: unchanged (through {base.index.max().date()})')
if changed: backup('cache/objects.pkl'); pickle.dump(o,open('cache/objects.pkl','wb'))

# ---- v3.55 (16 September 2026): the carried legs' channels, their confirmers and the leg data, refreshed where the
# ---- leg loaders read them (186/data, 183/data, 177/data, 176/data, 186/vintages). Without this the staged v3.55
# ---- legs were frozen at their 15-16 September files and could never fire on new data.
C186=os.path.join(MNT,'186_realtime_channels_2026-09-15'); C183=os.path.join(MNT,'183_transmission_channels_2026-09-15')
C177=os.path.join(MNT,'177_new_legs_priced_2026-09-15'); C176=os.path.join(MNT,'176_financial_leg_conjunction_2026-09-15')
def _where(sid):
    for d_ in ('data','data_highfreq','data_nber'):
        p_=os.path.join(C186,d_,sid+'.csv')
        if os.path.exists(p_): return p_
    return os.path.join(C186,'data',sid+'.csv')
CARRIED=[r['channel'] for r in csv.DictReader(open(os.path.join(MNT,'189_walk_from_1948_2026-09-16','out','v355','v355_carried_legs.csv')))]
DEAD={'DTB1':'ends 2001-08 (successor DTB1YR)','TOTRA':'ends 2018-04 (successor WALCL)','LOLAOL':'ends 2018-04','M14064USM144NNBR':'NBER Macrohistory, ends 1965',
      'DTWEXM':'ends 2019-12 (successor DTWEXBGS)','M0852BUSM497NNBR':'NBER Macrohistory','M03002USM544NNBR':'NBER Macrohistory'}
FRED_LIVE=[s for s in CARRIED if not s.startswith('WB_') and s not in DEAD]
CONF=['HOUST','AWHMAN','INDPRO','MANEMP','UNRATE','AWOTMAN']
LEGS186=['BORROW','M1SL','WBUSAPPWNSAUS','CCNSA','WPU101','TOTBORR','CASACBW027NBOG','IPDCONGD']
say('---- v3.55 carried-leg channels ----')
for s in sorted(set(FRED_LIVE+CONF+LEGS186)):
    try: refresh_series(s,_where(s))
    except Exception as e: say(f'{s:14s} NOT refreshed ({e})')
for s,p_ in [('BBKMCOIX',os.path.join(C177,'data','BBKMCOIX.csv')),('AUTHNOTT',os.path.join(C183,'data','AUTHNOTT.csv')),
             ('DRSFRMACBS',os.path.join(C183,'data','DRSFRMACBS.csv')),('NEWORDER',os.path.join(C183,'data','NEWORDER.csv')),
             ('GS10',os.path.join(C176,'data','GS10.csv')),('GS1',os.path.join(C176,'data','GS1.csv'))]:
    try: refresh_series(s,p_)
    except Exception as e: say(f'{s:14s} NOT refreshed ({e})')
for s in DEAD: say(f'{s:14s} dead series, not refreshed: {DEAD[s]}')
for s in ['UNRATE','HOUST','AWHMAN','INDPRO','MANEMP','PERMIT1','BUSINV','UMCSENT']:
    p_=os.path.join(C186,'vintages',s+'_firstprint.csv')
    if not os.path.exists(p_): say(f'{s} firstprint: no file'); continue
    try:
        old=pd.read_csv(p_); old['date']=pd.to_datetime(old['date']); last=old['date'].max()
        a=alfred_first(s,start=(last+pd.DateOffset(months=1)).strftime('%Y-%m-%d')); a=a[a.index>last]
        if len(a):
            backup(p_); add=pd.DataFrame({'date':a.index.strftime('%Y-%m-%d'),'published':a['release'].values,'value':a['first'].values})
            pd.concat([old.assign(date=old['date'].dt.strftime('%Y-%m-%d')),add]).to_csv(p_,index=False)
            say(f'{s} firstprint: +{len(a)} month(s), through {a.index[-1].strftime("%Y-%m")} (released {a["release"].iloc[-1]})')
        else: say(f'{s} firstprint: unchanged (through {last.strftime("%Y-%m")})')
    except Exception as e: say(f'{s} firstprint: NOT refreshed ({e})')
try:
    import re as _re
    u='https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/related/CMO-Historical-Data-Monthly.xlsx'
    try:   # the pink sheet moves to a new document id each month: read the current link off the commodity-markets page
        _pg=subprocess.run(['curl','-sSL','-m','60','-A','Mozilla/5.0','https://www.worldbank.org/en/research/commodity-markets'],capture_output=True,text=True).stdout
        _m=_re.search(r'https://thedocs\.worldbank\.org/en/doc/[0-9a-f]+-\d+/related/CMO-Historical-Data-Monthly\.xlsx',_pg)
        if _m: u=_m.group(0)
    except Exception: pass
    r_=subprocess.run(['curl','-sSL','-m','120','-o','/tmp/pink.xlsx',u],capture_output=True,text=True)
    d_=pd.read_excel('/tmp/pink.xlsx',sheet_name='Monthly Prices',header=None)
    hdr=next(i for i in range(10) if d_.iloc[i].astype(str).str.contains('Crude oil',case=False).any()); names=[str(v) for v in d_.iloc[hdr]]
    wanted=[c for c in CARRIED if c.startswith('WB_')]
    for j,nm in enumerate(names):
        key='WB_'+_re.sub(r'[^A-Za-z0-9]+','_',nm).strip('_').upper()[:40]
        if key not in wanted: continue
        vals=[]
        for i in range(hdr+1,len(d_)):
            m_=_re.match(r'^(\d{4})M(\d{1,2})$',str(d_.iloc[i,0]).strip())
            if not m_: continue
            v_=pd.to_numeric(d_.iloc[i,j],errors='coerce')
            if v_==v_: vals.append(('%s-%02d-01'%(m_.group(1),int(m_.group(2))),float(v_)))
        p_=_where(key); backup(p_); pd.DataFrame(vals,columns=['date','value']).to_csv(p_,index=False); say(f'{key:14s} pink sheet through {vals[-1][0]}')
except Exception as e: say(f'pink sheet: NOT refreshed ({e})')
say('open: leg M proposals (177/out/leg_M_money_proposals.csv) and leg N proposals (121/out/warn_leg_proposals.csv) are precomputed; rerun 177/code/build_legs.py and 121/code/warn_proposals.py to extend them')
open(os.path.join(COL,'live',f'refresh_{today}.txt'),'w').write('\n'.join(REPORT)+'\n')
if '--no-build' not in sys.argv:
    r=subprocess.run([sys.executable,'bhs_build_v355.py'],capture_output=True,text=True,env=dict(os.environ,BHS_VERSION_FILE=os.environ.get('BHS_VERSION_FILE','../staged_v355/bhs_version_v355_mac.json')))
    tail=[l for l in r.stdout.splitlines() if not l.endswith(' obs')][-24:]
    print('\n'.join(tail)); print('build rc',r.returncode)
    if r.returncode!=0: print(r.stderr[-1500:])
