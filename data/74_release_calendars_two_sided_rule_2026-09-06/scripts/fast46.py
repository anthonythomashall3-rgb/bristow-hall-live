"""v3.0 RECORD SCRIPT: v2.9 plus a THIRD proposer — initial claims, the fastest weekly object the Department publishes (five days after its
week). Four-week mean 50 per cent above its 52-week minimum, re-armed at a new minimum, confirmed like the 0.45 branch (vacancy or hours pair).
50 and 60 give the identical record and 50 is the safer corner; 45 additionally buys 2001 but is a singleton; 40 makes a July 2022 call.
Buys 2020: 33 -> 26 days, inside the month. Margins, quiet proposals and the live reading reported."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast45.py').read().split("go8('v2.9 (no initial-claims leg)',None)")[0].replace("out=open('fast45.out','w')","out=open('fast46.out','w')"))
def inw(dd): return any(p_-pd.DateOffset(months=6)<=dd<=t for p_,t in zip(PK,TR))
m4=(IC.rolling(4).mean()/IC.rolling(4).mean().rolling(52,min_periods=52).min().shift(1)-1)*100
m4f=(ICfp.rolling(4).mean()/ICfp.rolling(4).mean().rolling(52,min_periods=52).min().shift(1)-1)*100
for nm,ser in [('current file',m4),('first prints',m4f)]:
    q=[(t,v) for t,v in ser.dropna().items() if not any(p_-pd.DateOffset(months=9)<=t<=t2+pd.DateOffset(months=18) for p_,t2 in zip(PK,TR))]
    top=sorted(q,key=lambda x:-x[1])[:5]
    P(f"initial claims, {nm}: highest readings in quiet weeks {[(t.strftime('%Y-%m-%d'),round(v,0)) for t,v in top]} -> the 50 per cent line clears the highest by {50-top[0][1]:.0f} points")
    P(f"   the thirteen recessions' maxima: {[int(ser[(ser.index>=p_-pd.DateOffset(months=6))&(ser.index<=t2)].max()) if len(ser[(ser.index>=p_-pd.DateOffset(months=6))&(ser.index<=t2)]) else None for p_,t2 in zip(PK,TR)]}")
    P(f"   2025-26 maximum: {round(float(ser['2025-01':].max()),0)} per cent")
    P(f"   quiet proposals at 50 per cent: {[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in leg_ic(IC if nm=='current file' else ICfp,50) if not inw(d)]}")
P("")
for pct in [None,60,50,45]: go8(f"v3.0 with initial claims at {pct}%" if pct else "v2.9 (no initial-claims leg)",pct)
P("\nWITHIN THE MONTH: v3.0 has six of thirteen called within thirty-one days of the peak month's end (1948, 1980, 1990, 2001, 2007, 2020) and four of those before the month ended.")
P("The seven outside, and the publication that binds each: 1953 (71) and 1957 (40) the Fieldhouse monthly insured rate on the tenth of the following month; 1960 (91) the vacancy's release on the thirtieth; 1969 (37) and 1973 (35) the housing-starts release; 1981 (55) the insured rate's own crossing week; 2024 (94) the employment report that carries Sahm's line.")
out.close()
