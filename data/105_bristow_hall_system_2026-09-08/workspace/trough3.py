"""THE TROUGH SIDE SCORED THE WAY THE ONSET SIDE IS SCORED. The closers have been swept once, in sample, and never
looked at again. Here: what the tool's closes actually are on the corrected v3.6 rule; which object binds each close;
how the closes compare with the committee's own trough announcements; and whether an early close - a close before the
trough, which would be the trough side's false alarm - ever happens."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('trough3.out','w')"))
p=dict(BASE); p['deep']=999; p['wline']=0.30; p['wline2']=0.60; p['bshare']=0.50
r,t=build9(p)
NBERT={'1949-10':'1950-07-01','1954-05':'1955-05-01','1958-04':'1959-04-01','1961-02':'1962-02-01','1970-11':'1971-11-01',
       '1975-03':'1976-01-01','1980-07':'1980-07-08','1982-11':'1983-07-08','1991-03':'1992-12-22','2001-11':'2003-07-17',
       '2009-06':'2010-09-20','2020-04':'2021-07-19','2024-08':None}
P(f"{'trough':8s} {'closed':11s} {'leg':4s} {'dated':8s} {'lag d':>6s} {'err':>4s}   {'committee announced':20s} {'days it beat them by':>20s}")
rows=[]
for i in range(13):
    tr=TR[i]; key=tr.strftime('%Y-%m')
    c=r['closes'].get(i) if 'closes' in r else None
    if c is None:
        cand=[x for x in t if x['kind']=='trough' and tr-pd.DateOffset(months=6)<=x['date']<=tr+pd.DateOffset(months=12)]
        c=cand[0] if cand else None
    if c is None: P(f"{tr:%Y-%m}  {'-':11s}"); continue
    lag=(c['published']-me(tr)).days; err=(c['date'].year-tr.year)*12+c['date'].month-tr.month
    ann=NBERT.get(key); beat=((pd.Timestamp(ann)-c['published']).days if ann else None)
    rows.append((i,lag,err,beat))
    P(f"{tr:%Y-%m}  {c['published']:%Y-%m-%d}  {c['leg']:4s} {c['date']:%Y-%m}  {lag:6d} {err:+4d}   {str(ann):20s} {('' if beat is None else f'{beat:+d}'):>20s}")
lg=[x[1] for x in rows]; er=[x[2] for x in rows]; bt=[x[3] for x in rows if x[3] is not None]
P(f"\n   closed {len(rows)}/13 | median {np.median(lg):.0f} days, mean {np.mean(lg):.1f}, worst {max(lg)}")
P(f"   dates exact {sum(1 for e in er if e==0)}, within one {sum(1 for e in er if abs(e)<=1)}, worst {max(abs(e) for e in er)}")
P(f"   EARLY CLOSES (a close dated before the trough): {sum(1 for e in er if e<0)}")
P(f"   beat the committee's own trough announcement by a median of {np.median(bt):.0f} days (mean {np.mean(bt):.0f}, worst {min(bt)})")
allt=[x for x in t if x['kind']=='trough']
inside=[x for x in allt if any(tr-pd.DateOffset(months=6)<=x['date']<=tr+pd.DateOffset(months=12) for tr in TR)]
P(f"   closes in the record: {len(allt)}, of which {len(inside)} sit within a trough window; other closes {len(allt)-len(inside)}")
for x in allt:
    if x not in inside: P(f"      OTHER CLOSE {x['published']:%Y-%m-%d} dated {x['date']:%Y-%m} by {x['leg']}")
P("\nWHICH CLOSER BINDS: every closer's own call for each episode, and the one the chronology took")
for k in ['K','J','H','S']:
    v=TLH.get(k,[])
    P(f"   {k}: "+", ".join(f"{pp:%Y-%m-%d}/{dd:%Y-%m}" for pp,dd in v))
out.close()
