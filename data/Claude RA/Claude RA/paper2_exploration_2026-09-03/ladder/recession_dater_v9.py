"""Recession dater v9 (4 Sep 2026, round 21) — v8 plus one idea: no recession call without a
rise in layoffs.

THE CHANGE.  A global co-condition on every channel: an episode may open only while the 8-week
average of initial claims is at least 3 percent above its own 52-week minimum, and the ungated
no-inversion clause requires 12 percent.  One economic idea, two parameters, applied uniformly
rather than five bespoke guards.  It leaves all nine onset dates, all nine end dates, all nine
dated troughs and the single voided lane opening exactly as they were, keeps nine of nine in the
simulated world where the curve never inverts, and takes the number of quiet days on which the
machine would arm any channel from 2.97 percent of the calm record to ZERO -- not one day in the
13,810 calm days of 1968-2026.

Leave-one-out: refitting both floors on eight recessions and testing the ninth leaves every one of
the nine calls unchanged, so the floors are not fitted to any single episode; the held-out fits
consistently choose a stricter clause floor (15 percent) than the 12 percent adopted here.

GATE (fast channels only): 10y-1y Treasury curve inverted on some day in the prior 252 trading days.
GLOBAL CO-CONDITION: initial claims, 8-week average, at least 3% above its 52-week minimum.
FIVE FAST CHANNELS (gated, co-conditioned; any one on and fresh within 120 days):
  (1) Sahm indicator, first print, >= 0.36
  (2) insured unemployment rate, 4-week avg, >= 0.40 pp above its 52-week min   [weekly, known +12 days]
  (3) nonfarm payrolls, first print, 1-month change <= -0.18%
  (4) housing starts, first print, 3-month change <= -20% on two consecutive releases
  (5) 6-month Treasury bill down >= 1.45 pp over 60 trading days                [daily, unrevised]
ONE NO-INVERSION CLAUSE (fires only while the gate is NOT armed; claims floor 12%):
  (6) Sahm indicator, first print, >= 0.55
LIVE LANE (may only advance a frozen call made within the next 120 days; otherwise void and logged):
  (7) VIX, 20-trading-day change >= 22 points (1990->)
END: trough = week the 8-week average of initial claims peaks; end called when that average has
     fallen 3% below the peak; withdrawn if a new high prints.  CLOSE: end stands AND Sahm first
     print < 0.50 for three releases AND the 4-week claims average within 10% of its 52-week min.
DATES: peak = month before the onset call; trough = month of the claims-peak week.

RECORD 1968-2026 (Paper 1's Apr-Aug 2024), identical to v7, v7.1, v7.2 and v8 to the day:
  onsets 6 Oct 1969 (-2), 25 Oct 1973 (-1), 3 Jan 1980 (0), 18 Aug 1981 (+1), 3 Aug 1990 (+1),
         2 Feb 2001 (-1), 4 Jan 2008 (+1), 28 Feb 2020 (0), 3 May 2024 (+1)
  ends +1,+2,0,0,+2,+1,-1,+1,+1   troughs 0,0,0,-1,+1,0,-2,+1,0
  zero false episodes on current vintage and on first prints 2003->; one voided lane opening (9 Apr 2025)
  no-inversion simulation: nine of nine
HAZARD (extreme-value fits on the canonical quiet set): union 0.0162/yr - one in 62 years - against
  0.0282 (v8), 0.0347 (v7.2), 0.0459 (v7.1), 0.0664 (v7), 0.1239 (v6).  Detection x no false alarm
  over an average 6.5-year expansion: 78-86%."""
exec(open("stage46_v7.py").read().split('print("\\n=== (b) END')[0])
import numpy as np, pandas as pd
G=np.asarray(GATE[12],bool); NG=~G
def sd(s,lag):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
CL=np.nan_to_num(sd(r8,5),nan=-9); CO=CL>=0.03; CCO=CL>=0.12
FAST=[np.asarray(D(Srel>=0.36-1e-9),bool),np.asarray(gapch(iur4,0.40),bool),
      np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.18).values,index=pd.to_datetime(pay.rel.values))),bool),
      np.asarray(persist2(h3,20),bool),np.asarray(fall(tb6,60,1.45),bool)]
frozen=np.zeros(N,bool)
for c in FAST: frozen|=fresh(c&CO,120)&G
frozen|=fresh(np.asarray(D(Srel>=0.55-1e-9),bool)&CCO&NG,120)
la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120)
valid=la.copy(); l9=[]
for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
    if not frozen[i:i+121].any():
        j=i
        while j<N and la[j]: valid[j]=False; j+=1
        if cal[i]>=pd.Timestamp("1968-06-01"): l9.append(str(cal[i].date()))
eps=replay(frozen|valid)
print("EPISODES 1968-2026 (v9):")
for e in eps:
    print(f"  onset {e['onset'].date()} | claims peak week {e['trough_week'].date()} | end call {e['end_call'].date()} | closed {e['close'].date() if e['close'] is not None else 'open'}")
print("voided lane openings:", l9)
for tn,T_ in [("Paper 1 (Apr-Aug 2024)",T_P1),("Anthony (Jul 2023-Feb 2026)",T_AH)]:
    r,f=score_eps(eps,T_); print(f"\nSCORE vs {tn}: false {f}")
    for x in r: print(f"  peak {x['peak']}: onset {x['onset']} lag {x['lag']:+d} | end lag {x['end_lag']:+d} | trough err {x['tr_err']:+d}")
