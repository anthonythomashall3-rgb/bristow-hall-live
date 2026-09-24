import sys,io,contextlib,pickle
sys.argv=['x','2011','2012','w31dg']
src=open('walk31.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
SUM.update(pickle.load(open('cache/w31_sum.pkl','rb')))
pg=pickle.load(open('cache/w31_prog.pkl','rb')); CH=pg['chosen']
p62=CH[pd.Timestamp('1962-01-01')]
cut=pd.Timestamp('1962-01-01'); ks=[0,1,2,3]
print('1962 chosen',{k:p62[k] for k in ('u45','low','look','sahm','vl','hline','spr','hback','ic','wline','wline2','bshare')})
for u in [0.70,0.55,0.45,0.35,0.30]:
    q=dict(p62); q['u45']=u; s=summary(q); c=clean(q,cut,ks,[])
    print('u45',u,'errp0-3',[s['errp'].get(i) for i in range(4)],'lagsdays',[s['lags'].get(i) for i in range(4)],'obj',None if c is None else obj(c),'fa',[x.date().isoformat() for x in s['fa']][:3])
# the trough side under one clock at walk30's end configuration, full menu vs C only vs C+K
w30=pickle.load(open('cache/w30_carry.pkl','rb'))
def turns_with(p,keep=None):
    global TLH
    old=dict(TLH)
    if keep is not None: TLH={k:v for k,v in TLH.items() if k in keep}
    try: r,t=build_v(p)
    finally: TLH=old
    return t
for keep in (None,('C',),('C','K'),('C','K','H','J')):
    t=turns_with(w30,keep)
    print('menu',keep or 'all', [(x['kind'][0],x['published'].date().isoformat(),x['leg']) for x in t if x['published']>=pd.Timestamp('1969-01-01')])
