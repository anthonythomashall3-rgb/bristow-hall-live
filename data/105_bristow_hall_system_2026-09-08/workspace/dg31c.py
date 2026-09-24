import sys,io,contextlib,pickle
sys.argv=['x','2011','2012','w31dg']
src=open('walk31.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
w30=pickle.load(open('cache/w30_carry.pkl','rb'))
def md_(a,b): return (a.year-b.year)*12+a.month-b.month
for menu in (('C',),('K',),('H',),('J',),('S',),('R',),('T',),('Q',)):
    MENU=set(menu); r,t=build_v(w30)
    rows=[]
    for j,x in enumerate(t):
        if x['kind']!='peak' or x['published']<pd.Timestamp('1961-11-03'): continue
        nxt=next((y for y in t[j+1:] if y['kind']=='trough'),None)
        hit=[i for i in range(13) if abs(md_(x['date'],PK[i]))<=9]
        if not hit: continue
        i=hit[0]
        rows.append((TR[i].strftime('%Y-%m'), None if nxt is None else (nxt['published'].date().isoformat(), md_(nxt['date'],TR[i]))))
    print(menu[0], rows)
