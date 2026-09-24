"""The vacancy object swept through THE LAB'S OWN vacancy_gap(k, back) function, so the series is identical to the shipped one at (2,6),
and the housing half swept in the same shape (maximum of the smoothed series, shifted one month, rather than of the raw series).
Zero other calls on both vintages required; v2.8 elsewhere."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast41.py').read().split("def full(")[0].replace("out=open('fast41.out','w')","out=open('sweep10.out','w')"))
sys.path.insert(0,W+'/lab/weekly'); import american_chronology as A
VG={}
def vgap(k,back):
    if (k,back) not in VG: VG[(k,back)]=A.vacancy_gap(k,back)
    return VG[(k,back)]
P("identity check: the lab's vacancy_gap(2,6) against the shipped vr, max |diff| =",float((vgap(2,6).reindex(vr.index)-vr).abs().max()))
def mkpair3(starts,half,k,minw,smooth_max=False):
    rate=(((UR-UR.rolling(minw).min())*10).round()/half)
    mm=lh.rolling(k).mean()
    hh=((mm.shift(1).rolling(12).max()-mm)/starts) if smooth_max else ((lh.rolling(12).max()-mm)/starts)
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
    return dict(name='pair',gap=G,line=1.0,pubs=PB), pd.Series(mx).sort_index()
def inw(dd): return any(p_-pd.DateOffset(months=6)<=dd<=t for p_,t in zip(PK,TR))
QL=sorted({dd for p_,dd in leg_gapL(s_cur,0.25,52,rearm='window') if not inw(dd)}|{dd for p_,dd in leg_gapL(spl,0.25,52,rearm='window') if not inw(dd)}|{dd for p_,dd in leg_gap_mx2(gm,0.25,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)})
def wmax(ser,dd): seg=ser[(ser.index>=dd-pd.DateOffset(months=6))&(ser.index<=dd+pd.DateOffset(months=4))]; return round(float(seg.max()),3) if len(seg) else float('nan')
def go6(nm,vk=2,vb=6,vl=0.35,starts=29,hk=3,minw=18,smax=False,quiet_out=True):
    G=vgap(vk,vb); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=vl,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    Hc,MX=mkpair3(starts,4,hk,minw,smax); Hh=mkhours(2.0,1.20)
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)]; hit=w[w>=vl]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    res=[]
    for s in (s_cur,spl):
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,[Vc,Hh],'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,[Hc],'month'); X=hubv(0.50)
        pk={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TLH)
        res.append(score13(turns))
    ok=all(len(r['other'])==0 and len(r['lags_p'])==13 for r in res)
    lp=[res[0]['lags_p'].get(i) for i in range(13)]; allv=[x for x in lp if x is not None]
    v73=[res[0]['lags_p'][i] for i in range(5,13) if i in res[0]['lags_p']]
    if ok or not quiet_out:
        mm=sorted([(wmax(MX,dd),dd.strftime('%Y-%m')) for dd in QL if not np.isnan(wmax(MX,dd))],reverse=True)[:1]
        P(f"{'OK ' if ok else 'BAD'} {nm:34s} {lp} fp2007 {res[1]['lags_p'].get(10)} med73 {np.median(v73):.1f} MEAN {np.mean(allv):.1f} w1 {sum(1 for e in res[0]['errs_p'].values() if abs(e)<=1)} margin {1-mm[0][0]:.3f} others {[o[1] for r in res for o in r['other']]}")
    return ok,(np.mean(allv) if ok else 9e9),lp
P("\nbaseline v2.8"); go6('v2.8',quiet_out=False)
P("\n--- vacancy shape on the lab's own function ---")
best=[]
for vk in [1,2,3,4]:
    for vb in [3,4,6,9,12]:
        for vl in [0.60,0.50,0.45,0.40,0.36,0.35,0.30,0.25,0.20,0.15]:
            ok,mn,lp=go6(f'vac k={vk} back={vb} line {vl}',vk=vk,vb=vb,vl=vl)
            if ok: best.append((mn,vk,vb,vl,lp))
best.sort()
P("\nBEST VACANCY FORMS BY MEAN LAG OVER ALL THIRTEEN (v2.8 mean is the baseline above):")
for mn,vk,vb,vl,lp in best[:10]: P(f"   mean {mn:6.1f}  vacancy k={vk} back={vb} line {vl}   {lp}")
P("\n--- housing half with the maximum taken over the SMOOTHED series (the lab's shape) ---")
for st in [40,35,31,29,26,23,20]: go6(f'smoothed-max starts {st}',starts=st,smax=True)
out.close()
