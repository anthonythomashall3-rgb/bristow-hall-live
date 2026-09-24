"""Minimal-rule harness: runs the lab's state machine on any leg/confirmer set and scores against the
twelve committee turns PLUS Paper 1's 2024 (peak 2024-04, trough 2024-08)."""
import shim, sys, io, contextlib, pickle, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
W=shim.W
import bristow_rule_v3 as B
o=pickle.load(open('cache/objects.pkl','rb'))
g=o['sahm']; vr=o['vac']; PL=o['PL']; TLG=o['TLG']
PK=o['PK']+[pd.Timestamp('2024-04-01')]; TR=o['TR']+[pd.Timestamp('2024-08-01')]
def md(a,b): return (a.year-b.year)*12+a.month-b.month
def me(t): return t+pd.offsets.MonthEnd(0)
SEC=dict(S=None, V=dict(name='vacancy',gap=vr,line=0.36,pub_day=30))
# housing35 x rate pair and hours x nondurable pair, first prints (as frozen in v8)
import csv
AL=W.replace('24_bristow_rule_lab/workspace','onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/')
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
UR=first_prints('UNRATE'); HO=first_prints('HOUST'); lh=np.log(HO)*100
PAIR=pd.concat([(lh.rolling(12).max()-lh.rolling(2).mean())/35.0,(UR-UR.rolling(12).min())/0.20],axis=1).min(axis=1).dropna()
AWH=first_prints('AWHMAN'); ND=first_prints('NDMANEMP')
f12=lambda v,l:(v.rolling(12).max()/v-1)*100/l; f3=lambda v,l:(-(v/v.shift(3)-1)*100)/l
P1=pd.concat([f12(AWH,2.0),f3(ND,1.20)],axis=1).min(axis=1).dropna()
SEC['H']=dict(name='housing35',gap=PAIR,line=1.0,pub_day=18)
SEC['P']=dict(name='hourspair',gap=P1,line=1.0,pub_day=5)
def chron(pk, tl, confs, sahm=None, back=6, fwd=4):
    if sahm is None: sahm=('S' in confs)
    second=[SEC[c] for c in confs if c!='S']
    with contextlib.redirect_stdout(io.StringIO()):
        return B.american_chronology({k:pk[k] for k in pk},{k:tl[k] for k in tl},sahm=(g if sahm else None),line=0.5,
                                     second=(second or None),horizon_months=fwd,back_months=back)
def score13(turns, start='1948-06-01', verbose=False):
    pk=[t for t in turns if t['kind']=='peak' and t['published']>=pd.Timestamp(start)]
    tr=[t for t in turns if t['kind']=='trough' and t['published']>=pd.Timestamp(start)]
    used_p=set(); used_t=set(); lags_p={}; errs_p={}; lags_t={}; errs_t={}; other=[]; opens={}
    for t in pk:
        c=[i for i,(p,q) in enumerate(zip(PK,TR)) if p-pd.DateOffset(months=6)<=t['date']<=q and i not in used_p]
        cm=c[0] if c else None
        if cm is not None:
            used_p.add(cm); lags_p[cm]=(t['published']-me(PK[cm])).days; errs_p[cm]=md(t['date'],PK[cm]); opens[cm]=t
        else: other.append((t['published'].strftime('%Y-%m-%d'),t['date'].strftime('%Y-%m'),t['leg']))
        nxt=[u for u in tr if u['published']>t['published']]
        if nxt and cm is not None:
            u=nxt[0]; ct=[i for i,q in enumerate(TR) if abs(md(u['date'],q))<=6 and i not in used_t]
            if cm in ct: ct=[cm]
            if ct:
                used_t.add(ct[0]); lags_t[ct[0]]=(u['published']-me(TR[ct[0]])).days; errs_t[ct[0]]=md(u['date'],TR[ct[0]])
    return dict(called=sorted(used_p),lags_p=lags_p,errs_p=errs_p,closed=sorted(used_t),lags_t=lags_t,errs_t=errs_t,other=other,opens=opens,turns=turns)
def rep(nm, turns, start='1948-06-01', n_expected=13, first_peak_index=0):
    r=score13(turns,start)
    idx=[i for i in range(first_peak_index,13)]
    lp=[r['lags_p'][i] for i in idx if i in r['lags_p']]; ep=[r['errs_p'][i] for i in idx if i in r['errs_p']]
    lt=[r['lags_t'][i] for i in idx if i in r['lags_t']]; et=[r['errs_t'][i] for i in idx if i in r['errs_t']]
    missed=[PK[i].strftime('%Y-%m') for i in idx if i not in r['lags_p']]
    line=(f"{nm:40} peaks {len(lp)}/{len(idx)} other {len(r['other'])} | med {np.median(lp) if lp else float('nan'):4.0f}d mean {np.mean(lp) if lp else float('nan'):5.1f} worst {max(lp) if lp else 0:4d} in-mo {sum(1 for l in lp if l<=0)} <=31d {sum(1 for l in lp if l<=31)} | exact {sum(1 for e in ep if e==0)} mae {np.mean(np.abs(ep)) if ep else 0:.2f}"
          f" | troughs {len(lt)}/{len(idx)} med {np.median(lt) if lt else float('nan'):4.0f}d worst {max(lt) if lt else 0:4d} exact {sum(1 for e in et if e==0)}")
    print(line)
    if missed: print(f"{'':40}   missed: {missed}")
    if r['other']: print(f"{'':40}   other calls: {r['other']}")
    # 2024 detail
    if 12 in r['opens']:
        t=r['opens'][12]; print(f"{'':40}   2024: opened {t['published']:%Y-%m-%d} by {t['leg']} dated {t['date']:%Y-%m}" + (f"; closed lag {r['lags_t'][12]} d err {r['errs_t'][12]:+d}" if 12 in r['lags_t'] else "; NOT CLOSED"))
    return r
