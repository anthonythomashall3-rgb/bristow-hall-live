"""Australia on national series (ABS labour force via the RBA's tables on DBnomics, lab/nat/aus)
against ECRI's dates and the Melbourne Institute's monthly dates.  Level route, shipped
configuration.  Australia publishes no monthly production index; the added channels are hours
worked (1978) and full-time employment (1978) beside the OECD's employment series (1967)."""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/cmp')
import pandas as pd
import bench
from bench import pro
from ecri_countries import contractions, run, cnt, ecri
NAT='/home/claude/lab/nat/aus'
def load(f): return pd.read_csv(f,index_col=0,parse_dates=True).iloc[:,0].dropna().astype(float)
bench.PANELS.setdefault('Australia',{'ch':[],'chrono':[],'freq':'M'}); bench.CONCEPT['Australia']='level'
oecd=[(nm,pro(p,kind)) for nm,p,kind in bench.kei('AUS') if nm=='employment']
nat=oecd+[('hours worked (ABS)',load(f'{NAT}/AUS_hours_worked.csv')),('full-time employment (ABS)',load(f'{NAT}/AUS_fulltime_employment.csv'))]
MI=[('1975-05','1975-11'),('1981-10','1983-05'),('1990-03','1991-06'),('2020-03','2020-05')]
for label,chs in (('OECD employment alone, as in §8e',oecd),('with ABS hours worked and full-time employment',nat)):
    print(f'\n### {label}: {[(nm,str(s.index.min().date())[:7]) for nm,s in chs]}')
    for cl,chron in (('ECRI',contractions(ecri['Australia'])),('Melbourne Institute',MI)):
        rows,ep,et=run('AUS','Australia',chron,chs)
        print(f"{cl}, {len(chron)} contractions: peaks {cnt(ep)} | troughs {cnt(et)}")
        for r in rows: print('   ',r)
