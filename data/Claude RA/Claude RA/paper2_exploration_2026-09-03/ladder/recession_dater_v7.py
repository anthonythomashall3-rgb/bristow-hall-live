"""Recession dater v7 (4 Sep 2026, round 18) — v6 with the Michigan sentiment channel removed from both layers.
Sentiment carried a third of the rule's estimated false-alarm risk (its quiet maximum was 9.2 points against a 10-point line)
and changes no call on the record: 1980 is carried by the insured-unemployment channel and 2020 by the VIX lane.

GATE (fast channels only): 10y-1y Treasury curve inverted on some day in the prior 12 months (252 trading days).
FAST CHANNELS (gated; any one on and fresh within 120 days):
  (1) Sahm indicator, first print, >= 0.35
  (2) insured unemployment rate, 4-week avg, >= 0.40 pp above its 52-week min        [weekly, known +12 days]
  (3) nonfarm payrolls, first print, 1-month change <= -0.1%
  (4) housing starts, first print, 3-month change <= -20% on two consecutive releases
  (5) 6-month Treasury bill down >= 1.43 pp over 60 trading days                     [daily, unrevised]
BACKSTOPS (no gate; max-margin thresholds on the ungated record):
  (6) Sahm >= 0.55   (7) IUR gap >= 0.50 pp   (8) initial claims 8-wk >= 40% over 52-wk min
  (9) bill fall >= 2.5 pp / 60 trading days   (10) housing -25% x2   (11) industrial production first print -2% x2
LIVE LANE (may only advance a frozen call made within the next 120 days; otherwise the opening is void and logged):
  (12) VIX, 20-trading-day change >= 17.4 points (1990->)
  (13) Baa minus 10-year Treasury, rise from its 250-day low >= 1.50 pp (1987->)
END: trough = week the 8-week average of initial claims peaks; end called when that average has fallen 3% below the peak;
     withdrawn if a new high prints. CLOSE: end stands AND Sahm first print < 0.50 for three releases AND the 4-week claims
     average within 10% of its 52-week minimum. DATES: peak = month before the onset call; trough = month of the claims-peak week.
RECORD 1968-2026 (Paper 1's Apr-Aug 2024): onsets 6 Oct 1969 (-2), 25 Oct 1973 (-1), 3 Jan 1980 (0), 18 Aug 1981 (+1),
3 Aug 1990 (+1), 2 Feb 2001 (-1), 4 Jan 2008 (+1), 28 Feb 2020 (0), 3 May 2024 (+1); ends +1,+2,0,0,+2,+1,-1,+1,+1;
zero false episodes on current vintage and on first prints 2003->; one voided lane opening (5 Apr 2025)."""
exec(open("stage46_v7.py").read().split('print("\\n=== (b) END')[0])
eps=replay(t7); res,false=score_eps(eps,T_P1)
print("EPISODES 1968-2026 (v7):")
for e in eps: print(f"  onset {e['onset'].date()} | claims peak week {e['trough_week'].date()} | end call {e['end_call'].date()} | closed {e['close'].date() if e['close'] is not None else 'open'}")
print("voided lane openings:", l7)
for tn,T_ in [("Paper 1 (Apr-Aug 2024)",T_P1),("Anthony (Jul 2023-Feb 2026)",T_AH)]:
    r,f=score_eps(eps,T_); print(f"\nSCORE vs {tn}: false {f}")
    for x in r: print(f"  peak {x['peak']}: onset {x['onset']} lag {x['lag']:+d} | end lag {x['end_lag']:+d} | trough err {x['tr_err']:+d}")
