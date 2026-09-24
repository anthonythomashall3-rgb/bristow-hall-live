import sys,io,contextlib,pickle
sys.argv=['x','2011','2012','w31dg']
src=open('walk31.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
SUM.update(pickle.load(open('cache/w31_sum.pkl','rb')))
pg=pickle.load(open('cache/w31_prog.pkl','rb')); CH=pg['chosen']
p=CH[max(CH)]; print('last cut',max(CH).year,{k:p[k] for k in ('cD','cn','cs','low','u45','look','wline','wline2','bshare','ic','sahm')})
cut=pd.Timestamp('1977-01-01'); ks=[i for i in range(13) if ANNT[i]<cut]; kt=[i for i in range(13) if TANNT[i]<cut]
print('ks',ks,'kt',kt)
s=summary(p); print('errp',s['errp']); print('fa',s['fa']); print('pair',{i:(v[0].date().isoformat(),v[1],v[2]) for i,v in s['pair'].items()})
print('clean',clean(p,cut,ks,kt))
r,t=build_v(p)
print([(x['kind'][0],x['published'].date().isoformat(),x['date'].strftime('%Y-%m'),x['leg']) for x in t if pd.Timestamp('1973-01-01')<=x['published']<=pd.Timestamp('1976-12-31')])
for pub,kind,dt,leg in sorted(pg['log'],key=lambda z:z[0]): print(f"{pub:%Y-%m-%d} {kind:5s} {dt:%Y-%m} {leg}")
