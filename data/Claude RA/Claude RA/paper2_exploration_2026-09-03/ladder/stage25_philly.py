"""Stage 25: Philadelphia Fed Business Outlook Survey (1968->, released the third Thursday of the reference month, never revised
except seasonal factors): employment index (NEC), general activity (GAC), new orders (NOC). Scored alone (gated) and as a
replacement for the thin channels (payrolls -0.1, sentiment -10, housing -20)."""
exec(open("stage19b_iur.py").read().split("base=[SAHM[0.35]")[0])
F=HOME+"/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/"
def third_thursday(m):
    d=pd.Timestamp(m.year, m.month, 1); off=(3-d.weekday())%7; return d+pd.Timedelta(days=off+14)
def loadf(sid):
    s=pd.read_csv(F+sid+".csv"); s=s[s.value!="."]; s.index=pd.to_datetime(s.date); s=s.value.astype(float); s.index=[third_thursday(m) for m in s.index]; return s
NEC=loadf("NECDFSA066MSFRBPHI"); GAC=loadf("GACDFSA066MSFRBPHI"); NOC=loadf("NOCDFSA066MSFRBPHI")
PH={}
for x in [0,-5,-10,-15,-20,-25]:
    for k in [1,2,3]:
        c=(NEC<=x); 
        for j in range(1,k): c=c&(NEC.shift(j)<=x)
        PH[f"NEC<={x} x{k}"]=D(c)
for y in [-10,-20,-30,-40]:
    for k in [1,2]:
        c=(GAC<=y)
        for j in range(1,k): c=c&(GAC.shift(j)<=y)
        PH[f"GAC<={y} x{k}"]=D(c)
        c=(NOC<=y)
        for j in range(1,k): c=c&(NOC.shift(j)<=y)
        PH[f"NOC<={y} x{k}"]=D(c)
rows=[]
for nm,a in PH.items(): rows.append(score(pd.Series(a&GATE[12], index=cal), nm, start="1968-06-01"))
df=pd.DataFrame(rows); df["out1"]=df.lags.apply(lambda L: sum(abs(x)>1 for x in L)); pd.set_option("display.width",330); pd.set_option("display.max_colwidth",100); pd.set_option("display.max_rows",100)
print("=== Philly BOS channels alone, gated, 1968-2026 ===")
print(df.sort_values(["n_fa","misses","out1"]).drop(columns=["calls","fa"]).head(30).to_string())
print("\n=== quiet-period extremes (gated, outside windows) ===")
allowed=np.zeros(N,bool)
for pk,tr in T_P1:
    lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(tr)+12).to_timestamp(how="end")); allowed[lo:hi+1]=True
quiet=(~allowed)&GATE[12]&(cal>=pd.Timestamp("1968-06-01"))
for nm,s in [("NEC",NEC),("GAC",GAC),("NOC",NOC)]:
    v=s.reindex(cal).ffill().values; print(f"  {nm}: quiet gated min {np.nanmin(v[quiet]):.1f}; recession-window minima by episode:", [round(float(np.nanmin(v[cal.searchsorted((P(pk)-1).to_timestamp()):cal.searchsorted((P(tr)).to_timestamp(how='end'))])),1) for pk,tr in T_P1])
print("\n=== v3 with Philly channels replacing / adding to thin channels ===")
base=[SAHM[0.35], gapch(iur4,0.40)]
combos={"v3":base+[PAY, UM["um_d1_10"], persist2(h3,20)],
        "v3 + NEC<=-10 x2":base+[PAY, UM["um_d1_10"], persist2(h3,20), PH["NEC<=-10 x2"]],
        "v3 + NEC<=-15 x1":base+[PAY, UM["um_d1_10"], persist2(h3,20), PH["NEC<=-15 x1"]],
        "Sahm+IUR + NEC<=-10 x2 only":base+[PH["NEC<=-10 x2"]],
        "Sahm+IUR + NEC<=-15 x1 only":base+[PH["NEC<=-15 x1"]],
        "Sahm+IUR + GAC<=-30 x1":base+[PH["GAC<=-30 x1"]],
        "Sahm+IUR + NEC<=-10x2 + sent12 + hou20":base+[PH["NEC<=-10 x2"], UM["um_d1_8"] if False else D((um-um.shift(1))<=-12), persist2(h3,20)],
        "Sahm+IUR + NEC<=-10x2 + pay0.15 + sent12":base+[PH["NEC<=-10 x2"], D(pd.Series((pay.d1.astype(float)<=-0.15).values, index=pd.to_datetime(pay.rel.values))), D((um-um.shift(1))<=-12)]}
for nm,chs in combos.items():
    eps=replay3(chs, GATE[12], 120); res,false=score_eps(eps,T_P1); L=[r["lag"] for r in res]
    print(f"  {nm:42s} false {len(false)} {false[:3]} lags {L} out1 {sum(1 for l in L if l is None or abs(l)>1)} onsets {[r['onset'] for r in res]}")
