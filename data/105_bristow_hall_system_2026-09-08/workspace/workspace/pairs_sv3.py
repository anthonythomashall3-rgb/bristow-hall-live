exec(open('pairs_sv2.py').read().split("l0,o0,c0=lags_of([])")[0])
l0,o0,c0=lags_of([])
print(f"{'x':>6}{'y':>6}{'expo(6,4)':>10}{'expo(6,6)':>10}{'2007 lag':>9}   pair quiet firings")
for x in [0.20]:
    for y in [0.26,0.28,0.29,0.30,0.31,0.32,0.33,0.34]:
        pr=pd.concat([sahm/x,vac/y],axis=1).min(axis=1).dropna(); hp=hits(pr,1.0); qm2=quiet(hp.index)
        e=win_expo([S,V,H,HS['P'],hp],7,5)[0]; e6=win_expo([S,V,H,HS['P'],hp],7,7)[0]
        l,o,c=lags_of([dict(name='sv_pair',gap=pr,line=1.0,pub_day=30)])
        print(f"{x:6.2f}{y:6.2f}{e:10.2f}{e6:10.2f}{l.get(10):9d}   {[f'{t:%Y-%m}' for t in hp.index[(hp&qm2).values]]}")
# what the December 2007 call looks like with the pair
pr=pd.concat([sahm/0.20,vac/0.30],axis=1).min(axis=1).dropna()
print('pair readings Oct 2007 - Mar 2008:', pr['2007-10':'2008-03'].round(2).to_dict())
print('Sahm gap first prints:', sahm['2007-10':'2008-03'].round(2).to_dict()); print('vacancy fast form:', vac['2007-10':'2008-03'].round(2).to_dict())
print('2026 readings:', pr['2025-10':'2026-07'].round(2).to_dict())
