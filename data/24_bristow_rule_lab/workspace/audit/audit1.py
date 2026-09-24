import pandas as pd, numpy as np
def L(n):
    d=pd.read_csv(n+'.csv',parse_dates=['observation_date']); d.columns=['date','v']
    d['v']=pd.to_numeric(d.v,errors='coerce'); return d.dropna().reset_index(drop=True)
FAIL=[]; OK=[]
def chk(label, got, want, tol=1e-9):
    ok = abs(got-want)<=tol if isinstance(want,(int,float)) else got==want
    (OK if ok else FAIL).append(f"{'PASS' if ok else 'FAIL'} | {label} | got={got} claimed={want}")
def note(label,val): OK.append(f"VAL  | {label} = {val}")

# ---------- YIELD CURVE ----------
t=L('T10Y2Y'); t['neg']=t.v<0
runs=[];start=None
for i,r in t.iterrows():
    if r.neg and start is None: start=i
    if not r.neg and start is not None:
        seg=t.v[start:i]; runs.append((t.date[start],t.date[i-1],i-start,seg.min(),seg.sum())); start=None
if start is not None:
    seg=t.v[start:]; runs.append((t.date[start],t.date[len(t)-1],len(t)-start,seg.min(),seg.sum()))
byLen=sorted(runs,key=lambda r:-r[2])
r22=[r for r in runs if r[0]==pd.Timestamp('2022-07-06')][0]
chk("T10Y2Y 2022 run length (trading days)", r22[2], 537)
chk("T10Y2Y 2022 run start", r22[0].strftime('%Y-%m-%d'), '2022-07-06')
chk("T10Y2Y 2022 run end", r22[1].strftime('%Y-%m-%d'), '2024-08-26')
chk("T10Y2Y 2022 run min", round(r22[3],2), -1.08)
chk("Longest run is 2022-24", byLen[0][2]==r22[2], True)
chk("Second-longest run length (1978-80)", byLen[1][2], 423)
chk("1978-80 run min", round(byLen[1][3],2), -2.41)
r8081=[r for r in runs if r[0]==pd.Timestamp('1980-09-12')][0]
chk("1980-81 run min", round(r8081[3],2), -1.70)
chk("Series overall min", round(t.v.min(),2), -2.41)
note("Series overall min date", t.loc[t.v.idxmin(),'date'].strftime('%Y-%m-%d'))
byInt=sorted(runs,key=lambda r:r[4])
chk("2022-24 cumulative area (pp-days) approx -259", round(r22[4]), -259)
chk("1978-80 cumulative area approx -304", round(byInt[0][4]), -304)
chk("2022-24 is 2nd largest by area", byInt[1][0]==r22[0], True)
d=t[(t.date>='2022-03-30')&(t.date<='2022-04-06')]
note("Apr 2022 dip days", list(zip(d.date.dt.strftime('%m-%d'),d.v)))
p=t[(t.date>='2024-08-26')&(t.date<='2024-09-09')]
note("Sept 2024 turn", list(zip(p.date.dt.strftime('%m-%d'),p.v)))
chk("Trough date", t[(t.date>='2022-07-06')&(t.date<='2024-08-26')].sort_values('v').iloc[0].date.strftime('%Y-%m-%d'), '2023-07-03')

# ---------- GDP / GDI ----------
g=L('GDPC1'); i_=L('A261RX1Q020SBEA')
g['ann']=((g.v/g.v.shift(1))**4-1)*100; i_['ann']=((i_.v/i_.v.shift(1))**4-1)*100
def q(df,ds): return round(float(df.loc[df.date==ds,'ann'].iloc[0]),2)
chk("GDP 2022Q1 ann %", q(g,'2022-01-01'), -1.0, 0.05)
chk("GDP 2022Q2 ann %", q(g,'2022-04-01'), 0.6, 0.05)
chk("GDI 2022Q2 ann %", q(i_,'2022-04-01'), -0.3, 0.05)
chk("GDI 2022Q4 ann %", q(i_,'2022-10-01'), -2.3, 0.05)
chk("GDP 1947Q2 ann %", q(g,'1947-04-01'), -1.1, 0.05)
chk("GDP 1947Q3 ann %", q(g,'1947-07-01'), -0.8, 0.05)
chk("GDP 2003Q3 ann %", q(g,'2003-07-01'), 6.8, 0.05)

# ---------- NBER monthly indicators ----------
for nm,ser,claim in [("Real PI ex transfers Dec21->Jun22 %",'W875RX1',-1.7),
                     ("Real mfg+trade sales Jan22->Jun22 %",'CMRMTSPL',-2.6)]:
    s=L(ser).set_index('date').v
    if ser=='W875RX1': got=100*(s['2022-06-01']/s['2021-12-01']-1)
    else: got=100*(s['2022-06-01']/s['2022-01-01']-1)
    chk(nm, round(got,2), claim, 0.05)
ip=L('INDPRO').set_index('date').v
sub=ip['2021-06-01':'2024-06-01']; pk=sub.idxmax()
chk("INDPRO peak month", pk.strftime('%Y-%m'), '2022-04')
post=ip[pk:'2024-06-01']; tr=post.idxmin()
chk("INDPRO trough month", tr.strftime('%Y-%m'), '2024-01')
chk("INDPRO peak-to-trough %", round(100*(post.min()/sub.max()-1),2), -2.2, 0.05)

print("\n".join(OK)); print(); print("\n".join(FAIL) if FAIL else "NO FAILURES IN BLOCK 1")
