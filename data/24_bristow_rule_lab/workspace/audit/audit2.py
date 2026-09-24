import pandas as pd, numpy as np
def L(n):
    d=pd.read_csv(n+'.csv',parse_dates=['observation_date']); d.columns=['date','v']
    d['v']=pd.to_numeric(d.v,errors='coerce'); return d.dropna().reset_index(drop=True)
OK=[];FAIL=[]
def chk(l,g,w,tol=1e-9):
    ok=abs(g-w)<=tol if isinstance(w,(int,float)) and isinstance(g,(int,float)) else g==w
    (OK if ok else FAIL).append(f"{'PASS' if ok else 'FAIL'} | {l} | got={g} claimed={w}")
def note(l,v): OK.append(f"VAL  | {l} = {v}")
sc=L('SAHMCURRENT').set_index('date').v
sr=L('SAHMREALTIME').set_index('date').v
REC=[("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),("1960-04","1961-02"),
     ("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
     ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
for m,cv,rv in [('2024-07-01',0.50,0.53),('2024-08-01',0.57,0.57),('2024-09-01',0.53,0.50)]:
    chk(f"SAHMCURRENT {m[:7]}", round(float(sc[m]),2), cv, 0.001)
    chk(f"SAHMREALTIME {m[:7]}", round(float(sr[m]),2), rv, 0.001)
chk("SAHMCURRENT peak month 2024", sc['2024-01-01':'2024-12-01'].idxmax().strftime('%Y-%m'),'2024-08')
chk("SAHMREALTIME peak month 2024", sr['2024-01-01':'2024-12-01'].idxmax().strftime('%Y-%m'),'2024-08')
chk("SAHMCURRENT 2026-07", round(float(sc['2026-07-01']),2), -0.03, 0.001)
chk("SAHMCURRENT 2025-08 = 0.13", round(float(sc['2025-08-01']),2), 0.13, 0.001)
chk("SAHMCURRENT 2025-11 = 0.35", round(float(sc['2025-11-01']),2), 0.35, 0.001)
gaps=[];detail=[]
for p,t in REC:
    p=pd.Timestamp(p);t=pd.Timestamp(t)
    w=sc[p:t+pd.DateOffset(months=12)]; mx=w.max(); pk=w[w==mx].index[0]
    g=(pk.year-t.year)*12+(pk.month-t.month); gaps.append(g)
    detail.append((f"{p:%Y-%m}",f"{t:%Y-%m}",f"{pk:%Y-%m}",round(mx,2),g))
note("Bristow detail", detail)
chk("Bristow all 12 within 3 months", all(abs(g)<=3 for g in gaps), True)
chk("Bristow median abs gap", float(np.median([abs(g) for g in gaps])), 1.5)
coincide=[d[0] for d in detail if d[4]==0]
chk("Coincide exactly count", len(coincide), 4); note("Coinciding", coincide)
leads=[d for d in detail if d[4]<0]
chk("Exactly one lead", len(leads), 1); note("The lead", leads)
chk("1981-82 Sep82/Nov82 both 2.50", (round(float(sc['1982-09-01']),2), round(float(sc['1982-11-01']),2)), (2.5,2.5))
chk("2007-09 peak month", detail[10][2], '2009-06')
chk("Smallest in-recession peak", min(d[3] for d in detail), 1.5, 0.001)
note("1991 May/Jun/Jul", [round(float(sc[d]),2) for d in ['1991-05-01','1991-06-01','1991-07-01']])
d3=sc.diff(3); g2=[]
for p,t in REC:
    p=pd.Timestamp(p);t=pd.Timestamp(t)
    w=d3[p:t+pd.DateOffset(months=12)].dropna(); pk=w.idxmax()
    g2.append((pk.year-t.year)*12+(pk.month-t.month))
chk("2nd deriv exact-on-trough = 5", sum(x==0 for x in g2), 5)
chk("2nd deriv max overshoot = 2", max(g2), 2); note("2nd deriv gaps", g2)
lags=[]
for p,t in REC:
    p=pd.Timestamp(p);t=pd.Timestamp(t)
    w=sc[p:t+pd.DateOffset(months=6)]; c=w[w>=0.50]
    lags.append((f"{p:%Y-%m}",(c.index[0].year-p.year)*12+(c.index[0].month-p.month)))
post53=[l for n,l in lags if n>="1953"]
chk("lags count", len(post53), 11); chk("lag min", min(post53), 1); chk("lag max", max(post53), 8)
chk("lag median", float(np.median(post53)), 3.0); chk("lag mean", round(float(np.mean(post53)),2), 3.45, 0.01)
note("Onset lags", lags)
print("\n".join(OK)); print(); print("\n".join(FAIL) if FAIL else "NO FAILURES IN BLOCK 2")
