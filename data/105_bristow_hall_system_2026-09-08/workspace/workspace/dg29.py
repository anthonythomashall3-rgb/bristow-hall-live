import sys,io,contextlib,pickle
sys.argv=['x','2011','2012','w29dg']
src=open('walk29.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
SUM.update(pickle.load(open('cache/w29_sum.pkl','rb')))
CH=pickle.load(open('cache/w29_prog.pkl','rb'))['chosen']
p72=CH[pd.Timestamp('1972-01-01')]
cut=pd.Timestamp('1972-01-01'); ks=[i for i in range(13) if ANNT[i]<cut]; kt=[i for i in range(13) if TANNT[i]<cut]
print('ks',ks,'kt',kt)
for d_ in (8,6,5,4):
    q=dict(p72); q['cD']=d_; s=summary(q); c=clean(q,cut,ks,kt)
    print('cD',d_,'clean',None if c is None else obj(c),'fa',[x.date().isoformat() for x in s['fa']],'pair4',s['pair'].get(4),'lags',{i:s['lags'][i] for i in ks})
    r,t=build_v(q)
    print('   turns 1969-73:',[(x['kind'][0],x['published'].date().isoformat(),x['date'].strftime('%Y-%m'),x['leg']) for x in t if pd.Timestamp('1969-01-01')<=x['published']<=pd.Timestamp('1973-12-31')])
