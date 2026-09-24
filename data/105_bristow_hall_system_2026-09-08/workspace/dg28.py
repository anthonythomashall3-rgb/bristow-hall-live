import sys,io,contextlib
sys.argv=['x','2011','2012','w28dg']
src=open('walk28.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
p=dict(BASE15); s=summary(p)
print('lags',s['lags']); print('early',s['early'],'fa',s['fa'])
print('pair',{i:(v[0].date().isoformat(),v[1],v[2]) for i,v in s['pair'].items()})
print('tro',{i:(v[0].date().isoformat(),v[1]) for i,v in s['tro'].items()})
r,t=build_v(p)
for x in t:
    if x['published']<pd.Timestamp('1963-01-01'): print(x['kind'],x['published'].date(),x['date'].strftime('%Y-%m'),x['leg'])
