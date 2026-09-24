# q38.py - THE SEARCH WEEK ON THREE LABOUR TERMS, THE FULL RULE FROZEN 1948-2026 at walk54's walk-end lines (10 September
# 2026, evening). "unemployment" alone (v3.27/v3.28) against "unemployment" + "layoffs" + "laid off" (walk55's object):
# every call, any call outside a recession, the 2020 open, and each term's fires with and without the market gate.
# Run: PYTHONPATH=. python3 s2/q38.py
import sys,os,io,contextlib,pickle
sys.path.insert(0,os.getcwd()); sys.argv=['walk54.py','1962','2026','w54']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
SEARCH_TERMS=['unemp','layoffs','laidoff']; os.environ['BHS_SEARCH_TERMS']=','.join(SEARCH_TERMS)
with contextlib.redirect_stdout(io.StringIO()): exec(open('walk54.py').read().split(_MARK)[0])
p=pickle.load(open('cache/w54_carry.pkl','rb'))
REC=[(pd.Timestamp(a)-pd.DateOffset(months=6),pd.Timestamp(b)+pd.offsets.MonthEnd(0)) for a,b in zip(PK,TR)]
def inwin(d): return any(a<=d<=b for a,b in REC)
for tag,(day,g7,rel) in GT_TERMS.items():
    alone=[]; armed=True
    for t,v in rel.items():
        d=t+pd.Timedelta(days=1)
        if armed and v>=p['kc'][0]-EPS: alone.append(d); armed=False
        elif not armed and v<=EPS: armed=True
    gated=[d for d,m in leg_K_search_one(rel,p['kc'][0],p['kc'][1])]
    print(f"{tag}: history {day.index.min().date()}..{day.index.max().date()} | alone fires {len(alone)}, outside a recession window {len([d for d in alone if not inwin(d)])} | with the gate {[d.date().isoformat() for d in gated]} outside {[d.date().isoformat() for d in gated if not inwin(d)]}")
    print('   March 2020 (datum day -> reading):',{t.strftime('%m-%d'):round(float(v),1) for t,v in rel['2020-03-08':'2020-03-16'].items()})
for terms in (['unemp'],['unemp','layoffs','laidoff']):
    GT_TERMS_ALL=dict(GT_TERMS); GT_TERMS.clear(); GT_TERMS.update({k:GT_TERMS_ALL[k] for k in terms})
    r,t=build_v(p); op={i:(r['opens'][i]['published'].date().isoformat(),r['opens'][i]['leg']) for i in r['opens']}
    print(f"terms {terms}: peaks {len(r['lags_p'])}/13 other {r['other']} lags {[r['lags_p'][i] for i in sorted(r['lags_p'])]} | 2020 {op.get(11)} | troughs {len(r['lags_t'])}/13")
    print('   opens',op)
    GT_TERMS.clear(); GT_TERMS.update(GT_TERMS_ALL)
