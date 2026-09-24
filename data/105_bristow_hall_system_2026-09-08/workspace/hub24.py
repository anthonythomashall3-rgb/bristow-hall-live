"""THE 2024 CEILING, PRICED. In 2024 the only demand object above its line was the vacancy, so the hub - the Sahm gap
proposing and the vacancy confirming - is the only route. The hub's speed is therefore set by the month the Sahm gap
crosses its line. Every line from 0.43 down is run here, with every other call it makes printed in full."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('hub24.out','w')"))
P(f"{'hub line':>9s}  onsets 1948..2024                                              others")
for sl in [0.50,0.45,0.43,0.40,0.37,0.35,0.33,0.30]:
    p=dict(BASE); p['deep']=999; p['wline']=0.30; p['wline2']=0.60; p['bshare']=0.50; p['sahm']=sl
    r,t=build9(p); lp=[r['lags_p'].get(i) for i in range(13)]
    P(f"{sl:9.2f}  {lp}  {[(d,lg) for d,_,lg in r['other']]}")
P("\nthe Sahm gap month by month through the 2024 turn, and the report that would have carried it:")
for m in pd.date_range('2024-01-01','2024-08-01',freq='MS'):
    pub=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
    P(f"   {m:%Y-%m}  gap {g.get(m,float('nan')):.3f}  published {pub:%Y-%m-%d}  ({(pub-me(PK[12])).days:+d} days from the peak month end)")
out.close()
