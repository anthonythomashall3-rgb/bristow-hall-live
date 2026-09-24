"""THE BINDING SIDE, TURN BY TURN, FOR v3.1. For each of the thirteen calls: which leg carried it, the proposal's own
publication date, the confirming object's publication date, and therefore which of the two the call is waiting on.
Speed can only be bought on the binding side."""
from mini import *
from legu_min import s_cur, spl
exec(open('daily1.py').read().split('P("\\nbaseline v3.0")')[0].replace("out=open('daily1.out','w')","out=open('bind2.out','w')"))
C25=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','25_fred_daily_weekly')
def L25(nm):
    for d in ['fred_daily','fred_weekly','fred_biweekly']:
        p=os.path.join(C25,d,nm+'.csv')
        if os.path.exists(p):
            x=pd.read_csv(p).iloc[:,:2]; x.columns=['d','v']; x['d']=pd.to_datetime(x['d'],errors='coerce')
            s=pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna(); return s[s.index.notna()]
CS=L25('NFCICREDIT'); CRED=dict(name='credit12',gap=(CS-CS.rolling(12).min()).dropna(),line=1.25,pub_lag_days=1)
G=vgap(4,4); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
Vc=dict(name='vac',gap=G,line=0.20,pubs=pubs)
F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
Hc,MX=mkpair3(29,4,3,18); Hh=mkhours(2.0,1.20)
C1=[Vc,Hh,CRED]; C2=[Hc,CRED]
def cpub(c,dd):
    """the publication date of the earliest reading of confirmer c that stands at its line inside the window of dd"""
    gp=c['gap']; lo=dd-pd.DateOffset(months=6); hi=dd+pd.DateOffset(months=4)+pd.offsets.MonthEnd(0)
    w=gp[(gp.index>=lo)&(gp.index<=hi)]; hit=w[w>=c['line']]
    if not len(hit): return None,None
    k=hit.index[0]
    if 'pubs' in c and c['pubs'] is not None and k in c['pubs'].index: return c['pubs'][k],k
    if 'pub_lag_days' in c: return k+pd.Timedelta(days=c['pub_lag_days']),k
    if 'pub_day' in c: return pd.Timestamp(k.year,k.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=c['pub_day']-1),k
    return k,k
U=confirm_w(leg_gapL(s_cur,0.45,52,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s_cur,0.25,52,rearm='window')+F25,C2,'month')
I=confirm_w(leg_ic(IC,50),C1,'month')
def hubv(sl=0.50):
    calls=[]; armed=True
    for m,v in g.items():
        if m<pd.Timestamp('1948-06-01'): continue
        if armed and v>=sl:
            w=G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)]; hit=w[w>=0.20]
            if len(hit):
                kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub',sp,pubs[kk],kk)); armed=False
        elif not armed and v<sl: armed=True
    return calls
HUB=hubv()
legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c,_,_,_ in HUB],'I':[(a,b) for a,b,c in I]}
with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
r=score13(turns)
PROP={'U':dict(leg_gapL(s_cur,0.45,52,rearm='zero')+F45),'L':dict(leg_gapL(s_cur,0.25,52,rearm='window')+F25),'I':dict(leg_ic(IC,50))}
CONFS={'U':C1,'L':C2,'I':C1}
P(f"{'peak':9s} {'lag':>4s} {'leg':4s} {'call':11s} {'proposal pub':13s} {'confirmer':22s} {'conf pub':11s}  BINDING")
for i in range(13):
    if i not in r['opens']: continue
    t=r['opens'][i]; lg=r['lags_p'][i]; leg=t['leg']; call=t['published']
    if leg=='X':
        h=[x for x in HUB if x[0]==call]
        if h:
            _,dd,_,sp,vp,kk=h[0]
            b='the employment report' if sp>=vp else f'the vacancy for {kk:%Y-%m}'
            P(f"{PK[i]:%Y-%m}  {lg:4d} hub  {call:%Y-%m-%d}  UR {sp:%Y-%m-%d}   vacancy {kk:%Y-%m}          {vp:%Y-%m-%d}  {b}")
        continue
    dd=None
    for p_,d_ in PROP[leg].items():
        pass
    cand=[(p_,d_) for p_,d_ in (leg_gapL(s_cur,0.45,52,rearm='zero')+F45 if leg=='U' else leg_gapL(s_cur,0.25,52,rearm='window')+F25 if leg=='L' else leg_ic(IC,50))]
    best=None
    for p_,d_ in cand:
        for c in CONFS[leg]:
            cp,kk=cpub(c,d_)
            if cp is None: continue
            if max(p_,cp)==call: best=(p_,d_,c['name'],cp,kk)
    if best is None: P(f"{PK[i]:%Y-%m}  {lg:4d} {leg:4s} {call:%Y-%m-%d}  (not reconstructed)"); continue
    p_,d_,cn,cp,kk=best
    b='the PROPOSAL' if p_>=cp else f'the CONFIRMER ({cn})'
    P(f"{PK[i]:%Y-%m}  {lg:4d} {leg:4s} {call:%Y-%m-%d}  {p_:%Y-%m-%d}    {cn+' @'+kk.strftime('%Y-%m'):22s} {cp:%Y-%m-%d}  {b}")
out.close()
