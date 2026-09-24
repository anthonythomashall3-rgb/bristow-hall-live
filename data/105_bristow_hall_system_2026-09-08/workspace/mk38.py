# walk38 = walk37 with the hours pair dated by the Employment Situation release calendar (Rule Zero, V321 note §13,
# 8 September 2026). Nothing else changes: same objects, same lines, same grid, same objective, same closers.
s=open('walk37.py').read()
def rep(a,b):
    global s
    assert s.count(a)==1,(a[:60],s.count(a)); s=s.replace(a,b)
rep('"""WALK 37 - WALK 34 WITH THE PAPER SPREAD CORRECTED AFTER AUGUST 1997','"""WALK 38 - WALK 37 WITH THE HOURS PAIR DATED BY THE EMPLOYMENT SITUATION RELEASE CALENDAR (Rule Zero, V321 note\n§13, 8 September 2026). The lab dated the pair the fifth of the following month; the report comes out on the first\nFriday. One diary call was confirmed by the pair (2020) and moves from 5 to 8 May 2020. Otherwise WALK 37 - WALK 34\nWITH THE PAPER SPREAD CORRECTED AFTER AUGUST 1997')
HP='''
# ---- THE HOURS PAIR DATED BY THE RELEASE CALENDAR (relU: the unemployment rate's first-release dates) ----
_mkhours0=mkhours
def mkhours(h1,h2):
    d=dict(_mkhours0(h1,h2))
    d['pubs']=pd.Series({m:(pd.Timestamp(relU[m]) if m in relU.index and not pd.isna(relU[m]) else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4)) for m in d['gap'].index})
    d.pop('pub_day',None); return d
'''
rep("def build_v(p):\n","%sdef build_v(p):\n"%HP)
rep("out=open('walk37_%s.out'%sys.argv[1],'w')","out=open('walk38_%s.out'%sys.argv[1],'w')")
open('walk38.py','w').write(s); print('walk38 written')
