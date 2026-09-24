"""Does the pair, in its v2.7 form (three-month housing mean at 31, rate half four tenths over an eighteen-month minimum), now reach its line
in the 2024 window? If it does, the low branch — which DOES propose in 2024 (the advance insured rate reaches 0.30) — could call 2024 long
before the hub's 2 August. Also: the vacancy object's own shape (k-month mean vs back-month maximum) swept, and the hours pair's."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast41.py').read().split("def full(")[0].replace("out=open('fast41.out','w')","out=open('probe24.out','w')"))
Hc,MX=mkpair2(31,4,3,18)
P("pair (v2.7 form) monthly readings 2023-06..2024-12:",[(m.strftime('%Y-%m'),round(float(v),2)) for m,v in MX['2023-06':'2024-12'].items()])
rate18=(((UR-UR.rolling(18).min())*10).round()/4.0); hh3=(lh.rolling(12).max()-lh.rolling(3).mean())/31.0
P("  rate half:",[(m.strftime('%Y-%m'),round(float(v),2)) for m,v in rate18['2023-10':'2024-10'].items()])
P("  housing half:",[(m.strftime('%Y-%m'),round(float(v),2)) for m,v in hh3['2023-10':'2024-10'].items()])
gs=(spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna()
P("  low-branch proposals 2023-2026 (first prints):",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in leg_gapL(spl,0.25,52,rearm='window') if d>=pd.Timestamp('2023-01-01')])
P("  and on the current file:",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in leg_gapL(s_cur,0.25,52,rearm='window') if d>=pd.Timestamp('2023-01-01')])
P("  2025-26 pair readings:",[(m.strftime('%Y-%m'),round(float(v),2)) for m,v in MX['2025-06':].items()])
P("\nVACANCY OBJECT SHAPE — currently the two-month mean below the six-month maximum. Its span and the line it needs:")
sys.path.insert(0,W+'/lab/slack'); from objects import load
o=load(); vac=o['-vacancy rate'] if '-vacancy rate' in o else None
P("  lab keys:",[k for k in o.keys()][:14])
out.close()
