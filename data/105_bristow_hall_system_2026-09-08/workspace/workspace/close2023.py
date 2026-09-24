"""The 2023 episode is still OPEN under v8 (no K/J/H trough call has closed it).  What closes it, and at what price to the twelve
classic troughs: the diffusion trough clause T (the Department's monthly index, 48/13) or F (leg A's own index, 36/8) as a
fourth closer, or the claims side's own re-arm (the opening object back at its base)."""
exec(open('dominance.py').read().split('rows=[]')[0])
print('trough legs available:', list(TLG.keys()))
def run(tl):
    with contextlib.redirect_stdout(io.StringIO()):
        t=B.american_chronology({q:PLU[q] for q in PK5},{q:TLG[q] for q in tl},sahm=g,line=0.5,second=[CONF['V'],CONF['H'],CONF['P']],horizon_months=4,back_months=6)
    res={}; early=[]; cur=None; opens=[]; closes={}
    for o in t:
        if o['kind']=='peak':
            cur=None; opens.append(o)
            for i,(p,q) in enumerate(zip(PK,TR)):
                if p-pd.DateOffset(months=6)<=o['date']<=q: cur=i; break
        elif o['kind']=='trough':
            closes[len(opens)-1]=o
            if cur is not None and cur not in res:
                err=(o['date'].year-TR[cur].year)*12+o['date'].month-TR[cur].month; res[cur]=((o['published']-me(TR[cur])).days,err,o['leg'])
    cl=[res[i] for i in res if abs(res[i][1])<=6]
    last=opens[-1]; lastclose=closes.get(len(opens)-1)
    print(f"  {'+'.join(tl):8} troughs closed {len(cl)}/12 within 6 months, median {np.median([r[0] for r in cl]):.0f} d, worst {max(r[0] for r in cl)}, exact {sum(1 for r in cl if r[1]==0)}, within one {sum(1 for r in cl if abs(r[1])<=1)}; closers {sorted(set(r[2] for r in cl))}; early(<-6) {[i for i in res if res[i][1]<-6]}")
    cs='NO - still open' if lastclose is None else (lastclose['published'].strftime('%Y-%m-%d')+' dated '+lastclose['date'].strftime('%Y-%m')+' by '+lastclose['leg'])
    print(f"           last episode opened {last['published']:%Y-%m-%d} dated {last['date']:%Y-%m}; closed: {cs}")
for tl in [('K','J','H'),('K','J','H','T'),('K','J','H','F'),('K','J','H','T','F')]:
    if all(x in TLG for x in tl): run(tl)
