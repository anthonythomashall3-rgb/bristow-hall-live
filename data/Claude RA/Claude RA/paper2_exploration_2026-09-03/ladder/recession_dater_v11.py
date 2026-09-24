"""Recession dater v11 (4 Sep 2026, round 24) — v10 with the claims floor made revision-proof.

THE DEFECT FOUND.  Round 21 added a global co-condition: an episode may open only while the
8-week average of initial claims is at least 3 percent above its 52-week minimum.  It was
verified on the settled claims series.  Weekly claims are not settled: measured against
ALFRED's own first prints (901 weeks, 2009-2026) the initial print differs from the final
value by more than 1 percent in 63 percent of weeks, by up to 29 percent, and the floor's
own verdict flips in 18 percent of weeks at the 3 percent line.  Resampling that revision
distribution across the whole claims history, v10's record survives in only 44 percent of
draws and a spurious episode appears in 43 percent.  The floor as written was reading one
revisable weekly number on one day.

THE FIX.  Read it the way the rest of the rule already reads everything else -- as a
condition met *within a window* rather than on a single day:

  the fast channels' floor is met if the 8-week claims average has been at least 3 percent
  above its 52-week minimum AT ANY POINT IN THE PRIOR EIGHT WEEKS.

The no-inversion clause keeps its same-day 12 percent floor; it is ungated and never sits
near its line, so it needed no widening, and widening it only costs hazard.  Sweeping both
windows jointly, eight weeks for the fast channels and one for the clause dominates every
other pair on both measures at once.

  floor windows        record   fitted hazard   false episodes under revision noise (150 draws)
  fast  1 / clause  1  ok       1 in 136 yr     68  (45%)      <- v10
  fast  8 / clause  8  ok       1 in  58 yr      0  ( 0%)
  fast  8 / clause  1  ok       1 in  95 yr      0  ( 0%)      <- v11

v10's headline of one false alarm in 125 years was measured on data assumed exact.  Priced
against the revisions that actually occur, it was one in a few years.  v11's one in 95 is a
smaller nominal number that survives contact with the data.

GATE (fast channels only): 10y-1y Treasury curve inverted on some day in the prior 252 trading days.
GLOBAL CO-CONDITION: the 8-week average of initial claims has been at least 3% above its
  52-week minimum at some point in the prior eight weeks.
FIVE FAST CHANNELS (gated, co-conditioned; any one on and fresh within 120 days):
  (1) Sahm indicator, first print, >= 0.36
  (2) insured unemployment rate, 4-week avg, >= 0.40 pp above its 52-week min   [weekly, known +12 days]
  (3) nonfarm payrolls, first print, 1-month change <= -0.18%
  (4) housing starts, first print, 6-month change <= -19% on three consecutive releases
  (5) 6-month Treasury bill down >= 1.45 pp over 60 trading days                [daily, unrevised]
ONE NO-INVERSION CLAUSE (fires only while the gate is NOT armed; same-day claims floor 12%):
  (6) Sahm indicator, first print, >= 0.55
LIVE LANE (may only advance a frozen call made within the next 120 days; otherwise void and logged):
  (7) VIX, 20-trading-day change >= 22 points (1990->)
END: trough = week the 8-week average of initial claims peaks; end called when that average has
     fallen 3% below the peak; withdrawn if a new high prints.  CLOSE: end stands AND Sahm first
     print < 0.50 for three releases AND the 4-week claims average within 10% of its 52-week min.
DATES: peak = month before the onset call; trough = month of the claims-peak week.

RECORD 1968-2026 (Paper 1's Apr-Aug 2024), identical to v7 through v10 to the day:
  onsets 6 Oct 1969 (-2), 25 Oct 1973 (-1), 3 Jan 1980 (0), 18 Aug 1981 (+1), 3 Aug 1990 (+1),
         2 Feb 2001 (-1), 4 Jan 2008 (+1), 28 Feb 2020 (0), 3 May 2024 (+1)
  ends +1,+2,0,0,+2,+1,-1,+1,+1   troughs 0,0,0,-1,+1,0,-2,+1,0
  zero false episodes; one voided lane opening (9 Apr 2025); no-inversion simulation nine of nine;
  zero armed days in the 13,911 quiet days of 1968-2026.
KNOWN AND DISCLOSED: the END rule reads the week the claims average peaks, and that week does move
  with revisions -- under the same resampled noise the end dates shift by a median of zero days but
  with a 10th-90th range of -31 to +70 days in the two worst episodes (1970 and 2024).  The onsets
  are revision-stable; the ends are not, and no smoothing of the peak fixes that without delaying
  every end call."""
exec(open("stage46_v7.py").read().split('print("\\n=== (b) END')[0])
import numpy as np, pandas as pd
G=np.asarray(GATE[12],bool); NG=~G
def sd(s,lag=0):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
m8=ic.rolling(8).mean(); rr=(m8/m8.shift(1).rolling(52).min()-1)
CLx=np.nan_to_num(sd(rr,5),nan=-9)
CO=pd.Series(CLx>=0.03).rolling(8*7,min_periods=1).max().fillna(0).astype(bool).values
CCO=CLx>=0.12
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
valid=la.copy(); l11=[]
for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
    if not frozen[i:i+121].any():
        j=i
        while j<N and la[j]: valid[j]=False; j+=1
        if cal[i]>=pd.Timestamp("1968-06-01"): l11.append(str(cal[i].date()))
eps=replay(frozen|valid)
print("EPISODES 1968-2026 (v11):")
for e in eps:
    print(f"  onset {e['onset'].date()} | claims peak week {e['trough_week'].date()} | end call {e['end_call'].date()} | closed {e['close'].date() if e['close'] is not None else 'open'}")
print("voided lane openings:", l11)
for tn,T_ in [("Paper 1 (Apr-Aug 2024)",T_P1),("Anthony (Jul 2023-Feb 2026)",T_AH)]:
    r,f=score_eps(eps,T_); print(f"\nSCORE vs {tn}: false {f}")
    for x in r: print(f"  peak {x['peak']}: onset {x['onset']} lag {x['lag']:+d} | end lag {x['end_lag']:+d} | trough err {x['tr_err']:+d}")
