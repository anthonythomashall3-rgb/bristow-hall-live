import core, gen
def mo(s):
    y,m=map(int,s.split('-')[:2]); return y*12+m
def protocol(arr,thr,p=1):
    """Paper 2's real-time protocol on a first-print indicator: onset calls, end calls, revisions."""
    eps=[];open_ep=None;streak=0
    for v,m,x in arr:
        if x is None: continue
        streak=streak+1 if x>=thr-1e-9 else 0
        if open_ep is None:
            if streak>=p: open_ep=dict(onset=v,onset_month=m,mx=x,mx_month=m,end=None,rev=0)
        else:
            if x>open_ep['mx']:
                if open_ep['end']: open_ep['rev']+=1; open_ep['end']=None
                open_ep['mx'],open_ep['mx_month']=x,m
            elif open_ep['end'] is None:
                open_ep['end'],open_ep['end_month']=v,open_ep['mx_month']
            if x<thr-1e-9 and open_ep['end']:
                eps.append(open_ep); open_ep=None
    if open_ep: eps.append(open_ep)
    return eps
for name,(kc,kb,L),thr in [("Sahm 3/12 0.50",(3,3,12),0.50),("new 3/6/15 0.46",(3,6,15),0.46),
                            ("new 3/6/15 0.50",(3,6,15),0.50),("new 3/6/15 0.55",(3,6,15),0.55)]:
    arr=gen.build(kc,kb,L,'abs')
    eps=protocol(arr,thr)
    l,fa=core.score(core.episodes([(v,m,x) for v,m,x in arr if x is not None and x>=thr-1e-9]))
    lags=list(l.values())
    print(f"{name}: episodes={len(eps)} detected={len(l)}/10 lags={lags} mean={sum(lags)/len(lags):.2f} false={fa}")
    for e in eps:
        print(f"    onset {e['onset']} ({e['onset_month']})  trough {e.get('end_month')} confirmed {e['end']}  revisions {e['rev']}")
