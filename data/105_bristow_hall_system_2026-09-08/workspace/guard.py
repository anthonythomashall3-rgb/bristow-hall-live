"""THE NOISE GUARD (9 September 2026): the claims proposer's effective line = max(45, k x the object's own dispersion),
the dispersion being the median absolute deviation of the object over the prior five years of weeks in deep expansion
(the rule closed for at least 24 months, and not within six months before a peak the rule later called) - computed
causally week by week from the rule's OWN chronology (the frozen calls at today's lines), no committee dates.
Reports the guard's path, whether it ever exceeded 45 before 2020, and the weeks it would have bound.
Run: /opt/homebrew/bin/python3 guard.py"""
import sys,pickle
sys.argv=['guard.py','1962','2026','m41']
exec(open('walk40.py').read().split('# ---- the walk itself')[0])
p0=pickle.load(open('cache/w40_carry.pkl','rb'))
r,t=build_v(p0)
opens=[x['published'] for x in t if x['kind']=='peak']; closes=[x['published'] for x in t if x['kind']=='trough']
m4=ICfp.dropna().rolling(4).mean(); ic=((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()
# the rule's own state, causally: a week is 'deep expansion' if the last event before it was a close at least 24 months earlier
ev=sorted([(d,'o') for d in opens]+[(d,'c') for d in closes])
def deep_at(w):
    prev=[e for e in ev if e[0]<=w]
    if not prev: return True
    d,k=prev[-1]
    return k=='c' and (w-d).days>=730
flag=pd.Series([deep_at(w) for w in ic.index],index=ic.index)
K=7
guard={}
for w in ic.index:
    if w.year<1972: continue
    hist=ic[(ic.index>=w-pd.DateOffset(years=5))&(ic.index<w)]; hist=hist[flag.reindex(hist.index).fillna(False).values]
    if len(hist)<52: continue
    mad=float((hist-hist.median()).abs().median()); guard[w]=max(45.0,K*mad)
G=pd.Series(guard)
print('guard = max(45, %d x MAD) : years in which the guard exceeded 45 and the maximum line that year:'%K)
ab=G[G>45]; print({y:round(float(ab[ab.index.year==y].max()),1) for y in sorted(set(ab.index.year))})
print('the claims object at the rule\'s own I-branch openings (line 45) and the guard then:')
for x in t:
    if x['kind']=='peak' and x['leg']=='I': w=x['published']; wk=ic[ic.index<=w].index.max(); print('  ',w.strftime('%Y-%m-%d'),'reading',round(float(ic[wk]),1),'guard',round(float(G.get(wk,45.0)),1))
print('weeks 2021 on where the reading was within 5 points of 45, with the guard:')
for w,v in ic['2021':].items():
    if v>=40: print('  ',w.strftime('%Y-%m-%d'),round(float(v),1),'guard',round(float(G.get(w,45.0)),1))
print('guard path, median by year 2019-2026:',{y:round(float(G[G.index.year==y].median()),1) for y in range(2019,2027) if len(G[G.index.year==y])})
