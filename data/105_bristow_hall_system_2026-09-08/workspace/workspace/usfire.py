"""The one survivor of the corrected sweep, taken to the harness and then to
leave-one-out -- because the screen is not the test."""
exec(open('frontier.py').read().split('def rep(')[0])
import io, contextlib, numpy as np
UF=first_prints('USFIRE'); G=(UF.rolling(12).max()/UF-1)*100
SEC=[dict(name='vacancy',gap=vr,line=0.36,pub_day=30),PAY,H35]
def run(second):
    with contextlib.redirect_stdout(io.StringIO()):
        return score(B.american_chronology({k:PLU[k] for k in PK5},{k:TLG[k] for k in TR3},
                sahm=g,second=second,horizon_months=4,back_months=6),'x','1948-06-01')
r0=run(SEC); print(f"shipped v6          peaks {len(r0['lags_p'])}/12 other {r0['other']} "
                  f"median {np.median(r0['lags_p']):.0f} mean {np.mean(r0['lags_p']):.1f} worst {max(r0['lags_p'])}\n   {r0['lags_p']}")
print(f"\n{'USFIRE line':>12}{'peaks':>7}{'other':>7}{'median':>8}{'mean':>7}{'worst':>7}{'exact':>7}   lags")
best=[]
for line in (1.4,1.6,1.768,1.9,2.1,2.4,2.8):
    r=run(SEC+[dict(name='usfire',gap=G,line=line,pub_day=5)])
    lp,ep=r['lags_p'],r['errs_p']
    print(f"{line:12.3f}{len(lp):7d}{r['other']:7d}{np.median(lp):8.0f}{np.mean(lp):7.1f}{max(lp):7d}"
          f"{sum(1 for e in ep if e==0):7d}   {lp}")
    if len(lp)==12 and r['other']<=1: best.append(line)
print("\nleave one recession out on the LINE, over the twelve: does every fold accept one value?")
PKD=[pd.Timestamp(p+'-01') for p in PEAKS[:12]]
LINES=[round(x,2) for x in np.arange(1.2,3.01,0.1)]
def lags_at(line):
    r=run(SEC+[dict(name='usfire',gap=G,line=line,pub_day=5)])
    return r['lags_p'],r['other'],len(r['lags_p'])
cache={l:lags_at(l) for l in LINES}
picks=[]
for i in range(12):
    ok=[l for l in LINES if cache[l][2]==12 and cache[l][1]<=1]
    if not ok: picks.append(None); continue
    sc=sorted(ok,key=lambda l:(np.mean([x for j,x in enumerate(cache[l][0]) if j!=i]),
                               max(x for j,x in enumerate(cache[l][0]) if j!=i)))
    picks.append(sc[0])
print("   fold picks:", picks)
u=set(p for p in picks if p is not None)
print(f"   distinct choices across the twelve folds: {len(u)}  {sorted(u)}")
print("   " + ("UNANIMOUS -- admissible under Rule 18" if len(u)==1 else
      "THE FOLDS DO NOT AGREE -- Rule 18 forbids a clause the record cannot pin, whatever it buys."))
