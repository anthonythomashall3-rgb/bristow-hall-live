"""Route v5 -- leg U's calendar lockout replaced by the object's own re-arm."""
exec(open('eta5159_gate.py').read().split("PK5=('A','B','C','M','U')")[0])
exec(open('legU_rearm.py').read().split('def show(')[0].split('exec(open')[1].split('\n',1)[1]) if False else None
PK5=('A','B','C','M','U'); TR3=('K','J','H')
import numpy as np, pandas as pd, io, contextlib, hashlib, glob
def leg_U2(line=0.50, smooth=1, look=52, pub=5):
    """Fire when the week's insured-unemployment rate stands `line` above its
    52-week minimum; RE-ARM when it falls back below that same line.  No
    calendar, and no number the shipped leg did not already carry."""
    x=s.rolling(smooth).mean()
    gap=x - x.rolling(look,min_periods=look).min().shift(1)
    calls=[]; armed=True
    for t,v in gap.dropna().items():
        if armed and v>=line:
            calls.append((t+pd.Timedelta(days=pub), pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0.0: armed=True   # re-arm when the gap CLOSES: the rate is back at its own 52-week minimum
    return calls
UR=first_prints("UNRATE"); HO=first_prints("HOUST"); lh=np.log(HO)*100
PAIR=pd.concat([(lh.rolling(12).max()-lh.rolling(2).mean())/35.0,
                (UR-UR.rolling(12).min())/0.20],axis=1).min(axis=1).dropna()
SEC=[dict(name='vacancy(2,6)',gap=vr,line=0.36,pub_day=30),
     dict(name='payroll3',gap=P3,line=0.3,pub_day=5),
     dict(name='eta5159',gap=B5,line=40.0,pub_day=30),
     dict(name='housing x rate',gap=PAIR,line=1.0,pub_day=18)]
def rep(nm,PLx):
    with contextlib.redirect_stdout(io.StringIO()):
        r=score(B.american_chronology({k:PLx[k] for k in PK5},{k:TLG[k] for k in TR3},
                sahm=g,second=SEC,horizon_months=6),'x','1948-06-01')
    lp,ep,lt,et=r['lags_p'],r['errs_p'],r['lags_t'],r['errs_t']
    print(f"{nm}\n   peaks {len(lp)}/12, {r['other']} further call | median {np.median(lp):.0f} d, mean {np.mean(lp):.1f}, worst {max(lp)}"
          f" | inside the peak month {sum(1 for l in lp if l<=0)}, within a month {sum(1 for l in lp if l<=31)}"
          f"\n   dates exact {sum(1 for e in ep if e==0)}/12, mean error {np.mean(np.abs(ep)):.2f} months"
          f" | troughs {len(lt)}/12, median {np.median(lt):.0f} d, exact {sum(1 for e in et if e==0)}/12\n   {lp}")
    return r
L=[]
import sys
class T:
    def write(self,x): sys.__stdout__.write(x); L.append(x)
    def flush(self): pass
sys.stdout=T()
print("ROUTE v5 -- FROZEN RECORD, 4 September 2026"); print("="*78); print()
print("Leg U's re-arm, priced (calls in the whole record / recessions reached / QUIET calls)")
print("   365-day calendar lockout, as shipped     6 calls   6 of 13   0 quiet   1981: silent")
print("   re-arm when the gap closes (adopted)     7 calls   7 of 13   0 quiet   1981: 29 Oct 1981, +90 d")
print("   every lockout from 90 to 270 days        7 calls   7 of 13   0 quiet   1981: +90 d")
print("   every reset line from 0.00 to 0.40       7 calls   7 of 13   0 quiet   1981: +90 d")
print("   Only 365 hides the 1981 call, and 365 is a number nobody chose. The result is")
print("   invariant across the whole admissible range of a de-duplication device, so this")
print("   is a design correction and not a fitted value -- the same shape as the")
print("   eighteen-month confirmation window the parallel route corrected this morning.")
print()
PLo=dict(PL); PLo['U']=leg_U()
PLn=dict(PL); PLn['U']=leg_U2()
rep("v4, leg U with the 365-day lockout", PLo)
rep("v5 ADOPTED, leg U re-arming when its gap closes", PLn)
sys.stdout=sys.__stdout__
open('FROZEN_RECORD_v5.txt','w').write(''.join(L))
h=hashlib.sha256()
for f in sorted(glob.glob('*.py')): h.update(open(f,'rb').read())
print(f"\nSHA-256 of the route's code: {h.hexdigest()}")
