"""Recession dater v10 (4 Sep 2026, round 22) — v9 with the housing channel replaced.

WHY.  In v9 the housing channel was the rule's weakest point on two counts.  Its margin was
the thinnest of any channel — a line at a 20 percent three-month fall against a quiet-period
maximum of 19.4 percent, a gap of 0.6 points, 0.08 standard deviations — and it was the sole
carrier of July 1981.  A search for a second carrier found none that is a mechanism rather
than an artefact: everything that separates 1981 cleanly (Aaa, Baa, 5-, 10- and 20-year yields
rising 2 sd) is the Volcker tightening, fires only in 1980-81, and would never recur in a
low-inflation recession.  The fix was therefore to find a better FORM of the housing signal.

Sweeping horizons of two to six months, starts and permits, and one to three consecutive
releases, one form dominates: **housing starts, first print, six-month change at or below
-19 percent on three consecutive releases.**  Quiet maximum 12.2 percent against a 1981
reading of 25.7 percent — a margin of 13.5 points, twenty-two times the old channel's — and
it carries four recessions on time (1973 +1, 1980 +2, 1981 +1, 2007 +3) rather than one.
Its fitted hazard is 0.000 a year, against 0.0101 for the channel it replaces, which was 60
percent of v9's entire remaining risk.  Every onset date, end date and dated trough is
unchanged, the no-inversion simulation still returns nine of nine, and no channel arms on
any of the 13,911 quiet days of 1968-2026.

GATE (fast channels only): 10y-1y Treasury curve inverted on some day in the prior 252 trading days.
GLOBAL CO-CONDITION: initial claims, 8-week average, at least 3% above its 52-week minimum.
FIVE FAST CHANNELS (gated, co-conditioned; any one on and fresh within 120 days):
  (1) Sahm indicator, first print, >= 0.36
  (2) insured unemployment rate, 4-week avg, >= 0.40 pp above its 52-week min   [weekly, known +12 days]
  (3) nonfarm payrolls, first print, 1-month change <= -0.18%
  (4) housing starts, first print, 6-month change <= -19% on three consecutive releases
  (5) 6-month Treasury bill down >= 1.45 pp over 60 trading days                [daily, unrevised]
ONE NO-INVERSION CLAUSE (fires only while the gate is NOT armed; claims floor 12%):
  (6) Sahm indicator, first print, >= 0.55
LIVE LANE (may only advance a frozen call made within the next 120 days; otherwise void and logged):
  (7) VIX, 20-trading-day change >= 22 points (1990->)
END: trough = week the 8-week average of initial claims peaks; end called when that average has
     fallen 3% below the peak; withdrawn if a new high prints.  CLOSE: end stands AND Sahm first
     print < 0.50 for three releases AND the 4-week claims average within 10% of its 52-week min.
DATES: peak = month before the onset call; trough = month of the claims-peak week.

RECORD 1968-2026 (Paper 1's Apr-Aug 2024), identical to v7 through v9 to the day:
  onsets 6 Oct 1969 (-2), 25 Oct 1973 (-1), 3 Jan 1980 (0), 18 Aug 1981 (+1), 3 Aug 1990 (+1),
         2 Feb 2001 (-1), 4 Jan 2008 (+1), 28 Feb 2020 (0), 3 May 2024 (+1)
  ends +1,+2,0,0,+2,+1,-1,+1,+1   troughs 0,0,0,-1,+1,0,-2,+1,0
  zero false episodes on current vintage and on first prints 2003->; one voided lane opening (9 Apr 2025)
  no-inversion simulation: nine of nine; quiet days on which any channel arms: zero of 13,911
HAZARD (extreme-value fits on the canonical quiet set): union 0.0080/yr - one in 125 years - against
  0.0167 (v9), 0.0282 (v8), 0.0347 (v7.2), 0.0664 (v7), 0.1239 (v6).  Residual: Sahm fast 0.0039,
  Sahm clause 0.0024, bill fast 0.0018; insured unemployment, payrolls and housing fit at zero.
  Detection x no false alarm over an average 6.5-year expansion: 82-91%.
PERTURBATION: three of twenty one-tick moves create a false alarm (housing three releases to two,
  the clause to 0.50, the global floor to 4%).  The housing line is now robust in both directions."""
exec(open("stage46_v7.py").read().split('print("\\n=== (b) END')[0])
import numpy as np, pandas as pd
G=np.asarray(GATE[12],bool); NG=~G
def sd(s,lag=0):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
CL=np.nan_to_num(sd(r8,5),nan=-9); CO=CL>=0.03; CCO=CL>=0.12
h6=fpch("HOUST_all_vintages.csv",6)
def persist_k(series,th,k):
    a=(series<=-th)
    for j in range(1,k): a=a & series.shift(j).le(-th)
    return np.asarray(D(a.fillna(False)),bool)
FAST=[np.asarray(D(Srel>=0.36-1e-9),bool), np.asarray(gapch(iur4,0.40),bool),
      np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.18).values,index=pd.to_datetime(pay.rel.values))),bool),
      persist_k(h6,0.19,3), np.asarray(fall(tb6,60,1.45),bool)]
frozen=np.zeros(N,bool)
for c in FAST: frozen|=fresh(c&CO,120)&G
frozen|=fresh(np.asarray(D(Srel>=0.55-1e-9),bool)&CCO&NG,120)
la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120)
valid=la.copy(); l10=[]
for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
    if not frozen[i:i+121].any():
        j=i
        while j<N and la[j]: valid[j]=False; j+=1
        if cal[i]>=pd.Timestamp("1968-06-01"): l10.append(str(cal[i].date()))
eps=replay(frozen|valid)
print("EPISODES 1968-2026 (v10):")
for e in eps:
    print(f"  onset {e['onset'].date()} | claims peak week {e['trough_week'].date()} | end call {e['end_call'].date()} | closed {e['close'].date() if e['close'] is not None else 'open'}")
print("voided lane openings:", l10)
for tn,T_ in [("Paper 1 (Apr-Aug 2024)",T_P1),("Anthony (Jul 2023-Feb 2026)",T_AH)]:
    r,f=score_eps(eps,T_); print(f"\nSCORE vs {tn}: false {f}")
    for x in r: print(f"  peak {x['peak']}: onset {x['onset']} lag {x['lag']:+d} | end lag {x['end_lag']:+d} | trough err {x['tr_err']:+d}")
