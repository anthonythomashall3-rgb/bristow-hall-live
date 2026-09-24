"""Anthony, 5 Sep 2026: "We need to have the recession close in 2024 and hopefully we can make it open in 2024 too.
It was a 2024 mild recession as the paper states."  Before anything is changed: what every frozen object says about
2022-2026, read off the objects, and what Paper 1's own end rule (leg S, gated as in route v39) costs as a closer."""
exec(open('dominance.py').read().split('rows=[]')[0])
SEC=[CONF['V'],CONF['H'],CONF['P']]
T0=pd.Timestamp('2022-01-01')
def chron(tl):
    with contextlib.redirect_stdout(io.StringIO()):
        return B.american_chronology({q:PLU[q] for q in PK5},{q:TLG[q] for q in tl},sahm=g,line=0.5,second=SEC,horizon_months=4,back_months=6)
print("== 1. v8 turns from 2022 ==")
for o in chron(('K','J','H')):
    if o['published']>=T0: print({k:(v.strftime('%Y-%m-%d') if isinstance(v,pd.Timestamp) else v) for k,v in o.items()})
print("== 2. raw leg calls from 2022 (published, dated) ==")
for q in PK5: print(' peak leg',q,[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in PLU[q] if p>=T0])
for q in ['K','J','H','T','F','S']: print(' trough leg',q,[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in TLG[q] if p>=T0])
print(' S ungated',[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in leg_S(g) if p>=T0])
print(' claims armed (leg S gate) months from 2023:', [t.strftime('%Y-%m') for t,v in arm['2023-01':].items() if v])
print("== 3. confirmer gaps monthly 2023-01 on: Sahm first prints | vacancy(2,6) | housing35 pair | hours pair ==")
df=pd.concat([g.rename('sahm'),vr.rename('vac'),CONF['H']['gap'].rename('hous35'),CONF['P']['gap'].rename('hours')],axis=1)['2023-01':]
print(df.round(2).to_string())
print("== 4. closers priced on the twelve classic troughs + what closes 2023 ==")
def run(tl):
    t=chron(tl); res={}; cur=None; opens=[]; closes={}
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
    print(f"  {'+'.join(tl):10} troughs closed {len(cl)}/12 within 6 months, median {np.median([r[0] for r in cl]):.0f} d, worst {max(r[0] for r in cl)}, exact {sum(1 for r in cl if r[1]==0)}, within one {sum(1 for r in cl if abs(r[1])<=1)}; closers {sorted(set(r[2] for r in cl))}; early(<-6) {[i for i in res if res[i][1]<-6]}; other troughs {[(o['published'].strftime('%Y-%m-%d'),o['date'].strftime('%Y-%m'),o['leg']) for k,o in closes.items() if k<len(opens)-1 and all(not (PK[i]-pd.DateOffset(months=6)<=opens[k]['date']<=TR[i]+pd.DateOffset(months=6)) for i in range(12))]}")
    cs='NO - still open' if lastclose is None else (lastclose['published'].strftime('%Y-%m-%d')+' dated '+lastclose['date'].strftime('%Y-%m')+' by '+lastclose['leg'])
    print(f"             last episode opened {last['published']:%Y-%m-%d} dated {last['date']:%Y-%m} by {last['leg']}; closed: {cs}; per-trough lags {[res[i][0] for i in sorted(res)]}")
for tl in [('K','J','H'),('K','J','H','S'),('K','J','H','T'),('K','J','H','T','S')]: run(tl)
print("== 5. would the route have opened in 2024 with the 2023 episode absent?  Sahm crossings and claims proposals 2024 ==")
print(' Sahm >=0.50 first-print months:',[t.strftime('%Y-%m') for t,v in g['2023-01':].items() if v>=0.5])
print(' claims proposals 2024-2026 by leg:',{q:[d.strftime('%Y-%m') for p,d in PLU[q] if p>=pd.Timestamp('2024-01-01')] for q in PK5})
