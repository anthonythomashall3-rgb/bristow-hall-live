exec(open("stage20b_confirm.py").read().split("chs=[SAHM[0.35], ICmix")[0])
chsB=[SAHM[0.35], PAY, UM["um_d1_10"], HOU, IURmix]; namesB=["Sahm>=0.35","payrolls","sentiment","housing","IUR4 gap>=0.30 (first prints)"]
epsB=replay3(chsB, GATE[12], 120); resB,falseB=score_eps(epsB,T_P1)
print("v2 (claims dropped from onset) FIRST-PRINT replay: false", falseB, "onsets", [r["onset"] for r in resB], "lags", [r["lag"] for r in resB], "end", [r["end_lag"] for r in resB])
for K in [21,28]:
    print(f"confirmation H=90 K={K}:")
    for r in confirm(epsB, chsB, namesB, 90, K): print("  ", r["onset"], r["first"], "persist", r["persist_days"], "second", r["second"], "confirmed", r["confirmed"], r["confirm_day"], r["lag_days"])
# IUR first print Dec 2022 detail
print("IUR first-print 4wk gap Nov 2022-Feb 2023:", {str(k.date()):round(v,3) for k,v in g4f.loc["2022-11-15":"2023-02-15"].items()})
s4=iur4-iur4.shift(1).rolling(52).min(); print("IUR current-vintage 4wk gap same weeks:", {str(k.date()):round(v,3) for k,v in s4.loc["2022-11-10":"2023-02-10"].items()})
