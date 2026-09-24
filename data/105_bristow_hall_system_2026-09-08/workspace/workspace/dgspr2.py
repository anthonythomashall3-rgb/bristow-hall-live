import sys,io,contextlib
sys.argv=['x','2011','2012','wspr2']
src=open('walk37.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
print('aa splice', aa['1997-08-01':'1997-10-15'].round(2).to_dict())
for per in ['2001-01','2007-10','2007-12','2008-03','2008-10','2020-03','2024-05','2024-10','2026-08']:
    seg=CPB[per]; g=GSP[per]; print(per,'CPB',None if seg.empty else round(float(seg.iloc[-1]),2),'GSP',None if g.empty else round(float(g.iloc[-1]),2))
print('GSP max since 1997', round(float(GSP['1997':].max()),2), GSP['1997':].idxmax().date())
