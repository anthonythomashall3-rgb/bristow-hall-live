import pandas as pd, numpy as np
def rd(s):
    d=pd.read_csv(f'a20/{s}.csv'); d.columns=['date','v']
    d['date']=pd.to_datetime(d['date']); d['v']=pd.to_numeric(d['v'],errors='coerce')
    return d.set_index('date')['v'].dropna()
md=lambda a,b:(a.year-b.year)*12+(a.month-b.month)
def sahm(u):
    ub=u.rolling(3).mean()
    return (ub-ub.shift(1).rolling(12).min()).dropna()
def eps(s,thr=0.50):
    out=[];cur=[]
    for d,v in s.items():
        if v>=thr: cur.append(d)
        elif cur: out.append(cur); cur=[]
    if cur: out.append(cur)
    return out
def bristow(s,pk,tr):
    p=pd.Timestamp(pk); t=pd.Timestamp(tr)
    E=eps(s)
    c=[e for e in E if e[0]>=p and e[0]<=t+pd.DateOffset(months=12)]
    if not c: return None,None
    w=s[c[0][0]:c[0][-1]+pd.DateOffset(months=12)]
    return w.idxmax(), md(w.idxmax(),t)

print("="*72)
print("OUT-OF-SAMPLE A:  the United States before the validation window")
print("  monthly unemployment 1929-1942 (FRED M0892AUSM156SNBR, NBER macrohistory)")
print("="*72)
u=rd('M0892AUSM156SNBR'); s=sahm(u)
for pk,tr,lab in [('1929-08-01','1933-03-01','1929-33 contraction'),('1937-05-01','1938-06-01','1937-38 contraction')]:
    d,g=bristow(s,pk,tr)
    print(f"  {lab}: NBER trough {tr[:7]}   Bristow date {d.strftime('%Y-%m') if d is not None else 'no crossing'}   gap {g}"
          f"   {'within three' if g is not None and abs(g)<=3 else 'OUTSIDE THREE' if g is not None else ''}")
print(f"  (peak Sahm value in the 1929-33 window: {s['1929-08-01':'1934-03-01'].max():.2f})")

print("\n"+"="*72)
print("OUT-OF-SAMPLE B:  outside the United States")
print("  harmonised unemployment rates against OECD-based recession chronologies")
print("="*72)
for cc,ur,rc in [('Canada','LRHUTTTTCAM156S','CANRECDM'),('Japan','LRHUTTTTJPM156S','JPNRECDM'),
                 ('United Kingdom','LRHUTTTTGBM156S','GBRRECDM'),('Germany','LRHUTTTTDEM156S','DEURECDM')]:
    u=rd(ur); s=sahm(u); r=rd(rc)
    rm=r.resample('MS').max().dropna()
    ep=[];cur=[]
    for d,v in rm.items():
        if v==1: cur.append(d)
        elif cur: ep.append(cur); cur=[]
    if cur: ep.append(cur)
    ep=[e for e in ep if e[0]>=s.index[0]]
    print(f"\n  {cc}: unemployment from {u.index[0]:%Y-%m}; {len(ep)} chronology episodes inside that span")
    hits=n=0
    for e in ep:
        pk=e[0]-pd.DateOffset(months=1); tr=e[-1]
        d,g=bristow(s,pk.strftime('%Y-%m-%d'),tr.strftime('%Y-%m-%d'))
        if g is None:
            print(f"     {pk:%Y-%m} to {tr:%Y-%m}: no threshold crossing"); continue
        n+=1; hits+= abs(g)<=3
        print(f"     {pk:%Y-%m} to {tr:%Y-%m}: Bristow {d:%Y-%m}  gap {g:+d}  {'hit' if abs(g)<=3 else 'MISS'}")
    if n: print(f"     -> {hits}/{n} within three months")
