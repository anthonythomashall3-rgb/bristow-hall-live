"""The zero-exposure pairs, taken to the harness and then to the folds.
Factory hours, refused twice on its own at 10.62 per cent, is free inside a
pair: hours is the fast object and an employment fall is the gate that keeps it
out of every inventory correction."""
exec(open('frontier.py').read().split('def rep(')[0])
import io, contextlib, numpy as np
AWH=first_prints('AWHMAN'); AWO=first_prints('AWOTMAN'); ND=first_prints('NDMANEMP')
DM=first_prints('DMANEMP'); MN=first_prints('MANEMP'); GV=first_prints('USGOVT'); HO2=first_prints('HOUST')
f12=lambda v,l:(v.rolling(12).max()/v-1)*100/l
f3 =lambda v,l:(-(v/v.shift(3)-1)*100)/l
g12=lambda v,l:(v-v.rolling(12).min())/l
PR =lambda a,b: pd.concat([a,b],axis=1).min(axis=1).dropna()
CAND={'hours 2.0 x nondurable emp 1.28   [1980]':PR(f12(AWH,1.995),f3(ND,1.2801)),
      'hours 2.0 x overtime gap 0.70     [1980]':PR(f12(AWH,1.995),g12(AWO,0.7)),
      'overtime 14 x housing 3-fall 17.8 [1980]':PR(f12(AWO,13.9535),f3(HO2,17.8164)),
      'overtime 14 x durable emp 1.45    [2001]':PR(f12(AWO,13.9535),f3(DM,1.446)),
      'hours 2.9 x factory emp 1.26      [2001]':PR(f12(AWH,2.9033),f3(MN,1.2635)),
      'hours 2.0 x government emp 1.68   [2001]':PR(f12(AWH,1.995),f12(GV,1.6811))}
SEC=[dict(name='vacancy',gap=vr,line=0.36,pub_day=30),PAY,H35]
def run(extra):
    with contextlib.redirect_stdout(io.StringIO()):
        return score(B.american_chronology({k:PLU[k] for k in PK5},{k:TLG[k] for k in TR3},
                sahm=g,second=SEC+extra,horizon_months=4,back_months=6),'x','1948-06-01')
r0=run([]); print(f"shipped v6                                12/12 other {r0['other']} "
    f"median {np.median(r0['lags_p']):.0f} mean {np.mean(r0['lags_p']):.1f} worst {max(r0['lags_p'])}\n  {r0['lags_p']}\n")
print(f"{'pair':42}{'pk':>4}{'oth':>5}{'med':>5}{'mean':>7}{'wst':>5}{'ex':>4}   lags")
keep=[]
for nm,o in CAND.items():
    r=run([dict(name=nm[:10],gap=o,line=1.0,pub_day=5)]); lp,ep=r['lags_p'],r['errs_p']
    print(f"{nm:42}{len(lp):4d}{r['other']:5d}{np.median(lp):5.0f}{np.mean(lp):7.1f}{max(lp):5d}"
          f"{sum(1 for e in ep if e==0):4d}   {lp}")
    if len(lp)==12 and r['other']<=1 and np.mean(lp)<np.mean(r0['lags_p'])-0.5: keep.append((nm,o))
print(f"\n{len(keep)} improve the mean without breaking the record")
for i in range(len(keep)):
    for j in range(i+1,len(keep)):
        r=run([dict(name='p1',gap=keep[i][1],line=1.0,pub_day=5),
               dict(name='p2',gap=keep[j][1],line=1.0,pub_day=5)]); lp=r['lags_p']
        print(f"  {keep[i][0][:24]:26}+ {keep[j][0][:24]:26} {len(lp)}/12 other {r['other']} "
              f"median {np.median(lp):.0f} mean {np.mean(lp):.1f}  {lp}")
