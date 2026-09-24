import sys,io,contextlib,pickle
sys.argv=['x','2011','2012','w34dg']
src=open('walk34.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
import numpy as np
pg=pickle.load(open('cache/w34_prog.pkl','rb'))
closes=[(pub,leg) for pub,kind,dt,leg in pg['log'] if kind=='CLOSE']
sp_=np.nan_to_num(_Csp,nan=-99); fc_=np.nan_to_num(_Cfc,nan=-99); du_=np.nan_to_num(_Cdu,nan=-99)
for pub,leg in closes:
    # the firing week: the claims week whose release day is pub, or whose CC/IUR release (+12 d after tc) is pub
    idx=[i for i in range(len(_CW)) if _CpI[i]==pub or (_Ctc[i]+pd.Timedelta(days=12))==pub]
    for i in idx:
        print(pub.date(),leg,'week',_CW[i].date(),'drop %.1f run %d amp %.1f'%(_FI['drop'].values[i],_FI['run'].values[i],_FI['amp'].values[i]),'S&P %.1f CC %.1f IUR %.0f'%(sp_[i],fc_[i],du_[i]))
