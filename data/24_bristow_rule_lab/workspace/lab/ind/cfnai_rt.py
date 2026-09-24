"""CFNAI gate in real time: the Chicago Fed's own vintages (cfnai-realtime-{1,2,3}.xlsx,
api.data.chicagofed.org, fetched 2 Sep 2026).  Column CF3{m}{yyyy} is the three-month average
as released in month m of year yyyy.  For each vintage in order, the gate fires the first time
the MA3 stands at or below the threshold after six months above it (same rule as the
current-vintage test); the call is charged to the vintage's release month and dated at the
month the MA3 crossed."""
import pandas as pd, numpy as np, re, sys
NBER=[('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04')]
def load():
    cols={}
    for i in (1,2,3):
        x=pd.read_excel(f'cfnai-realtime-{i}.xlsx',sheet_name='cfnai_realtime',header=None)
        hdr=x.iloc[0].tolist(); dates=pd.to_datetime(x.iloc[1:,0],errors='coerce')
        dates=dates.dt.to_period('M').dt.to_timestamp()
        for j,h in enumerate(hdr):
            if isinstance(h,str) and h.startswith('CF3'):
                m=re.match(r'CF3(\d{1,2})(\d{4})$',h)
                if not m: continue
                rel=pd.Timestamp(int(m.group(2)),int(m.group(1)),1)
                s=pd.to_numeric(x.iloc[1:,j],errors='coerce'); s.index=dates; s=s.dropna()
                if len(s): cols[rel]=s
    return dict(sorted(cols.items()))
V=load()
print('vintages',len(V),min(V).date(),max(V).date())
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
for th in (-0.7,-0.6,-0.5):
    print(f'=== threshold {th}')
    calls=[]; armed=True
    prev_state=None
    for rel,s in V.items():
        # the gate as it would have stood on this release: evaluate the crossing in the latest 6 months
        on=(s<=th)
        # find crossings in the vintage: months where on and the previous six months all off
        cr=[t for i,t in enumerate(s.index) if i>=6 and on.iloc[i] and not on.iloc[i-6:i].any()]
        last=s.index[-1]
        # a NEW call: a crossing within the last 3 months of this vintage that no earlier call covers
        for t in cr:
            if md(last,t)<=3 and all(md(t,c[1])>12 for c in calls):
                calls.append((rel,t)); break
    for rel,t in calls:
        near=min(NBER,key=lambda pt: abs(md(t,pd.Timestamp(pt[0]+'-01'))))
        pk=pd.Timestamp(near[0]+'-01'); tr=pd.Timestamp(near[1]+'-01')
        inside = pk-pd.DateOffset(months=3)<=t<=tr+pd.DateOffset(months=3)
        print(f'   released {rel:%Y-%m}  crossing month {t:%Y-%m}  nearest peak {near[0]}  crossing-peak {md(t,pk):+d} m  release-peak {md(rel,pk):+d} m  {"inside" if inside else "FALSE ALARM"}')
