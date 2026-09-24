"""The corner of the first-print pre-1971 proposal, and the two Federal Reserve accounting items the 1960 search
turned up, run through the machine so the refusal is on the record with numbers."""
exec(open('daily9.py').read().split('P("\\n=== baseline v3.1 ===")')[0].replace("out=open('daily9.out','w')","out=open('daily12.out','w')"))
import glob
FH45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
FH25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
P("=== baseline v3.1 ==="); go('v3.1',[CRED])
P("\n=== the safe corner: highest clean line on each branch ===")
for a in [0.50,0.52]:
    for b in [0.75,0.90,1.00,1.10,1.25]:
        for c,d in [(0.30,0.60),(0.35,0.60),(0.30,0.75)]:
            go(f'rt {a}+{b} / {c}+{d}',[CRED],F45x=FH45+leg_rt(RT,a)+leg_rt(RT,b),F25x=FH25+leg_rt(RT,c)+leg_rt(RT,d))
P("\n=== the 1960 candidates from the turn-targeted sweep, through the machine ===")
QP=sorted({dd for p_,dd in leg_gapL(s_cur,0.25,52,rearm='window') if not inw(dd)}|{dd for p_,dd in leg_gapL(spl,0.25,52,rearm='window') if not inw(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.25,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.45,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)}
          |{dd for p_,dd in leg_gapL(s_cur,0.45,52,rearm='zero') if not inw(dd)}|{dd for p_,dd in leg_ic(IC,50) if not inw(dd)})
P("   quiet proposal windows on the record:",len(QP))
def wseg(G,dd): 
    lo=dd-pd.DateOffset(months=6); hi=dd+pd.DateOffset(months=4)+pd.offsets.MonthEnd(0); return G[(G.index>=lo)&(G.index<=hi)]
for nm,kind,win,line in [('RADFOFRB','rise',12,345.4679),('MCONLIAPFC','rise',12,1025.1)]:
    s=L25(nm)
    if s is None: P(f"   {nm}: not held"); continue
    per=max(1,int(round(float(np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int))))))
    w=max(4,int(win*30/per)); G=((s.rolling(w).max()-s) if kind=='fall' else (s-s.rolling(w).min())).dropna()
    cov=[dd for dd in QP if len(wseg(G,dd))]
    P(f"   {nm}: {s.index.min().date()} -> {s.index.max().date()}; covers {len(cov)} of {len(QP)} quiet windows; silent on the record after {G.index.max().date()}")
    go(f'{nm} {kind} confirms',[CRED,dict(name=nm,gap=G,line=line,pub_lag_days=7)])
P("\n=== and with the pre-1971 first prints in, the same two ===")
for nm,kind,win,line in [('RADFOFRB','rise',12,345.4679),('MCONLIAPFC','rise',12,1025.1)]:
    s=L25(nm); per=max(1,int(round(float(np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int))))))
    w=max(4,int(win*30/per)); G=((s.rolling(w).max()-s) if kind=='fall' else (s-s.rolling(w).min())).dropna()
    go(f'{nm}+rt corner',[CRED,dict(name=nm,gap=G,line=line,pub_lag_days=7)],F45x=FH45+leg_rt(RT,0.50)+leg_rt(RT,1.00),F25x=FH25+leg_rt(RT,0.30)+leg_rt(RT,0.60))
out.close()
