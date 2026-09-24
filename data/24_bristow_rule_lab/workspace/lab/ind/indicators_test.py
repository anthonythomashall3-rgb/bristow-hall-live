"""Rule 18 item 5: the thirteen indicators named on 2 September 2026, each tried against the
NBER dates two ways - (A) as a dating object on its own, read with the rule's own clauses
inside each contraction's window, and (B) as a channel added to the shipped United States
panel.  Financial gauges are also read as gates (C): the threshold with no false alarm and
the lead it then has on the peak.  Everything here is retrospective (current vintage)."""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import pandas as pd, numpy as np
import bristow_rule_v3 as B, bench
D='/home/claude/lab/ind/'
def fred(f, col=None):
    x=pd.read_csv(D+f); x.columns=['d','v']; x['d']=pd.to_datetime(x.d); x['v']=pd.to_numeric(x.v,errors='coerce')
    s=x.set_index('d').v.dropna(); s.index=s.index.to_period('M').to_timestamp(); return s.groupby(level=0).mean()
NBER=[(pd.Timestamp(p+'-01'),pd.Timestamp(t+'-01')) for p,t in bench.PANELS['United States']['chrono']]
md=B._md
# ---------------------------------------------------------------- the indicators
cfnai=fred('CFNAI.csv'); ma3=fred('CFNAIMA3.csv')
ads=pd.read_excel(D+'ads.xlsx'); ads['d']=pd.to_datetime(ads.Date,format='%Y:%m:%d'); ads=ads.set_index('d').ADS_Index
ads_m=ads.resample('MS').mean()
nfci=fred('nfci_m.csv'); anfci=fred('ANFCI.csv').resample('MS').mean()
houst=fred('HOUST.csv'); permit=fred('PERMIT.csv')
ahe=fred('AHETPI.csv'); cpi=fred('CPIAUCSL.csv'); realw=(ahe/cpi).dropna()
umcs=fred('UMCSENT.csv')
baa=fred('BAA.csv'); aaa=fred('AAA.csv'); gs10=fred('GS10.csv'); tb3=fred('TB3MS.csv')
spread_ba=(baa-aaa).dropna(); spread_bg=(baa-gs10).dropna(); curve=(gs10-tb3).dropna()
bkcr=fred('totbkcr_m.csv'); t10yie=fred('t10yie_m.csv')
gold=fred('PGOLD.csv'); copp=fred('PCOPP.csv'); cg=(copp/gold).dropna()
phil=fred('GACDFSA066MSFRBPHI.csv')
# level-type objects: cumulate the growth-type indexes so the rule can read a level
def cum(s): return np.exp((s/100.0).cumsum())    # CFNAI is in standard deviations of growth; scale is immaterial to the clauses
IND={
 'CFNAI, cumulated (activity relative to trend)':      ('level', cum(cfnai)),
 'CFNAI three-month average, as a growth-cycle object':('cycl',  ma3),
 'ADS index, monthly mean, cumulated':                 ('level', cum(ads_m)),
 'ADS index, monthly mean, as a growth-cycle object':  ('cycl',  ads_m),
 'housing starts':                                     ('level', houst),
 'building permits':                                   ('level', permit),
 'real hourly earnings (AHE/CPI)':                     ('level', realw),
 'Michigan consumer sentiment':                        ('level', umcs),
 'Philadelphia Fed general activity (PMI proxy)':      ('cycl',  phil),
 'bank credit, cumulative (TOTBKCR)':                  ('level', bkcr),
 'credit impulse (12-month change in bank credit growth)': ('cycl', (np.log(bkcr).diff(12)*100).diff(12).dropna()),
 'Baa-Aaa spread (inverted)':                          ('cycl',  -spread_ba),
 'Baa-10y Treasury spread (inverted)':                 ('cycl',  -spread_bg),
 'NFCI (inverted)':                                    ('cycl',  -nfci),
 'adjusted NFCI (inverted)':                           ('cycl',  -anfci),
 'yield curve 10y-3m':                                 ('cycl',  curve),
 '10-year breakeven inflation':                        ('cycl',  t10yie),
 'copper/gold ratio':                                  ('cycl',  cg),
}
# ---------------------------------------------------------------- (A) as a dating object on its own
def own(kind, s):
    out=[]
    for pk,tr in NBER:
        w0=pk-pd.DateOffset(months=12); w1=tr+pd.DateOffset(months=12)
        if s.index.min()>w0 or s.index.max()<w1: out.append((pk,None,None)); continue
        if kind=='level':
            t=B.channel_trough(s,w0,w1,0.12,3,12,False)
            u=B.channel_trough(s,w0,w1,0.12,3,12,False,refine=False)
            p=B.channel_peak(s,w0,u if u is not None else w1,0.01,3,False)
        else:   # a detrended / bounded object: the cyclical clauses, band zero, smoothing 3
            s=s-s.min()+100.0 if (s<=0).any() else s    # D needs a positive level; a shift moves no extremum
            t=B.channel_trough(s,w0,w1,0.0,3,12,False)
            u=B.channel_trough(s,w0,w1,0.0,3,12,False,refine=False)
            p=B.channel_peak(s,w0,u if u is not None else w1,0.01,3,False,refine=False)
        out.append((pk, None if p is None else md(p,pk), None if t is None else md(t,tr)))
    return out
def summ(errs):
    e=[x for x in errs if x is not None]
    if not e: return 'n=0'
    return f"n={len(e):2d} exact {sum(x==0 for x in e):2d} w1 {sum(abs(x)<=1 for x in e):2d} w3 {sum(abs(x)<=3 for x in e):2d} mean {np.mean(e):+.1f} mae {np.mean(np.abs(e)):.2f}"
print('=== (A) each indicator as a dating object on its own, inside each NBER window (peak -12 .. trough +12)')
for nm,(kind,s) in IND.items():
    r=own(kind,s)
    print(f"{nm:58s} peaks {summ([x[1] for x in r])} | troughs {summ([x[2] for x in r])}")
    print(' '*58, 'errors', [(str(pk.year), a, b) for pk,a,b in r if a is not None or b is not None][:12])
# ---------------------------------------------------------------- (B) as a channel added to the shipped US panel
print()
print('=== (B) added as one more channel to the shipped United States panel (level route, refinement on)')
bench.SKIP={'exports','imports','car registrations','unemployment','construction production','construction output',
            'capital goods production','intermediate goods production','consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
base=[(nm,s) for nm,s in bench.channels('United States') if nm not in bench.SKIP]
def score_panel(chs):
    ep=[];et=[]
    for pk,tr in NBER:
        w0=pk-pd.DateOffset(months=12); w1=tr+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=tr]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=tr and s.index.max()>=tr]
        if not use: use=chs
        b=bench.date_any('United States',use,w0,w1,**K)
        ep.append(None if b['peak'] is None else md(b['peak'],pk)); et.append(None if b['trough'] is None else md(b['trough'],tr))
    return ep,et
ep,et=score_panel(base)
print(f"{'shipped panel':58s} peaks {summ(ep)} | troughs {summ(et)}")
print(' '*58,'errors',list(zip([p.year for p,_ in NBER],ep,et)))
for nm,(kind,s) in IND.items():
    if kind!='level': continue
    ep2,et2=score_panel(base+[(nm,s)])
    print(f"{'+ '+nm:58s} peaks {summ(ep2)} | troughs {summ(et2)}")
# ---------------------------------------------------------------- (C) gates: zero-false-alarm thresholds and their lead on the peak
print()
print('=== (C) financial and survey gauges as real-time gates: the tightest threshold with no call outside a recession (-3..+3 months of the NBER dates)')
def gate(s, direction, name, grid):
    # a call is the first month the series crosses the threshold in `direction` after having been on the other side for 6 months
    best=None
    for th in grid:
        on = (s>=th) if direction=='above' else (s<=th)
        calls=[]; armed=True
        for i in range(6,len(s)):
            if on.iloc[i] and armed and not on.iloc[i-6:i].any(): calls.append(s.index[i]); armed=False
            if not on.iloc[i]: armed=True
        # classify each call: inside a recession window (peak-3 .. trough+3) or a false alarm
        inside=[]; false=0
        for c in calls:
            hit=[(pk,md(c,pk)) for pk,tr in NBER if pk-pd.DateOffset(months=3)<=c<=tr+pd.DateOffset(months=3)]
            if hit: inside.append(hit[0])
            else: false+=1
        covered=len({pk for pk,_ in inside}); n=sum(1 for pk,tr in NBER if s.index.min()<=pk<=s.index.max())
        row=(th,covered,n,false,[e for _,e in inside])
        if false==0 and (best is None or covered>best[1]): best=row
    return best
GATES=[('CFNAI three-month average below x', ma3,'below',[-0.4,-0.5,-0.6,-0.7,-0.8,-0.9,-1.0,-1.2]),
       ('ADS monthly mean below x', ads_m,'below',[-0.5,-0.7,-0.9,-1.0,-1.2,-1.5,-2.0]),
       ('NFCI above x', nfci,'above',[-0.3,-0.2,-0.1,0.0,0.1,0.2,0.3,0.5,0.7,1.0]),
       ('adjusted NFCI above x', anfci,'above',[-0.2,0.0,0.2,0.4,0.6,0.8,1.0,1.2]),
       ('Baa-Aaa spread above x', spread_ba,'above',[1.0,1.2,1.4,1.6,1.8,2.0,2.5,3.0]),
       ('Baa-10y spread above x', spread_bg,'above',[2.0,2.5,3.0,3.5,4.0,4.5,5.0]),
       ('yield curve 10y-3m below x', curve,'below',[0.5,0.25,0.0,-0.25,-0.5,-0.75,-1.0]),
       ('Philadelphia Fed activity below x', phil,'below',[-5,-10,-15,-20,-25,-30,-35,-40]),
       ('Michigan sentiment below x', umcs,'below',[80,75,70,65,60,55,50]),
       ('housing starts, 12-month log change below x', (np.log(houst).diff(12)*100).dropna(),'below',[-10,-15,-20,-25,-30,-35,-40]),
       ('real hourly earnings, 12-month change below x', (np.log(realw).diff(12)*100).dropna(),'below',[-0.5,-1.0,-1.5,-2.0,-2.5,-3.0]),
       ('copper/gold ratio, 12-month log change below x', (np.log(cg).diff(12)*100).dropna(),'below',[-10,-20,-30,-40,-50]),
       ('10-year breakeven, 12-month change below x', t10yie.diff(12).dropna(),'below',[-0.25,-0.5,-0.75,-1.0,-1.5])]
for name,s,dr,grid in GATES:
    b=gate(s,dr,name,grid)
    if b is None: print(f"{name:52s} no threshold in the grid is free of false alarms"); continue
    th,cov,n,false,leads=b
    print(f"{name:52s} threshold {th:>6}: {cov}/{n} recessions called, 0 false alarms; call month minus peak month {leads}")
