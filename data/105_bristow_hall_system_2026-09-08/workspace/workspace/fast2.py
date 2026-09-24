from mini import *
from hub import leg_X2
from legu_min import leg_U, s_cur, spl
o2=pickle.load(open('cache/claims_objects.pkl','rb')); Wk=o2['df']
out=open('fast2.out','w')
def P(*a):
    print(*a); print(*a,file=out); out.flush()
# (a) exact quiet maxima of the weekly IUR gap and what the demand side read there
gap=(s_cur-s_cur.rolling(52,min_periods=52).min().shift(1)).dropna()
def inwin(d,back=6,fwd=18): return any(p-pd.DateOffset(months=back)<=d<=t+pd.DateOffset(months=fwd) for p,t in zip(PK,TR))
q=gap[[not inwin(d) for d in gap.index]]
P("(a) weekly IUR gap, quiet weeks (outside peak-6..trough+18), the highest readings by episode:")
top=q[q>=0.30]
runs=[]
for d,v in top.items():
    if runs and (d-runs[-1]['end']).days<=70: runs[-1]['end']=d; runs[-1]['max']=max(runs[-1]['max'],v)
    else: runs.append(dict(start=d,end=d,max=v))
for r in runs:
    m=pd.Timestamp(r['start'].year,r['start'].month,1); seg=slice(m-pd.DateOffset(months=1),r['end']+pd.DateOffset(months=1))
    P(f"   {r['start']:%Y-%m-%d}..{r['end']:%Y-%m-%d} max gap {r['max']:.2f} | vacancy(2,6) max {vr[seg].max():.2f} | housing pair max {PAIR[seg].max():.2f} | hours pair max {P1[seg].max():.2f} | Sahm fp max {g[seg].max():.2f}")
P("   IUR gap at the recessions (first week >= 0.40 / 0.50, months from peak):")
for p,t in zip(PK,TR):
    seg=gap[(gap.index>=p-pd.DateOffset(months=6))&(gap.index<=t)]
    if len(seg)==0: continue
    f4=seg[seg>=0.40]; f5=seg[seg>=0.50]
    P(f"   {p:%Y-%m}: >=0.40 {('never' if len(f4)==0 else f4.index[0].strftime('%Y-%m-%d')+' ('+str(md(pd.Timestamp(f4.index[0].year,f4.index[0].month,1),p))+')')}; >=0.50 {('never' if len(f5)==0 else f5.index[0].strftime('%Y-%m-%d')+' ('+str(md(pd.Timestamp(f5.index[0].year,f5.index[0].month,1),p))+')')}; window max {seg.max():.2f}")
# (b) the hub's Sahm line with vac 0.30, U 0.40 confirmed by V|H|P; dating rules
KJHS={k:TLG[k] for k in 'KJHS'}
SEC['V']=dict(name='vacancy',gap=vr,line=0.30,pub_day=30)
U40=leg_U(s_cur,0.40); U40f=leg_U(spl,0.40)
P("\n(b) hub Sahm line (vacancy 0.30 in the six months back), U 0.40 confirmed by V|H|P; closers K,J,H,S")
for sl in [0.35,0.40,0.43,0.45,0.50]:
    for dr in ['minus3','month']:
        X=leg_X2(sahm_line=sl,vac_line=0.30,date_rule=dr)
        r=score13(chron({'U':U40,'X':X},KJHS,['V','H','P'])); lp=[r['lags_p'].get(i) for i in range(13)]; ep=[r['errs_p'].get(i) for i in range(13)]
        P(f"   Sahm {sl:.2f} dated {dr:6}: lags {[('-' if l is None else l) for l in lp]} errs {[('-' if e is None else e) for e in ep]} other {[(d,lg) for _,d,lg in r['other']]}; 2024: {('opened '+r['opens'][12]['published'].strftime('%Y-%m-%d')+' by '+r['opens'][12]['leg']+' dated '+r['opens'][12]['date'].strftime('%Y-%m')) if 12 in r['opens'] else 'not opened'}")
P("   quiet Sahm first prints >= 0.35 with the vacancy (2,6) >= 0.30 in the prior six months (the hub's exposure at lower lines):")
for m,v in g.items():
    if v>=0.35 and not inwin(m,6,3) and m>=pd.Timestamp('1949-01-01'):
        w=vr[(vr.index>=m-pd.DateOffset(months=6))&(vr.index<=m)]
        if len(w) and w.max()>=0.30: P(f"      {m:%Y-%m} Sahm {v:.2f} vacancy max {w.max():.2f}")
# (c) U 0.40 on the Department's advance first prints
X=leg_X2(sahm_line=0.50,vac_line=0.30)
for nm,U in [('U 0.40 current file',U40),('U 0.40 advance first prints (2002 on)',U40f)]:
    r=score13(chron({'U':U,'X':X},KJHS,['V','H','P'])); lp=[r['lags_p'].get(i) for i in range(13)]
    P(f"\n(c) {nm}: lags {[('-' if l is None else l) for l in lp]} other {r['other']}")
    for i in range(5,13):
        if i in r['opens']: t=r['opens'][i]; P(f"      {PK[i]:%Y-%m}: call {t['published']:%Y-%m-%d} by {t['leg']} dated {t['date']:%Y-%m} cond {t.get('condition')}")
out.close()
