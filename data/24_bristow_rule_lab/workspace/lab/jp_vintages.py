"""Japan on the ESRI's own component sets, vintage by vintage (Pass A.4 of the plan).

The National Diet Library's archive of esri.cao.go.jp carries the ESRI's end-of-revision
workbooks for the 9th to 12th revisions of the indexes of business conditions (pulled through
Anthony's browser on 2 September 2026, lab/acq/esri/vintages/, SHA-256 manifest beside them).
pastci2_last{09,10,11,12}th holds the coincident components as they stood at the end of each
revision - the 9th on the 2005 base to August 2011 (production, producer shipments, large-lot
power, capacity utilization, non-scheduled hours, investment-goods shipments, retail and
wholesale sales (change from a year earlier), operating profits, SME shipments, the job-offer
ratio); the 10th to May 2015; the 11th to May 2020; the 12th to December 2020 (exports volume
added).  Every component is positively signed in the ESRI's own tables.

For each vintage, the tool's diffusion route (bench.date_diffusion_panel, the shipped
settings) is run on that vintage's components alone, over every ESRI contraction whose
window lies inside the vintage's span, and the dates are scored against the ESRI's
chronology; beside them the shipped record on today's panel for the same contractions.  The
question is Rule 17's: does the committee's own component set, as it stood when the
committee dated, put the rule on the exact month where today's panel does not?
"""
import sys, re, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import numpy as np, pandas as pd
import bench, bristow_rule_v3 as B
V='/home/claude/lab/acq/esri/vintages'
FILES={'9th':'pastci2_last09th.xls','10th':'pastci2_last10th.xls','11th':'pastci2_last11th.xlsx','12th':'pastci2_last12th.xlsx'}
def load_vintage(f):
    d=pd.read_excel(f'{V}/{f}',sheet_name=0,header=None)
    codes=[str(d.iloc[0,c]).strip().split()[0] if str(d.iloc[0,c])!='nan' else None for c in range(d.shape[1])]
    names=[str(d.iloc[2,c]).replace('\n',' ').strip() for c in range(d.shape[1])]
    rows=d[pd.to_numeric(d[1],errors='coerce').notna() & pd.to_numeric(d[2],errors='coerce').notna()]
    t=pd.to_datetime(dict(year=rows[1].astype(int),month=rows[2].astype(int),day=1))
    chs=[]
    for c in range(3,d.shape[1]):
        code=codes[c]
        if not code or not re.match(r'^C\d+$',code): continue      # skip C10-1/C10-2 sub-series and notes
        s=pd.to_numeric(rows[c],errors='coerce'); s.index=t.values; s=s.dropna().astype(float)
        if len(s)<60: continue
        chs.append((f'{code} {names[c][:50]}',s))
    return chs
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def score(rows):
    ep=[r[2] for r in rows if r[2] is not None]; et=[r[3] for r in rows if r[3] is not None]
    f=lambda e,k: sum(abs(x)<=k for x in e)
    return f'peaks exact {f(ep,0)} w1 {f(ep,1)} w3 {f(ep,3)} of {len(ep)} (mae {np.mean(np.abs(ep)):.2f}) | troughs exact {f(et,0)} w1 {f(et,1)} w3 {f(et,3)} of {len(et)} (mae {np.mean(np.abs(et)):.2f})'
if __name__=='__main__':
    bench.SKIP={'exports','imports','car registrations','unemployment','construction production','construction output','capital goods production','intermediate goods production','consumer durables production'}
    bench.ABSTAIN=True
    chrono=bench.PANELS['Japan']['chrono']
    # the shipped record on today's panel, per contraction
    ship={}
    for r in bench.run_country_concept('Japan'):
        ship[(r['peak_off'],r['tr_off'])]=(r['ep'],r['et'])
    for rev,f in FILES.items():
        chs=load_vintage(f)
        span=(min(s.index.min() for n,s in chs), max(s.index.max() for n,s in chs))
        print(f'\n=== {rev} revision: {len(chs)} components, {span[0]:%Y-%m}..{span[1]:%Y-%m}')
        for n,s in chs: print(f'     {n}  {s.index.min():%Y-%m}..{s.index.max():%Y-%m}')
        rows=[]; rows_ship=[]
        for _e in chrono:
            pk_off,tr_off,freq=bench.ep3(_e,'M')
            pkm=bench.ts(pk_off); trm=bench.ts(tr_off)
            w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
            if w0<span[0] or w1>span[1]: continue
            use=[(n,s) for n,s in chs if s.index.min()<=w0 and s.index.max()>=w1]
            if len(use)<5: continue
            d=bench.date_diffusion_panel(use,w0,w1)
            ep=md(d['peak'],pkm) if d['peak'] is not None else None
            et=md(d['trough'],trm) if d['trough'] is not None else None
            se=ship.get((pk_off,tr_off),(None,None))
            rows.append((pk_off,tr_off,ep,et,len(use))); rows_ship.append((pk_off,tr_off,se[0],se[1]))
            print(f'   {pk_off[:7]} / {tr_off[:7]}: vintage peak {ep!s:>5} trough {et!s:>5} ({len(use)} components) | shipped panel peak {se[0]!s:>5} trough {se[1]!s:>5}')
        print('   vintage components:', score(rows))
        print('   shipped panel     :', score(rows_ship))
