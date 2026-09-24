exec(open("stage19b_iur.py").read().split("base=[SAHM[0.35]")[0])
PAY15=D(pd.Series((pay.d1.astype(float)<=-0.15).values, index=pd.to_datetime(pay.rel.values))); SENT12=D((um-um.shift(1))<=-12)
for nm,chs in [("v3",[SAHM[0.35], gapch(iur4,0.40), PAY, UM["um_d1_10"], persist2(h3,20)]),
               ("v3.1 sent12 pay0.15",[SAHM[0.35], gapch(iur4,0.40), PAY15, SENT12, persist2(h3,20)]),
               ("v3 sent12 only",[SAHM[0.35], gapch(iur4,0.40), PAY, SENT12, persist2(h3,20)]),
               ("v3 pay0.15 only",[SAHM[0.35], gapch(iur4,0.40), PAY15, UM["um_d1_10"], persist2(h3,20)])]:
    eps=replay3(chs, GATE[12], 120); res,false=score_eps(eps,T_P1)
    print(f"{nm:22s} false {false} lags {[r['lag'] for r in res]} onsets {[r['onset'] for r in res]}")
umd=(um-um.shift(1)); print("sentiment monthly changes <=-9 outside recessions:", {str(k.date()):v for k,v in umd[umd<=-9].items()})
print("payroll first prints <=-0.08:", {str(k):round(v,3) for k,v in pay.d1.astype(float)[pay.d1.astype(float)<=-0.08].items()})
