"""Keep the state FIRST PRINTS current from the weekly claims press release the system already downloads.

The breadth proposer reads `45_dol_first_prints_2026-09/state_iu_first_print_wide.csv` - each state's insured
unemployment as first published. Collection 45 built it from the Department's page-8 archive, which runs about two
weeks behind; nothing refreshed it afterwards, so the object froze at the week ending 22 August 2026 (found
11 September 2026). `bhs_dol_press.py` already saves every week's press release PDF in `45/raw/press_live/`; page 4 of
it, 'Advance State Claims - Not Seasonally Adjusted', carries each state's initial claims and insured unemployment as
first published. This script parses the PDFs the wide files do not carry and appends their weeks.

Causal: each release is read once, as published; weeks already in hand are never rewritten. The page-8 archive remains
the source for older weeks - when it catches up, its figures for these weeks are the same advance numbers.
Prints one line for the run log. Run: python3 s2/state_press_live.py
"""
import os,re,sys,glob,shutil,subprocess,datetime
import pandas as pd
C45=os.path.expanduser('~/Projects/Onset Detector Data/45_dol_first_prints_2026-09')
IUW=os.path.join(C45,'state_iu_first_print_wide.csv'); ICW=os.path.join(C45,'state_ic_first_print_wide.csv')
PRESS=os.path.join(C45,'raw','press_live')
HEAD=re.compile(r'Initial Claims Filed During Week Ended\s+([A-Z][a-z]+ \d{1,2}).{0,80}?Insured Unemployment For Week Ended\s+([A-Z][a-z]+ \d{1,2})',re.S)
ROW=re.compile(r'^\s{0,6}([A-Z][A-Za-z\.\' ]{2,24}?)\*?\s+([\d,]+)\s+([\d,]+)\s+(-?[\d,]+)\s+([\d,]+)\s+([\d,]+)\s+(-?[\d,]+)\s*$')   # a trailing * marks a state whose figure the Department flags
def _num(s):
    try: return float(s.replace(',',''))
    except Exception: return None
def _date(md,rel):
    for y in (rel.year,rel.year-1):
        try:
            d=pd.Timestamp(f'{md}, {y}')
            if pd.Timedelta(days=0)<=rel-d<=pd.Timedelta(days=45): return d
        except Exception: pass
    return None
def parse_pdf(p,rel):
    txt='/tmp/_press_%s.txt'%os.path.basename(p).replace('.pdf','')
    r=subprocess.run(['pdftotext','-layout',p,txt],capture_output=True,text=True)
    if r.returncode!=0 or not os.path.exists(txt): return None,None,{}
    t=open(txt,errors='ignore').read()
    m=HEAD.search(t)
    if not m: return None,None,{}
    wk_ic=_date(m.group(1),rel); wk_iu=_date(m.group(2),rel)
    ic={}; iu={}
    for line in t[m.end():].splitlines():
        g=ROW.match(line)
        if not g: continue
        st=g.group(1).strip()
        if st.upper()==st or st in ('STATE','TOTAL'): continue
        ic[st]=_num(g.group(2)); iu[st]=_num(g.group(5))
        if len(ic)>=53: break
    return wk_ic,wk_iu,{'ic':ic,'iu':iu}

def main():
    if not os.path.isdir(PRESS): print('state first prints: no press folder'); return 1
    iu=pd.read_csv(IUW,index_col=0,parse_dates=True); ic=pd.read_csv(ICW,index_col=0,parse_dates=True)
    have=iu.index.max(); added=[]
    pdfs=sorted(p for p in glob.glob(os.path.join(PRESS,'*.pdf')) if re.search(r'\d{4}-\d{2}-\d{2}\.pdf$',p))
    for p in pdfs:
        rel=pd.Timestamp(re.search(r'(\d{4}-\d{2}-\d{2})\.pdf$',p).group(1))
        wk_ic,wk_iu,v=parse_pdf(p,rel)
        if wk_iu is None or not v.get('iu'): continue
        if wk_iu<=have: continue
        if len(v['iu'])<40: continue                       # a short table is a parse failure, not a release
        iu.loc[wk_iu]=pd.Series(v['iu']).reindex(iu.columns)
        if wk_ic is not None: ic.loc[wk_ic]=pd.Series(v['ic']).reindex(ic.columns)
        added.append((rel.date(),wk_iu.date(),len([x for x in v['iu'].values() if x is not None])))
    if not added:
        print(f'state first prints: nothing new (insured unemployment through {have.date()}; {len(pdfs)} press release(s) on file)'); return 0
    shutil.copy(IUW,IUW+'.bak'); shutil.copy(ICW,ICW+'.bak')
    iu.sort_index().to_csv(IUW); ic.sort_index().to_csv(ICW)
    last=added[-1]
    print(f'state first prints: {len(added)} release(s) parsed from the press PDF, insured unemployment through {last[1]} ({last[2]} states; release {last[0]})')
    return 0

if __name__=='__main__': sys.exit(main())
