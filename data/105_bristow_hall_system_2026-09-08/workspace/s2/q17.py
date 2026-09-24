# q17.py - the trough closers on the release-day vintage: build the as-of objects (s2/asof_trough.py), compare every
# closer's calls with the first-print versions, and run the rule frozen at w46's walk-end lines on both.
# Run in the workspace: PYTHONPATH=. python3 s2/q17.py
import sys,pickle,io,contextlib,os
sys.path.insert(0,os.getcwd()); sys.argv=['walk46.py','1962','2026','w46']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
exec(open('walk46.py').read().split(_MARK)[0])
pw=pickle.load(open('cache/w46_carry.pkl','rb'))
# 0. the raw S proposals: TLH['S'] as walked must equal _confirm_close(TLC['S']) on the first-print objects
chk=_confirm_close(TLC['S'])
print('S as walked == _confirm_close(TLC[S]) on first prints:',chk==TLH['S'],len(chk),len(TLH['S']))
r0,t0=build_v(pw)
def closes(t): return [(x['published'].date().isoformat(),x['date'].strftime('%Y-%m'),x['leg']) for x in t if x['kind']=='trough']
def opens(t): return [(x['published'].date().isoformat(),x['leg']) for x in t if x['kind']=='peak']
print('FROZEN first-print closers: troughs',len(r0['lags_t']),closes(t0))
exec(open('s2/asof_trough.py').read())
def diff(name,a,b):
    a=[(p.date().isoformat(),d.strftime('%Y-%m')) for p,d in a]; b=[(p.date().isoformat(),d.strftime('%Y-%m')) for p,d in b]
    only_a=[x for x in a if x not in b]; only_b=[x for x in b if x not in a]
    print(f'  {name}: first-print {len(a)} as-of {len(b)} | only first-print {only_a[:8]} | only as-of {only_b[:8]}')
print('closers, first print against release-day vintage:')
for s_ in (8,6,5,4): diff(f'R[{s_}]',_TL_FIRSTPRINT['RC'][s_],RC[s_])
for s_ in (6,5,4,3): diff(f'T[{s_}]',_TL_FIRSTPRINT['TC'][s_],TC[s_])
for s_ in (13,10,8,6): diff(f'Q[{s_}]',_TL_FIRSTPRINT['QC'][s_],QC[s_])
diff('S',_TL_FIRSTPRINT['S'],TLH['S'])
r1,t1=build_v(pw)
print('FROZEN as-of closers: peaks',len(r1['lags_p']),'others',r1['other'],'| troughs',len(r1['lags_t']),closes(t1))
print('peaks identical:',opens(t0)==opens(t1),'| closes identical:',closes(t0)==closes(t1))
