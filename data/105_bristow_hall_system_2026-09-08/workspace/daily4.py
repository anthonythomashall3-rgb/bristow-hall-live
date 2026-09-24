"""The one that survives: the Chicago Fed's national financial conditions CREDIT subindex, weekly since March 1971, read as its rise over
twelve weeks. Find the top of its clean plateau, check its margins, and check whether it combines with any other survivor."""
from mini import *
from legu_min import s_cur, spl
exec(open('daily1.py').read().split('P("\\nbaseline v3.0")')[0].replace("out=open('daily1.out','w')","out=open('daily4.out','w')"))
def L(nm):
    for d in ['fred_daily','extra']:
        f=os.path.join(DD,d,nm+'.csv')
        if os.path.exists(f):
            x=pd.read_csv(f); x.columns=['d','v']; x['d']=pd.to_datetime(x['d']); return pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna()
CR=L('NFCICREDIT'); G12=(CR-CR.rolling(12).min()).dropna()
QP=sorted({dd for p_,dd in leg_gapL(s_cur,0.25,52,rearm='window') if not inw(dd)}|{dd for p_,dd in leg_gapL(spl,0.25,52,rearm='window') if not inw(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.25,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.45,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)}
          |{dd for p_,dd in leg_gapL(s_cur,0.45,52,rearm='zero') if not inw(dd)}|{dd for p_,dd in leg_ic(IC,50) if not inw(dd)})
def wseg(G,dd,back=6,fwd=4):
    lo=dd-pd.DateOffset(months=back); hi=dd+pd.DateOffset(months=fwd)+pd.offsets.MonthEnd(0); return G[(G.index>=lo)&(G.index<=hi)]
qq=sorted([(round(float(wseg(G12,dd).max()),3),dd.strftime('%Y-%m')) for dd in QP if len(wseg(G12,dd))],reverse=True)[:5]
rr=[(PK[i].strftime('%Y-%m'),round(float(wseg(G12,PK[i]).max()),3)) for i in range(13) if len(wseg(G12,PK[i]))]
P("NFCICREDIT twelve-week rise: span",G12.index.min().date(),"->",G12.index.max().date())
P("   highest readings in quiet proposal windows:",qq)
P("   the recessions' window maxima:",rr)
P("   2025-26 maximum:",round(float(G12['2025-01':].max()),3))
for ln in [0.72,0.90,1.10,1.30,1.50,1.70,1.90,2.10]:
    go9(f'NFCICREDIT 12-week rise >= {ln}',[dict(name='crd',gap=G12,line=ln,pub_lag_days=1)])
P("\nwindow length swept at the plateau's top line:")
for w in [6,9,12,16,20,26]:
    Gw=(CR-CR.rolling(w).min()).dropna()
    qm=max([float(wseg(Gw,dd).max()) for dd in QP if len(wseg(Gw,dd))]+[0]); ln=round(qm*1.05,3)
    go9(f'  window {w} weeks, line {ln} (5% over the quiet maximum {qm:.3f})',[dict(name='crd',gap=Gw,line=ln,pub_lag_days=1)])
out.close()
