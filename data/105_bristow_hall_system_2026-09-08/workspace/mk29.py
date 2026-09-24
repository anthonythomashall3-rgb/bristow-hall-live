# walk29 = walk28 with the run of two falling weeks removed from the grid (collection 104, 8 September 2026)
s=open('walk28.py').read()
def rep(a,b):
    global s
    assert s.count(a)==1,(a,s.count(a)); s=s.replace(a,b)
rep('"""WALK 28 - WALK 27 WITH THE PRE-1980 ANNOUNCEMENT DATES SOURCED','"""WALK 29 - WALK 28 WITH THE RUN OF TWO FALLING WEEKS REMOVED FROM THE GRID (collection 104, 8 September 2026).\nwalk28 loosened C to a drop of 4 with a run of 2 at the 1977 cut, rewarded by the two ratified troughs of 1970 and\n1975, and that configuration closed the 1980 recession on 14 February 1980, 168 days early, on a two-week fall in the\nflow with the market fifteen per cent off its low: a false start of the claims rise, a pattern the two ratified troughs\ncould not show. The frozen screen shows the same run of two closing 2009 five months early. A run of two falling\nweeks is inside the week-to-week noise of a weekly series and cannot establish a direction; three is the conventional\nminimum, and the other closers on the menu already carry run-length floors declared on the same ground. The grid for\nn is therefore [4,3]. Declared after walk28, and logged as such.\n\nWALK 28 - WALK 27 WITH THE PRE-1980 ANNOUNCEMENT DATES SOURCED')
rep("CD_=[8,6,5,4]; CN_=[4,3,2]; CS_=[30,25,20,15]","CD_=[8,6,5,4]; CN_=[4,3]; CS_=[30,25,20,15]")
rep("('cD',[8,6,5,4,None]),('cn',[4,3,2]),('cs',[30,25,20,15]),","('cD',[8,6,5,4,None]),('cn',[4,3]),('cs',[30,25,20,15]),")
rep("out=open('walk28_%s.out'%sys.argv[1],'w')","out=open('walk29_%s.out'%sys.argv[1],'w')")
open('walk29.py','w').write(s); print('walk29 written')
