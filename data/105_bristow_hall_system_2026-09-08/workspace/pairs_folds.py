"""Are the pair lines identified, or a knife edge? The v44 standard: where the
optimum is flat the folds share no argmax, so the test is whether a setting
exists that EVERY fold accepts."""
exec(open('frontier.py').read().split('def rep(')[0])
import io, contextlib, numpy as np
AWH=first_prints('AWHMAN'); ND=first_prints('NDMANEMP'); MN=first_prints('MANEMP')
f12=lambda v,l:(v.rolling(12).max()/v-1)*100/l
f3 =lambda v,l:(-(v/v.shift(3)-1)*100)/l
PR =lambda a,b: pd.concat([a,b],axis=1).min(axis=1).dropna()
SEC=[dict(name='vacancy',gap=vr,line=0.36,pub_day=30),PAY,H35]
def run(x1,y1,x2,y2):
    e=[dict(name='p1',gap=PR(f12(AWH,x1),f3(ND,y1)),line=1.0,pub_day=5),
       dict(name='p2',gap=PR(f12(AWH,x2),f3(MN,y2)),line=1.0,pub_day=5)]
    with contextlib.redirect_stdout(io.StringIO()):
        r=score(B.american_chronology({k:PLU[k] for k in PK5},{k:TLG[k] for k in TR3},
                sahm=g,second=SEC+e,horizon_months=4,back_months=6),'x','1948-06-01')
    return r
print("how wide is the plateau? vary each of the four lines around the shipped point")
base=(1.995,1.2801,2.9033,1.2635)
print(f"{'which line':22}{'value':>8}{'peaks':>7}{'other':>6}{'mean':>7}   lags")
for i,(nm,grid) in enumerate([('hours (1980 pair)',[1.6,1.8,1.995,2.2,2.5,2.8]),
                              ('nondurable emp',[1.0,1.15,1.2801,1.4,1.6]),
                              ('hours (2001 pair)',[2.4,2.7,2.9033,3.1,3.4]),
                              ('factory emp',[1.0,1.15,1.2635,1.4,1.6])]):
    for v in grid:
        a=list(base); a[i]=v; r=run(*a); lp=r['lags_p']
        ok='' if (len(lp)==12 and r['other']<=1) else '  BREAKS'
        print(f"{nm:22}{v:8.3f}{len(lp):7d}{r['other']:6d}{np.mean(lp):7.1f}{ok}")
