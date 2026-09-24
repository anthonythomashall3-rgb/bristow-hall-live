"""Rule 18 item 4: the rule on economies that have NO dating committee, scored against the one
independent classical chronology that dates them - ECRI's 22-country table (July 2021; the
September 2010 table with ECRI_TABLE=2010).
Panels are the OECD Key Economic Indicator channels already on disk (lab/kei), routed as a
level chronology at the shipped configuration; nothing about these economies entered any
choice.  Australia is also scored against the Melbourne Institute's monthly dates."""
import sys, json, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import pandas as pd, numpy as np
import bristow_rule_v3 as B, bench
from bench import kei, pro, date_any, KEI
import os
ecri=json.load(open(f"/home/claude/lab/cmp/ecri_chronology_{os.environ.get('ECRI_TABLE','2021')}.json"))
bench.SKIP={'exports','imports','car registrations','unemployment','construction production','construction output',
            'capital goods production','intermediate goods production','consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
md=B._md
def contractions(lst):
    """ECRI lists P and T in order; pair each P with the next T."""
    out=[]; pk=None
    for k,d in lst:
        if k=='P': pk=d
        elif k=='T' and pk is not None: out.append((pk,d)); pk=None
    return out
def panel(area):
    chs=[]
    for nm,p,kind in kei(area):
        if nm in bench.SKIP: continue
        try: chs.append((nm,pro(p,kind)))
        except Exception as e: print('  !',area,nm,e)
    return chs
def run(area, name, chron, chs):
    rows=[]; ep=[]; et=[]
    for pk,tr in chron:
        pkm=pd.Timestamp(pk+'-01'); trm=pd.Timestamp(tr+'-01')
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if len(use)<1: rows.append((pk,tr,'no data','')); continue
        b=date_any(name,use,w0,w1,**K)
        e1=None if b['peak'] is None else md(b['peak'],pkm); e2=None if b['trough'] is None else md(b['trough'],trm)
        ep.append(e1); et.append(e2); rows.append((pk,tr,e1,e2,len(use),b['verdict']))
    return rows,ep,et
def cnt(e):
    e=[x for x in e if x is not None]
    return f"{sum(x==0 for x in e)} / {sum(abs(x)<=1 for x in e)} / {sum(abs(x)<=3 for x in e)} of {len(e)}" + (f", mae {np.mean(np.abs(e)):.2f}" if e else '')
bench.PANELS.setdefault('United Kingdom',{'ch':[],'chrono':[],'freq':'M'})
AREAS=(('GBR','United Kingdom'),('ITA','Italy'),('AUT','Austria'),('AUS','Australia'),
       # the rest of ECRI's 22 with a monthly OECD channel on disk (pulled 2 September 2026): Sweden, Poland, Russia, India, Switzerland
       ('SWE','Sweden'),('POL','Poland'),('RUS','Russia'),('IND','India'),('CHE','Switzerland'))
for area,name in AREAS:
    bench.PANELS.setdefault(name,{'ch':[],'chrono':[],'freq':'M'}); bench.CONCEPT[name]='level'
    chs=panel(area)
    print(f"\n### {name} — channels: {[(nm,str(s.index.min().date())[:7]) for nm,s in chs]}")
    chron=contractions(ecri[name])
    rows,ep,et=run(area,name,chron,chs)
    print(f"ECRI, {len(chron)} contractions: peaks {cnt(ep)} | troughs {cnt(et)}")
    for r in rows: print('   ',r)
    if area=='AUS':
        MI=[('1975-05','1975-11'),('1981-10','1983-05'),('1990-03','1991-06'),('2020-03','2020-05')]   # Melbourne Institute monthly dates
        rows,ep,et=run(area,name,MI,chs)
        print(f"Melbourne Institute monthly dates, {len(MI)} contractions: peaks {cnt(ep)} | troughs {cnt(et)}")
        for r in rows: print('   ',r)
