"""THE WALK-FORWARD DIARY FOR v3.6 — v3.5 plus the claims deep branch (initial claims 7.5 per cent above their 52-week
minimum, requiring TWO of the four demand objects). Same standard as walk1: start 1949, re-choose every January from
what had been published and only from recessions dated AND announced by then, freeze, run the year, write down every
call, never look forward."""
import sys
exec(open('causal28.py').read().split('MODE=sys.argv[2]')[0].replace("out=open('causal28_%s.out'%(sys.argv[2] if len(sys.argv)>2 else 'fast'),'w')","out=open('walk3_%s.out'%sys.argv[1],'w')"))
Y0,Y1=int(sys.argv[1]),int(sys.argv[2])
def confirm_n(calls,confs,n=1,back=6,fwd=4):
    out_=[]
    for p_,dd in calls:
        lo=dd-pd.DateOffset(months=back); hi=dd+pd.DateOffset(months=fwd)+pd.offsets.MonthEnd(0); pubs_=[]
        for c in confs:
            gp=c['gap']; w=gp[(gp.index>=lo)&(gp.index<=hi)]; hit=w[w>=c['line']]
            if not len(hit): continue
            k=hit.index[0]
            if 'pubs' in c and c['pubs'] is not None and k in c['pubs'].index: pubs_.append((c['pubs'][k],c['name']))
            elif 'pub_lag_days' in c: pubs_.append((k+pd.Timedelta(days=c['pub_lag_days']),c['name']))
            else: pubs_.append((k,c['name']))
        if len(pubs_)<n: continue
        pubs_.sort(); out_.append((max(p_,pubs_[n-1][0]),dd,'+'.join(x[1] for x in pubs_[:n])))
    return out_
def build6(p):
    G=vgap(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1)
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)]; hit=w[w>=p['vl']]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]; ALL=[Vc,Hh,Hc,SP]
    U=confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')
    X=hubv(p['sahm']); I=confirm_w(leg_ic(ICfp,p['ic']),C1,'month')
    m4=ICfp.rolling(4).mean(); rel_=((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()
    cc=[]; armed=True
    for t,v in rel_.items():
        if armed and v>=p['deep']: cc.append((t+pd.Timedelta(days=5),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I],
          'D':[(a,b) for a,b,c in confirm_n(cc,ALL,n=2)]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
    return score13(turns),turns
CACHE6={}
def ev6(p):
    k=tuple(sorted(p.items()))
    if k not in CACHE6: CACHE6[k]=build6(p)
    return CACHE6[k]
BASE6=dict(BASE); BASE6['deep']=7.5
ANN={'1948-11':'1949-06-01','1953-07':'1954-08-01','1957-08':'1958-06-01','1960-04':'1961-02-01','1969-12':'1970-08-01',
     '1973-11':'1974-11-01','1980-01':'1980-06-03','1981-07':'1982-01-06','1990-07':'1991-04-25','2001-03':'2001-11-26',
     '2007-12':'2008-12-01','2020-02':'2020-06-08','2024-04':None}
ANNT=[pd.Timestamp(ANN[PK[i].strftime('%Y-%m')]) if ANN[PK[i].strftime('%Y-%m')] else pd.Timestamp('2100-01-01') for i in range(13)]
GRID=[('sahm',[0.50,0.45,0.43,0.40]),('vl',[0.30,0.25,0.20,0.15]),('u45',[0.55,0.45,0.35]),('low',[0.30,0.25,0.20]),
      ('look',[52,78,91,130]),('spr',[1.6,round(LINE,3),1.1]),('ic',[60,50,45]),('deep',[15,10,7.5,5])]
LOG=[]
for Y in range(Y0,Y1+1):
    cut=pd.Timestamp(Y,1,1); ks=[i for i in range(13) if ANNT[i]<cut]
    if not ks: continue
    p=dict(BASE6)
    for _ in range(2):
        changed=False
        for name,grid in GRID:
            cands=[]
            for gv in grid:
                q=dict(p); q[name]=gv; r,t=ev6(q)
                other=[o for o in r['other'] if pd.Timestamp(o[0])<cut]
                early=[x for x in t if x['kind']=='peak' and x['published']<pd.Timestamp('1948-06-01')]
                v=[r['lags_p'][j] for j in ks if j in r['lags_p']]
                if len(v)==len(ks) and not other and not early: cands.append((gv,float(np.mean(v))))
            if cands:
                nv=min(cands,key=lambda c:(c[1],grid.index(c[0])))[0]
                if nv!=p[name]: changed=True
                p[name]=nv
        if not changed: break
    r,t=ev6(p)
    for x in t:
        if x['kind'] in ('peak','trough') and cut<=x['published']<pd.Timestamp(Y+1,1,1):
            LOG.append((x['published'],'OPEN' if x['kind']=='peak' else 'CLOSE',x['date'],x['leg']))
LOG.sort(key=lambda z:z[0])
for pub,kind,dt,leg in LOG: P(f"   {pub:%Y-%m-%d}  {kind:5s} dated {dt:%Y-%m}  by {leg}")
import pickle; pickle.dump(LOG,open(f'cache/walk3_{Y0}.pkl','wb'))
out.close()
