"""Keep the state FIRST PRINTS current: the Department's 'Regular State Data' (page 8 of the weekly claims release).

The breadth proposer reads `45_dol_first_prints_2026-09/state_iu_first_print_wide.csv` - each state's insured
unemployment as first published on the Thursday after the week. Collection 45 built it once (4-5 September 2026) and
nothing refreshed it, so the breadth object froze at the week ending 22 August while claims moved on (found
11 September 2026). This script fetches this year's page-8 releases, parses any release the files do not carry, and
appends: the raw HTML to `45/dol_page8_live/`, the tidy rows to `state_first_prints_clean.csv`, and the week's row to
`state_iu_first_print_wide.csv` and `state_ic_first_print_wide.csv`.

Causal: a release is parsed once, as published, and appended; weeks already in hand are never rewritten.
Prints one line for the run log. Run: python3 s2/state_page8_live.py
"""
import os,re,sys,csv,time,shutil,datetime,urllib.request,urllib.parse
import pandas as pd
C45=os.path.expanduser('~/Projects/Onset Detector Data/45_dol_first_prints_2026-09')
CLEAN=os.path.join(C45,'state_first_prints_clean.csv')
IUW=os.path.join(C45,'state_iu_first_print_wide.csv'); ICW=os.path.join(C45,'state_ic_first_print_wide.csv')
RAWD=os.path.join(C45,'dol_page8_live')
UA={'User-Agent':'Mozilla/5.0'}
def get(url,data=None,tries=3,timeout=60):
    err=None
    for i in range(tries):
        try:
            req=urllib.request.Request(url,data=data,headers=UA); return urllib.request.urlopen(req,timeout=timeout).read().decode('latin-1')
        except Exception as e: err=e; time.sleep(3*(i+1))
    raise err
def parse(h,fname):
    t=re.sub(r'<[^>]+>',' ',h); t=re.sub(r'\s+',' ',t)
    m1=re.search(r'Initial Claims Filed During Week Ended\s*([A-Za-z]+ \d+, \d{4})',t)
    m2=re.search(r'Insured Unemployment For Week Ended\s*([A-Za-z]+ \d+, \d{4})',t)
    d1=m1.group(1) if m1 else ''; d2=m2.group(1) if m2 else ''
    rows=[]
    for row in re.findall(r'<TR[^>]*>(.*?)</TR>',h,re.S|re.I):
        cells=[re.sub(r'<[^>]+>','',c).replace('&nbsp','').replace(';','').strip() for c in re.findall(r'<T[DH][^>]*>(.*?)</T[DH]>',row,re.S|re.I)]
        if len(cells)<14 or not cells[0] or cells[0].upper()==cells[0]: continue
        vals=[c.replace(',','') for c in cells]
        rows.append([fname,d1,d2]+[vals[0]]+vals[1:6]+vals[7:16])
    return d1,d2,rows

def main():
    iu=pd.read_csv(IUW,index_col=0,parse_dates=True); have=iu.index.max()
    year=datetime.date.today().year
    try:
        h=get('https://oui.doleta.gov/unemploy/archive.asp',urllib.parse.urlencode({'report':'page8','year':str(year),'submit':'Submit'}).encode())
    except Exception as e:
        print(f'state first prints: archive not read ({str(e)[:70]}); wide file stands through {have.date()}'); return 1
    links=sorted(set(re.findall(r'/unemploy/page8/%d/[0-9]+\.html'%year,h)))
    if not links: print(f'state first prints: no {year} releases listed; wide file stands through {have.date()}'); return 1
    os.makedirs(RAWD,exist_ok=True)
    cl=pd.read_csv(CLEAN,low_memory=False); seen=set(cl['release_file'].astype(str))
    new_rows=[]; weeks=[]
    for l in links:
        fn=l.split('/')[-1]
        if fn in seen: continue
        p=os.path.join(RAWD,fn)
        try: h2=open(p,encoding='latin-1').read() if os.path.exists(p) else get('https://oui.doleta.gov'+l)
        except Exception as e: print(f'state first prints: {fn} not read ({str(e)[:50]})'); continue
        if not os.path.exists(p): open(p,'w',encoding='latin-1').write(h2); time.sleep(0.4)
        d1,d2,rows=parse(h2,fn)
        if not rows or not d2: continue
        wk2=pd.Timestamp(d2)
        if wk2<=have: continue
        new_rows+=rows; weeks.append((wk2,pd.Timestamp(d1) if d1 else None,rows))
    if not new_rows:
        print(f'state first prints: nothing new (wide file through {have.date()}, {len(links)} releases listed for {year})'); return 0
    # tidy rows
    cols=list(cl.columns)
    add=pd.DataFrame(new_rows,columns=cols[:len(new_rows[0])])
    add['wk']=pd.to_datetime(add['ic_week_ended'],errors='coerce').dt.date.astype(str)
    for c in cols:
        if c not in add.columns: add[c]=pd.NA
    shutil.copy(CLEAN,CLEAN+'.bak'); pd.concat([cl,add[cols]],ignore_index=True).to_csv(CLEAN,index=False)
    # wide rows, one per release
    ic=pd.read_csv(ICW,index_col=0,parse_dates=True)
    for wk2,wk1,rows in sorted(weeks):
        r_iu={x[3]:pd.to_numeric(x[9],errors='coerce') for x in rows}
        r_ic={x[3]:pd.to_numeric(x[4],errors='coerce') for x in rows}
        iu.loc[wk2]=pd.Series(r_iu).reindex(iu.columns)
        if wk1 is not None: ic.loc[wk1]=pd.Series(r_ic).reindex(ic.columns)
    shutil.copy(IUW,IUW+'.bak'); shutil.copy(ICW,ICW+'.bak')
    iu.sort_index().to_csv(IUW); ic.sort_index().to_csv(ICW)
    print(f'state first prints: {len(weeks)} release(s) parsed, insured unemployment through {iu.index.max().date()} ({len(rows)} states in the last)')
    return 0

if __name__=='__main__': sys.exit(main())
