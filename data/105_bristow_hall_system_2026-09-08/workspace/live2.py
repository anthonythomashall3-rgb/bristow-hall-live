"""WHAT THE TOOL IS SAYING NOW, AND WHAT THE FASTER LINE WOULD HAVE SAID. The Sahm gap, the vacancy and the two new
objects from mid-2025 to the latest month on the file, with the calls each line would have made."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('live2.out','w')"))
G=vgap2(4,4); Hc,MX=mkpair3(29,4,3,18); SV=(SI-SI.rolling(52,min_periods=52).min().shift(1))
P(f"{'month':8s} {'Sahm gap':>9s} {'vacancy':>8s} {'survey wk':>10s} {'breadth':>8s} {'housing':>8s} {'spread':>8s}")
for m in pd.date_range('2025-06-01','2026-08-01',freq='MS'):
    br=BR[(BR.index>=m)&(BR.index<m+pd.DateOffset(months=1))]; sp=GSP[(GSP.index>=m)&(GSP.index<m+pd.DateOffset(months=1))]
    P(f"{m:%Y-%m}  {g.get(m,float('nan')):9.3f} {G.get(m,float('nan')):8.3f} {SV.get(m,float('nan')):10.3f} {(br.max() if len(br) else float('nan')):8.2f} {Hc['gap'].get(m,float('nan')):8.3f} {(sp.max() if len(sp) else float('nan')):8.3f}")
for sl,nm in [(0.43,'the shipped line 0.43'),(0.36,'the faster line 0.36')]:
    p=dict(BASE); p['deep']=999; p['wline']=0.30; p['wline2']=0.60; p['bshare']=0.50; p['sahm']=sl
    r,t=build9(p)
    late=[x for x in t if x['published']>=pd.Timestamp('2024-01-01')]
    P(f"\n{nm}: "+" | ".join(f"{x['published']:%Y-%m-%d} {x['kind']} dated {x['date']:%Y-%m} by {x['leg']}" for x in late))
out.close()
