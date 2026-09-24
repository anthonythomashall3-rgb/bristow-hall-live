exec(open('frontier.py').read().split('def rep(')[0])
import io, contextlib, numpy as np
AWH=first_prints('AWHMAN'); ND=first_prints('NDMANEMP'); MN=first_prints('MANEMP')
f12=lambda v,l:(v.rolling(12).max()/v-1)*100/l
f3 =lambda v,l:(-(v/v.shift(3)-1)*100)/l
PR =lambda a,b: pd.concat([a,b],axis=1).min(axis=1).dropna()
SEC=[dict(name='vacancy',gap=vr,line=0.36,pub_day=30),PAY,H35]
def run(extra):
    with contextlib.redirect_stdout(io.StringIO()):
        return score(B.american_chronology({k:PLU[k] for k in PK5},{k:TLG[k] for k in TR3},
                sahm=g,second=SEC+extra,horizon_months=4,back_months=6),'x','1948-06-01')
for tag,V2,lab in [('1980 pair: hours x NONDURABLE employment',ND,'nondur'),
                   ('2001 pair: hours x FACTORY employment',MN,'factory')]:
    print(f"\n{tag}   (each cell: peaks/other, mean lag)")
    ys=[0.9,1.0,1.1,1.2,1.3,1.4,1.5,1.6]
    print("hours/emp".rjust(10) + ''.join(f"{y:>12.2f}" for y in ys))
    for x in [1.4,1.6,1.8,2.0,2.2,2.6,3.0]:
        row=f"{x:10.2f}"
        for y in ys:
            r=run([dict(name='p',gap=PR(f12(AWH,x),f3(V2,y)),line=1.0,pub_day=5)])
            lp=r['lags_p']
            row+=f"{str(len(lp))+'/'+str(r['other'])+' '+f'{np.mean(lp):.1f}':>12}"
        print(row)
