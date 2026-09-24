"""Recession dater v6 (4 Sep 2026, round 15) — v5 (six gated fast channels + seven ungated backstops) plus a LIVE LANE of
short-history, real-time, unrevised channels that may only ADVANCE a call the frozen channels make within the next 120 days:
  L1  VIX, 20-trading-day change >= 17.4 points (1990->; threshold = max-margin midpoint: quiet max 15.6 on 2007-08-17)
  L2  Baa minus 10-year Treasury, rise from its 250-day minimum >= 1.50 pp (1987->; quiet max 1.35 on 2000-12-23)
A lane opening with no frozen trigger inside 120 days is void and logged (on the record: 2025-04-05, VIX, voided).
Lane candidates NOT admitted (histories back-filled, not real-time): OFR FSI and components (2000->), NFCI (1971->).
Record 1968-2026: onsets Oct 6 1969 (-2), Oct 25 1973 (-1), Jan 3 1980 (0), Aug 18 1981 (+1), Aug 3 1990 (+1), Feb 2 2001 (-1),
Jan 4 2008 (+1), Feb 28 2020 (0), May 3 2024 (+1); zero false episodes (current vintage and first prints 2003->)."""
exec(open("stage38_v6.py").read().split("T={pk:(P(pk)+1)")[0])
eps,lfa=run(["VIX 20d change>=17.4 (1990->)","Baa-10y rise from 250d min>=1.5 (1987->)"])
print("EPISODES 1968-2026 (v6, real-time lane):")
for e in eps: print(f"  onset {e['onset'].date()} | claims peak week {e['trough_week'].date() if e['trough_week'] is not None else None} | end call {e['end_call'].date() if e['end_call'] is not None else None} | closed {e['close'].date() if e['close'] is not None else 'open'}")
print("voided lane openings:", lfa)
for tn,T_ in [("Paper 1 (Apr-Aug 2024)",T_P1),("Anthony (Jul 2023-Feb 2026)",T_AH)]:
    res,false=score_eps(eps,T_); print(f"SCORE vs {tn}: false {false}")
    for r in res: print(f"  peak {r['peak']}: onset {r['onset']} lag {r['lag']:+d} | end lag {r['end_lag']:+d} | trough err {r['tr_err']:+d}")
