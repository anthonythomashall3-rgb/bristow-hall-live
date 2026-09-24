from mini import *
o2=pickle.load(open('cache/claims_objects.pkl','rb')); Mx=o2['M']; W_=o2['df']
sys.path.insert(0,W+'/lab/slack'); from objects import load
v=-load()['-vacancy rate']; m3=v.rolling(3).mean(); V312=(m3.shift(1).rolling(12).max()-m3).dropna()
objs={'Sahm>=.50 (fp)':(g,0.5,'M'),'vac(2,6)>=.36':(vr,0.36,'M'),'vac(3,12)>=.60':(V312,0.6,'M'),'hous35xrate':(PAIR,1.0,'M'),'hours x ndur':(P1,1.0,'M'),
      'IUR gap>=.50 (wk)':(W_['iur_gap'],0.5,'W'),'IUR gap>=.30 (wk)':(W_['iur_gap'],0.3,'W'),'ic4 +30% (wk)':(W_['ic4_rise%'],30,'W'),'ic4 +20% (wk)':(W_['ic4_rise%'],20,'W'),'breadth>=50 (wk)':(W_['breadth%'],50,'W')}
print("first reading at/above the line inside [peak-6m, trough]; months relative to the peak month (weekly objects: the week's month); '-' = never; 'na' = no data")
hdr=f"{'peak':8}"+''.join(f"{k:>18}" for k in objs); print(hdr)
for p,t in zip(PK,TR):
    row=f"{p:%Y-%m}  "
    for k,(ser,line,f) in objs.items():
        seg=ser[(ser.index>=p-pd.DateOffset(months=6))&(ser.index<=t)].dropna()
        if len(seg)==0: row+=f"{'na':>18}"; continue
        h=seg[seg>=line]
        if len(h)==0: row+=f"{'-':>18}"; continue
        d=h.index[0]; row+=f"{md(pd.Timestamp(d.year,d.month,1),p):>+17d} "
    print(row)
print("\nquiet firings (outside peak-6..trough+18 of the 13), episodes:")
def quiet_eps(ser,line):
    q=[d for d,x in ser.dropna().items() if x>=line and not any(p-pd.DateOffset(months=6)<=d<=t+pd.DateOffset(months=18) for p,t in zip(PK,TR)) and d>=pd.Timestamp('1948-06-01')]
    runs=[]
    for d in q:
        if runs and (d-runs[-1][1]).days<=70: runs[-1][1]=d
        else: runs.append([d,d])
    return [(a.strftime('%Y-%m'),b.strftime('%Y-%m')) for a,b in runs]
for k,(ser,line,f) in objs.items(): print(f"  {k:20}", quiet_eps(ser,line))
