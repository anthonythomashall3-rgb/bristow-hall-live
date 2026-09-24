"""WHICH SIDE BINDS. For every recession the tool calls, print the date the proposal was published, the confirming
object, the month it confirms on and the date that confirmation was published. The call is the later of the two. If
the confirmer binds, speed must come from a faster confirmer; if the proposal binds, from a faster proposer."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk3.py').read().split('CACHE6={}')[0].replace("out=open('walk3_%s.out'%sys.argv[1],'w')","out=open('bind1.out','w')"))
CACHE6={}
def ev6(p):
    k=tuple(sorted(p.items()))
    if k not in CACHE6: CACHE6[k]=build6(p)
    return CACHE6[k]
def parts(p):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1)
    prop={'U':leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,'L':leg_gapL(spl,p['low'],52,rearm='window')+F25,'I':leg_ic(ICfp,p['ic'])}
    confs={'U':[Vc,Hh,SP],'L':[Hc,SP],'I':[Vc,Hh,SP]}
    return prop,confs
def show(nm,p):
    r,t=ev6(p); prop,confs=parts(p)
    P(f"\n{nm}")
    P(f"   {'peak':8s} {'called':11s} {'leg':4s} {'proposal pub':13s} {'confirmer':22s} {'conf pub':11s} {'binds':9s}")
    for i in range(13):
        if i not in r['opens']: continue
        o=r['opens'][i]; leg=o['leg']
        if leg not in prop: P(f"   {PK[i]:%Y-%m}  {o['published']:%Y-%m-%d}  {leg:4s} (hub or deep branch: one object)"); continue
        cand=[(pp,dd) for pp,dd in prop[leg] if dd==o['date']]
        if not cand: P(f"   {PK[i]:%Y-%m}  {o['published']:%Y-%m-%d}  {leg:4s} (proposal not matched)"); continue
        pp,dd=cand[0]; best=None
        for cf in confs[leg]:
            ser=cf['gap']; seg=ser[(ser.index>=dd-pd.DateOffset(months=6))&(ser.index<=dd+pd.DateOffset(months=4))]
            hit=seg[seg>=cf['line']]
            if not len(hit): continue
            tt=hit.index[0]; ps=pubof(cf,tt)
            if best is None or ps<best[0]: best=(ps,cf['name'],tt)
        b='PROPOSAL' if pp>=best[0] else 'CONFIRMER'
        P(f"   {PK[i]:%Y-%m}  {o['published']:%Y-%m-%d}  {leg:4s} {pp:%Y-%m-%d}    {best[1]+'@'+best[2].strftime('%Y-%m'):22s} {best[0]:%Y-%m-%d}  {b}")
B0=dict(BASE); B0['deep']=999
show('the frozen rule, v3.5',B0)
B7=dict(BASE); B7['deep']=7.5
show('with the claims deep branch at 7.5 per cent',B7)
out.close()
