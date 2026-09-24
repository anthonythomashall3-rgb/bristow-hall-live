# walk30 = walk29 with the run fixed at three falling weeks, not walked (collection 104, 8 September 2026)
s=open('walk29.py').read()
def rep(a,b):
    global s
    assert s.count(a)==1,(a,s.count(a)); s=s.replace(a,b)
rep('"""WALK 29 - WALK 28 WITH THE RUN OF TWO FALLING WEEKS REMOVED FROM THE GRID','"""WALK 30 - WALK 29 WITH THE RUN FIXED AT THREE FALLING WEEKS, NOT WALKED (collection 104, 8 September 2026).\nThe run of falling weeks is a convention about weekly noise, not a magnitude to be chosen: three consecutive falls is\nthe conventional minimum for a weekly series to have a direction (the four-week average exists for the same reason).\nIn walk29 the run began at four, the safest value, and moved to three at the 1972 cut once the 1970 trough was\nratified; the only close that difference touched was 1970 itself, closed by K at +52 under the run of four where C\nwould have closed it at +24 under the run of three. Fixing the run at three removes a walked number and leaves the\ndrop D and the market bar s as the only numbers C carries into the grid. Declared after walk29, and logged as such.\n\nWALK 29 - WALK 28 WITH THE RUN OF TWO FALLING WEEKS REMOVED FROM THE GRID')
rep("CD_=[8,6,5,4]; CN_=[4,3]; CS_=[30,25,20,15]","CD_=[8,6,5,4]; CN_=[3]; CS_=[30,25,20,15]")
rep("('cD',[8,6,5,4,None]),('cn',[4,3]),('cs',[30,25,20,15]),","('cD',[8,6,5,4,None]),('cn',[3]),('cs',[30,25,20,15]),")
rep("hback=6,cD=8,cn=4,cs=30)","hback=6,cD=8,cn=3,cs=30)")
rep("out=open('walk29_%s.out'%sys.argv[1],'w')","out=open('walk30_%s.out'%sys.argv[1],'w')")
open('walk30.py','w').write(s); print('walk30 written')
