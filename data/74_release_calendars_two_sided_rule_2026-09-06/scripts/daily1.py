"""DAILY AND WEEKLY SERIES ALREADY HELD, tested as ADDITIONAL CONFIRMERS. The confirmer side is what binds 1960 (the vacancy's release),
1969 and 1973 (the starts release); a daily object is published the next day, so a clean one would collapse those to their proposal dates.
Held before 1972: the weekly three-month bill from 1954 and the weekly prime rate from 1955; daily bills, funds and prime from 1960; daily
Treasury yields from 1962; weekly national claims from 1967; the Chicago Fed's financial conditions index from 1971.
Each is read as a FALL over a trailing window (the easing a recession forces) or a RISE (financial stress), published the next day."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast46.py').read().split("def inw(dd)")[0].replace("out=open('fast46.out','w')","out=open('daily1.out','w')"))
DD=W.replace('24_bristow_rule_lab/workspace','../Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched')
import glob
def load_series(nm):
    for d in ['fred_daily','extra']:
        f=os.path.join(DD,d,nm+'.csv')
        if os.path.exists(f):
            x=pd.read_csv(f); x.columns=['d','v']; x['d']=pd.to_datetime(x['d'])
            return pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna()
    return None
CAND={}
for nm in ['DTB6','DTB3','DFF','DPRIME','WTB3MS','WPRIME','DGS1','DGS10','T10YFF','T1YFF','NFCI','ANFCI','NFCICREDIT','NFCIRISK','RIFSPFFNB','DTB1YR']:
    s=load_series(nm)
    if s is not None: CAND[nm]=s; P(f"{nm}: {s.index.min().date()} -> {s.index.max().date()}, {len(s)} obs")
def fall(s,win): return (s.rolling(win).max()-s)          # points below the trailing maximum
def rise(s,win): return (s-s.rolling(win).min())
def as_conf(nm,s,win,line,kind='fall',pub=1):
    G=(fall(s,win) if kind=='fall' else rise(s,win)).dropna()
    return dict(name=f'{nm}{kind}{win}',gap=G,line=line,pub_lag_days=pub)
def inw(dd): return any(p_-pd.DateOffset(months=6)<=dd<=t for p_,t in zip(PK,TR))
def go9(nm,extra,pct=50,vk=4,vb=4,vl=0.20,starts=29):
    G=vgap(vk,vb); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=vl,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    Hc,MX=mkpair3(starts,4,3,18); Hh=mkhours(2.0,1.20)
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
    C1=[Vc,Hh]+extra; C2=[Hc]+extra
    res=[]
    for s,ics in [(s_cur,IC),(spl,ICfp)]:
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,C2,'month'); X=hubv(0.50)
        I=confirm_w(leg_ic(ics,pct),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        res.append(score13(turns))
    ok=all(len(r['other'])==0 and len(r['lags_p'])==13 for r in res)
    lp=[res[0]['lags_p'].get(i) for i in range(13)]; allv=[x for x in lp if x is not None]
    P(f"{'OK ' if ok else 'BAD'} {nm:36s} {lp} MEAN {np.mean(allv):.1f} in31 {sum(1 for x in allv if x<=31)}/13 others {[o[1] for r in res for o in r['other']][:4]}")
    return ok,np.mean(allv),sum(1 for x in allv if x<=31)
P("\nbaseline v3.0"); go9('v3.0',[])
P("\n--- rate falls as an extra confirmer (window in trading days / weeks) ---")
for nm,wins in [('DTB6',[60,120,250]),('DTB3',[60,120,250]),('DFF',[60,120,250]),('DPRIME',[60,120,250]),('WTB3MS',[13,26,52]),('WPRIME',[13,26,52])]:
    s=CAND.get(nm)
    if s is None: continue
    for win in wins:
        for line in [3.0,2.5,2.0,1.5,1.0]:
            go9(f'{nm} fall {win} >= {line}',[as_conf(nm,s,win,line,'fall')])
out.close()
