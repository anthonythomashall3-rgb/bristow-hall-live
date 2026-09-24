import pandas as pd, numpy as np
def L(n):
    d=pd.read_csv(n+'.csv',parse_dates=['observation_date']); d.columns=['date','v']
    d['v']=pd.to_numeric(d.v,errors='coerce'); return d.dropna().reset_index(drop=True)
OK=[];FAIL=[]
def chk(l,g,w,tol=1e-9):
    ok=abs(g-w)<=tol if isinstance(w,(int,float)) and isinstance(g,(int,float)) else g==w
    (OK if ok else FAIL).append(f"{'PASS' if ok else 'FAIL'} | {l} | got={g} claimed={w}")
def note(l,v): OK.append(f"VAL  | {l} = {v}")

sc=L('SAHMCURRENT'); sr=L('SAHMREALTIME'); ur=L('USREC')
def screen(df,lab):
    m=pd.merge(df,ur,on='date',suffixes=('','_r'))
    o=m[(m.v>=0.50)&(m.v_r==0)].reset_index(drop=True)
    runs=[];cur=[o.date[0]]
    for i in range(1,len(o)):
        if (o.date[i]-o.date[i-1]).days<=32: cur.append(o.date[i])
        else: runs.append(cur); cur=[o.date[i]]
    runs.append(cur)
    out=[]
    for r in runs:
        vals=m[(m.date>=r[0])&(m.date<=r[-1])].v
        out.append((r[0].strftime('%Y-%m'),r[-1].strftime('%Y-%m'),len(r),round(vals.max(),2)))
    note(lab,out); return out
cv=screen(sc,"CURRENT-vintage screen (>=0.50, no NBER recession)")
rt=screen(sr,"REAL-TIME screen (>=0.50, no NBER recession)")
chk("Current-vintage: 15 episodes total", len(cv), 15)
chk("Current-vintage 2003 episode present, 2 months, max 0.50", ('2003-07','2003-08',2,0.5) in cv, True)
chk("Current-vintage 2024 episode 3 months max 0.57", ('2024-07','2024-09',3,0.57) in cv, True)
chk("1959 early warning Nov-Dec, max 0.60", ('1959-11','1959-12',2,0.6) in cv, True)
chk("1991-92 tail ends Oct 1992", any(r[1]=='1992-10' for r in cv), True)
chk("2001-02 tail ends Nov 2002", any(r[1]=='2002-11' for r in cv), True)
chk("Current: 12 lagging tails (15 - 1959 - 2003 - 2024)", len(cv)-3, 12)
chk("REAL-TIME: 2003 absent", not any(r[0].startswith('2003') for r in rt), True)
scr=sr.set_index('date').v
chk("REAL-TIME 2003 peak = 0.47", round(float(scr['2003-01-01':'2003-12-01'].max()),2), 0.47, 0.001)
chk("REAL-TIME 1976-11 = 0.50", round(float(scr['1976-11-01']),2), 0.50, 0.001)
chk("REAL-TIME 1969-10 = 0.50", round(float(scr['1969-10-01']),2), 0.50, 0.001)
chk("REAL-TIME 2024 run 3 months max 0.57", ('2024-07','2024-09',3,0.57) in rt, True)
chk("SAHMREALTIME starts Dec 1959", sr.date.min().strftime('%Y-%m'), '1959-12')

# soft patches
u=L('UNRATE').set_index('date').v; s=sc.set_index('date').v
chk("1966-11 unrate 3.6", float(u['1966-11-01']), 3.6, 0.001)
chk("1967-10 unrate 4.0", float(u['1967-10-01']), 4.0, 0.001)
chk("1966-67 Sahm peak 0.23", round(float(s['1966-01-01':'1968-06-01'].max()),2), 0.23, 0.001)
chk("1986-01 unrate 6.7", float(u['1986-01-01']), 6.7, 0.001)
chk("1985-86 Sahm peak 0.27", round(float(s['1985-01-01':'1987-06-01'].max()),2), 0.27, 0.001)
chk("1962-63 unrate min 5.4", float(u['1962-01-01':'1963-12-01'].min()), 5.4, 0.001)
chk("1962-63 unrate max 5.9", float(u['1962-01-01':'1963-12-01'].max()), 5.9, 0.001)
chk("1962-63 Sahm peak 0.30", round(float(s['1962-01-01':'1964-06-01'].max()),2), 0.30, 0.001)
chk("1959-11 = 0.60", round(float(s['1959-11-01']),2), 0.60,0.001)
chk("1959-12 = 0.53", round(float(s['1959-12-01']),2), 0.53,0.001)
chk("Nov1959 to Apr1960 = 5 months", 5, 5)
chk("2003-06 unrate peak 6.3", float(u['2003-06-01']), 6.3, 0.001)
chk("2001-11 unrate 5.5", float(u['2001-11-01']), 5.5, 0.001)
chk("unrate trough 3.4 Apr 2023", (float(u['2023-04-01']), u['2023-01-01':'2024-12-01'].idxmin().strftime('%Y-%m')), (3.4,'2023-04'))
chk("2024-07 unrate 4.2 current", float(u['2024-07-01']), 4.2, 0.001)
chk("2025-11 unrate 4.5", float(u['2025-11-01']), 4.5, 0.001)
chk("2026-07 unrate 4.1", float(u['2026-07-01']), 4.1, 0.001)
chk("Oct 2025 missing", pd.Timestamp('2025-10-01') not in u.index, True)
# lagging unemployment claims
for tr,claim in [('1991-03-01',15),('2001-11-01',19)]:
    t=pd.Timestamp(tr); w=u[t:t+pd.DateOffset(months=36)]; pk=w.idxmax()
    chk(f"unemployment peaks {claim} months after {tr[:7]} trough", (pk.year-t.year)*12+(pk.month-t.month), claim)
# 2017-19
chk("2017-19 min unrate 3.5", float(u['2017-01-01':'2019-12-01'].min()), 3.5, 0.001)
pre=u[:'2016-12-01']; chk("last <=3.5 before 2017 = Dec 1969", pre[pre<=3.5].index.max().strftime('%Y-%m'), '1969-12')
print("\n".join(OK)); print(); print("\n".join(FAIL) if FAIL else "NO FAILURES IN BLOCK 3")
