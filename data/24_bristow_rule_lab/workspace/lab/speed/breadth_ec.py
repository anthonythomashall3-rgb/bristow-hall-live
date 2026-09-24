"""The claims-field lesson applied to the zero-lag surveys: breadth beats amplitude for speed.

Stage 1 is twostage_ec's (the activity panel's D, in hand two months late, opens a
contraction).  Stage 2 replaces one survey balance with a BREADTH index over many survey
series published the same day: for an economy, the non-price questions of the industry survey
(six), the consumer survey (nine) and the retail, services and building surveys (four, four and
three; those three files are the Commission's seasonally adjusted balances, the only form
downloaded) - some twenty-six balances - the unadjusted ones adjusted in real time; for the
euro area, the industry confidence indicator of every member state with a series
(member-state breadth).  Each series is signed so that a rise is an improvement (stocks and
consumers' unemployment expectations inverted; the sign table below cites the user guide).

B(t) = share of series whose `k`-month change is positive at month t.  Inside an open
contraction the trough is called at the first month B has stood at or above `q` per cent for
`r` consecutive months, dated at the month the composite (mean of the standardised series)
reached its minimum, published in the month of the call.  Scored as in twostage_ec: hits
within six months, exact, within one, within three, published within the month, other calls.
Grid over k, q, r, printed in full for the committee.
"""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/speed')
import numpy as np, pandas as pd
import ecbcs_speed as E, twostage_ec as T2
ACQ=E.ACQ
EA_MEMBERS=['AT','BE','CY','DE','EE','EL','ES','FI','FR','HR','IE','IT','LT','LU','LV','MT','NL','PT','SI','SK']
# Signs from the Commission's BCS user guide (section 3.6): the industrial confidence indicator
# averages Q2 order books, Q4 stocks of finished products WITH INVERTED SIGN and Q5 production
# expectations; the consumer confidence indicator averages Q1/Q2 (financial situation past and
# expected), Q4 (expected general economic situation) and Q9 (major purchases next 12 months);
# consumer Q7 (unemployment expectations) is shown on an inverted scale in the Commission's own
# releases.  Price questions (industry Q6, consumer Q5/Q6, retail Q6, services Q6, building Q5)
# are left out - their sign for activity is not a survey convention.  Consumer Q10 was withdrawn.
IND_Q={1:1,2:1,3:1,4:-1,5:1,7:1}
CONS_Q={1:1,2:1,3:1,4:1,7:-1,8:1,9:1,11:1,12:1}
RETA_Q={'1':1,'2':-1,'4':1,'5':1}
SERV_Q={'1':1,'2':1,'3':1,'5':1}
BUIL_Q={'1':1,'3':1,'4':1}
_cache={}
def sheet(f,sh):
    if (f,sh) not in _cache: _cache[(f,sh)]=E.load_sheet(f,sh)
    return _cache[(f,sh)]
def subseries(cc):
    out=[]
    ind=sheet('industry_total_nsa_nace2.xlsx','INDUSTRY MONTHLY')
    for q,sg in IND_Q.items():
        c=f'INDU.{cc}.TOT.{q}.B.M'
        if c in ind: out.append((f'industry q{q}',pd.to_numeric(ind[c],errors='coerce').dropna().astype(float)*sg))
    con=sheet('consumer_total_nsa_nace2.xlsx','CONSUMER MONTHLY')
    for q,sg in CONS_Q.items():
        c=f'CONS.{cc}.TOT.{q}.B.M'
        if c in con: out.append((f'consumer q{q}',pd.to_numeric(con[c],errors='coerce').dropna().astype(float)*sg))
    for f,sh,pre,QS in (('retail_total_sa_nace2.xlsx','RETAIL TRADE MONTHLY','RETA',RETA_Q),('services_total_sa_nace2.xlsx','SERVICES MONTHLY','SERV',SERV_Q),('building_total_sa_nace2.xlsx','BUILDING MONTHLY','BUIL',BUIL_Q)):
        try: d=sheet(f,sh)
        except Exception as e: print('  !',f,e); continue
        for q,sg in QS.items():
            c=f'{pre}.{cc}.TOT.{q}.BS.M'
            if c in d: out.append((f'{pre.lower()} q{q} (sa as published)',pd.to_numeric(d[c],errors='coerce').dropna().astype(float)*sg))
    return out
MIG=['CONS','INTM','INVE','CDUR','CNDU','FOBE']
CONS_GROUPS=['RE1','RE2','RE3','RE4','PR0','PR1','PR2','PR3','PR4','PR5','PR6','PR7','PR8','PR9','ED1','ED2','ED3','AG1','AG2','AG3','AG4','MAL','FEM']
def subseries_extended(cc):
    """the wide field: the industry survey by main industrial grouping (six groupings x six
    non-price questions) and the consumer survey by income quartile, occupation, education,
    age and sex (23 groups x nine non-price questions), on top of subseries(cc).  These
    breakdowns exist only as the Commission's seasonally adjusted balances, so they enter as
    published (the one look-ahead in the field)."""
    out=list(subseries(cc))
    for g in MIG:
        try: d=sheet('industry_mig_sa_m_nace2.xlsx',g)
        except Exception: continue
        for q,sg in IND_Q.items():
            c=f'INDU.{cc}.{g}.{q}.BS.M'
            if c in d: out.append((f'industry {g} q{q} (sa)',pd.to_numeric(d[c],errors='coerce').dropna().astype(float)*sg))
    for g in CONS_GROUPS:
        try: d=sheet('consumer_subsectors_sa_m_nace2.xlsx',g)
        except Exception: continue
        for q,sg in CONS_Q.items():
            c=f'CONS.{cc}.{g}.{q}.BS.M'
            if c in d: out.append((f'consumer {g} q{q} (sa)',pd.to_numeric(d[c],errors='coerce').dropna().astype(float)*sg))
    return out
def members():
    ind=sheet('industry_total_nsa_nace2.xlsx','INDUSTRY MONTHLY'); out=[]
    for m in EA_MEMBERS:
        c=f'INDU.{m}.TOT.COF.B.M'
        if c in ind:
            s=pd.to_numeric(ind[c],errors='coerce').dropna().astype(float)
            if len(s)>120: out.append((m,s))
    return out
def prepare(series, adjust):
    X={}
    for nm,s in series:
        x=E.sa_rt(s).dropna() if (adjust and '(sa' not in nm) else s
        X[nm]=x
    X=pd.DataFrame(X)
    return X
def breadth(X,k):
    ch=X.diff(k)
    return (ch>0).sum(axis=1)/ch.notna().sum(axis=1)*100.0, (X-X.expanding().mean())/X.expanding().std()
def composite(X):
    Z=(X-X.rolling(120,min_periods=36).mean())/X.rolling(120,min_periods=36).std()
    return Z.mean(axis=1)
def calls_breadth(D,B,C,q,r,pre=3,min_cycle=12):
    out=[]; state='quiet'; open_at=None; last=None
    for t in B.index:
        if t not in D.index or np.isnan(B[t]): continue
        d=float(D[t])
        if state=='quiet':
            if d>=2.0 and (last is None or T2.md(t,last)>=min_cycle): state='open'; open_at=t
        elif state=='open':
            seg=B[open_at:t]
            if len(seg)>=r and bool((seg.iloc[-r:]>=q).all()):
                cs=C[open_at-pd.DateOffset(months=pre):t].dropna()
                m=cs.idxmin() if len(cs) else t
                out.append((t,m)); last=m; state='recover'
        else:
            if d<2.0: state='quiet'
    return out
if __name__=='__main__':
    ccs=sys.argv[1:] or ['DE','EA','FR','ES','IT','UK','AT','SE']
    for cc in ccs:
        D=T2.d_available(cc)
        sets=[('sub-series breadth',subseries(cc),True),('wide field breadth (groupings and consumer groups)',subseries_extended(cc),True)]
        if cc=='EA': sets.append(('member-state breadth (industry confidence)',members(),True))
        rulers=[]
        if cc in E.COMMITTEE: rulers.append(('the committee',[E.ts(t) for p,t in E.COMMITTEE[cc]]))
        if cc in E.ECRI_CC: rulers.append(('ECRI',[E.ts(d) for k,d in E.ECRI[E.ECRI_CC[cc]] if k=='T' and d>='1986-01']))
        for label,ser,adj in sets:
            X=prepare(ser,adj); C=composite(X)
            print(f'\n############ {cc} {label}: {X.shape[1]} series, {X.index.min():%Y-%m}..{X.index.max():%Y-%m}')
            for rl,T in rulers:
                print(f'  === troughs against {rl} ({len(T)})')
                rows=[]
                for k,q,r in itertools.product((1,2,3),(60.,70.,80.,90.),(1,2)):
                    B,_=breadth(X,k)
                    calls=calls_breadth(D,B,C,q,r)
                    res=T2.line(f'  k={k} q={q:.0f} r={r}',calls,T,show=False)
                    rows.append((res,k,q,r,calls))
                rows.sort(key=lambda x:(x[0][0],-x[0][1],x[0][5],x[0][4]),reverse=True)
                for res,k,q,r,calls in rows[:4]:
                    T2.line(f'  k={k} q={q:.0f} r={r}',calls,T)
                z=[x for x in rows if x[0][1]==0]
                if z:
                    res,k,q,r,calls=z[0]; T2.line(f'  best with no other call k={k} q={q:.0f} r={r}',calls,T)
