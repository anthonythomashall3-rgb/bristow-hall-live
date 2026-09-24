# q27.py - consumer sentiment (Michigan, UMCSENT, ALFRED vintages) as a confirmer of the weak proposers: the index as it
# stood on each release day, points below its twelve-month high as then known; lines 10, 15, 20 points (a NEW number - a
# screen, not a clause). Frozen 1948-2026 at v3.26's walk-end lines with q16's build_variant. Reported: calls, false
# alarms, and the months the confirmer stood at each line outside a recession. Run: PYTHONPATH=. python3 s2/q27.py
import sys,os,io,contextlib,pickle
sys.path.insert(0,os.getcwd()); sys.argv=['walk46.py','1962','2026','w46']
import pandas as pd, numpy as np
src=open('s2/q16.py').read().split("VARIANTS=[")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
MNT=os.path.expanduser('~/Projects/Onset Detector Data')
V=pd.read_csv(os.path.join(MNT,'onset-detector-new-2026-08-23','27_realtime_vintages','alfred_all_vintages','UMCSENT_all_vintages.csv'))
V['date']=pd.to_datetime(V['date']); V=V.set_index('date'); V.columns=[pd.Timestamp(str(c).replace('UMCSENT_','')) for c in V.columns]
V=V.sort_index(axis=1); VFIRST=V.columns.min()   # (V0 is the lab's vacancy series - not shadowed)
print('UMCSENT vintages',V.shape,'first vintage',VFIRST.date(),'obs',V.index.min().date(),'..',V.index.max().date())
def last_friday(m):
    e=(m+pd.offsets.MonthEnd(0)); return e-pd.Timedelta(days=(e.weekday()-4)%7)
# each month's value as first published and the day it appeared; before the first vintage (July 1998) the earliest
# vintage's value with the final release's usual day (the last Friday of the month) - a declared bound
first={}; pub={}; high={}
for m in V.index:
    row=V.loc[m].dropna()
    if not len(row): continue
    d=row.index[0]; first[m]=float(row.iloc[0]); pub[m]=d if m>=VFIRST-pd.DateOffset(months=2) else last_friday(m)
    col=V[d].dropna(); col=col[(col.index<m)&(col.index>=m-pd.DateOffset(months=12))]
    high[m]=float(max(col.max() if len(col) else -np.inf,first[m]))
S=pd.Series(first).sort_index(); P=pd.Series(pub).sort_index(); H=pd.Series(high).sort_index(); DROP=(H-S)
PKm=[pd.Timestamp(x) for x in PK]; TRm=[pd.Timestamp(x) for x in TR]
def in_rec(t): return any(PKm[i]-pd.DateOffset(months=6)<=pd.Timestamp(t.year,t.month,1)<=TRm[i] for i in range(len(PKm)))
for line in (10.0,15.0,20.0):
    at=[m for m,v in DROP.items() if v>=line-EPS]; out=sorted(set((m.year,m.month) for m in at if not in_rec(m)))
    print(f'line {line}: months at line {len(at)}; outside a recession: {[f"{y}-{mo:02d}" for y,mo in out]}')
    SENT=dict(name='sent',gap=(DROP/line),line=1.0,pubs=P)
    _old=build_variant
    def build_sent(p):
        # q16's build_variant with the sentiment object appended to the weak proposers' confirmers
        import types
        src2=src.split('def build_variant')[1]
        return None
    # append through the dict q16 uses for c2_extra
    globals()['MK15']=MK15; globals()['CR20']=CR20
    _c2map={'hours':None,'vac':None,'mkt15':MK15,'crash20':CR20,'sent':SENT}
    # monkeypatch: q16 builds the map inline, so rebuild build_variant with SENT available under 'crash20' slot swapped
    CR20_backup=dict(CR20); CR20.clear(); CR20.update(SENT)
    r,t=build_variant(pw,c2_extra=('crash20',))
    CR20.clear(); CR20.update(CR20_backup)
    lags=[r['lags_p'][i] for i in sorted(r['lags_p'])]; opens_={i:(r['opens'][i]['published'].date().isoformat(),r['opens'][i]['leg']) for i in r['opens']}
    print(f"   sentiment confirmer at {line}: peaks {len(r['lags_p'])}/13 FALSE {len(r['other'])} {r['other']} | lags {lags} | 1990 {opens_.get(8)} 2008 {opens_.get(10)} | troughs {len(r['lags_t'])}/13")
