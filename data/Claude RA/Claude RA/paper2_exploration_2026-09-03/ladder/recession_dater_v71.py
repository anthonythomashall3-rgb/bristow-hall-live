"""Recession dater v7.1 (4 Sep 2026, round 19) — v7 with the ungated bill backstop removed.

Why: round 17's extreme-value fit puts the ungated bill backstop (a 2.5 pp fall in the six-month
bill over 60 trading days, no curve gate) at 0.0215 per year — one in 46 — which is a third of v7's
whole false-alarm hazard; and round 19's foreign panel makes the ungated rate channels one of the
two largest out-of-sample offenders abroad.  Against that it buys nothing measurable: removing it
leaves all nine onsets unchanged to the day, all nine ends unchanged, zero false episodes, the same
single voided lane opening, and — in the simulated world where the curve never inverts and the five
gated fast channels are therefore silent — the backstops still call nine of nine.  (The Sahm
backstop is not removable on the same test: it alone carries April 2024 in the no-inversion world.)
Estimated union hazard falls from 0.0664 to 0.0459 per year, one in 15 years to one in 22.

GATE (fast channels only): 10y-1y Treasury curve inverted on some day in the prior 12 months (252 trading days).
FAST CHANNELS (gated; any one on and fresh within 120 days):
  (1) Sahm indicator, first print, >= 0.35
  (2) insured unemployment rate, 4-week avg, >= 0.40 pp above its 52-week min        [weekly, known +12 days]
  (3) nonfarm payrolls, first print, 1-month change <= -0.1%
  (4) housing starts, first print, 3-month change <= -20% on two consecutive releases
  (5) 6-month Treasury bill down >= 1.43 pp over 60 trading days                     [daily, unrevised]
BACKSTOPS (no gate; max-margin thresholds on the ungated record):
  (6) Sahm >= 0.55   (7) IUR gap >= 0.50 pp   (8) initial claims 8-wk >= 40% over 52-wk min
  (9) housing -25% x2   (10) industrial production first print -2% x2
LIVE LANE (may only advance a frozen call made within the next 120 days; otherwise the opening is void and logged):
  (11) VIX, 20-trading-day change >= 17.4 points (1990->)
  (12) Baa minus 10-year Treasury, rise from its 250-day low >= 1.50 pp (1987->)
END: trough = week the 8-week average of initial claims peaks; end called when that average has fallen 3% below the peak;
     withdrawn if a new high prints. CLOSE: end stands AND Sahm first print < 0.50 for three releases AND the 4-week claims
     average within 10% of its 52-week minimum. DATES: peak = month before the onset call; trough = month of the claims-peak week.
RECORD 1968-2026 (Paper 1's Apr-Aug 2024), identical to v7: onsets 6 Oct 1969 (-2), 25 Oct 1973 (-1), 3 Jan 1980 (0),
18 Aug 1981 (+1), 3 Aug 1990 (+1), 2 Feb 2001 (-1), 4 Jan 2008 (+1), 28 Feb 2020 (0), 3 May 2024 (+1);
ends +1,+2,0,0,+2,+1,-1,+1,+1; zero false episodes on current vintage and on first prints 2003->;
one voided lane opening (5 Apr 2025)."""
exec(open("stage46_v7.py").read().split('print("\\n=== (b) END')[0])
import numpy as np, pandas as pd
FAST71=[SAHM[0.35], gapch(iur4,0.40), PAY, persist2(h3,20), fall(tb6,60,1.43)]
BS71=['Sahm>=0.55 x1 [nogate]','IUR gap>=0.5 [nogate]','claims 8wk>=40% [nogate]',
      'housing -25% x2 [nogate]','IP 3m first print <=-2.0% x2 [nogate]']
t71,l71=build(FAST71,BS71)
eps=replay(t71); res,false=score_eps(eps,T_P1)
print("EPISODES 1968-2026 (v7.1):")
for e in eps:
    print(f"  onset {e['onset'].date()} | claims peak week {e['trough_week'].date()} | end call {e['end_call'].date()} | closed {e['close'].date() if e['close'] is not None else 'open'}")
print("voided lane openings:", l71)
for tn,T_ in [("Paper 1 (Apr-Aug 2024)",T_P1),("Anthony (Jul 2023-Feb 2026)",T_AH)]:
    r,f=score_eps(eps,T_); print(f"\nSCORE vs {tn}: false {f}")
    for x in r: print(f"  peak {x['peak']}: onset {x['onset']} lag {x['lag']:+d} | end lag {x['end_lag']:+d} | trough err {x['tr_err']:+d}")
