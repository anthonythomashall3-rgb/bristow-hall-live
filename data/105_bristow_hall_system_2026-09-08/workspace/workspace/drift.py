"""DRIFT DIAGNOSTIC (9 September 2026): do the proposers' expansion-time readings drift toward or away from their fixed
lines over the decades? For each proposer object, the largest reading in deep expansion (outside six months before a
peak to twenty-four months after a trough) by decade, as a fraction of its walk-end line; and the dispersion of the
object in those weeks (median absolute deviation), by decade. Run: /opt/homebrew/bin/python3 drift.py"""
import sys
sys.argv=['drift.py','1962','2026','m41']
exec(open('walk40.py').read().split('# ---- the walk itself')[0])
win=[(PK[i]-pd.DateOffset(months=6),TR[i]+pd.DateOffset(months=24)) for i in range(13)]
def deep(s): return s[[not any(a<=t<=b for a,b in win) for t in s.index]]
m4=ICfp.dropna().rolling(4).mean()
objs={'insured 91-wk (0.45)':((spl-spl.rolling(91,min_periods=91).min().shift(1)).dropna(),0.45),
      'insured 52-wk (0.20)':((spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna(),0.20),
      'survey-week (0.4)':((SI-SI.rolling(52,min_periods=52).min().shift(1)).dropna(),0.4),
      'claims 4-wk % (45)':(((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna(),45),
      'state breadth (0.60)':(BR.dropna(),0.60),
      'unemp. gap (0.367)':(g.dropna(),0.3667)}
dec=list(range(1960,2030,10))
print('%-22s'%'object','  '.join('%5ds'%d for d in dec))
print('largest deep-expansion reading as a fraction of the line:')
for k,(s,line) in objs.items():
    d=deep(s); row=[]
    for y in dec:
        x=d[(d.index.year>=y)&(d.index.year<y+10)]
        row.append('%6s'%('%.2f'%(x.max()/line) if len(x) else '  -'))
    print('%-22s'%k,' '.join(row))
print('median absolute deviation of the object in deep expansion (its noise), by decade:')
for k,(s,line) in objs.items():
    d=deep(s); row=[]
    for y in dec:
        x=d[(d.index.year>=y)&(d.index.year<y+10)]
        row.append('%6s'%('%.3f'%float((x-x.median()).abs().median()) if len(x) else '  -'))
    print('%-22s'%k,' '.join(row))
print('level of the insured rate at its 91-week low, by decade (median):')
lo=spl.rolling(91,min_periods=91).min().shift(1).dropna(); d=deep(lo)
print(' '.join('%ds %.2f'%(y,float(d[(d.index.year>=y)&(d.index.year<y+10)].median())) for y in dec if len(d[(d.index.year>=y)&(d.index.year<y+10)])))
print('vacancy rate level (V0), median by decade:')
print(' '.join('%ds %.2f'%(y,float(V0[(V0.index.year>=y)&(V0.index.year<y+10)].median())) for y in dec if len(V0[(V0.index.year>=y)&(V0.index.year<y+10)])))
