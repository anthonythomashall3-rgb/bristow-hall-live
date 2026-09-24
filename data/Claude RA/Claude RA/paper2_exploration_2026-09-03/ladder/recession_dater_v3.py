"""Recession dater v3 (3 Sep 2026, round 6) — five onset channels; initial claims kept as the end channel only; clean on first prints 2003->. Replays 1968-2026 and prints every call.
GATE   : 10y-1y Treasury curve (DGS10-DGS1) was inverted on some day in the prior 12 months (252 trading days).
TRIGGER: any channel on and 'fresh' (was off on some day in the prior 120 days):
  (1) Sahm indicator, first print, >= 0.35                              [ALFRED UNRATE vintages; known on release day]
  (2) insured unemployment rate, 4-week avg, >= 0.40 pp above its 52-week min  [weekly, known +12 days; DOL first prints 2002-> reproduce every call and add no false episode]
  (3) nonfarm payrolls, first print, 1-month change <= -0.1%              [ALFRED PAYEMS vintages]
  (4) Michigan consumer sentiment down >= 10 points in one month          [monthly, known at month end; from 1978]
  (5) housing starts, first print, 3-month change <= -20% on two consecutive releases [ALFRED HOUST vintages]
  (initial claims 8-wk >= 30% dropped as an onset channel: it fired on advance prints in Aug 2022 and revisions erased it)
END    : trough = week the 8-week avg of initial claims peaks; end called when the avg has fallen 3% below it; withdrawn on a new high.
CLOSE  : end stands AND Sahm first print < 0.50 on three consecutive releases AND 4-week claims within 10% of the 52-week min.
DATES  : peak = month before the onset call; trough = month of the claims peak week.
CONFIRM (reporting layer, not a call): a stamp is confirmed when some channel has stayed on 42 consecutive days or a second channel
         fires within 90 days; otherwise the watch is killed. Stamps are unchanged by confirmation."""
exec(open("stage19b_iur.py").read().split("base=[SAHM[0.35]")[0])
IUR4=gapch(iur4,0.40)
chs={"Sahm>=0.35":SAHM[0.35], "IUR 4wk gap>=0.40pp":IUR4, "payrolls -0.1%":PAY, "sentiment -10":UM["um_d1_10"], "housing starts -20% x2":HOU}
names=list(chs); arrs=[chs[n] for n in names]
eps=replay3(arrs, GATE[12], 120)
fresh_arrs=[fresh(a,120)&GATE[12] for a in arrs]
print("EPISODES 1968-2026 (Paper 1 target for 2024):")
for e in eps:
    i=int(np.where(cal==e["onset"])[0][0]); who=[n for n,a in zip(names,fresh_arrs) if a[i]]
    print(f"  onset call {e['onset'].date()} via {who} | dated peak {(e['onset'].to_period('M')-1)} | claims peak week {e['trough_week'].date() if e['trough_week'] is not None else None} -> dated trough {e['trough_week'].to_period('M') if e['trough_week'] is not None else None} | end call {e['end_call'].date() if e['end_call'] is not None else None} | closed {e['close'].date() if e['close'] is not None else 'open'}")
for tn,T in [("Paper 1 (Apr-Aug 2024)",T_P1),("Anthony (Jul 2023-Feb 2026)",T_AH)]:
    res,false=score_eps(eps,T)
    print(f"\nSCORE vs {tn}: false episodes {len(false)} {false}")
    for r in res: print(f"  peak {r['peak']}: onset {r['onset']} lag {r['lag']:+d} | end lag {r['end_lag']:+d} | trough err {r['tr_err']:+d}")
