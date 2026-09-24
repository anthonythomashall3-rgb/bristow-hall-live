"""Can v7 be simplified? Drop each object in turn; anything whose removal costs
nothing goes."""
exec(open('frontier.py').read().split('def rep(')[0])
import io, contextlib, numpy as np, itertools
AWH=first_prints('AWHMAN'); ND=first_prints('NDMANEMP')
f12=lambda v,l:(v.rolling(12).max()/v-1)*100/l; f3=lambda v,l:(-(v/v.shift(3)-1)*100)/l
P1=pd.concat([f12(AWH,2.0),f3(ND,1.20)],axis=1).min(axis=1).dropna()
CONF={'vacancy':dict(name='vacancy',gap=vr,line=0.36,pub_day=30),'payrolls':PAY,'housing':H35,
      'pair':dict(name='pair',gap=P1,line=1.0,pub_day=5)}
def run(legs,confs,sahm=True):
    with contextlib.redirect_stdout(io.StringIO()):
        r=score(B.american_chronology({k:PLU[k] for k in legs},{k:TLG[k] for k in TR3},
                sahm=g if sahm else None,second=[CONF[c] for c in confs],horizon_months=4,back_months=6),'x','1948-06-01')
    lp,ep,lt=r['lags_p'],r['errs_p'],r['lags_t']
    return len(lp),r['other'],np.median(lp),np.mean(lp),max(lp),sum(1 for e in ep if e==0),len(lt),np.median(lt)
print(f"{'configuration':44}{'pk':>4}{'oth':>4}{'med':>5}{'mean':>6}{'wst':>5}{'ex':>4}{'tr':>4}{'trmed':>6}")
def row(nm,legs,confs,sahm=True):
    r=run(legs,confs,sahm); print(f"{nm:44}{r[0]:4d}{r[1]:4d}{r[2]:5.0f}{r[3]:6.1f}{r[4]:5d}{r[5]:4d}{r[6]:4d}{r[7]:6.0f}")
ALL=['vacancy','payrolls','housing','pair']
row("v7 as frozen",'ABCMU',ALL)
print("-- confirming side, drop one")
for c in ALL: row(f"  without {c}",'ABCMU',[x for x in ALL if x!=c])
row("  without Sahm",'ABCMU',ALL,sahm=False)
print("-- claims side, drop one")
for k in 'ABCMU': row(f"  without leg {k}",''.join(x for x in 'ABCMU' if x!=k),ALL)
print("-- both sides, drop two")
for c in ALL:
    for k in 'ABCMU': 
        r=run(''.join(x for x in 'ABCMU' if x!=k),[x for x in ALL if x!=c])
        if r[0]==12 and r[1]<=1 and r[3]<=20.5: print(f"  without {c} and leg {k}: identical")
