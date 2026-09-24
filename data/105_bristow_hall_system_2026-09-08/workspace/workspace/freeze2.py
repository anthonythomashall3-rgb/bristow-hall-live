exec(open('third.py').read().split('V=[dict(name=')[0])
import numpy as np, io, contextlib
V=[dict(name='vacancy(2,6)',gap=vr,line=0.36,pub_day=30)]
SECOND=V+[dict(name='payroll3',gap=P3,line=0.3,pub_day=5)]
with contextlib.redirect_stdout(io.StringIO()):
    r=score(B.american_chronology({k:PLU[k] for k in ('A','B','C','M','U')},
            {k:TLG[k] for k in ('K','J','H')}, sahm=g, second=SECOND),'x','1948-06-01')
lp,ep,lt,et=r['lags_p'],r['errs_p'],r['lags_t'],r['errs_t']
print("ROUTE v2 — the shipped pair plus payrolls, three-month fall >= 0.3 per cent on first prints")
print(f"  peaks   {len(lp)}/12 called, other onset calls {r['other']}")
print(f"          lag median {np.median(lp):.0f} d, mean {np.mean(lp):.1f}, worst {max(lp)}, inside the peak month {sum(1 for l in lp if l<=0)}, within a month {sum(1 for l in lp if l<=31)}")
print(f"          dates exact {sum(1 for e in ep if e==0)}/12, within one {sum(1 for e in ep if abs(e)<=1)}/12, mean error {np.mean(np.abs(ep)):.2f}")
print(f"  troughs {len(lt)}/12 closed, lag median {np.median(lt):.0f} d, worst {max(lt)}")
print(f"          dates exact {sum(1 for e in et if e==0)}/12, within one {sum(1 for e in et if abs(e)<=1)}/12, mean error {np.mean(np.abs(et)):.2f}")
print(f"  onset lags {lp}")
print(f"  peak date errors {ep}")
print(f"  trough date errors {et}")
