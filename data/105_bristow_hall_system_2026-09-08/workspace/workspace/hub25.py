"""THE 2024 CEILING, PRICED. In 2024 the only demand object above its line was the vacancy, so the hub - the Sahm gap
proposing and the vacancy confirming - is the only route. The hub's speed is therefore set by the month the Sahm gap
crosses its line. Every line from 0.43 down is run here, with every other call it makes printed in full."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('hub25.out','w')"))
P(f"{'hub line':>9s}  onsets 1948..2024                                              others")
for sl in [0.37,0.3667,0.366,0.36,0.355,0.35]:
    p=dict(BASE); p['deep']=999; p['wline']=0.30; p['wline2']=0.50; p['bshare']=0.50; p['sahm']=sl
    r,t=build9(p); lp=[r['lags_p'].get(i) for i in range(13)]
    P(f"{sl:9.2f}  {lp}  {[(d,lg) for d,_,lg in r['other']]}")
out.close()
