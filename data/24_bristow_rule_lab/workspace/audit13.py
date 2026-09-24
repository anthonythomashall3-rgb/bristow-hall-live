import pandas as pd, numpy as np
def rd(s):
    d=pd.read_csv(f'a10/{s}.csv'); d.columns=['date','v']
    d['date']=pd.to_datetime(d['date']); d['v']=pd.to_numeric(d['v'],errors='coerce')
    return d.set_index('date')['v'].dropna()
sc=rd('SAHMCURRENT'); rec=rd('USREC')
PK=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02']
TR=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']
md=lambda a,b:(a.year-b.year)*12+(a.month-b.month)

print("=== A. Is the Bristow date reachable WITHOUT NBER dates? ===")
print("A.2 defines the window as 'NBER peak to twelve months after the NBER trough'.")
print("For 2024 there is no NBER peak and no NBER trough, so that window cannot be formed.\n")

# operational alternative: anchor only on the crossing episode itself
def episodes(s,thr=0.50):
    out=[];cur=[]
    for d,v in s.items():
        if v>=thr: cur.append(d)
        elif cur: out.append(cur); cur=[]
    if cur: out.append(cur)
    return out
eps=episodes(sc)
print("crossing episodes on SAHMCURRENT (>=0.50):",len(eps))

def op_bristow(first,last,extra=12):
    w=sc[first:last+pd.DateOffset(months=extra)]
    return w.idxmax()

print("\n--- operational rule: arg max from first crossing to 12 months after last month >= 0.50 ---")
rows=[]
for tr,pk in zip(TR,PK):
    trd=pd.Timestamp(tr+'-01'); pkd=pd.Timestamp(pk+'-01')
    # the crossing episode belonging to this recession: first episode starting at/after the NBER peak
    cand=[e for e in eps if e[0]>=pkd and e[0]<=trd+pd.DateOffset(months=12)]
    if not cand:
        rows.append((tr,'NO CROSSING',None)); continue
    e=cand[0]
    d=op_bristow(e[0],e[-1])
    rows.append((tr,d.strftime('%Y-%m'),md(d,trd)))
bad=0
for tr,d,g in rows:
    flag='' if (g is not None and abs(g)<=3) else '   << outside +/-3'
    if g is None or abs(g)>3: bad+=1
    print(f"  trough {tr}: operational Bristow {d}  gap {g}{flag}")
print(f"operational rule: {12-bad}/12 within three months of the NBER trough")

print("\n--- the NBER-anchored rule, for comparison ---")
bad2=0
for tr,pk in zip(TR,PK):
    trd=pd.Timestamp(tr+'-01'); pkd=pd.Timestamp(pk+'-01')
    w=sc[pkd:trd+pd.DateOffset(months=12)]
    if len(w)==0: print(f"  trough {tr}: NO DATA"); bad2+=1; continue
    g=md(w.idxmax(),trd)
    if abs(g)>3: bad2+=1
    print(f"  trough {tr}: {w.idxmax().strftime('%Y-%m')}  gap {g}")
print(f"NBER-anchored rule: {12-bad2}/12 within three months")

print("\n--- applying the operational rule to the 2024 episode ---")
e24=[e for e in eps if e[0]==pd.Timestamp('2024-07-01')][0]
print("  2024 crossing episode:",[d.strftime('%Y-%m') for d in e24])
print("  operational Bristow date:",op_bristow(e24[0],e24[-1]).strftime('%Y-%m'))
for lo,hi,lbl in [('2024-01-01','2024-12-01','calendar 2024'),('2023-01-01','2026-07-01','2023-2026'),
                  ('2022-01-01','2026-07-01','2022-2026'),('2021-01-01','2026-07-01','2021-2026')]:
    print(f"  arg max over {lbl}: {sc[lo:hi].idxmax().strftime('%Y-%m')}")

print("\n=== B. Does the screen's result depend on the classification windows? ===")
def screen(tail_w,warn_w,series):
    inr=rec.reindex(series.index).fillna(0)
    fl=(series>=0.50)&(inr==0); out=[];cur=[]
    for d,f in fl.items():
        if f: cur.append(d)
        elif cur: out.append(cur); cur=[]
    if cur: out.append(cur)
    trs=[pd.Timestamp(x+'-01') for x in TR]; pks=[pd.Timestamp(x+'-01') for x in PK]
    tails=warn=stand=[];tails=[];warn=[];stand=[]
    for e in out:
        if any(0<=md(e[0],x)<=tail_w for x in trs): tails.append(e)
        elif any(0<=md(x,e[-1])<=warn_w for x in pks): warn.append(e)
        else: stand.append(e)
    return len(tails),len(warn),[ (e[0].strftime('%Y-%m'),len(e)) for e in stand]
print(" current vintage, varying the tail and warning windows:")
for tw in (0,1,2,3):
    for ww in (3,5,7):
        nt,nw,st=screen(tw,ww,sc)
        mark=" <- as published" if (tw,ww)==(1,5) else ""
        print(f"   tail<={tw}, warn<={ww}: tails={nt} warnings={nw} standalone={st}{mark}")

print("\n=== C. Is the April 2024 onset robust to the lag statistic chosen? ===")
lags=[]
for p,tr in zip(PK[1:],TR[1:]):
    p=pd.Timestamp(p+'-01'); trd=pd.Timestamp(tr+'-01')
    w=sc[p:trd+pd.DateOffset(months=6)]; x=w[w>=0.50]
    if len(x): lags.append(md(x.index[0],p))
first24=pd.Timestamp('2024-07-01')
import statistics
for stat,val in [('median',statistics.median(lags)),('mean',round(statistics.mean(lags),1)),
                 ('min',min(lags)),('max',max(lags)),('mode',statistics.mode(lags))]:
    d=(first24-pd.DateOffset(months=int(round(val)))).strftime('%Y-%m')
    print(f"   lag {stat} = {val} -> onset {d}")
print("   lags:",sorted(lags))

print("\n=== D. Second-derivative herald under the operational (crossing-anchored) window ===")
d3=sc-sc.shift(3)
ok=0
for tr,pk in zip(TR,PK):
    trd=pd.Timestamp(tr+'-01'); pkd=pd.Timestamp(pk+'-01')
    cand=[e for e in eps if e[0]>=pkd and e[0]<=trd+pd.DateOffset(months=12)]
    if not cand: print(f"   trough {tr}: no crossing"); continue
    e=cand[0]; w=d3[e[0]:e[-1]+pd.DateOffset(months=12)]
    g=md(w.idxmax(),trd)
    if g==0: ok+=1
    print(f"   trough {tr}: herald {w.idxmax().strftime('%Y-%m')} gap {g}")
print(f"   lands exactly on the trough in {ok} of 12 under the operational window")
w24=d3[e24[0]:e24[-1]+pd.DateOffset(months=12)]
print("   2024 episode herald:",w24.idxmax().strftime('%Y-%m'))

print("\n=== E. verification of the audit-13 edits ===")
P=F=0
def chk(lab,got,want,claim=None):
    global P,F
    ok = got==want
    print(("PASS " if ok else "FAIL ")+f"{lab}: got={got!r} want={want!r}"+("" if ok else f"  << {claim}"))
    P,F=(P+1,F) if ok else (P,F+1)
t=open('paper_v6_full.md').read()
# operational rule reproduces the NBER-anchored dates exactly
same=True
for tr,pk in zip(TR,PK):
    trd=pd.Timestamp(tr+'-01'); pkd=pd.Timestamp(pk+'-01')
    cand=[e for e in eps if e[0]>=pkd and e[0]<=trd+pd.DateOffset(months=12)]
    a=sc[cand[0][0]:cand[0][-1]+pd.DateOffset(months=12)].idxmax()
    b=sc[pkd:trd+pd.DateOffset(months=12)].idxmax()
    if a!=b: same=False
chk("operational and NBER-anchored windows give identical dates",same,True,"returns exactly the same twelve dates")
chk("operational rule 12/12 within three months",
    all(abs(md(sc[e[0]:e[-1]+pd.DateOffset(months=12)].idxmax(),pd.Timestamp(tr+'-01')))<=3
        for tr,pk in zip(TR,PK)
        for e in [[x for x in eps if x[0]>=pd.Timestamp(pk+'-01') and x[0]<=pd.Timestamp(tr+'-01')+pd.DateOffset(months=12)][0]]),
    True,"the record reported in Section 2 is unchanged under either")
chk("2024 operational Bristow date is Aug 2024",
    sc[pd.Timestamp('2024-07-01'):pd.Timestamp('2024-09-01')+pd.DateOffset(months=12)].idxmax().strftime('%Y-%m'),'2024-08',"end August 2024")
d3=sc-sc.shift(3)
chk("2024 herald over the rule's own window is Aug 2024",
    d3[pd.Timestamp('2024-07-01'):pd.Timestamp('2024-09-01')+pd.DateOffset(months=12)].idxmax().strftime('%Y-%m'),'2024-08',
    "fastest three-month climb ends in August 2024")
gaps=[md(d3[pd.Timestamp(pk+'-01'):pd.Timestamp(tr+'-01')+pd.DateOffset(months=12)].idxmax(),pd.Timestamp(tr+'-01')) for pk,tr in zip(PK,TR)]
chk("herald exact in 5 of 12",sum(1 for x in gaps if x==0),5,"five of the twelve")
chk("herald never more than 2 months late",max(gaps),2,"never runs more than two months past it")
chk("herald earliest is 11 months",min(gaps),-11,"eleven in 1981-82")
chk("herald -3 in 1949 and 1954",(gaps[0],gaps[1]),(-3,-3),"three months in 1949 and 1954")
chk("herald -7 in 1970",gaps[4],-7,"seven in 1970")
for tw,ww,exp in [(1,5,2),(3,5,2),(1,7,2),(3,7,2),(1,3,3)]:
    _,_,st=screen(tw,ww,sc)
    chk(f"screen tail<={tw} warn<={ww}: {exp} standalone",len(st),exp,"Neither window drives the result")
for s in ["A crossing episode is a maximal run","requires no official dates",
          "the indicator's fastest three-month climb ends in August 2024",
          "eleven in 1981–82","widening the tail window to three months"]:
    chk(f"text present: {s[:44]}",s in t,True,"edit landed")
print(f"\nPASSED {P}  FAILED {F}")
