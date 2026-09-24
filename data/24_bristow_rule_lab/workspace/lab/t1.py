import sys; sys.path.insert(0,'/home/claude/lab')
from bench import *
for c in ['Japan','Korea','Brazil']:
    chs=channels(c)
    print('='*70, c)
    for pk_off,tr_off in PANELS[c]['chrono']:
        freq=PANELS[c]['freq']
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: print(f'  {pk_off} {tr_off}  no channels'); continue
        raw=[]; adj=[]
        for nm,s in use:
            m=s.rolling(3).mean()[w0:w1].dropna()
            if len(m)<4: continue
            i=m.idxmin(); hi=float(m[:i].max()) if len(m[:i]) else float(m.max())
            raw.append(100*(float(m.min())-hi)/hi)
            z=trend_adjust(s)[w0:w1].dropna()
            if len(z)<4: continue
            j=z.idxmin(); hj=float(z[:j].max()) if len(z[:j]) else float(z.max())
            adj.append(100*(float(z.min())-hj)/hj)
        f=lambda v: f'{np.median(v):6.1f}' if v else '   n/a'
        print(f'  {pk_off} {tr_off}  depth_level={f(raw)}   depth_trendadj={f(adj)}')
