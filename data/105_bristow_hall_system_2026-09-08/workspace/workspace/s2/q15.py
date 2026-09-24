# q15.py - name the proposer's day and the confirmer of every walked call of w46 (v3.26), at the lines in force at
# that call's cut. Run in the workspace: python3 s2/q15.py   (loads walk46's preamble: the as-of objects, no walk)
import sys,pickle,io,contextlib,os
sys.path.insert(0,os.getcwd()); sys.argv=['walk46.py','1962','2026','w46']   # the chain reads argv; the walk itself is not run
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
exec(open('walk46.py').read().split(_MARK)[0])
pg=pickle.load(open('cache/w46_prog.pkl','rb')); CH=pg['chosen']
OPEN=['1969-10-06','1973-09-17','1979-11-29','1981-02-26','1990-09-19','2001-03-29','2007-12-24','2020-03-19','2024-06-07']
def named(p):
    """build_v's legs with the confirmer kept: branch -> [(call day, proposal month, confirmer@month, proposer's day)]"""
    global cosign
    G=vgap2_asof(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['low'])
    Hc=mkpair_asof(p['hline']); Hh=HOURS_ASOF
    SP=dict(name='spread',gap=GSP,line=p['spr'],pubs=SP_PUBS)
    SV=mkpair_sv_asof(G,pubs,p['vl'])
    out={}
    def hub(sl,back):
        calls=[]; armed=True
        for m,v in g_asof.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl-EPS:
                w=G[(G.index>=m-pd.DateOffset(months=back))&(G.index<=m)]; hit=w[w>=p['vl']-EPS]
                sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                ok=len(hit)>=2
                if ok:
                    known=pubs[(pubs.index<=m)&(pubs<=sp)]
                    ok=len(known)>0 and float(G.get(known.index.max(),np.nan))>=p['vl']-EPS
                if ok:
                    kk=hit.index[1]
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub: rate month %s on %s; vacancy hits %s (pub %s) and %s (pub %s); latest known %s'%(m.strftime('%Y-%m'),sp.date(),hit.index[0].strftime('%Y-%m'),pubs[hit.index[0]].date(),kk.strftime('%Y-%m'),pubs[kk].date(),known.index.max().strftime('%Y-%m')),sp)); armed=False
            elif not armed and v<sl-EPS: armed=True
        return calls
    _c0=cosign; cosign=cosign_asof
    try:
        C1=[Vc,Hh,SP]; C2=[Hc,SP,SV]
        def cw(props,confs):
            res=[]
            for a,b,c in confirm_wx(props,confs,'month'):
                pd_=[x[0] for x in props if x[1]==b]
                res.append((a,b,c,min(pd_) if pd_ else None))
            return res
        out['U']=cw(leg_gapL_cx(spl,p['u45'],p['look'])+F45,C1)
        out['L']=cw(leg_gapL_x(spl,p['low'],52,rearm='window')+F25,C2)
        out['I']=cw(leg_ic_cx(ICfp,p['ic']),C1)
        out['X']=hub(p['sahm'],p['hback'])
        if p.get('wline'): out['W']=cw(leg_sv_x(p['wline'],rearm='zero'),C2)
        if p.get('wline2'): out['V']=cw(leg_sv_x(p['wline2'],rearm='window'),C2)
        if p.get('bshare'): out['B']=cw(leg_br_x(p['bshare']),C2)
        if p.get('kc'): out['K']=[(a,b,'sudden stop: claims week %s'%b.strftime('%Y-%m'),a) for a,b in leg_K_x(ICfp,p['kc'][0],p['kc'][1])]
    finally: cosign=_c0
    return out,Hc,SV,SP,Vc
for d in OPEN:
    day=pd.Timestamp(d); cut=pd.Timestamp(day.year,1,1); p=CH[cut]
    L_,Hc,SV,SP,Vc=named(p)
    print('\n==',d,'lines at the',cut.year,'cut:',{k:p[k] for k in ('low','u45','ic','spr','hline','hback','kc','cs')})
    hits=[(br,x) for br,v in L_.items() for x in v if x[0]==day]
    for br,x in hits: print('   ',br,'call',x[0].date(),'proposal month',x[1].strftime('%Y-%m'),'|',x[2],'| proposer day',(x[3].date() if x[3] is not None else None))
    if not hits:
        near=[(br,x[0].date(),x[1].strftime('%Y-%m'),x[2]) for br,v in L_.items() for x in v if abs((x[0]-day).days)<=120]
        print('    NO EXACT MATCH; near:',near)
    # the confirmers' readings around the call, for the narrative
    for nm,cf in (('housing pair',Hc),('starts x vacancy',SV),('spread',SP),('vacancy',Vc)):
        ser=cf['gap']; seg=ser[(ser.index>=day-pd.DateOffset(months=8))&(ser.index<=day+pd.DateOffset(months=1))]
        at=[(m.strftime('%Y-%m'),round(float(v),3),(cf['pubs'][m].date() if m in cf['pubs'].index else None)) for m,v in seg.items() if v>=cf['line']-EPS]
        if at: print('     ',nm,'at its line (%s):'%cf['line'],at[:6])
