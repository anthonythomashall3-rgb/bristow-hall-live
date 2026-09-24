exec(open("stage20b_confirm.py").read().split("chs=[SAHM[0.35], ICmix")[0])
for g in [0.40,0.45]:
    IURg=gapch(iur4,g); IURFg=D(g4f>=g-1e-12); IURmixg=IURg.copy(); IURmixg[cal>=cut]=IURFg[cal>=cut]
    for nm,chs in [(f"IUR{g} no claims, current",[SAHM[0.35], IURg, PAY, UM["um_d1_10"], HOU]),(f"IUR{g} no claims, first prints",[SAHM[0.35], IURmixg, PAY, UM["um_d1_10"], HOU]),
                   (f"IUR{g} + claims, current",[SAHM[0.35], IURg, IC["ic8_30_k1"], PAY, UM["um_d1_10"], HOU]),(f"IUR{g} + claims, first prints",[SAHM[0.35], IURmixg, ICmix, PAY, UM["um_d1_10"], HOU])]:
        eps=replay3(chs, GATE[12], 120); res,false=score_eps(eps,T_P1)
        print(f"{nm}: false {false} | onsets {[r['onset'] for r in res]} | lags {[r['lag'] for r in res]}")
