exec(open('frontier.py').read().split('def rep(')[0])
import io,contextlib
SEC=[dict(name='vacancy',gap=vr,line=0.36,pub_day=30),PAY,H35]
print(f"\n{'window':26}{'peaks':>7}{'other':>7}{'median':>8}{'mean':>7}{'worst':>7}{'exact':>7}")
for bk,fw in [(6,18),(6,6),(6,4),(5,4),(5,3),(4,3),(3,3)]:
    with contextlib.redirect_stdout(io.StringIO()):
        r=score(B.american_chronology({k:PLU[k] for k in PK5},{k:TLG[k] for k in TR3},
                sahm=g,second=SEC,horizon_months=fw,back_months=bk),'x','1948-06-01')
    lp,ep=r['lags_p'],r['errs_p']
    print(f"   back {bk:2d}, forward {fw:2d}     {len(lp):5d}{r['other']:7d}{np.median(lp):8.0f}{np.mean(lp):7.1f}{max(lp):7d}{sum(1 for e in ep if e==0):7d}")
