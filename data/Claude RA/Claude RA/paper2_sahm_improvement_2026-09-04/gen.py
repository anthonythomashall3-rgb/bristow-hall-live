import core, json, statistics as st
S=[(core.VIN[j],core.series(j)) for j in range(len(core.VIN))]
S=[(v,s) for v,s in S if s]
def mas(s,k): return [sum(v for _,v in s[i-k+1:i+1])/k for i in range(k-1,len(s))]
def build(kc,kb,L,mode,vol=24):
    """kc = MA length for current, kb = MA length for baseline min, L = lookback months."""
    out=[]
    for v,s in S:
        if len(s)<max(kc,kb)+L+2: out.append((v,s[-1][0] if s else None,None)); continue
        mc=mas(s,kc); mb=mas(s,kb)
        cur=mc[-1]; base=min(mb[-1-L:-1]) if len(mb)>L else None
        if base is None: out.append((v,s[-1][0],None)); continue
        gap=cur-base
        if mode=='abs': x=gap
        elif mode=='rel': x=gap/base if base>0 else None          # proportional rise
        elif mode=='z':
            d=[s[i][1]-s[i-1][1] for i in range(len(s)-vol,len(s))]
            sd=st.pstdev(d) or 1e-9; x=gap/sd                      # volatility-scaled
        out.append((v,s[-1][0],x))
    return out
def scan(arr,lo,hi,step,persist=(1,2)):
    best=[]
    t=lo
    while t<=hi+1e-12:
        for p in persist:
            fires=[];streak=0
            for v,m,x in arr:
                if x is None: continue
                hit=x>=t-1e-12
                streak=streak+1 if hit else 0
                if streak>=p: fires.append((v,m,x))
            l,fa=core.score(core.episodes(fires))
            if len(l)==len(core.REC) and not fa:
                lags=list(l.values())
                best.append((round(t,4),p,sorted(lags)[len(lags)//2],round(sum(lags)/len(lags),2),max(lags),lags))
        t+=step
    return best
if __name__=='__main__':
    print("=== RELATIVE Sahm  (MA3 - min12 MA3) / min12  ===")
    r=scan(build(3,3,12,'rel'),0.02,0.30,0.002)
    r.sort(key=lambda z:(z[2],z[3]))
    for z in r[:8]: print("  thr=%.3f p=%d med=%s mean=%s max=%s %s"%z)
    print("  clean configs:",len(r))
    print("=== VOLATILITY-SCALED Sahm  gap / sd(monthly change, 24m) ===")
    r=scan(build(3,3,12,'z'),1.0,8.0,0.05)
    r.sort(key=lambda z:(z[2],z[3]))
    for z in r[:6]: print("  thr=%.2f p=%d med=%s mean=%s max=%s %s"%z)
    print("  clean configs:",len(r))
