"""Which weeks produced the 2020s deep-expansion maxima of the claims and insured-rate proposers, and what the
confirmers read then. Run: /opt/homebrew/bin/python3 drift2.py"""
import sys
sys.argv=['drift2.py','1962','2026','m41']
exec(open('walk40.py').read().split('# ---- the walk itself')[0])
win=[(PK[i]-pd.DateOffset(months=6),TR[i]+pd.DateOffset(months=24)) for i in range(13)]
def deep(s): return s[[not any(a<=t<=b for a,b in win) for t in s.index]]
m4=ICfp.dropna().rolling(4).mean(); ic=((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()
d=deep(ic); d=d[d.index.year>=2021]; print('claims object, deep expansion 2021 on, top weeks:'); print(d.sort_values(ascending=False).head(6).round(1).to_string())
u=(spl-spl.rolling(91,min_periods=91).min().shift(1)).dropna(); d=deep(u); d=d[d.index.year>=2021]
print('insured 91-wk object, deep expansion 2021 on, weeks at 0.4:'); print(d[d>=0.4].round(2).to_string())
G=vgap2(4,4); print('vacancy confirmer gap (line 0.20), 2021-06..2023-06:'); print(G['2021-06':'2023-06'].round(2).to_string())
print('deep-expansion weeks 2021 on where claims object >= 40 AND vacancy gap at its line in the prior 6 months:')
for t,v in deep(ic)[deep(ic).index.year>=2021].items():
    if v>=40:
        w=G[(G.index>=t-pd.DateOffset(months=6))&(G.index<=t)]
        print('  ',t.strftime('%Y-%m-%d'),round(float(v),1),'vacancy gap max in prior 6 months',round(float(w.max()),2) if len(w) else None)
