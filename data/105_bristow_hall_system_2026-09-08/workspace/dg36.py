import sys,io,contextlib,pickle
sys.argv=['x','2011','2012','w36dg']
src=open('walk36.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
p=dict(BASE15); s=summary(p)
print('BASE15 lags',{PK[i].strftime('%Y-%m'):v for i,v in s['lags'].items()}); print('missing',[PK[i].strftime('%Y-%m') for i in range(13) if i not in s['lags']]); print('fa',[x.date().isoformat() for x in s['fa']])
# try the loosest peak-side lines without the vacancy: which pre-1962 peaks can any configuration reach?
best=None
import itertools
for u45,low,hline,spr in itertools.product([0.45,0.30],[0.35,0.20,0.15],[0.85,0.80],[0.9]):
    q=dict(p); q.update(u45=u45,low=low,hline=hline,spr=spr); s=summary(q)
    miss=[PK[i].strftime('%Y-%m') for i in range(4) if i not in s['lags']]; fa=[x.date().isoformat() for x in s['fa'] if x<pd.Timestamp('1962-01-01')]
    print(u45,low,hline,'missing pre-1962',miss,'fa pre-1962',fa)
