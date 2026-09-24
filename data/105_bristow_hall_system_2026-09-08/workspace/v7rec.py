exec(open('frontier.py').read().split('def rep(')[0])
import io, contextlib, numpy as np
AWH=first_prints('AWHMAN'); ND=first_prints('NDMANEMP')
f12=lambda v,l:(v.rolling(12).max()/v-1)*100/l
f3 =lambda v,l:(-(v/v.shift(3)-1)*100)/l
P1=pd.concat([f12(AWH,2.0),f3(ND,1.20)],axis=1).min(axis=1).dropna()
SEC=[dict(name='vacancy',gap=vr,line=0.36,pub_day=30),PAY,H35]
for nm,ex in [("v6 shipped",[]),("v7 + the pair",[dict(name='hoursXnondur',gap=P1,line=1.0,pub_day=5)])]:
    with contextlib.redirect_stdout(io.StringIO()):
        r=score(B.american_chronology({k:PLU[k] for k in PK5},{k:TLG[k] for k in TR3},
                sahm=g,second=SEC+ex,horizon_months=4,back_months=6),'x','1948-06-01')
    lp,ep,lt,et=r['lags_p'],r['errs_p'],r['lags_t'],r['errs_t']
    print(f"{nm:16} peaks {len(lp)}/12 other {r['other']} | median {np.median(lp):.0f}d mean {np.mean(lp):.1f} worst {max(lp)}"
          f" | in-month {sum(1 for l in lp if l<=0)} | dates exact {sum(1 for e in ep if e==0)} mae {np.mean(np.abs(ep)):.2f}"
          f" | troughs {len(lt)}/12 median {np.median(lt):.0f}d\n    {lp}")
