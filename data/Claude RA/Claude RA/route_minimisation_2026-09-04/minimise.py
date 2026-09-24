import shim, sys, io, contextlib, itertools, numpy as np, pandas as pd
W=shim.W
src=open("/home/claude/lab/weekly/american_chronology.py").read()
src=src.split("if __name__ == '__main__':")[0]
G={"__name__":"notmain"}
exec(compile(src,"ac","exec"),G)
B=G['B']; legs=G['legs']; sahm_rt=G['sahm_rt']; vacancy_gap_rt=G['vacancy_gap_rt']
leg_S=G['leg_S']; leg_S_gated=G['leg_S_gated']; claims_armed=G['claims_armed']; score=G['score']
PK,TR=G['PK'],G['TR']; month_end=G['month_end']; md=G['md']
PL,TLu=legs(safe=False); _,TL=legs(safe=True)
g=sahm_rt(); vr=vacancy_gap_rt(2,6)
SECOND=[dict(name='vacancy(2,6)',gap=vr,line=0.36,pub_day=30)]
arm=claims_armed(); TLG=dict(TL); TLG['S']=leg_S_gated(g,arm)
def run(pl,tl,start='1948-06-01'):
    with contextlib.redirect_stdout(io.StringIO()) as b:
        r=score(B.american_chronology(pl,tl,sahm=g,second=SECOND),'x',start)
    return r
def summarise(r):
    lp,ep=r['lags_p'],r['errs_p']
    return dict(peaks=len(lp),other=r['other'],med=float(np.median(lp)),worst=max(lp),
                inmonth=sum(1 for l in lp if l<=0),within31=sum(1 for l in lp if l<=31),
                exact=sum(1 for e in ep if e==0),mae=round(float(np.mean(np.abs(ep))),2))
print("PEAK-LEG SUBSETS  (second condition fixed: Sahm 0.50 first prints OR vacancy(2,6) 0.36; trough legs = candidate set)")
print(f"  {'legs':8} {'peaks':>5} {'other':>5} {'med':>5} {'worst':>5} {'inMo':>4} {'<=31d':>5} {'exact':>5} {'mae':>5}")
rows=[]
keys=list(PL.keys())
for n in range(1,len(keys)+1):
    for c in itertools.combinations(keys,n):
        try: s=summarise(run({k:PL[k] for k in c},TLG))
        except Exception as e: continue
        rows.append((c,s))
        if s['peaks']==len(PK) and s['other']<=1:
            print(f"  {''.join(c):8} {s['peaks']:>5} {s['other']:>5} {s['med']:>5.0f} {s['worst']:>5} {s['inmonth']:>4} {s['within31']:>5} {s['exact']:>5} {s['mae']:>5}")
print(f"\n  subsets tried {len(rows)}; complete (12/12, <=1 other) {sum(1 for c,s in rows if s['peaks']==len(PK) and s['other']<=1)}")
