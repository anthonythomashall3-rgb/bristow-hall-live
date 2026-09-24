import sys,io,contextlib
sys.argv=['x','2011','2012','wspr']
src=open('walk34.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
print('CPB 1997-08..1998-01', CPB['1997-08-01':'1998-01-31'].round(2).tolist()[:8])
for per in ['2001-01','2007-10','2008-03','2008-12','2020-03','2024-05','2024-10','2026-08']:
    seg=CPB[per]; g=GSP[per]; print(per,'CPB',None if seg.empty else round(float(seg.iloc[-1]),2),'GSP',None if g.empty else round(float(g.iloc[-1]),2))
print('spread line', CFG.get('spr') if 'CFG' in dir() else 'n/a')
