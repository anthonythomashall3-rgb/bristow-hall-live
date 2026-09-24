import sys, pickle, itertools, pandas as pd
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/rt')
import bristow_rule_v3 as br, replay as rp

def decide(Dmap, threshold=2.0, fall_months=4, drop=0.5, min_cycle=15, warmup=24, t0='1962-06-01'):
    calls=[]; start=None
    for T in sorted(Dmap):
        if T < pd.Timestamp(t0): continue
        D=Dmap[T]
        if len(D)<warmup: continue
        if start is None: start=D.index[0]
        seg=D[start:]
        if len(seg)<4: continue
        at=seg.idxmax(); hi=float(seg.max())
        if hi<threshold: continue
        after=seg[seg.index>at]
        if len(after)<fall_months: continue
        tail=list(after.iloc[-fall_months:])
        prev=float(after.iloc[-fall_months-1]) if len(after)>fall_months else hi
        falling=all(tail[k]<(tail[k-1] if k>0 else prev) for k in range(fall_months))
        if falling and (hi-float(after.iloc[-1]))>=drop:
            start=D.index[-1]+pd.DateOffset(months=1)
            if calls and min_cycle and br._md(at,calls[-1][1])<min_cycle: continue
            calls.append((T,at,D.index[-1]))
    return calls

def summarize(calls):
    rows=[]; used=set()
    for tr in rp.NBER_T:
        best=None
        for i,c in enumerate(calls):
            if i in used: continue
            e=br._md(c[1],tr)
            if abs(e)<=6 and (best is None or abs(e)<abs(best[1])): best=(i,e,c[0])
        if best is None: rows.append(None); continue
        used.add(best[0]); rows.append((best[1],(best[2]-tr).days))
    other=len([c for i,c in enumerate(calls) if i not in used])
    hit=sum(r is not None for r in rows); ex=sum(r is not None and r[0]==0 for r in rows)
    w1=sum(r is not None and abs(r[0])<=1 for r in rows)
    lags=[r[1] for r in rows if r is not None]
    return hit,ex,w1,other,(max(lags) if lags else None),(sum(lags)/len(lags) if lags else None),[None if r is None else r[0] for r in rows]

if __name__=='__main__':
    res=[]
    for panel in ('core3','core6'):
        for s in (1,2,3):
            Dmap=pickle.load(open(f'D_{panel}_s{s}.pkl','rb'))
            for thr,fm,dr in itertools.product((1.0,1.5,2.0),(1,2,3,4),(0.25,0.5,1.0)):
                calls=decide(Dmap,thr,fm,dr)
                h,ex,w1,oth,mx,mean,errs=summarize(calls)
                res.append((panel,s,thr,fm,dr,h,ex,w1,oth,mx,mean,errs))
    res.sort(key=lambda r:(-(r[5]),r[8],-(r[6]),-(r[7]),r[10] or 999))
    for r in res[:40]: print(r)
