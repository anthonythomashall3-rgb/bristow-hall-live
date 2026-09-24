"""Stage 21g: v3 = Sahm 0.35 + IUR 4wk gap 0.35 + payrolls + sentiment + housing (initial claims kept only as the end channel).
Current-vintage and first-print replays; confirmation not needed if the first-print record is clean."""
exec(open("stage20b_confirm.py").read().split("chs=[SAHM[0.35], ICmix")[0])
IUR35=gapch(iur4,0.35); IURF35=D(g4f>=0.35-1e-12); IURmix35=IUR35.copy(); IURmix35[cal>=cut]=IURF35[cal>=cut]
for nm,chs,fp in [("v3 current vintage",[SAHM[0.35], IUR35, PAY, UM["um_d1_10"], HOU],False),("v3 first prints (IUR first prints from Oct 2002)",[SAHM[0.35], IURmix35, PAY, UM["um_d1_10"], HOU],True),
                  ("v3 + initial-claims onset channel, current vintage",[SAHM[0.35], IUR35, IC["ic8_30_k1"], PAY, UM["um_d1_10"], HOU],False),("v3 + initial-claims onset channel, first prints",[SAHM[0.35], IURmix35, ICmix, PAY, UM["um_d1_10"], HOU],True)]:
    eps=replay3(chs, GATE[12], 120); res,false=score_eps(eps,T_P1)
    print(f"{nm}: false {false} | onsets {[r['onset'] for r in res]} | lags {[r['lag'] for r in res]} | end lags {[r['end_lag'] for r in res]} | trough err {[r['tr_err'] for r in res]}")
print("IUR first-print 4wk gap max by year 2003-2026:", {y: round(float(g4f.loc[str(y)].max()),3) for y in range(2003,2027) if len(g4f.loc[str(y)])})
print("IUR current-vintage 4wk gap max by year 1972-2026 (quiet years):", {y: round(float((iur4-iur4.shift(1).rolling(52).min()).loc[str(y)].max()),3) for y in [1972,1976,1977,1978,1979,1984,1985,1986,1987,1989,1992,1995,1996,1998,2003,2005,2011,2016,2019,2022,2023,2024,2025,2026]})
