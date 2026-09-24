"""THE CLOSER DROPS SWEPT. J and H are the lab's level_trough_calls on the monthly continued-claims and initial-claims
fields (drops of 5.0 and 8.0 log points from the episode's peak); K is the weekly continued-claims clause at 4.0. All
three were inherited whole. Swept here against v3.5 read real-time, with an early close counted as a failure."""
exec(open('trough1.py').read().split('P("\\n=== the shipped closers ===")')[0].replace("out=open('trough1.out','w')","out=open('trough2.out','w')"))
FH=pd.read_csv(W+'/lab/fh/FH_nat_sa_rt.csv',index_col=0,parse_dates=True)
icm=np.log(FH['initial claims'].dropna()); ccm=np.log(FH['continued weeks claimed'].dropna())
def pub10(p): return pd.Timestamp(p.year,p.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=9)
def mkJH(j,h):
    Hh=[(pub10(p-pd.DateOffset(months=1)),d) for p,d in B.level_trough_calls(icm,drop=h)]
    Jj=[(pub10(p-pd.DateOffset(months=1)),d) for p,d in B.level_trough_calls(ccm,drop=j)]
    return Jj,Hh
P("=== the shipped closers ==="); rep('v3.5 as shipped',TLH)
J0,H0=mkJH(5.,8.)
TL0={k:list(v) for k,v in TLH.items()}; TL0['J']=J0; TL0['H']=[(p-pd.Timedelta(days=4),d) for p,d in H0]
rep('  rebuilt at the shipped drops (5.0 / 8.0)',TL0)
P("\n=== J (monthly continued claims) swept, H held at 8.0 ===")
for j in [3.,4.,4.5,5.,6.,7.,8.,10.]:
    Jj,Hh=mkJH(j,8.); TL={k:list(v) for k,v in TLH.items()}; TL['J']=Jj; TL['H']=[(p-pd.Timedelta(days=4),d) for p,d in Hh]
    rep(f'  J drop {j}',TL)
P("\n=== H (monthly initial claims) swept, J held at 5.0 ===")
for h in [4.,5.,6.,7.,8.,10.,12.,15.]:
    Jj,Hh=mkJH(5.,h); TL={k:list(v) for k,v in TLH.items()}; TL['J']=Jj; TL['H']=[(p-pd.Timedelta(days=4),d) for p,d in Hh]
    rep(f'  H drop {h}',TL)
P("\n=== both, at the fastest clean corner ===")
best=None
for j in [3.,4.,5.,6.,8.]:
    for h in [4.,5.,6.,8.,10.,12.]:
        Jj,Hh=mkJH(j,h); TL={k:list(v) for k,v in TLH.items()}; TL['J']=Jj; TL['H']=[(p-pd.Timedelta(days=4),d) for p,d in Hh]
        r=score_only(TL); lt=[r['lags_t'].get(i) for i in range(13)]; tv=[x for x in lt if x is not None]; et=[r['errs_t'].get(i) for i in range(13)]
        early=sum(1 for x in tv if x<0); n=len(tv)
        if n==13 and early==0 and len(r['other'])==0:
            key=(np.median(tv),np.mean(tv))
            if best is None or key<best[0]: best=(key,j,h)
        P(f"   J {j:4.1f} H {h:5.1f}: n {n} median {np.median(tv):.0f} mean {np.mean(tv):.0f} worst {max(tv)} exact {sum(1 for e in et if e==0)} early {early}")
P(f"\n   fastest clean corner: J {best[1]} H {best[2]} at median {best[0][0]:.0f} days" if best else "\n   no clean corner beats the shipped pair")
out.close()
