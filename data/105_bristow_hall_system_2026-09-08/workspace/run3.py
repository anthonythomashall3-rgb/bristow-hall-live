from mini import *
from hub import leg_X2
# ---- leg U on the current file and on the Department's advance first prints (collection 45), re-arm when the gap closes
N=pd.read_csv(W.replace('24_bristow_rule_lab/workspace','45_dol_first_prints_2026-09/national_first_prints.csv'),parse_dates=['release_date','ic_week_ended','iu_week_ended'])
iur_fp=N.set_index('iu_week_ended')['iur_sa'].dropna(); iur_fp=iur_fp[~iur_fp.index.duplicated()].sort_index()
s_cur=o['iursa']; spl=s_cur.copy(); common=iur_fp.index.intersection(spl.index); spl.loc[common]=iur_fp.loc[common]
def leg_U(series,line=0.50,look=52,pub=5):
    gap=series-series.rolling(look,min_periods=look).min().shift(1); c=[]; armed=True
    for t,v in gap.dropna().items():
        if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0.0: armed=True
    return c
Uc=leg_U(s_cur); Uf=leg_U(spl)
print('U current    :',[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in Uc])
print('U first print:',[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in Uf])
X=leg_X2()
KJHS={k:TLG[k] for k in 'KJHS'}
def lagrow(nm,turns):
    r=score13(turns); s=[]
    for i in range(13):
        s.append(f"{r['lags_p'][i]:>5d}" if i in r['lags_p'] else '    -')
    lp=list(r['lags_p'].values()); lt=list(r['lags_t'].values())
    print(f"{nm:34}"+''.join(s)+f" | n {len(lp):2d} oth {len(r['other'])} med {np.median(lp):4.0f} worst {max(lp):4d} inmo {sum(1 for l in lp if l<=0)} <=31 {sum(1 for l in lp if l<=31)} | tr {len(lt)} med {np.median(lt):3.0f}")
    if r['other']: print(f"{'':34}   other: {r['other']}")
    return r
print(f"{'lags in days from the peak month-end':34}"+''.join(f"{p:%Y-%m}"[2:].rjust(5) for p in PK))
print("== reference ==")
lagrow("v8 frozen (+S closer)", chron({k:PL[k] for k in 'ABCMU'},KJHS,['S','V','H','P']))
print("== the hub alone and the two-sided minimal rule ==")
lagrow("hub X alone (Sahm & vacancy)", chron({'X':X},KJHS,['V']))
lagrow("U + X, V confirms U", chron({'U':Uc,'X':X},KJHS,['V']))
lagrow("U + X, S|V confirm U", chron({'U':Uc,'X':X},KJHS,['S','V']))
lagrow("U + X, V|H|P confirm U", chron({'U':Uc,'X':X},KJHS,['V','H','P']))
lagrow("U + X, S|V|H|P confirm U", chron({'U':Uc,'X':X},KJHS,['S','V','H','P']))
lagrow("U(fp) + X, S|V|H|P", chron({'U':Uf,'X':X},KJHS,['S','V','H','P']))
lagrow("U alone unconfirmed + X", chron({'U':Uc,'X':X},KJHS,[]) if False else chron({'U':[(p,d) for p,d in Uc],'X':X},KJHS,['S','V','H','P']))
print("== adding the historical legs back ==")
lagrow("B U + X, S|V|H|P", chron({'B':PL['B'],'U':Uc,'X':X},KJHS,['S','V','H','P']))
lagrow("A M U + X, S|V|H|P", chron({'A':PL['A'],'M':PL['M'],'U':Uc,'X':X},KJHS,['S','V','H','P']))
lagrow("A B M U + X (v8 - C + hub)", chron({k:PL[k] for k in 'ABMU'}|{'X':X},KJHS,['S','V','H','P']))
lagrow("A B C M U + X (v8 + hub)", chron({k:PL[k] for k in 'ABCMU'}|{'X':X},KJHS,['S','V','H','P']))
