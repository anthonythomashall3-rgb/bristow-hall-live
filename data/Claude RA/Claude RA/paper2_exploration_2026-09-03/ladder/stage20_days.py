"""Stage 20: day-level metrics. (a) revision-robustness of the onset stamp: replay the rule on DOL first prints (claims advance,
IUR) 2002-> and compare stamp days with the current-vintage replay (the RMV1 'to the day' metric: real-time stamp vs revised stamp).
(b) an external daily reference: the Philadelphia Fed ADS index (current vintage, daily 1960->): first day at/below a line inside
each recession window, compared with the rule's onset call day."""
exec(open("stage19b_iur.py").read().split("base=[SAHM[0.35]")[0])
IUR4=gapch(iur4,0.30)
V1=[SAHM[0.35], IC["ic8_30_k1"], PAY, UM["um_d1_10"], HOU]; V2=V1+[IUR4]
eps1=replay3(V1, GATE[12], 120); eps2=replay3(V2, GATE[12], 120)
res2,false2=score_eps(eps2,T_P1)
print("v2 = v1 + IUR4 gap>=0.30: false", false2)
lastday=lambda pk: (P(pk)).to_timestamp(how="end").normalize()
print("onset call minus last day of NBER peak month (days):")
for r in res2: print(f"  {r['peak']}: call {r['onset']}  {(pd.Timestamp(r['onset'])-lastday(r['peak'])).days:+d} d")
# ---------- (a) first-print replay 2002-> ----------
H=ODD+"bristow-hall-harvest/data/dol_claims_press/"
px=pd.read_csv(H+"weekly_claims_press_index.csv", parse_dates=["release_date"]).dropna(subset=["initial_claims_headline"])
icf=pd.Series(px.initial_claims_headline.values, index=px.release_date.values).sort_index()   # advance first print, indexed by release day
n=pd.read_csv(H+"national_iur_first_prints.csv", parse_dates=["obs_period","vintage_date"]); n=n[n.series_id=="national_iur"]
iurf=pd.Series(n.value.values, index=n.vintage_date.values).sort_index()
# rolling stats on the first-print sequences (release-day indexed; each release adds one week)
def fp_ratio8(s):  # 8-release avg vs min over prior 52 releases
    m8=s.rolling(8).mean(); return m8/m8.shift(1).rolling(52).min()-1
r8f=fp_ratio8(icf); g4f=iurf.rolling(4).mean()-iurf.rolling(4).mean().shift(1).rolling(52).min()
ICF=D(r8f>=0.30); IURF=D(g4f>=0.30-1e-12)
# the first-print series begin Oct 2002; before that use current vintage so the machine has history
cut=pd.Timestamp("2003-10-30")  # first-print stats valid after 52 releases
ICmix=IC["ic8_30_k1"].copy(); ICmix[cal>=cut]=ICF[cal>=cut]; IURmix=IUR4.copy(); IURmix[cal>=cut]=IURF[cal>=cut]
epsF=replay3([SAHM[0.35], ICmix, PAY, UM["um_d1_10"], HOU, IURmix], GATE[12], 120)
resF,falseF=score_eps(epsF,T_P1)
print("\n(a) FIRST-PRINT replay (claims advance + IUR first prints from Oct 2002; Sahm/payrolls/housing first prints throughout):")
print("   false episodes:", falseF)
for a,b in zip(res2,resF):
    if a["peak"]>="2007": print(f"   {a['peak']}: current-vintage stamp {a['onset']} | first-print stamp {b['onset']} | delta {(pd.Timestamp(b['onset'])-pd.Timestamp(a['onset'])).days:+d} d | end call cv {a['end_lag']} fp {b['end_lag']}")
print("   which channel fires first (first-print replay):")
namesF=["Sahm>=0.35","claims 8wk>=30% (advance prints)","payrolls","sentiment","housing","IUR4 gap>=0.30 (first prints)"]
arrsF=[fresh(a,120)&GATE[12] for a in [SAHM[0.35], ICmix, PAY, UM["um_d1_10"], HOU, IURmix]]
for e in epsF:
    if e["onset"]>=pd.Timestamp("2003-01-01"):
        i=int(np.where(cal==e["onset"])[0][0]); print("   ", e["onset"].date(), [nm for nm,a in zip(namesF,arrsF) if a[i]])
# first-print vs current-vintage ratio series around the 2008 and 2020 and 2024 stamps
for y0,y1 in [("2007-11","2008-09"),("2020-02","2020-04"),("2024-03","2024-09"),("2022-06","2022-10")]:
    seg=pd.DataFrame(dict(cv_r8=r8.loc[y0:y1], fp_r8=r8f.reindex(r8.loc[y0:y1].index+pd.Timedelta(days=5)).values, cv_iur4gap=(iur4-iur4.shift(1).rolling(52).min()).loc[y0:y1], fp_iur4gap=g4f.reindex(r8.loc[y0:y1].index+pd.Timedelta(days=5)).values))
    print(f"   window {y0}..{y1}: max cv_r8 {seg.cv_r8.max():.3f} fp_r8 {seg.fp_r8.max():.3f} | max cv_iur4gap {seg.cv_iur4gap.max():.3f} fp {seg.fp_iur4gap.max():.3f}")
# ---------- (b) ADS daily reference ----------
ads=pd.read_csv(ODD+"bristow-hall/projects-old/raw/ADS_INDEX.csv"); ads["d"]=pd.to_datetime(ads.Date.str.replace(":","-")); ads=ads.set_index("d").ADS_Index
print("\n(b) ADS index (Philadelphia Fed, current vintage, daily): first day at/below a line inside [peak-3mo, trough], vs the rule's call day")
for line in [0.0,-0.5,-1.0]:
    out=[]
    for r in res2:
        pk=P(r["peak"]); tr=[t for p,t in T_P1 if p==r["peak"]][0]
        w=ads[((ads.index>=(pk-3).to_timestamp())&(ads.index<=P(tr).to_timestamp(how="end")))]
        h=w[w<=line]
        if len(h)==0: out.append((r["peak"],None,None)); continue
        d0=h.index[0]; out.append((r["peak"], str(d0.date()), (pd.Timestamp(r["onset"])-d0).days))
    print(f"  line {line:+.1f}: ", "; ".join(f"{p}: ADS {d} call {x:+d}d" if d else f"{p}: none" for p,d,x in out))
# ADS local peak (max) in [peak-6mo, peak+1mo] as the day 'conditions turned'
out=[]
for r in res2:
    pk=P(r["peak"]); w=ads[(ads.index>=(pk-6).to_timestamp())&(ads.index<=(pk+1).to_timestamp(how="end"))]
    d0=w.idxmax(); out.append(f"{r['peak']}: ADS max {d0.date()} call {(pd.Timestamp(r['onset'])-d0).days:+d}d")
print("  ADS local max in [peak-6mo, peak+1mo]:", "; ".join(out))
