from mini import *
from hub import leg_X2
from legu_min import leg_U, s_cur
out=open('fast5.out','w')
def P(*a):
    print(*a); print(*a,file=out); out.flush()
PAY=first_prints('PAYEMS'); ch1=(PAY/PAY.shift(1)-1)*100; ch3=(PAY/PAY.shift(3)-1)*100
def inwin(d,back=6,fwd=18): return any(p-pd.DateOffset(months=back)<=d<=t+pd.DateOffset(months=fwd) for p,t in zip(PK,TR))
P("payroll first prints: quiet months with a 1-month fall <= -0.10% / 3-month fall <= -0.30%, and the demand side there")
for nm,ser,line in [('1-month <= -0.10%',ch1,-0.10),('3-month <= -0.30%',ch3,-0.30)]:
    q=[m for m,v in ser.dropna().items() if v<=line and not inwin(m) and m>=pd.Timestamp('1962-01-01')]
    P(f"  {nm}: {[(m.strftime('%Y-%m'), round(float(vr.get(m,np.nan)),2), round(float(PAIR.get(m,np.nan)),2), round(float(P1.get(m,np.nan)),2)) for m in q]}  (month, vacancy26, housing pair, hours pair)")
    P("   first reading in each recession window (months from peak):",[ (lambda seg: (md(seg[seg<=line].index[0],p) if (seg<=line).any() else None))(ser[(ser.index>=p-pd.DateOffset(months=6))&(ser.index<=t)]) for p,t in zip(PK,TR)])
# as a proposer in the machine: published the 5th of m+1, dated m; re-arm after a month above the line
def leg_pay(ser,line,pub_day=5):
    c=[]; armed=True
    for m,v in ser.dropna().items():
        if m<pd.Timestamp('1962-01-01'): continue
        if armed and v<=line: c.append((pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pub_day-1),m)); armed=False
        elif not armed and v>line: armed=True
    return c
KJHS={k:TLG[k] for k in 'KJHS'}
SEC['V']=dict(name='vacancy',gap=vr,line=0.30,pub_day=30)
X43=leg_X2(sahm_line=0.43,vac_line=0.30); U45=leg_U(s_cur,0.45)
for nm,leg in [('payrolls 1-month -0.10%',leg_pay(ch1,-0.10)),('payrolls 3-month -0.30%',leg_pay(ch3,-0.30))]:
    for cf in [['V'],['V','H','P']]:
        r=score13(chron({'U':U45,'Y':leg,'X':X43},KJHS,cf)); lp=[r['lags_p'].get(i) for i in range(13)]; v73=[r['lags_p'][i] for i in range(5,13) if i in r['lags_p']]
        P(f"\n  corner + {nm} as proposer, U/Y confirmed by {'|'.join(cf)}: lags {[('-' if l is None else l) for l in lp]} other {[(d,lg) for _,d,lg in r['other']]}; 1973 on median {np.median(v73):.1f}")
        for i in range(5,13):
            if i in r['opens']: t=r['opens'][i]; P(f"      {PK[i]:%Y-%m}: {t['published']:%Y-%m-%d} by {t['leg']} dated {t['date']:%Y-%m} ({t.get('condition')})")
out.close()
