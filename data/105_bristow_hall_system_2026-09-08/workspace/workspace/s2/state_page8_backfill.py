"""Fill the gaps in the state first-print wide files from the Department's page-8 archive.

`45/state_iu_first_print_wide.csv` has 41 weeks with no states in it (2002, 2007, 2019, 2022 and eight weeks of
2025). A missing week costs TWO readings of the breadth object: its own, and the week 52 weeks later, whose
year-over-year base it is. That is why the object stopped at 22 August 2026 even after the live feed was wired
(11 September 2026): its base week, 30 August 2025, is one of the holes.

This fetches the page-8 release for each missing week from the archive and writes it in. Weeks already in hand are
untouched. Run: python3 s2/state_page8_backfill.py [year ...]
"""
import os,re,sys,time,shutil,urllib.request,urllib.parse
import pandas as pd
C45=os.path.expanduser('~/Projects/Onset Detector Data/45_dol_first_prints_2026-09')
IUW=os.path.join(C45,'state_iu_first_print_wide.csv'); ICW=os.path.join(C45,'state_ic_first_print_wide.csv')
RAWD=os.path.join(C45,'dol_page8_live'); os.makedirs(RAWD,exist_ok=True)
UA={'User-Agent':'Mozilla/5.0'}
def get(url,data=None,tries=3,timeout=60):
    err=None
    for i in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url,data=data,headers=UA),timeout=timeout).read().decode('latin-1')
        except Exception as e: err=e; time.sleep(3*(i+1))
    raise err
def parse(h):
    t=re.sub(r'<[^>]+>',' ',h); t=re.sub(r'\s+',' ',t)
    m1=re.search(r'Initial Claims Filed During Week Ended\s*([A-Za-z]+ \d+, \d{4})',t)
    m2=re.search(r'Insured Unemployment For Week Ended\s*([A-Za-z]+ \d+, \d{4})',t)
    ic={}; iu={}
    for row in re.findall(r'<TR[^>]*>(.*?)</TR>',h,re.S|re.I):
        cells=[re.sub(r'<[^>]+>','',c).replace('&nbsp','').replace(';','').strip() for c in re.findall(r'<T[DH][^>]*>(.*?)</T[DH]>',row,re.S|re.I)]
        if len(cells)<14 or not cells[0] or cells[0].upper()==cells[0]: continue
        v=[c.replace(',','') for c in cells]
        st=v[0].strip().rstrip('*')
        def _n(x):
            try: return float(x)
            except Exception: return None
        ic[st]=_n(v[1]); iu[st]=_n(v[7])
    return (pd.Timestamp(m1.group(1)) if m1 else None),(pd.Timestamp(m2.group(1)) if m2 else None),ic,iu

def main():
    iu=pd.read_csv(IUW,index_col=0,parse_dates=True); ic=pd.read_csv(ICW,index_col=0,parse_dates=True)
    F=iu.resample('W-SAT').last()
    miss=[i for i in F.index if F.loc[i].notna().sum()<20]
    years=[int(y) for y in sys.argv[1:]] or sorted({d.year for d in miss})
    miss=[d for d in miss if d.year in years]
    print(f'{len(miss)} missing week(s) in {years}')
    filled=0
    for y in years:
        want={d for d in miss if d.year==y}
        if not want: continue
        try: h=get('https://oui.doleta.gov/unemploy/archive.asp',urllib.parse.urlencode({'report':'page8','year':str(y),'submit':'Submit'}).encode())
        except Exception as e: print(f'  {y}: archive not read ({str(e)[:60]})'); continue
        links=sorted(set(re.findall(r'/unemploy/page8/%d/[0-9]+\.html'%y,h)))
        # a week's figures are published 1-2 weeks later, so scan that year's releases and the next year's January ones
        extra=[]
        if any(d.month==12 for d in want):
            try:
                h2=get('https://oui.doleta.gov/unemploy/archive.asp',urllib.parse.urlencode({'report':'page8','year':str(y+1),'submit':'Submit'}).encode())
                extra=sorted(set(re.findall(r'/unemploy/page8/%d/[0-9]+\.html'%(y+1),h2)))[:6]
            except Exception: pass
        for l in links+extra:
            if not want: break
            fn=l.split('/')[-2]+'_'+l.split('/')[-1]; p=os.path.join(RAWD,fn)
            try: h3=open(p,encoding='latin-1').read() if os.path.exists(p) else get('https://oui.doleta.gov'+l)
            except Exception: continue
            if not os.path.exists(p): open(p,'w',encoding='latin-1').write(h3); time.sleep(0.35)
            w1,w2,r_ic,r_iu=parse(h3)
            if w2 is None or w2 not in want or len([v for v in r_iu.values() if v]) <40: continue
            iu.loc[w2]=pd.Series(r_iu).reindex(iu.columns)
            if w1 is not None: ic.loc[w1]=pd.Series(r_ic).reindex(ic.columns)
            want.discard(w2); filled+=1; print(f'  filled {w2.date()} from {fn} ({len([v for v in r_iu.values() if v])} states)')
        if want: print(f'  {y}: still missing {[d.date() for d in sorted(want)]}')
    if filled:
        shutil.copy(IUW,IUW+'.bak2'); shutil.copy(ICW,ICW+'.bak2')
        iu.sort_index().to_csv(IUW); ic.sort_index().to_csv(ICW)
    print(f'filled {filled} week(s); insured unemployment now through {iu.index.max().date()}')
    return 0
if __name__=='__main__': sys.exit(main())
