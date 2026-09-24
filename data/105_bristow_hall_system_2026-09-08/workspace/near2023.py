"""How close the insured-rate proposer (0.45 above its 91-week low) came to firing outside a recession, 1962-2026,
on the data the rule reads. Run: /opt/homebrew/bin/python3 near2023.py"""
import sys
sys.argv=['near2023.py','1962','2026','m41']
exec(open('walk40.py').read().split('# ---- the walk itself')[0])
gap=(spl-spl.rolling(91,min_periods=91).min().shift(1)).dropna()
rec=[(PK[i]-pd.DateOffset(months=6),TR[i]) for i in range(13)]
out=gap[[not any(a<=t<=b for a,b in rec) for t in gap.index]]
print('largest readings of the 0.45 object OUTSIDE any recession window (six months before the peak to the trough):')
top=out.sort_values(ascending=False)
seen=set()
for t,v in top.items():
    y=t.year
    if y in seen: continue
    seen.add(y); print('  ',t.strftime('%Y-%m-%d'),round(float(v),3))
    if len(seen)>=8: break
print('2023 by week (gap above 0.30):'); print(gap['2023'][gap['2023']>=0.30].round(2).to_string())
g52=(spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna(); o52=g52[[not any(a<=t<=b for a,b in rec) for t in g52.index]]
print('largest readings of the 0.20 object (52-week low) outside any recession window, by year:')
seen=set()
for t,v in o52.sort_values(ascending=False).items():
    if t.year in seen: continue
    seen.add(t.year); print('  ',t.strftime('%Y-%m-%d'),round(float(v),3))
    if len(seen)>=8: break
