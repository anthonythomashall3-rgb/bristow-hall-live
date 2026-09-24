# q29.py - THE AUDIT OF WALK51 (the search week in the sudden stop; starts or permits in the housing x rate pair): (1) the
# frozen record 1948-2026 at walk51's own walk-end lines (the survey-week line 0.3 from the 1992 cut) and at v3.26's;
# (2) for each walked call, the proposer and the confirmer that bound it, with the half of the pair that stood at the
# line (starts, permits, or both) and the source of the permits reading that day (ALFRED vintage, the printed table,
# the current file); (3) the margins of 2025: the survey-week proposals open at the 0.3 line and the largest reading of
# each weak confirmer while they were open. Run: PYTHONPATH=. python3 s2/q29.py
import sys,pickle,io,contextlib,os
sys.path.insert(0,os.getcwd()); sys.argv=['walk51.py','1962','2026','w51']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
with contextlib.redirect_stdout(io.StringIO()): exec(open('walk51.py').read().split(_MARK)[0])
p51=pickle.load(open('cache/w51_carry.pkl','rb')); p46=pickle.load(open('cache/w46_carry.pkl','rb'))
def show(nm,p):
    r,t=build_v(p); op={i:(r['opens'][i]['published'].date().isoformat(),r['opens'][i]['leg']) for i in r['opens']}
    print(f"{nm}: peaks {len(r['lags_p'])}/13 other {r['other']} lags {[r['lags_p'][i] for i in sorted(r['lags_p'])]} troughs {len(r['lags_t'])}/13"); print('   opens',op); return r,t
show('frozen at walk51 walk-end lines (wline 0.3)',p51)
show('frozen at v3.26 walk-end lines (wline 0.4)',p46)
# (2) the pair's halves and the permits source on the walked open days
A=mkpair_asof(p51['hline']); Pm=mkpair_perm_asof(p51['hline']); E=mkpair_either_asof(p51['hline'])
pg=pickle.load(open('cache/w51_prog.pkl','rb')); LOG=sorted(pg['log'],key=lambda z:z[0])
print('--- walked opens: leg, the pair on that day (starts pair, permits pair, either), permits source of the binding month')
for d,kind,dated,leg in LOG:
    if kind!='OPEN': continue
    d=pd.Timestamp(d)
    def last_at(obj):
        s=obj['pubs'][obj['pubs']<=d]; 
        if not len(s): return None
        m=s.index.max(); return (m.strftime('%Y-%m'),round(float(obj['gap'].get(m,np.nan)),3),s.max().date().isoformat())
    src=None
    try:
        ms=[m for m in PERM_SRC.index if m<=d]; src=(PERM_SRC[ms[-1]] if ms else None)
    except Exception: pass
    print(f"  {d.date()} {leg}: starts pair {last_at(A)} | permits pair {last_at(Pm)} | either {last_at(E)} | permits source {src}")
# (3) 2025 margins at the 0.3 survey-week line
props=[(a,b) for a,b in leg_sv_x(0.3,rearm='zero') if a.year>=2024]
print('--- survey-week proposals at 0.3 from 2024:',[(a.date().isoformat(),b.strftime('%Y-%m')) for a,b in props])
G=vgap2_asof(p51['vk'],p51['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
SV=mkpair_sv_asof(G,pubs,p51['vl'])
for nm,obj in (('either pair',E),('starts pair',A),('permits pair',Pm),('starts x vacancy pair',SV)):
    g=obj['gap']; w=g[(g.index>='2024-10-01')&(g.index<='2026-08-01')]
    print(f"  {nm} 2024-10..2026: max {round(float(w.max()),3)} at {w.idxmax().strftime('%Y-%m')} (line 1.0)")
w=GSP[(GSP.index>='2024-10-01')]; print(f"  spread object 2024-10..2026: max {round(float(w.max()),3)} at {w.idxmax().date()} (line {p51['spr']})")
