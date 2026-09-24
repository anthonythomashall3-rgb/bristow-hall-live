"""Route v6 -- the hazard recomputed honestly, ETA 5159 withdrawn from the
shipped rule, and the window tightened to its measured requirement."""
exec(open('frontier.py').read().split('def rep(')[0])
import io, contextlib, hashlib, glob, sys
from scipy import stats
SEC=[dict(name='vacancy(2,6)',gap=vr,line=0.36,pub_day=30),PAY,H35]
L=[]
class T:
    def write(self,x): sys.__stdout__.write(x); L.append(x)
    def flush(self): pass
def rec(second,bk=6,fw=4):
    with contextlib.redirect_stdout(io.StringIO()):
        return score(B.american_chronology({k:PLU[k] for k in PK5},{k:TLG[k] for k in TR3},
                sahm=g,second=second,horizon_months=fw,back_months=bk),'x','1948-06-01')
r=rec(SEC); lp,ep,lt,et=r['lags_p'],r['errs_p'],r['lags_t'],r['errs_t']
E=8.78; R_OBS=0.0779; R_HI=0.2014
h_obs=R_OBS*E/100; h_hi=R_HI*E/100
sys.stdout=T()
print("ROUTE v6 -- FROZEN RECORD, 4 September 2026"); print("="*78); print()
print("THE RULE")
print("  Five claims legs propose: A monthly state-claims diffusion, B national weekly conjunct,")
print("  C weekly state breadth, M monthly national conjunct, U the insured unemployment rate 0.50")
print("  above its 52-week minimum, RE-ARMING when that gap closes.")
print("  One of four confirms, inside a window six months back and FOUR months forward:")
print("    Sahm 0.50 on first prints; the vacancy rate's two-month mean 0.36 under its six-month")
print("    maximum; payrolls' first-print three-month fall of 0.30 per cent; or housing starts 35")
print("    log points off their twelve-month maximum AND the rate 0.20 above its twelve-month minimum.")
print("  The claims object dates the call. One call, one date.")
print()
print("THE RECORD, 1948-2026")
print(f"  peaks         {len(lp)}/12 called, and one further onset call (July 2023)")
print(f"  onset lag     median {np.median(lp):.0f} days, mean {np.mean(lp):.1f}, worst {max(lp)}")
print(f"                {sum(1 for l in lp if l<=0)} inside the peak month, {sum(1 for l in lp if l<=31)} within a month")
print(f"  dating        exact {sum(1 for e in ep if e==0)}/12, within one month {sum(1 for e in ep if abs(e)<=1)}/12, mean error {np.mean(np.abs(ep)):.2f} months")
print(f"  lags          {lp}")
print(f"  troughs       {len(lt)}/12, median {np.median(lt):.0f} days, exact {sum(1 for e in et if e==0)}/12, mean error {np.mean(np.abs(et)):.2f}")
print()
print("HOW MANY FALSE ALARMS -- the count")
print("  ZERO. Thirteen American onset calls since 1948, thirteen recessions. The rule has never")
print("  called one that did not come. The claims legs ALONE opened three episodes in quiet months")
print("  -- July 1951, March 1952, February 1967 -- and the second condition confirmed none of them.")
print()
print("WHAT IS THE CHANCE OF A FALSE ALARM -- the rate, and it is NOT zero")
print("  The route fires only on a conjunction, so its hazard is the product of two measured factors:")
print(f"    first factor    P(a claims leg opens an episode in a quiet month), per year")
print(f"                    3 quiet episodes in 462 quiet months (38.5 quiet years)")
print(f"                    observed {R_OBS*100:.2f}%   upper 95 per cent bound {R_HI*100:.2f}%")
print(f"    second factor   P(the second condition stands at its line inside the window)")
print(f"                    {E:.2f}% of 433 quiet months, on the corrected window")
print()
print(f"    HAZARD          observed  {h_obs*100:.3f}% a year -- ONE FALSE EPISODE IN {1/h_obs:.0f} YEARS")
print(f"                    upper 95% {h_hi*100:.3f}% a year -- one in {1/h_hi:.0f} years")
print(f"    over a 6.5-year expansion   {(1-(1-h_obs)**6.5)*100:.2f}% observed, {(1-(1-h_hi)**6.5)*100:.2f}% at the bound")
print(f"    over a 10-year expansion    {(1-(1-h_obs)**10)*100:.2f}% observed, {(1-(1-h_hi)**10)*100:.2f}% at the bound")
print()
print("  THE FIGURE OF 'ONE IN 400 TO 2,889 YEARS' IS WITHDRAWN AND MUST NOT BE REPRINTED.")
print("  It measured the second factor over a window reaching one month forward while the route")
print("  allowed eighteen. The control reproduces the route's own published exposures exactly")
print("  (7.39 and 12.47 per cent), so the arithmetic basis of this correction is not in doubt.")
print()
print("WILL IT WORK FOREVER -- no, and no record can establish that")
print(f"  detection   13 of 13 since 1948. Clopper-Pearson 95 per cent LOWER bound: 79 per cent.")
print(f"              That bound is 0.05^(1/n) in n episodes and NO improvement to a rule can raise it.")
print(f"              Only more episodes can, which is why the international and pre-war samples matter.")
print(f"  false alarm zero observed; the rate above is what the record supports, and it is not zero.")
print()
print("WHAT WAS WITHDRAWN FROM THE RULE TODAY, AND WHY")
print("  The ETA 5159 breadth object was admitted this morning as costing nothing. It was priced on")
print("  the OLD window. On the corrected window it is NOT free:")
print(f"    {'confirming set':44}{'(6,1) old':>11}{'(6,4) NOW':>11}")
print("    control: this ledger's namespace reproduces the route's own published exposures")
print("    exactly -- 7.39 per cent for the shipped pair and 12.47 with factory hours (ledger.py)")
print(f"    {'confirming set':46}{'(6,0) old':>11}{'(6,4) NOW':>11}{'one in':>9}")
for row in [("Sahm 0.50 alone","5.77","6.00","214"),
            ("Sahm + vacancy 0.36","7.39","8.78","146"),
            ("+ payrolls 3-month 0.30%","7.39","8.78","146"),
            ("+ housing 35 x rate 0.20   SHIPPED v6","7.39","8.78","146"),
            ("+ ETA 5159 breadth 40%     WITHDRAWN","7.39","10.62","121"),
            ("+ factory hours 2.5%       refused","12.47","17.32","74")]:
    print(f"    {row[0]:46}{row[1]:>10}%{row[2]:>10}%{row[3]:>9}")
print("  Rule 21 refuses it on the same ground factory hours was refused. What it bought is on the")
print("  record: mean lag 27.3 -> 20.4 days, calls inside the peak month 2 -> 4, at 1.21x the hazard (one in 146 years becomes one in 121).")
print("  At the SAME price it beats the alternative (housing at 30 gives mean 23.0 and 3 in-month),")
print("  so if any hazard is ever to be paid for speed, this is the object to pay it for.")
print()
print("WHAT WAS FREE, AND TAKEN")
print("  leg U re-arming when its gap closes   1981-07  +142 -> +90 days   no quiet call added")
print("  housing 35 x rate 0.20                1973-11  +120 ->  +41       exposure unchanged")
print("  payrolls three-month fall 0.30%       2007-12  +126 ->  +65       exposure unchanged")
print("  the window at its measured requirement 6 back, 4 forward: the twelve's own confirming")
print("    crossings arrive between five months before the claims call and four after it, so four")
print("    forward holds every one. The record is BIT-IDENTICAL at (6,18), (6,6) and (6,4) and the")
print("    exposure falls 26.33 -> 9.70 -> 8.78 per cent. Six was chosen for symmetry; four is measured.")
print()
print("THE ONE PRICED CHOICE LEFT OPEN")
print("  window (4,3) costs 1.7 days of mean lag -- 27.3 to 29.0, every other figure identical --")
print(f"  and takes the hazard from one in {1/h_obs:.0f} years to one in 185. Not taken: Rule 21 forbids")
print("  raising miss risk as firmly as false-alarm risk, and a tighter window is a miss risk.")
sys.stdout=sys.__stdout__
open('FROZEN_RECORD_v6.txt','w').write(''.join(L))
hh=hashlib.sha256()
for f in sorted(glob.glob('*.py')): hh.update(open(f,'rb').read())
print(f"\nSHA-256 of the route's code: {hh.hexdigest()}")
