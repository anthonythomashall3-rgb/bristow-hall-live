"""ANTHONY'S RULING (6 Sep 2026): lines may be fitted — the Michez/Sahm/SOS standard, the tightest clean line on the whole record —
so long as there is NO FALSE ALARM. So: sweep every line of v2.5 to its fastest value that keeps ZERO other calls on BOTH vintages and on
the 1947-70 reconstruction. The Sahm hub line stays at 0.50 by Anthony's explicit instruction; everything else is swept.
Boundary fix ('at four months') in throughout."""
from mini import *
from legu_min import s_cur, spl
exec(open('speed61.py').read().split("P(\"Aug 1953")[0].replace("out=open('speed61.out','w')","out=open('sweep1.out','w')"))
def mkpair(starts,half):
    rate=(((UR-UR.rolling(12).min())*10).round()/half); hh=(lh.rolling(12).max()-lh.rolling(2).mean())/starts
    ev=[(relH[m],'D',m) for m in hh.index if m in relH.index]+[(relU[m],'U',m) for m in rate.index if m in relU.index and m>=pd.Timestamp('1960-01-01')]
    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastU=None; fires={}; mx={}
    for d,kind,m in ev:
        if kind=='D': lastD=m if (lastD is None or m>lastD) else lastD
        else: lastU=m if (lastU is None or m>lastU) else lastU
        if lastD is None or lastU is None: continue
        v=min(hh.get(lastD,np.nan),rate.get(lastU,np.nan))
        if np.isnan(v): continue
        key=max(lastD,lastU); mx[key]=max(mx.get(key,-9),v)
        if v>=1.0 and key not in fires: fires[key]=d
    G=pd.Series({m:(1.0 if m in fires else mx[m]) for m in mx}).sort_index(); PB=pd.Series({m:fires.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=2)) for m in mx}).sort_index()
    return dict(name=f'pair{starts}x{half}',gap=G,line=1.0,pubs=PB), pd.Series(mx).sort_index()
def mkhours(h1,h2):
    AWHt=(AWH*10).round().astype('Int64'); mx_=AWHt.rolling(12).max(); hf=(1000*(mx_-AWHt)>=int(h1*10)*AWHt).fillna(False).astype(bool)
    NDt=ND.round().astype('Int64'); nd3=NDt.shift(3); nf=(10000*(nd3-NDt)>=int(h2*100)*nd3).fillna(False).astype(bool)
    ser=pd.Series({m:(1.0 if (bool(hf.get(m,False)) and bool(nf.get(m,False))) else 0.0) for m in AWH.index}).dropna()
    return dict(name=f'hours{h1}x{h2}',gap=ser,line=1.0,pub_day=5)
def run(p,s,tag=''):
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    V=dict(name='vac',gap=vr,line=p['vac'],pubs=VJ36['pubs']); Hc,_=mkpair(p['starts'],p['half']); Hh=mkhours(p['h1'],p['h2'])
    U=confirm_w(leg_gapx(s,p['u45'],rearm='zero')+F45,[V,Hh],'month'); L=confirm_w(leg_gapx(s,p['low'],rearm='window')+F25,[Hc],'month'); X=hub_actual(p['sahm'],vr,p['vac'])
    pk={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TLC)
    return score13(turns)
BASE=dict(sahm=0.50,vac=0.36,u45=0.45,low=0.25,starts=35,half=4,h1=2.0,h2=1.20)
def show(nm,p):
    rs=[run(p,s) for s in (s_cur,spl)]
    ok=all(len(r['other'])==0 and len(r['lags_p'])==13 for r in rs)
    lp=[rs[0]['lags_p'].get(i) for i in range(13)]; lf=[rs[1]['lags_p'].get(i) for i in range(13)]
    v73=[rs[0]['lags_p'][i] for i in range(5,13) if i in rs[0]['lags_p']]
    P(f"{'OK ' if ok else 'BAD'} {nm:44s} cur {lp} | fp2007 {lf[10]} | 1973-on med {np.median(v73):.1f} mean {np.mean(v73):.1f} | others {[o[1] for r in rs for o in r['other']]}")
    return ok,np.mean(v73),lp
P("baseline v2.5 (boundary fixed):"); show('v2.5',BASE)
P("\n--- vacancy line ---")
for v in [0.42,0.36,0.35,0.34,0.32,0.30,0.28]: show(f'vacancy {v}',{**BASE,'vac':v})
P("\n--- starts line (housing half) ---")
for st in [40,35,32,30,28,25]: show(f'starts {st}',{**BASE,'starts':st})
P("\n--- pair rate half (tenths) ---")
for h in [5,4,3]: show(f'rate half {h} tenths',{**BASE,'half':h})
P("\n--- 0.45 branch line ---")
for u in [0.70,0.55,0.45,0.40,0.35,0.30]: show(f'u45 {u}',{**BASE,'u45':u})
P("\n--- low branch line ---")
for l in [0.35,0.30,0.25,0.22,0.20]: show(f'low {l}',{**BASE,'low':l})
P("\n--- hours pair lines ---")
for h1,h2 in [(2.0,1.20),(1.8,1.20),(2.0,1.00),(1.8,1.00),(1.6,1.20)]: show(f'hours {h1} x {h2}',{**BASE,'h1':h1,'h2':h2})
out.close()
