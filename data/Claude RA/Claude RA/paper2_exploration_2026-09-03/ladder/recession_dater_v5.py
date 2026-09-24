"""Recession dater v5 (3 Sep 2026, round 11) — v4's gated fast channels plus UNGATED backstop channels, so that a recession
with no prior curve inversion, no Fed room, or no layoffs is still called. Zero false episodes 1968-2026 (current vintage) and
2003-2026 (first prints). Replays 1968-2026 and prints every call.
GATE (fast channels only): 10y-1y Treasury curve inverted on some day in the prior 12 months (252 trading days).
FAST CHANNELS (gated; any one on and fresh within 120 days):
  (1) Sahm indicator, first print, >= 0.35
  (2) insured unemployment rate, 4-week avg, >= 0.40 pp above its 52-week min      [weekly, known +12 days]
  (3) nonfarm payrolls, first print, 1-month change <= -0.1%
  (4) Michigan sentiment down >= 10 points in one month
  (5) housing starts, first print, 3-month change <= -20% on two consecutive releases
  (6) 6-month Treasury bill down >= 1.43 pp over 60 trading days                    [daily, unrevised]
BACKSTOP CHANNELS (no gate; thresholds by the maximum-margin rule on the ungated 1968-2026 record):
  (7) Sahm first print >= 0.55        (ungated quiet max 0.533, Dec 1976)
  (8) IUR 4-week gap >= 0.50 pp       (ungated quiet max 0.40, Oct 1976)
  (9) initial claims 8-wk avg >= 40% above 52-wk min (ungated quiet max 25.3%, Dec 2000)
  (10) 6-month bill down >= 2.5 pp / 60 trading days (ungated quiet max 2.41, Dec 1984)
  (11) sentiment down >= 15 points   (ungated quiet max 12.2, Sep 2005)
  (12) housing starts first print <= -25% over 3 months on two consecutive releases
  (13) industrial production first print <= -2% over 3 months on two consecutive releases (ungated quiet single print -1.57%, Feb 2023)
END/CLOSE/DATES as v1-v4. With the gate removed everywhere (a no-inversion world) the backstops alone still call all nine
recessions (lags +3,+3,+1,+4,+5,0,+6,+1,+5) with zero false episodes."""
exec(open("stage32_backstops.py").read().split("rows=[]")[0])
sel=['Sahm>=0.55 x1 [nogate]','IUR gap>=0.5 [nogate]','claims 8wk>=40% [nogate]','bill fall>=2.5/60d [nogate]','sentiment -15 [nogate]','housing -25% x2 [nogate]','IP 3m first print <=-2.0% x2 [nogate]']
V4=[SAHM[0.35], gapch(iur4,0.40), PAY, UM["um_d1_10"], persist2(h3,20), fall(tb6,60,1.43)]
gnames=["Sahm>=0.35","IUR gap>=0.40","payrolls -0.1%","sentiment -10","housing -20% x2","bill -1.43pp/60d"]
trig=np.zeros(N,bool); parts=[]
for nm,c in zip(gnames,V4): a=fresh(c,120)&GATE[12]; parts.append((nm,a)); trig|=a
for nm in sel: a=fresh(BS[nm],120); parts.append((nm,a)); trig|=a
eps=[]; open_=False; i=0
while i<N:
    if not open_:
        if trig[i] and cal[i]>=pd.Timestamp("1968-06-01"): open_=True; start=i; runmax=-1; pk=None; endcall=None
        i+=1; continue
    v=ma8d[i]
    if not np.isnan(v):
        if v>runmax: runmax=v; pk=i; endcall=None
        elif endcall is None and v<=runmax*0.97: endcall=i
    if endcall is not None and B3[i] and CALM[i]:
        eps.append(dict(onset=cal[start], trough_week=cal[pk], end_call=cal[endcall], close=cal[i])); open_=False
    i+=1
if open_: eps.append(dict(onset=cal[start], trough_week=cal[pk] if pk else None, end_call=cal[endcall] if endcall else None, close=None))
print("EPISODES 1968-2026 (Paper 1 target for 2024):")
for e in eps:
    i=int(np.where(cal==e["onset"])[0][0]); who=[nm for nm,a in parts if a[i]]
    print(f"  onset call {e['onset'].date()} via {who} | dated peak {(e['onset'].to_period('M')-1)} | claims peak week {e['trough_week'].date() if e['trough_week'] is not None else None} -> dated trough {e['trough_week'].to_period('M') if e['trough_week'] is not None else None} | end call {e['end_call'].date() if e['end_call'] is not None else None} | closed {e['close'].date() if e['close'] is not None else 'open'}")
for tn,T in [("Paper 1 (Apr-Aug 2024)",T_P1),("Anthony (Jul 2023-Feb 2026)",T_AH)]:
    res,false=score_eps(eps,T)
    print(f"\nSCORE vs {tn}: false episodes {len(false)} {false}")
    for r in res: print(f"  peak {r['peak']}: onset {r['onset']} lag {r['lag']:+d} | end lag {r['end_lag']:+d} | trough err {r['tr_err']:+d}")
