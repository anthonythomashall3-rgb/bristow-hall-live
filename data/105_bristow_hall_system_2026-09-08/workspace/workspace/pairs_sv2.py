exec(open('dominance.py').read().split('rows=[]')[0])
def lags_of(sec_extra):
    with contextlib.redirect_stdout(io.StringIO()):
        t=B.american_chronology({q:PLU[q] for q in PK5},{q:TLG[q] for q in TR3},sahm=g,line=0.5,second=[CONF['V'],CONF['H'],CONF['P']]+sec_extra,horizon_months=4,back_months=6)
    on=[(o['published'],o['date'],o.get('condition')) for o in t if o['kind']=='peak' and o['published']>=pd.Timestamp('1948-06-01')]
    lags={}; other=[]; cond={}
    for pub,d,c in on:
        hit=None
        for i,(p,q) in enumerate(zip(PK,TR)):
            if p-pd.DateOffset(months=6)<=d<=q: hit=i; break
        if hit is None: other.append(d)
        elif hit not in lags: lags[hit]=(pub-me(PK[hit])).days; cond[hit]=c
    return lags,other,cond
l0,o0,c0=lags_of([])
print('v8   ', [l0.get(i) for i in range(12)], 'conditions', [c0.get(i) for i in range(12)])
for x,y in [(0.20,0.30),(0.20,0.35),(0.20,0.40),(0.18,0.30),(0.22,0.30),(0.15,0.30),(0.20,0.50)]:
    pr=pd.concat([sahm/x,vac/y],axis=1).min(axis=1).dropna(); e=win_expo([S,V,H,HS['P'],hits(pr,1.0)],7,5)[0]
    l,o,c=lags_of([dict(name='sv_pair',gap=pr,line=1.0,pub_day=30)])
    print(f"pair Sahm {x:.2f} x vac {y:.2f}  expo {e:5.2f}  ", [l.get(i) for i in range(12)], 'other', [f'{d:%Y-%m}' for d in o], 'moved:', [i for i in range(12) if l.get(i)!=l0.get(i)])
# the pair's own hits: which months, quiet or not
pr=pd.concat([sahm/0.20,vac/0.30],axis=1).min(axis=1).dropna(); hp=hits(pr,1.0); qm2=quiet(hp.index)
print('pair 0.20x0.30 fires in', int(hp.sum()), 'months; quiet months among them:', int((hp&qm2).sum()), [f'{t:%Y-%m}' for t in hp.index[(hp&qm2).values]])
print('vacancy series starts', vac.dropna().index[0].date())
