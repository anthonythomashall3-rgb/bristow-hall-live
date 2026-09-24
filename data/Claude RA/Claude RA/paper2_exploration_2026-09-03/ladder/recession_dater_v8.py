"""Recession dater v8 (4 Sep 2026, round 20) — v7.2 stripped to what it actually uses, then
tightened as far as the record allows without moving a single call by a single day.

WHAT CHANGED FROM v7.2, AND WHY
(1) FIVE CHANNELS DELETED.  The insured-unemployment and housing no-inversion clauses, the claims
    backstop, the industrial-production backstop and the Baa lane carry nothing: not one of the nine
    calls, and not one call in the simulated world where the curve never inverts.  Deleted jointly,
    not one at a time — the joint test is what matters and it passes.  Payrolls was kept although it
    is redundant on this record, because it is a distinct mechanism and costs almost nothing.
(2) FOUR THRESHOLDS TIGHTENED, under a day-level constraint: all nine onset dates and all nine end
    dates identical to v7.2.  Sahm 0.35 -> 0.36; payrolls -0.10% -> -0.18%; bill 1.43 -> 1.45 pp;
    VIX lane 17.4 -> 22 points.  The insured-unemployment line stays at 0.40 (0.45 costs 28 days in
    1980 and buys nothing), housing stays at 20% and the Sahm clause at 0.55 (neither has any room).
(3) FRESHNESS AND PERSISTENCE: no gain.  Shortening the 120-day window does not stop an episode
    opening at the crossing, so it cannot lower the hazard; requiring two consecutive Sahm prints
    breaks April 2024 in the no-inversion world.
(4) CONFIRMATION WITH WITHDRAWAL, TESTED AND REJECTED (see the round-20 memo).  Requiring a second
    channel on a different series before a call becomes final needs a 180-day window to confirm all
    nine, and turns the onset lags into +3,+2,+3,+3,+4,+1,+1,+1,+4 — six of nine outside a month.
    At 90 days only six of nine confirm at all.  It converts a one-month dater into a three-month one.

GATE (fast channels only): 10y-1y Treasury curve inverted on some day in the prior 252 trading days.
FIVE FAST CHANNELS (gated; any one on and fresh within 120 days):
  (1) Sahm indicator, first print, >= 0.36
  (2) insured unemployment rate, 4-week avg, >= 0.40 pp above its 52-week min   [weekly, known +12 days]
  (3) nonfarm payrolls, first print, 1-month change <= -0.18%
  (4) housing starts, first print, 3-month change <= -20% on two consecutive releases
  (5) 6-month Treasury bill down >= 1.45 pp over 60 trading days                [daily, unrevised]
ONE NO-INVERSION CLAUSE (fires only while the gate is NOT armed):
  (6) Sahm indicator, first print, >= 0.55
LIVE LANE (may only advance a frozen call made within the next 120 days; otherwise void and logged):
  (7) VIX, 20-trading-day change >= 22 points (1990->)
END: trough = week the 8-week average of initial claims peaks; end called when that average has fallen
     3% below the peak; withdrawn if a new high prints.  CLOSE: end stands AND Sahm first print < 0.50
     for three releases AND the 4-week claims average within 10% of its 52-week minimum.
DATES: peak = month before the onset call; trough = month of the claims-peak week.

RECORD 1968-2026 (Paper 1's Apr-Aug 2024), identical to v7, v7.1 and v7.2 to the day:
  onsets 6 Oct 1969 (-2), 25 Oct 1973 (-1), 3 Jan 1980 (0), 18 Aug 1981 (+1), 3 Aug 1990 (+1),
         2 Feb 2001 (-1), 4 Jan 2008 (+1), 28 Feb 2020 (0), 3 May 2024 (+1)
  ends +1,+2,0,0,+2,+1,-1,+1,+1   troughs 0,0,0,-1,+1,0,-2,+1,0
  zero false episodes on current vintage and on first prints 2003->; one voided lane opening (5 Apr 2025)
  no-inversion simulation: nine of nine
HAZARD (extreme-value fits, gated channels conditioned on the gate's 40% share of quiet years):
  union 0.0282/yr — one in 35 years — against 0.0347 (v7.2), 0.0459 (v7.1), 0.0664 (v7), 0.1239 (v6).
  Residual: Sahm clause 0.0152, housing fast 0.0071, bill fast 0.0038, Sahm fast 0.0025; the other
  three fit at zero.  Detection x no false alarm over an average 6.5-year expansion: 72-79%."""
exec(open("stage46_v7.py").read().split('print("\\n=== (b) END')[0])
import numpy as np, pandas as pd
G=np.asarray(GATE[12],bool); NG=~G
def PAYc(x): return np.asarray(D(pd.Series((pay.d1.astype(float)<=-x*100).values, index=pd.to_datetime(pay.rel.values))),bool)
FAST=[np.asarray(D(Srel>=0.36-1e-9),bool), np.asarray(gapch(iur4,0.40),bool), PAYc(0.0018),
      np.asarray(persist2(h3,20),bool), np.asarray(fall(tb6,60,1.45),bool)]
frozen=np.zeros(N,bool)
for c in FAST: frozen|=fresh(c,120)&G
frozen|=fresh(np.asarray(D(Srel>=0.55-1e-9),bool)&NG,120)
la=fresh(lane_arr(vix-vix.shift(20),1,22.0),120)
valid=la.copy(); l8=[]
for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
    if not frozen[i:i+121].any():
        j=i
        while j<N and la[j]: valid[j]=False; j+=1
        if cal[i]>=pd.Timestamp("1968-06-01"): l8.append(str(cal[i].date()))
eps=replay(frozen|valid)
print("EPISODES 1968-2026 (v8):")
for e in eps:
    print(f"  onset {e['onset'].date()} | claims peak week {e['trough_week'].date()} | end call {e['end_call'].date()} | closed {e['close'].date() if e['close'] is not None else 'open'}")
print("voided lane openings:", l8)
for tn,T_ in [("Paper 1 (Apr-Aug 2024)",T_P1),("Anthony (Jul 2023-Feb 2026)",T_AH)]:
    r,f=score_eps(eps,T_); print(f"\nSCORE vs {tn}: false {f}")
    for x in r: print(f"  peak {x['peak']}: onset {x['onset']} lag {x['lag']:+d} | end lag {x['end_lag']:+d} | trough err {x['tr_err']:+d}")
