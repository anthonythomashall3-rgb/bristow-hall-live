# q33.py - 2024 AND THE HUB'S HOLD. The hub X fires when the Sahm gap (as it stood on the release day) is at 0.3667 with the
# vacancy gap at its line in two of the prior nine months AND in the latest JOLTS print known that day. In 2024 the Sahm gap
# reached the line with the April report (3 May 2024) but the latest print (March JOLTS, 1 May) stood at 0.187 against
# 0.20, so the hub waited for the May report (7 June, +38). Without the hold the hub fires 16 December 2025 (the delayed
# November report) - a false alarm. This script prints the monthly anatomy 2023-2025 and tests, frozen 1948-2026 on
# walk51's objects at its walk-end lines, three holds with no new number: (A) as walked; (B) the latest OR the print before
# it at the line (a two-print reading of 'still falling'); (C) the latest print at the line OR the vacancy at the line in
# three of the prior nine months (the hold's own count, one more). Run: PYTHONPATH=. python3 s2/q33.py
import sys,os,io,contextlib,pickle
sys.path.insert(0,os.getcwd()); sys.argv=['walk51.py','1962','2026','w51']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
with contextlib.redirect_stdout(io.StringIO()): exec(open('walk51.py').read().split(_MARK)[0])
p=pickle.load(open('cache/w51_carry.pkl','rb'))
G=vgap2_asof(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
print('--- 2023-08..2025-12: month | Sahm gap as of its release | release day | latest JOLTS print known that day (month, gap) | print before it | hits in prior 9 months')
for m in pd.date_range('2023-08-01','2025-12-01',freq='MS'):
    sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
    known=pubs[(pubs.index<=m)&(pubs<=sp)]; km=known.index.max() if len(known) else None
    prev=[x for x in known.index if x<km] if km is not None else []
    w=G[(G.index>=m-pd.DateOffset(months=p['hback']))&(G.index<=m)]; hits=int((w>=p['vl']-EPS).sum())
    print(f"{m.strftime('%Y-%m')} | Sahm {float(g_asof.get(m,np.nan)):.3f} | {sp.date()} | latest {km.strftime('%Y-%m') if km is not None else None} {float(G.get(km,np.nan)) if km is not None else np.nan:.3f} | prior {float(G.get(prev[-1],np.nan)) if prev else np.nan:.3f} | hits9 {hits}")
def hub_variant(kind):
    calls=[]; armed=True; sl=p['sahm']; back=p['hback']; vl=p['vl']
    for m,v in g_asof.items():
        if m<pd.Timestamp('1948-06-01'): continue
        if armed and v>=sl-EPS:
            w=G[(G.index>=m-pd.DateOffset(months=back))&(G.index<=m)]; hit=w[w>=vl-EPS]
            sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
            ok=len(hit)>=2
            if ok and kind!='nohold':
                known=pubs[(pubs.index<=m)&(pubs<=sp)]
                if not len(known): ok=False
                else:
                    ks=sorted(known.index); latest=float(G.get(ks[-1],np.nan))>=vl-EPS
                    prior=(len(ks)>=2 and float(G.get(ks[-2],np.nan))>=vl-EPS)
                    if kind=='A': ok=latest
                    elif kind=='B': ok=latest or prior
                    elif kind=='C': ok=latest or len(hit)>=3
            if ok:
                kk=hit.index[1] if len(hit)>=2 else m; calls.append((max(sp,pubs[kk]) if kk in pubs.index else sp,m-pd.DateOffset(months=3),'hub')); armed=False
        elif not armed and v<sl-EPS: armed=True
    return calls
PKm=[pd.Timestamp(x) for x in PK]; TRm=[pd.Timestamp(x) for x in TR]
def in_rec(t): return any(PKm[i]-pd.DateOffset(months=6)<=pd.Timestamp(t.year,t.month,1)<=TRm[i] for i in range(len(PKm)))
for kind in ('A','B','C','nohold'):
    c=hub_variant(kind); out=[(d.date().isoformat(),m.strftime('%Y-%m')) for d,m,_ in c if not in_rec(d)]
    y24=[d.date().isoformat() for d,m,_ in c if d.year==2024]
    print(f"hub hold {kind}: {len(c)} proposals since 1948; outside a recession: {out}; 2024: {y24}")
# the full rule frozen with hold B, to see every call and any other change
_hub_kind='B'
_build0=build_v
import types
src=open('walk51.py').read().split(_MARK)[0]
