exec(open("stage32_backstops.py").read().split("rows=[]")[0])
sel=['Sahm>=0.55 x1 [nogate]','IUR gap>=0.5 [nogate]','claims 8wk>=40% [nogate]','bill fall>=2.5/60d [nogate]','sentiment -15 [nogate]','housing -25% x2 [nogate]','IP 3m first print <=-2.0% x2 [nogate]']
V4=[SAHM[0.35], gapch(iur4,0.40), PAY, UM["um_d1_10"], persist2(h3,20), fall(tb6,60,1.43)]
def replay_mixed(gated_chs, ungated_chs):
    trig=np.zeros(N,bool)
    for c in gated_chs: trig|=fresh(c,120)&GATE[12]
    for c in ungated_chs: trig|=fresh(c,120)
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
    return eps
eps=replay_mixed(V4,[BS[n] for n in sel]); res,false=score_eps(eps,T_P1)
print("v5: false", false, "| lags", [r["lag"] for r in res], "| end", [r["end_lag"] for r in res], "| onsets", [r["onset"] for r in res])
eps0=replay_mixed([],[BS[n] for n in sel]); res0,false0=score_eps(eps0,T_P1)
print("v5 with the gate removed everywhere (no-inversion world): false", false0, "| lags", [r["lag"] for r in res0], "| onsets", [r["onset"] for r in res0])
# first-print replay of v5 (IUR first prints from 2002; others first prints; bills unrevised; claims advance prints for the 40% backstop)
IUR40=gapch(iur4,0.40); IURF40=D(g4f>=0.40-1e-12); IURmix40=IUR40.copy(); IURmix40[cal>=cut]=IURF40[cal>=cut]
IUR50=gapch(iur4,0.50); IURF50=D(g4f>=0.50-1e-12); IURmix50=IUR50.copy(); IURmix50[cal>=cut]=IURF50[cal>=cut]
IC40=wk(r8>=0.40); ICF40=D(r8f>=0.40); ICmix40=IC40.copy(); ICmix40[cal>=cut]=ICF40[cal>=cut]
epsF=replay_mixed([SAHM[0.35], IURmix40, PAY, UM["um_d1_10"], persist2(h3,20), fall(tb6,60,1.43)], [BS['Sahm>=0.55 x1 [nogate]'], IURmix50, ICmix40, BS['bill fall>=2.5/60d [nogate]'], BS['sentiment -15 [nogate]'], BS['housing -25% x2 [nogate]'], BS['IP 3m first print <=-2.0% x2 [nogate]']])
resF,falseF=score_eps(epsF,T_P1); print("v5 first-print replay (2003->): false", falseF, "| lags", [r["lag"] for r in resF])
print("first-print quiet maxima 2003-2026: IUR gap", round(float(g4f[(g4f.index>=pd.Timestamp('2003-01-01'))].max()),3), "| claims 8wk ratio", round(float(r8f.max()),3))
# margins of the backstops (ungated quiet max vs threshold)
print("\nbackstop margins (ungated): Sahm 0.55 vs quiet-max 0.533 (Dec 1976); IUR 0.50 vs 0.40 (Oct 1976); claims 40% vs 25.3% (Dec 2000); bill 2.5 vs 2.41 (Dec 1984); sentiment 15 vs 12.2 (Sep 2005); housing 25% x2 vs 33% single (Mar 1979); IP -2% x2 vs ?")
ip3=fpch3("INDPRO_all_vintages.csv"); allowed=np.zeros(N,bool)
for pk,tr in T_P1:
    lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(tr)+12).to_timestamp(how="end")); allowed[lo:hi+1]=True
v=ip3.reindex(cal).ffill().values; q=(~allowed)&(cal>=pd.Timestamp("1968-06-01")); vv=v[q]; c2=(ip3<=-0.02)&(ip3.shift(1)<=-0.02)
print("IP 3m first print: ungated quiet min", np.nanmin(vv).round(4), "on", str(cal[q][np.nanargmin(vv)].date()), "| two-print pairs <=-2% outside windows:", [str(d.date()) for d in c2[c2].index if not allowed[cal.searchsorted(d)]][:5])
