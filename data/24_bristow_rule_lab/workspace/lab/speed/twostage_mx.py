"""The two-stage trough in Mexico on INEGI's Encuesta Mensual de Opinión Empresarial (EMOE).

The EMOE (manufacturing since January 2004; open data lab/acq/mexsurv/emoe/, fetched 2
September 2026 from inegi.org.mx/contenidos/programas/emoe/2018/datosabiertos/
emoe_mensual_csv.zip, unadjusted) is published on the first working day of the month after
the month it describes - a zero-lag survey in the sense of section 8c.  Three indicators for
manufacturing: the confidence indicator ICE (five questions on the country's and the firm's
situation and the moment to invest), the aggregate-trend indicator IAT (production, capacity
use, domestic demand, exports, employment, investment, stocks, prices), and the IPM, the
pedidos-manufactureros index (orders, production volume, expected employment, delivery times,
input stocks); each also by seven manufacturing groups, for a breadth reading.  Adjusted here
in real time (ecbcs_speed.sa_rt).

Stage 1 is the level route's D on the Mexican panel of section 13d (industrial production,
construction, exports, imports, retail volume, unemployment, IGAE, vehicle production; each
reading in hand two months after its month - the IGAE's own lag; the others arrive sooner).
Stage 2 as twostage_ec: the survey rising `a` points from its minimum for `r` months, dated at
the minimum, published in the month after the data month.  Scored against the committee's
two troughs in the survey era (May 2009, May 2020) and ECRI's two; the earlier troughs of
2002 and 1995 lie before the survey.  Beside it the tool's own trough clause on the same D.
"""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/speed'); sys.path.insert(0,'/home/claude/lab/mex')
import numpy as np, pandas as pd
import bristow_rule_v3 as B
from bench import load
import ecbcs_speed as E, twostage_ec as T2
ACQ='/home/claude/lab/acq/mexsurv/emoe/conjunto_de_datos'
KEI='/home/claude/lab/kei'
COMM_T=[E.ts(x) for x in ['2009-05','2020-05']]
ECRI_T=[E.ts(d) for k,d in E.ECRI['Mexico'] if k=='T' and d>='2004-06']
def panel():
    return [('industrial production',load(f'{KEI}/MEX_PRVM_BTE.csv')),('construction production',load(f'{KEI}/MEX_PRVM_F.csv')),
            ('exports',load(f'{KEI}/MEX_EX__T.csv')),('imports',load(f'{KEI}/MEX_IM__T.csv')),('retail volume',load(f'{KEI}/MEX_TOVM_G47.csv')),
            ('unemployment',100.0-load(f'{KEI}/MEX_UNEMP__T.csv')),('IGAE',load('/home/claude/lab/mex/MEX_igae_sa.csv')),('vehicle production',load('/home/claude/lab/mex/MEX_vehicles_sa.csv'))]
def d_available():
    D=B.composite_deviation(panel(),12,3,1).dropna(); D.index=D.index+pd.DateOffset(months=2); return D
def emoe(file, col, activity='Industrias manufactureras'):
    d=pd.read_csv(f'{ACQ}/{file}',dtype=str); d.columns=[c.strip() for c in d.columns]
    d=d[d.DESCRIPCION_ACTIVIDAD.str.strip()==activity]
    t=pd.to_datetime(dict(year=d.ANIO.str.strip().astype(int),month=d.MES.str.strip().astype(int),day=1))
    return pd.Series(pd.to_numeric(d[col].str.strip(),errors='coerce').values,index=t).dropna().sort_index()
def emoe_groups(file, col):
    d=pd.read_csv(f'{ACQ}/{file}',dtype=str); d.columns=[c.strip() for c in d.columns]
    out={}
    for act,g in d.groupby(d.DESCRIPCION_ACTIVIDAD.str.strip()):
        if act=='Industrias manufactureras': continue
        t=pd.to_datetime(dict(year=g.ANIO.str.strip().astype(int),month=g.MES.str.strip().astype(int),day=1))
        out[act]=pd.Series(pd.to_numeric(g[col].str.strip(),errors='coerce').values,index=t).dropna().sort_index()
    return pd.DataFrame(out)
def shift_pub(calls): return [(p+pd.DateOffset(months=1),d) for p,d in calls]
def enco(col):
    """INEGI's consumer confidence survey (ENCO, with Banxico), monthly from April 2001, unadjusted
    (lab/acq/mexsurv/enco/MEX_enco_icc_nsa.csv, pulled 2 September 2026 from the BIE tabulado
    service, series 454168-454173); published in the first week of the following month, so a
    call on month T is public in T+1 like the Watchers survey"""
    d=pd.read_csv('/home/claude/lab/acq/mexsurv/enco/MEX_enco_icc_nsa.csv',index_col=0,parse_dates=True)
    return d[col].dropna()
if __name__=='__main__':
    D=d_available(); print('D in hand',D.index.min().strftime('%Y-%m'),'->',D.index.max().strftime('%Y-%m'))
    SER={'ICE manufacturing':('emoe_ind_manufactura_ice_ipm_2004_2025.csv','ICE'),'IPM manufacturing':('emoe_ind_manufactura_ice_ipm_2004_2025.csv','IPM'),
         'IAT manufacturing':('emoe_ind_manufactura_iat_2004_2025.csv','IAT'),'IAT production':('emoe_ind_manufactura_iat_2004_2025.csv','PRODUCCION'),
         'IAT domestic demand':('emoe_ind_manufactura_iat_2004_2025.csv','DEMANDA_INTERNA'),'IPM orders':('emoe_ind_manufactura_ice_ipm_2004_2025.csv','PEDIDOS'),
         'ICE present situation of the firm':('emoe_ind_manufactura_ice_ipm_2004_2025.csv','SIT_ECON_PRESENTE_EMP')}
    ENCO={'ENCO consumer confidence':'ICC','ENCO household now vs a year ago':'hogar_actual','ENCO country now vs a year ago':'pais_actual','ENCO durables, a good time to buy':'bienes_duraderos'}
    for label,T in (('the committee',COMM_T),('ECRI',ECRI_T)):
        print(f'\n=== troughs against {label} ({len(T)}): {[t.strftime("%Y-%m") for t in T]}')
        for which,col in ENCO.items():
            s=E.sa_rt(enco(col)).dropna(); rows=[]
            for a,r in itertools.product((2.,3.,5.,8.),(1,2,3)):
                calls=shift_pub(T2.twostage(D,s,a,r)); rows.append((T2.line(f'  {which} a={a} r={r}',calls,T,show=False),a,r,calls))
            rows.sort(key=lambda x:(x[0][0],-x[0][1],x[0][5],x[0][4]),reverse=True)
            for res,a,r,calls in rows[:2]: T2.line(f'  {which} a={a:.0f} r={r}',calls,T)
        tt=[(p,d) for p,d in B.real_time_trough_calls(panel(),publication_lag=2,fall_months=4,drop=0.5,min_channels=1) if d>=pd.Timestamp('2004-06-01')]
        T2.line("the tool's own clause on D, published +2 months",tt,T)
        for which,(f,col) in SER.items():
            s=E.sa_rt(emoe(f,col)).dropna(); rows=[]
            for a,r in itertools.product((2.,3.,5.,8.),(1,2,3)):
                calls=shift_pub(T2.twostage(D,s,a,r)); rows.append((T2.line(f'  {which} a={a} r={r}',calls,T,show=False),a,r,calls))
            rows.sort(key=lambda x:(x[0][0],-x[0][1],x[0][5],x[0][4]),reverse=True)
            for res,a,r,calls in rows[:2]: T2.line(f'  {which} a={a:.0f} r={r}',calls,T)
        X=pd.DataFrame({c:E.sa_rt(v.dropna()) for c,v in emoe_groups('emoe_ind_manufactura_ice_ipm_2004_2025.csv','ICE').items()}).dropna(how='all')
        rows=[]
        for k,q,r in itertools.product((1,2,3),(60.,70.,80.,90.,100.),(1,2)):
            ch=X.diff(k); Bd=(ch>0).sum(axis=1)/ch.notna().sum(axis=1)*100.0
            C=((X-X.rolling(120,min_periods=36).mean())/X.rolling(120,min_periods=36).std()).mean(axis=1)
            out=[]; state='quiet'; open_at=None; last=None
            for t in Bd.index:
                if t not in D.index or np.isnan(Bd[t]): continue
                dd=float(D[t])
                if state=='quiet':
                    if dd>=2.0 and (last is None or T2.md(t,last)>=12): state='open'; open_at=t
                elif state=='open':
                    seg=Bd[open_at:t]
                    if len(seg)>=r and bool((seg.iloc[-r:]>=q).all()):
                        cs=C[open_at-pd.DateOffset(months=3):t].dropna(); m=cs.idxmin() if len(cs) else t
                        out.append((t,m)); last=m; state='recover'
                else:
                    if dd<2.0: state='quiet'
            calls=shift_pub(out); rows.append((T2.line(f'  ICE breadth of seven groups k={k} q={q:.0f} r={r}',calls,T,show=False),k,q,r,calls))
        rows.sort(key=lambda x:(x[0][0],-x[0][1],x[0][5],x[0][4]),reverse=True)
        for res,k,q,r,calls in rows[:2]: T2.line(f'  ICE breadth of seven groups k={k} q={q:.0f} r={r}',calls,T)
