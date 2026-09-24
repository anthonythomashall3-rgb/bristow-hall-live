from mini import *
o2=pickle.load(open('cache/claims_objects.pkl','rb')); Mx=o2['M']
print("claims objects, monthly max, Nov 2025 - Mar 2026 and Jan-Aug 2024:")
print(Mx.loc['2025-10':'2026-03',['iur_gap','ic4_rise%','ic4rt_rise%','cc4_rise%','breadth%']].round(2).to_string())
print(Mx.loc['2024-01':'2024-09',['iur_gap','ic4_rise%','ic4rt_rise%','cc4_rise%','breadth%']].round(2).to_string())
def inwin(d,back=6,fwd=18): return any(p-pd.DateOffset(months=back)<=d<=t+pd.DateOffset(months=fwd) for p,t in zip(PK,TR))
# hub exposure: quiet months (peak-6..trough+18 excluded) where Sahm>=s and vacancy>=v in [m-6,m] (and claims rise >= c% in [m-6,m])
ic=Mx['ic4_rise%']
def hub_quiet(s,v,c=None):
    hits=[]
    for m,val in g.items():
        if m<pd.Timestamp('1968-01-01') or inwin(m): continue
        if val<s: continue
        w=vr[(vr.index>=m-pd.DateOffset(months=6))&(vr.index<=m)]
        if len(w)==0 or w.max()<v: continue
        if c is not None:
            wc=ic[(ic.index>=m-pd.DateOffset(months=6))&(ic.index<=m)]
            if len(wc)==0 or wc.max()<c: continue
        hits.append(m.strftime('%Y-%m'))
    return hits
print("\nquiet-month firings of the hub 1968-2026 (Sahm line, vacancy line, claims co-condition):")
for s in [0.35,0.40,0.43,0.50]:
    for v in [0.30,0.36]:
        for c in [None,5,10,15]:
            h=hub_quiet(s,v,c); print(f"  Sahm {s:.2f} vac {v:.2f} claims {('none' if c is None else '>='+str(c)+'%'):>6}: {len(h)} {h}")
print("\nrecession months where the hub triple would first fire (Sahm 0.35, vac 0.30, claims >= c%), months from peak:")
for c in [None,5,10]:
    row=[]
    for p,t in zip(PK,TR):
        seg=g[(g.index>=p-pd.DateOffset(months=6))&(g.index<=t)]
        f=None
        for m,val in seg.items():
            if val<0.35: continue
            w=vr[(vr.index>=m-pd.DateOffset(months=6))&(vr.index<=m)]
            if len(w)==0 or w.max()<0.30: continue
            if c is not None:
                wc=ic[(ic.index>=m-pd.DateOffset(months=6))&(ic.index<=m)]
                if len(wc)==0 or wc.max()<c: continue
            f=md(m,p); break
        row.append(f)
    print(f"  claims {('none' if c is None else '>='+str(c)+'%'):>6}: {row}")
