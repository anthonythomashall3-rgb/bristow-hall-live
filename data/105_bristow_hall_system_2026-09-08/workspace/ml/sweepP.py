import time
RES={}
for fam in ('P','C'):
    print('==== family',fam)
    for pU in (15,20,25,30,35,40,45):
        for pL in (8,10,12,15,20):
            t0=time.time(); r,t=build_alt(p0,fam,dict(pU=pU,pL=pL)); RES[(fam,pU,pL)]=(r,t)
            report(f"{fam} pU={pU} pL={pL}",r,t)
    import sys; sys.stdout.flush()
import pickle; pickle.dump({k:(v[0]['called'],v[0]['other'],[(x['published'],x['kind'],x['leg']) for x in v[1]]) for k,v in RES.items()},open('cache/ml_sweepPC.pkl','wb'))
