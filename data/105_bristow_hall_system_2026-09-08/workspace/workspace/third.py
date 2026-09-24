exec(open('legU.py').read().split('U=leg_U()')[0])
U=leg_U(); PLU=dict(PL); PLU['U']=U
import numpy as np, csv, pandas as pd
AL=os.path.expanduser("~/mnt/")+"Onset Detector Data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/"
def first_prints(series):
    rows=list(csv.reader(open(AL+series+"_all_vintages.csv"))); h=rows[0]
    dates=[pd.Timestamp(r[0]) for r in rows[1:]]; out={}
    for j in range(1,len(h)):
        col=[rows[1+i][j] for i in range(len(dates))]
        idx=[i for i,v in enumerate(col) if v not in ('','.')]
        if not idx: continue
        m=dates[idx[-1]]
        if m not in out: out[m]=float(col[idx[-1]])
    return pd.Series(out).sort_index()
P3=-(first_prints("PAYEMS")/first_prints("PAYEMS").shift(3)-1)*100
AW=(first_prints("AWHMAN").rolling(6).max()/first_prints("AWHMAN")-1)*100
PK5=('A','B','C','M','U'); TR3=('K','J','H')
def rep(nm, second):
    r=run({k:PLU[k] for k in PK5},{k:TLG[k] for k in TR3}) if second is None else None
    if second is not None:
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            r=score(B.american_chronology({k:PLU[k] for k in PK5},{k:TLG[k] for k in TR3},sahm=g,second=second),'x','1948-06-01')
    lp,ep,lt=r['lags_p'],r['errs_p'],r['lags_t']
    print(f"{nm}")
    print(f"   peaks {len(lp)}/12  other {r['other']}  | median {np.median(lp):.0f} d  worst {max(lp)}  in-month {sum(1 for l in lp if l<=0)}  <=31d {sum(1 for l in lp if l<=31)}  | dates exact {sum(1 for e in ep if e==0)} mae {np.mean(np.abs(ep)):.2f}")
    print(f"   lags {lp}")
V=[dict(name='vacancy(2,6)',gap=vr,line=0.36,pub_day=30)]
rep("FROZEN: Sahm 0.50 OR vacancy 0.36", V)
rep("+ payrolls 3-month fall >=0.3% (first prints)", V+[dict(name='payroll3',gap=P3,line=0.3,pub_day=5)])
rep("+ factory hours off 6-month max >=2.5%", V+[dict(name='hours',gap=AW,line=2.5,pub_day=5)])
rep("+ payrolls AND hours", V+[dict(name='payroll3',gap=P3,line=0.3,pub_day=5),dict(name='hours',gap=AW,line=2.5,pub_day=5)])
MN=first_prints("MANEMP")
M3=-(MN/MN.shift(3)-1)*100
M12=(MN.rolling(12).max()/MN-1)*100
P3b=P3
BASE=V+[dict(name='payroll3',gap=P3,line=0.3,pub_day=5)]
rep("base+payrolls, then + factory payrolls 3-month >=2.0%", BASE+[dict(name='manemp3',gap=M3,line=2.0,pub_day=5)])
rep("base+payrolls, then + factory payrolls off 12-month max >=3.0%", BASE+[dict(name='manemp12',gap=M12,line=3.0,pub_day=5)])
rep("payrolls at 0.5% instead of 0.3%", V+[dict(name='payroll3',gap=P3,line=0.5,pub_day=5)])
rep("payrolls 0.3% + factory payrolls 3-month 2.5%", BASE+[dict(name='manemp3',gap=M3,line=2.5,pub_day=5)])
