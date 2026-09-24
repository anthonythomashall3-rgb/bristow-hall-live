# q32.py - 2020 BEFORE THE MONTH'S END? The only instruments that moved in February 2020 were the market and the epidemic
# itself. (1) The WHO's Public Health Emergencies of International Concern (a formal, dated instrument since the 2005
# Regulations; eight declarations 2009-2024) as a proposer in the sudden stop's labour slot, confirmed by the market at the
# rule's own numbers: the S&P 500 20 per cent under its 20-day high (the sudden stop's) within the rule's confirmation
# window (four months forward), and, for information, 15 per cent under its 26-week high (the closer's number). (2) The
# market alone in February 2020: its drawdown at each close, and how often a drawdown of that size has occurred outside a
# recession since 1962 (why a smaller market number is not available). Run: PYTHONPATH=. python3 s2/q32.py
import sys,os,io,contextlib
sys.path.insert(0,os.getcwd()); sys.argv=['walk46.py','1962','2026','w46']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
with contextlib.redirect_stdout(io.StringIO()): exec(open('walk46.py').read().split(_MARK)[0])
PKm=[pd.Timestamp(x) for x in PK]; TRm=[pd.Timestamp(x) for x in TR]
def in_rec(t): return any(PKm[i]-pd.DateOffset(months=6)<=pd.Timestamp(t.year,t.month,1)<=TRm[i] for i in range(len(PKm)))
px=_SPX.dropna(); c20=(1-px/px.rolling(20,min_periods=10).max())*100; c26=(1-px/px.rolling(130,min_periods=60).max())*100
PHEIC={'2009-04-25':'H1N1 influenza','2014-05-05':'polio','2014-08-08':'Ebola (West Africa)','2016-02-01':'Zika','2019-07-17':'Ebola (DRC)','2020-01-30':'COVID-19','2022-07-23':'mpox','2024-08-14':'mpox (clade I)'}
print('PHEIC declarations and the market within the four months after each (first close at the line; the maximum drawdown in the window):')
for d,nm in PHEIC.items():
    d=pd.Timestamp(d); w20=c20[(c20.index>=d)&(c20.index<=d+pd.DateOffset(months=4))]; w26=c26[(c26.index>=d)&(c26.index<=d+pd.DateOffset(months=4))]
    f20=w20[w20>=20-EPS]; f26=w26[w26>=15-EPS]
    print(f"  {d.date()} {nm:22s} | 20-day crash: first >=20 {f20.index[0].date() if len(f20) else None}, max {round(float(w20.max()),1)} | 26-week: first >=15 {f26.index[0].date() if len(f26) else None}, max {round(float(w26.max()),1)} | {'in a recession window' if in_rec(d) else 'no recession'}")
print('February-March 2020, the S&P 500 under its 20-day high at each close:',{t.strftime('%m-%d'):round(float(v),1) for t,v in c20['2020-02-20':'2020-03-16'].items()})
for L in (10,12,15):
    s=c20[c20.index>='1962-01-01']; days=s[s>=L-EPS].index; eps=[]; last=None
    for t in days:
        if last is None or (t-last).days>182: eps.append(t)
        last=t
    out=[t for t in eps if not in_rec(t)]
    print(f'  20-day drawdown >= {L} since 1962: {len(eps)} episodes, {len(out)} outside a recession: {[t.date().isoformat() for t in out]}')
