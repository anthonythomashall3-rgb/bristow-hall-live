"""Stage 21d: onset variants for the +-1 target (no early calls beyond one month, no false alarms)."""
exec(open("stage19b_iur.py").read().split("base=[SAHM[0.35]")[0])
s35=(Srel>=0.35-1e-9); S2=D(pd.Series((s35&s35.shift(1).fillna(False)).values, index=s35.index))   # two consecutive prints >=0.35
s40=(Srel>=0.40-1e-9); S2_40=D(pd.Series((s40&s40.shift(1).fillna(False)).values, index=s40.index))
SR=D(pd.Series(((Srel>=0.35-1e-9)&(Srel>Srel.shift(1))).values, index=Srel.index))  # >=0.35 and rising
print("Sahm first prints 1969-70:", {str(k.date()):round(v,2) for k,v in Srel.loc["1969-08":"1970-03"].items()})
print("Sahm first prints 2007-08:", {str(k.date()):round(v,2) for k,v in Srel.loc["2007-11":"2008-05"].items()})
print("Sahm first prints 2024:", {str(k.date()):round(v,2) for k,v in Srel.loc["2024-04":"2024-10"].items()})
cands={
 "v2: Sahm35 + IUR30": [SAHM[0.35], IUR4:=gapch(iur4,0.30), IC["ic8_30_k1"], PAY, UM["um_d1_10"], HOU],
 "Sahm35 + IUR35": [SAHM[0.35], gapch(iur4,0.35), IC["ic8_30_k1"], PAY, UM["um_d1_10"], HOU],
 "Sahm35x2 + IUR35": [S2, gapch(iur4,0.35), IC["ic8_30_k1"], PAY, UM["um_d1_10"], HOU],
 "Sahm35x2 + IUR30k2": [S2, gapch(iur4,0.30,2), IC["ic8_30_k1"], PAY, UM["um_d1_10"], HOU],
 "Sahm35x2 + IUR30": [S2, gapch(iur4,0.30), IC["ic8_30_k1"], PAY, UM["um_d1_10"], HOU],
 "Sahm35 rising + IUR35": [SR, gapch(iur4,0.35), IC["ic8_30_k1"], PAY, UM["um_d1_10"], HOU],
 "Sahm40 + IUR35": [SAHM[0.40], gapch(iur4,0.35), IC["ic8_30_k1"], PAY, UM["um_d1_10"], HOU],
 "Sahm35x2 + IUR35 + claims k2": [S2, gapch(iur4,0.35), IC["ic8_30_k2"] if "ic8_30_k2" in IC else IC["ic4_30_k2"], PAY, UM["um_d1_10"], HOU],
}
for nm,chs in cands.items():
    eps=replay3(chs, GATE[12], 120); res,false=score_eps(eps,T_P1)
    L=[r["lag"] for r in res]
    print(f"{nm:32s} false {len(false)} {false[:3]} | lags {L} | out-of-±1 {sum(1 for l in L if l is None or abs(l)>1)} | onsets {[r['onset'] for r in res]}")
