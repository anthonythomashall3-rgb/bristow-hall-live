import sys; sys.path.insert(0,"/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/ext")
from panel import *
REC=[("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),("1960-04","1961-02"),
("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04"),("2024-04","2024-08")]
UN,PA,HO,IP=vintages("UNRATE"),vintages("PAYEMS"),vintages("HOUST"),vintages("INDPRO")
g10,g1=cur('GS10.csv'),cur('GS1.csv')
cUN,cPA,cIP=cur('UNRATE.csv'),cur('PAYEMS.csv'),cur('INDPRO.csv')
cHO=HO[-1][1]
SPREAD={m:g10[m]-g1[m] for m in g10 if m in g1}
def gate(vm):
    """curve inverted in any of the 12 months known by vintage-month vm (yields lag ~1 month)."""
    return any(SPREAD.get(addm(vm,-j),9)<0 for j in range(1,14))
def latest_month(d):  return max(d)
def build(mode):
    """mode 'rt' = vintages only; 'mixed' = current vintage before each series' vintages begin."""
    ev=[]   # (vintage_date, month, channel)
    def push(vd,m,ch): ev.append((vd,m,ch))
    for vd,d in UN:
        m=latest_month(d); s=sahm(d,m)
        if s is not None and s>=0.35: push(vd,m,"Sahm 0.35")
        if s is not None and s>=0.55: push(vd,m,"Sahm 0.55 [nogate]")
    for vd,d in PA:
        m=latest_month(d); f=pct_fall(d,m,1)
        if f is not None and f<=-0.1: push(vd,m,"payrolls")
    for name,V,thr,k in (("housing",HO,-20,3),("IP",IP,-2,3)):
        prev=False
        for vd,d in V:
            m=latest_month(d); f=pct_fall(d,m,k)
            hit=f is not None and f<=thr
            if hit and prev: push(vd,m,name)
            prev=hit
    if mode=="mixed":
        for m in sorted(cUN):
            if m>="1960-02": break
            s=sahm(cUN,m)
            if s is not None and s>=0.35: push(addm(m,1)+"-05",m,"Sahm 0.35 (cv)")
            if s is not None and s>=0.55: push(addm(m,1)+"-05",m,"Sahm 0.55 [nogate] (cv)")
        for m in sorted(cPA):
            if m>="1961-10": break
            f=pct_fall(cPA,m,1)
            if f is not None and f<=-0.1: push(addm(m,1)+"-05",m,"payrolls (cv)")
    ev.sort()
    return ev
def episodes(ev,start,fresh=4):
    eps=[];last=None
    for vd,m,ch in ev:
        vm=vd[:7]
        if vm<start: continue
        nogate="nogate" in ch
        if not nogate and not gate(vm): continue
        if last is None or mo(vm)-mo(last)>fresh:
            eps.append((vd,ch)); 
        last=vm
    return eps
def score(eps):
    hits={};used=set();false=[]
    for i,(vd,ch) in enumerate(eps):
        vm=mo(vd[:7]); tgt=None
        for p,t in REC:
            if mo(p)-6<=vm<=mo(t)+12: tgt=p;break
        if tgt is None: false.append((vd,ch))
        elif tgt not in hits: hits[tgt]=(vd,ch,vm-mo(tgt))
    return hits,false
for mode,start,label in (("rt","1960-03","REAL TIME 1960-03 -> 2026 (vintages only)"),
                         ("mixed","1948-01","MIXED BASIS 1948 -> 2026 (current vintage before each series' vintages begin)")):
    ev=build(mode); eps=episodes(ev,start); h,f=score(eps)
    cov=[p for p,t in REC if mo(p)>=mo(start)-6]
    print(f"\n===== {label}")
    print(f"  recessions in window: {len(cov)} | detected {len(h)}")
    for p in cov:
        if p in h: print(f"    {p}  call {h[p][0]}  lag {h[p][2]:+d}  via {h[p][1]}")
        else:      print(f"    {p}  MISSED")
    print(f"  false alarms ({len(f)}):", [(v,c) for v,c in f])
