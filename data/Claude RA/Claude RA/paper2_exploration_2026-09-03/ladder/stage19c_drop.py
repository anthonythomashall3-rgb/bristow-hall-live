exec(open("stage19b_iur.py").read().split("base=[SAHM[0.35]")[0])
IUR4=gapch(iur4,0.30)
for nm,chs in [("v2 full",[SAHM[0.35], IC["ic8_30_k1"], PAY, UM["um_d1_10"], HOU, IUR4]),("v2 minus claims",[SAHM[0.35], PAY, UM["um_d1_10"], HOU, IUR4]),("v2 minus claims minus payrolls",[SAHM[0.35], UM["um_d1_10"], HOU, IUR4]),("v2 minus payrolls",[SAHM[0.35], IC["ic8_30_k1"], UM["um_d1_10"], HOU, IUR4])]:
    eps=replay3(chs, GATE[12], 120); res,false=score_eps(eps,T_P1)
    print(nm, "false", false, "onsets", [r["onset"] for r in res], "lags", [r["lag"] for r in res], "end", [r["end_lag"] for r in res])
