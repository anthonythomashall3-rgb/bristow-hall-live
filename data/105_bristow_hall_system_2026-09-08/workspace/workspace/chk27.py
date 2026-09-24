import sys,io,contextlib
sys.argv=['x','2011','2012','wchk']
src=open('walk27.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
print('ICfp',ICfp.dropna().index[0].date(),'CC',_CCw.index[0].date(),'IUR',_IURw.index[0].date(),'SPX',_SPX.index[0].date(),'FI',_FI.index[0].date())
print('TR',[t.strftime('%Y-%m') for t in TR]); print('PK',[t.strftime('%Y-%m') for t in PK])
for key in [(8,4,15),(6,3,15),(4,3,15)]:
    print(key,[(p.date().isoformat(),d.strftime('%Y-%m')) for p,d in CMENU[key] if p<pd.Timestamp('1971-01-01')])
print('K pre-1971',[(p.date().isoformat(),d.strftime('%Y-%m')) for p,d in TLH['K'] if p<pd.Timestamp('1971-01-01')][:12])
