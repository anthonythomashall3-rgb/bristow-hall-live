# q22.py - v3.26's own rule (no co-signer clause) with the survey-week line at 0.3: does 2025 fire? And the demand-side readings of 2025.
import sys,pickle,io,contextlib,os
sys.path.insert(0,os.getcwd()); sys.argv=['walk46.py','1962','2026','w46']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
exec(open('walk46.py').read().split(_MARK)[0])
pw=pickle.load(open('cache/w46_carry.pkl','rb'))
for wl in (0.4,0.3):
    q=dict(pw); q['wline']=wl; r,t=build_v(q)
    print(f"v3.26 rule, survey-week line {wl}: peaks {len(r['lags_p'])}/13 FALSE {r['other']}")
G=vgap2_asof(pw['vk'],pw['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
Hc=mkpair_asof(1.0); SV=mkpair_sv_asof(G,pubs,pw['vl'])
sel=lambda s:{m.strftime('%Y-%m'):round(float(v),3) for m,v in s.items() if pd.Timestamp('2025-01-01')<=m<=pd.Timestamp('2025-12-01')}
print('housing x rate pair 2025 (mx):',sel(Hc['mx'])); print('starts x vacancy pair 2025 (mx):',sel(SV['mx']))
sp=GSP[(GSP.index>='2025-01-01')&(GSP.index<='2025-12-31')]; print('spread 2025 max',round(float(sp.max()),3),'line',pw['spr'])
