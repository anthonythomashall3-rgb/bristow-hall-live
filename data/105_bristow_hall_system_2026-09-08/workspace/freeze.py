exec(open('legU.py').read().split('U=leg_U()')[0])
U=leg_U(); PLU=dict(PL); PLU['U']=U
import numpy as np, hashlib, json
CFG=dict(peak_legs=['A','B','C','M','U'], trough_legs=['K','J','H'],
         second=['Sahm 0.50 first prints','vacancy (2,6) 0.36 first prints'])
r=run({k:PLU[k] for k in CFG['peak_legs']},{k:TLG[k] for k in CFG['trough_legs']})
lp,ep,lt,et=r['lags_p'],r['errs_p'],r['lags_t'],r['errs_t']
print("FROZEN CONFIGURATION — peak legs A,B,C,M,U | trough legs K,J,H | second condition Sahm 0.50 OR vacancy(2,6) 0.36")
print(f"  peaks   {len(lp)}/12 called, other onset calls {r['other']}")
print(f"          lag median {np.median(lp):.0f} d, worst {max(lp)}, inside the peak month {sum(1 for l in lp if l<=0)}, within a month {sum(1 for l in lp if l<=31)}")
print(f"          dates exact {sum(1 for e in ep if e==0)}/12, within one month {sum(1 for e in ep if abs(e)<=1)}/12, mean error {np.mean(np.abs(ep)):.2f}")
print(f"  troughs {len(lt)}/12 closed")
print(f"          lag median {np.median(lt):.0f} d, worst {max(lt)}, within a month {sum(1 for l in lt if l<=31)}")
print(f"          dates exact {sum(1 for e in et if e==0)}/12, within one month {sum(1 for e in et if abs(e)<=1)}/12, mean error {np.mean(np.abs(et)):.2f}")
print(f"  onset lags {lp}")
print(f"  peak date errors {ep}")
print(f"  trough date errors {et}")
print(f"  leg U calls ({len(U)}): " + ', '.join(f'{p:%Y-%m-%d}>{d:%Y-%m}' for p,d in U))
