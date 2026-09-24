from mini import *
N=pd.read_csv(W.replace('24_bristow_rule_lab/workspace','45_dol_first_prints_2026-09/national_first_prints.csv'),parse_dates=['release_date','ic_week_ended','iu_week_ended'])
iur_fp=N.set_index('iu_week_ended')['iur_sa'].dropna(); iur_fp=iur_fp[~iur_fp.index.duplicated()].sort_index()
s_cur=o['iursa']; spl=s_cur.copy(); common=iur_fp.index.intersection(spl.index); spl.loc[common]=iur_fp.loc[common]
def leg_U(series,line=0.50,look=52,pub=5):
    gap=series-series.rolling(look,min_periods=look).min().shift(1); c=[]; armed=True
    for t,v in gap.dropna().items():
        if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0.0: armed=True
    return c
