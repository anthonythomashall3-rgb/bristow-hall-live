"""Recession dater v7.2 (4 Sep 2026, round 19) — v7 with two exposure removals, neither of which
changes a single call, an end, a trough or the voided lane opening.

(1) THE UNGATED BILL BACKSTOP IS DELETED.  Round 17's extreme-value fit prices it at 0.0215 a year
    (one in 46) — a third of v7's whole false-alarm hazard — and round 19's foreign panel makes the
    ungated rate channels one of the two worst out-of-sample offenders.  Against that it buys nothing:
    the record is identical to the day, and in the simulated world where the curve never inverts (so
    all five gated fast channels are silent) the remaining backstops still call nine of nine.

(2) THE THREE BACKSTOPS THAT DOMINATE A FAST CHANNEL FIRE ONLY WHEN THE GATE IS NOT ARMED.
    Sahm 0.55 dominates Sahm 0.35; IUR 0.50 dominates IUR 0.40; housing -25%x2 dominates -20%x2.
    Whenever the gate IS armed and a dominating backstop is on, the same series is on the looser fast
    threshold on the same day with the same freshness, so the fast channel has already fired — verified
    on every day of the record.  The restriction is therefore free by construction, and it removes those
    three channels' exposure in the 40 percent of quiet years in which the gate is armed.

GATE: 10y-1y Treasury curve inverted on some day in the prior 12 months (252 trading days).
FAST CHANNELS (gated; any one on and fresh within 120 days):
  (1) Sahm indicator, first print, >= 0.35
  (2) insured unemployment rate, 4-week avg, >= 0.40 pp above its 52-week min        [weekly, known +12 days]
  (3) nonfarm payrolls, first print, 1-month change <= -0.1%
  (4) housing starts, first print, 3-month change <= -20% on two consecutive releases
  (5) 6-month Treasury bill down >= 1.43 pp over 60 trading days                     [daily, unrevised]
NO-INVERSION CLAUSES (fire only while the gate is NOT armed):
  (6) Sahm >= 0.55   (7) IUR gap >= 0.50 pp   (8) housing -25% x2
UNGATED BACKSTOPS (no fast channel dominates these, so they run at all times):
  (9) initial claims 8-wk average >= 40% over its 52-week min
  (10) industrial production, first print, 3-month change <= -2% on two consecutive releases
LIVE LANE (may only advance a frozen call made within the next 120 days; otherwise void and logged):
  (11) VIX, 20-trading-day change >= 17.4 points (1990->)
  (12) Baa minus 10-year Treasury, rise from its 250-day low >= 1.50 pp (1987->)
END: trough = week the 8-week average of initial claims peaks; end called when that average has fallen 3%
     below the peak; withdrawn if a new high prints.  CLOSE: end stands AND Sahm first print < 0.50 for three
     releases AND the 4-week claims average within 10% of its 52-week minimum.
DATES: peak = month before the onset call; trough = month of the claims-peak week.

RECORD 1968-2026 (Paper 1's Apr-Aug 2024), identical to v7 and v7.1:
  onsets  6 Oct 1969 (-2), 25 Oct 1973 (-1), 3 Jan 1980 (0), 18 Aug 1981 (+1), 3 Aug 1990 (+1),
          2 Feb 2001 (-1), 4 Jan 2008 (+1), 28 Feb 2020 (0), 3 May 2024 (+1)
  ends    +1, +2, 0, 0, +2, +1, -1, +1, +1      troughs 0, 0, 0, -1, +1, 0, -2, +1, 0
  zero false episodes on current vintage and on first prints 2003->; one voided lane opening (5 Apr 2025)
  no-inversion simulation: nine of nine
ESTIMATED FALSE-ALARM HAZARD (round 17 extreme-value fits, gated channels conditioned on the gate's
40 percent share of quiet years): union 0.0347 a year — one in 29 — against 0.0459 for v7.1, 0.0664 for v7
and 0.1239 for v6.  Out-of-sample foreign check (round 19): 0.039-0.097 a year for the reduced structure."""
exec(open("stage46_v7.py").read().split('print("\\n=== (b) END')[0])
import numpy as np, pandas as pd
G=np.asarray(GATE[12],bool); NG=~G
FAST=[SAHM[0.35], gapch(iur4,0.40), PAY, persist2(h3,20), fall(tb6,60,1.43)]
frozen=np.zeros(N,bool)
for c in FAST: frozen|=fresh(c,120)&G
for nm,dom in [("Sahm>=0.55 x1 [nogate]",True),("IUR gap>=0.5 [nogate]",True),
               ("housing -25% x2 [nogate]",True),("claims 8wk>=40% [nogate]",False),
               ("IP 3m first print <=-2.0% x2 [nogate]",False)]:
    a=np.asarray(BS[nm],bool)
    if dom: a=a&NG
    frozen|=fresh(a,120)
la=np.zeros(N,bool)
for nm in LANE2: la|=fresh(LANE[nm],120)
valid=la.copy(); l72=[]
for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
    if not frozen[i:i+121].any():
        j=i
        while j<N and la[j]: valid[j]=False; j+=1
        if cal[i]>=pd.Timestamp("1968-06-01"): l72.append(str(cal[i].date()))
eps=replay(frozen|valid)
print("EPISODES 1968-2026 (v7.2):")
for e in eps:
    print(f"  onset {e['onset'].date()} | claims peak week {e['trough_week'].date()} | end call {e['end_call'].date()} | closed {e['close'].date() if e['close'] is not None else 'open'}")
print("voided lane openings:", l72)
for tn,T_ in [("Paper 1 (Apr-Aug 2024)",T_P1),("Anthony (Jul 2023-Feb 2026)",T_AH)]:
    r,f=score_eps(eps,T_); print(f"\nSCORE vs {tn}: false {f}")
    for x in r: print(f"  peak {x['peak']}: onset {x['onset']} lag {x['lag']:+d} | end lag {x['end_lag']:+d} | trough err {x['tr_err']:+d}")
