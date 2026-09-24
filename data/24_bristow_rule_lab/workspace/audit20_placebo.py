import pandas as pd, numpy as np, random
def rd(s):
    d=pd.read_csv(f'a20/{s}.csv'); d.columns=['date','v']
    d['date']=pd.to_datetime(d['date']); d['v']=pd.to_numeric(d['v'],errors='coerce')
    return d.set_index('date')['v'].dropna()
sc=rd('SAHMCURRENT'); rec=rd('USREC')
PK=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02']
TR=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']
md=lambda a,b:(a.year-b.year)*12+(a.month-b.month)
def eps(s,thr=0.50):
    out=[];cur=[]
    for d,v in s.items():
        if v>=thr: cur.append(d)
        elif cur: out.append(cur); cur=[]
    if cur: out.append(cur)
    return out
E=eps(sc)
windows=[]
for pk,tr in zip(PK,TR):
    p=pd.Timestamp(pk+'-01'); t=pd.Timestamp(tr+'-01')
    c=[e for e in E if e[0]>=p and e[0]<=t+pd.DateOffset(months=12)]
    if not c: continue
    w=sc[c[0][0]:c[0][-1]+pd.DateOffset(months=12)]
    windows.append((tr,t,w))
print("=== PLACEBO 1: how informative is 'peak within three months of the trough'? ===")
print("Each recession's Bristow window, its length, and where in it the true trough sits.\n")
tot_ok=0; probs=[]
for tr,t,w in windows:
    n=len(w); pos=list(w.index).index(t) if t in w.index else None
    # if the peak month were uniform over the window, what is P(|gap| <= 3)?
    within=sum(1 for d in w.index if abs(md(d,t))<=3)
    p_chance=within/n
    probs.append(p_chance)
    actual=md(w.idxmax(),t)
    ok=abs(actual)<=3; tot_ok+=ok
    print(f"  {tr}: window {n:3d} months, months within +/-3 of trough {within:2d} -> chance {p_chance:5.2f}   actual gap {actual:+d} {'hit' if ok else 'MISS'}")
import math
mean_p=sum(probs)/len(probs)
# probability that a uniform-peak rule scores 12/12
p_all=1.0
for x in probs: p_all*=x
print(f"\n  mean per-recession chance under a uniform-peak null: {mean_p:.3f}")
print(f"  probability all twelve land within three months by chance: {p_all:.2e}  (1 in {1/p_all:,.0f})")
print(f"  observed: {tot_ok}/12")

print("\n=== PLACEBO 2: does the indicator peak near troughs, or near anything? ===")
print("Same rule, but scored against FALSE troughs displaced by k months.\n")
for k in (-24,-18,-12,-6,6,12,18,24):
    hits=0; n=0
    for tr,t,w in windows:
        fake=t+pd.DateOffset(months=k)
        n+=1
        if abs(md(w.idxmax(),fake))<=3: hits+=1
    print(f"  troughs displaced {k:+3d} months: {hits:2d}/{n} within three")

print("\n=== PLACEBO 3: random windows of the same lengths, anywhere in the series ===")
random.seed(7)
lens=[len(w) for _,_,w in windows]
trials=20000; succ=0
idx=list(sc.index)
for _ in range(trials):
    ok=True
    for L in lens:
        if L>=len(idx): ok=False; break
        st=random.randrange(0,len(idx)-L)
        seg=sc.iloc[st:st+L]
        # a "trough" placed uniformly at random inside the window
        tpos=random.randrange(0,L)
        if abs(list(seg.index).index(seg.idxmax())-tpos)>3: ok=False; break
    succ+=ok
print(f"  {trials} draws of twelve random windows with a randomly placed trough: {succ} scored 12/12 ({100*succ/trials:.3f}%)")
