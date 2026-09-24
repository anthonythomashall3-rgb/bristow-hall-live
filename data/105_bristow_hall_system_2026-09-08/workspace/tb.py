import sys,time
sys.argv=['x','2011','2012','wtb']
src=open('walk26.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
t0=time.time(); exec(src); t1=time.time()
print("preamble",round(t1-t0,1),"s")
import io,contextlib
p=dict(BASE15); p['sahm']=0.3667  # an unusual combination, likely uncached
t2=time.time(); r,t=build_v(p); t3=time.time()
print("build_v",round(t3-t2,2),"s; turns",len(t))
print(sorted(RC.keys()), sorted(TC.keys()), sorted(QC.keys()))
print("RC[8] calls:",[(a.strftime('%Y-%m-%d'),b.strftime('%Y-%m')) for a,b in RC[8]][:30])
print("TLH keys",sorted(TLH))
out.close()
