"""Stage 47: (c) +-1-tick perturbation map of v7, (d) leave-one-out and recursive re-selection on the v7 menu."""
exec(open("stage46_v7.py").read().split('print("\\n=== (b) END')[0])
import warnings; warnings.filterwarnings("ignore")
def v7_with(sahm=0.35,iurg=0.40,payx=0.001,houx=20,billx=1.43,bsSahm=0.55,bsIUR=0.50,bsIC=0.40,bsBill=2.50,bsHou=25,bsIP=0.02,vixx=17.425,baax=1.50,lanes=True):
    PAYc=D(pd.Series((pay.d1.astype(float)<=-payx*100).values, index=pd.to_datetime(pay.rel.values)))
    fast=[SAHM[sahm] if sahm in SAHM else D(Srel>=sahm-1e-9), gapch(iur4,iurg), PAYc, persist2(h3,houx), fall(tb6,60,billx)]
    frozen=np.zeros(N,bool)
    for c in fast: frozen|=fresh(c,120)&GATE[12]
    bsarr=[D(Srel>=bsSahm-1e-9), gapch(iur4,bsIUR), wk(r8>=bsIC), fall(tb6,60,bsBill), persist2(h3,bsHou), D((ip3c<=-bsIP)&(ip3c.shift(1)<=-bsIP))]
    for c in bsarr: frozen|=fresh(c,120)
    lanearr=np.zeros(N,bool)
    if lanes:
        for a in [lane_arr(vix-vix.shift(20),1,vixx), lane_arr(baa-baa.rolling(250).min(),1,baax)]: lanearr|=fresh(a,120)
        valid=lanearr.copy()
        for i in np.flatnonzero(np.diff(lanearr.astype(np.int8))==1)+1:
            if not frozen[i:i+121].any():
                j=i
                while j<N and lanearr[j]: valid[j]=False; j+=1
        lanearr=valid
    eps=replay(frozen|lanearr)
    return score_eps(eps,T_P1)
ip3c=fpch3("INDPRO_all_vintages.csv")
base=v7_with()
print("v7 base: false", base[1], "lags", [r["lag"] for r in base[0]])
print("\n=== (c) PERTURBATION MAP: one threshold moved by one data tick at a time ===")
print(f"{'threshold moved':34s} {'false':>6s} {'misses':>7s} {'lags outside a month':>22s}")
grid=[("Sahm fast 0.35 -> 0.30",dict(sahm=0.30)),("Sahm fast 0.35 -> 0.40",dict(sahm=0.40)),
 ("IUR fast 0.40 -> 0.35",dict(iurg=0.35)),("IUR fast 0.40 -> 0.45",dict(iurg=0.45)),
 ("payrolls 0.10 -> 0.05",dict(payx=0.0005)),("payrolls 0.10 -> 0.15",dict(payx=0.0015)),
 ("housing 20% -> 18%",dict(houx=18)),("housing 20% -> 22%",dict(houx=22)),
 ("bill 1.43 -> 1.33",dict(billx=1.33)),("bill 1.43 -> 1.53",dict(billx=1.53)),
 ("bs Sahm 0.55 -> 0.50",dict(bsSahm=0.50)),("bs Sahm 0.55 -> 0.60",dict(bsSahm=0.60)),
 ("bs IUR 0.50 -> 0.45",dict(bsIUR=0.45)),("bs IUR 0.50 -> 0.55",dict(bsIUR=0.55)),
 ("bs claims 40% -> 35%",dict(bsIC=0.35)),("bs claims 40% -> 45%",dict(bsIC=0.45)),
 ("bs bill 2.50 -> 2.40",dict(bsBill=2.40)),("bs bill 2.50 -> 2.60",dict(bsBill=2.60)),
 ("bs housing 25% -> 23%",dict(bsHou=23)),("bs IP 2.0% -> 1.8%",dict(bsIP=0.018)),
 ("VIX 17.4 -> 16.4",dict(vixx=16.425)),("VIX 17.4 -> 18.4",dict(vixx=18.425)),
 ("Baa 1.50 -> 1.40",dict(baax=1.40)),("Baa 1.50 -> 1.60",dict(baax=1.60)),
 ("no lane at all",dict(lanes=False))]
nfa=0
for nm,kw in grid:
    res,false=v7_with(**kw); L=[r["lag"] for r in res]
    out=[(res[i]["peak"],L[i]) for i in range(9) if L[i] is None or abs(L[i])>1]
    if false: nfa+=1
    print(f"{nm:34s} {len(false):6d} {sum(1 for x in L if x is None):7d} {str(out):>22s}")
print(f"\n  {nfa} of {len(grid)} one-tick perturbations produce a false alarm.")
