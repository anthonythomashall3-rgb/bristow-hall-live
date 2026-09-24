from mini import *
from hub import leg_X2
from legu_min import leg_U, s_cur
import itertools, json
KJHS={k:TLG[k] for k in 'KJHS'}
UL=[0.30,0.35,0.40,0.45,0.50,0.55,0.60,0.70]; VL=[0.20,0.24,0.30,0.36,0.42,0.50]
cells={}
for ul,vl in itertools.product(UL,VL):
    SEC['V']=dict(name='vacancy',gap=vr,line=vl,pub_day=30)
    r=score13(chron({'U':leg_U(s_cur,ul),'X':leg_X2(vac_line=vl)},KJHS,['V','H','P']))
    cells[(ul,vl)]=dict(lags={i:r['lags_p'][i] for i in r['lags_p']},other=[pd.Timestamp(d+'-01') for _,d,_ in r['other']])
    if len(r['lags_p'])<13: print(f"cell U{ul} vac{vl}: missed",[PK[i].strftime('%Y-%m') for i in range(13) if i not in r['lags_p']],'other',r['other'])
print("\nCAUSAL REPLAY on the grid (safe: every prior recession called, fewest prior other calls, then highest U line, highest vac line):")
print(f"{'recession':10}{'chosen U':>9}{'vac':>6}{'lag d':>7}")
res=[]
for k in range(5,13):   # from 1973 on: leg U exists from 1971; prior recessions include the hub-only era
    p=PK[k]; best=None
    for (ul,vl),c in cells.items():
        prior=[i for i in range(k)]
        if any(i not in c['lags'] for i in prior): continue
        noth=sum(1 for d in c['other'] if d<p)
        key=(noth,-ul,-vl)
        if best is None or key<best[0]: best=(key,(ul,vl))
    (ul,vl)=best[1]; lag=cells[(ul,vl)]['lags'].get(k)
    res.append(lag); print(f"{p:%Y-%m}    {ul:>7.2f}{vl:>6.2f}{('-' if lag is None else lag):>7}")
print("  causal record 1973-2024:",sum(1 for l in res if l is not None),"/",len(res),"called; median",np.median([l for l in res if l is not None]))
print("\nfast criterion (all prior called, <=0 prior other calls, then lowest median prior lag):")
res=[]
for k in range(5,13):
    p=PK[k]; best=None
    for (ul,vl),c in cells.items():
        prior=[i for i in range(k)]
        if any(i not in c['lags'] for i in prior): continue
        if sum(1 for d in c['other'] if d<p)>0: continue
        key=(np.median([c['lags'][i] for i in prior]),)
        if best is None or key<best[0]: best=(key,(ul,vl))
    (ul,vl)=best[1]; lag=cells[(ul,vl)]['lags'].get(k); res.append(lag); print(f"{p:%Y-%m}    {ul:>7.2f}{vl:>6.2f}{('-' if lag is None else lag):>7}")
print("  causal record 1973-2024:",sum(1 for l in res if l is not None),"/",len(res),"called; median",np.median([l for l in res if l is not None]))
