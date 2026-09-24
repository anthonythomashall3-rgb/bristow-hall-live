"""THE LAST FIVE. With the claims deep branch at 7.5 per cent needing two demand objects the median is 26 and eight of
thirteen are inside the month. Outside it: 1953 (62), 1957 (40), 1960 (91), 1969 (37) and 2024 (66). This asks, for
each of those five, WHAT EVERY DEMAND OBJECT ACTUALLY REACHES inside its window — because a two-of-N branch can afford
looser lines, and the question is whether any pair of objects gets there at all."""
exec(open('fast53.py').read().split('P("=== baseline and the claims deep branch found in fast52 ===")')[0].replace("out=open('fast53.out','w')","out=open('fast54.out','w')"))
G=vgap(4,4); Hc,MX=mkpair3(29,4,3,18); Hh=mkhours(2.0,1.20)
OBJS=[('vacancy (line 0.20)',G,0.20),('hours pair (line 1.00)',Hh['gap'],Hh['line']),('housing x rate pair (line 1.00)',MX,1.0),('paper spread (line 1.323)',GSP,LINE)]
P(f"{'turn':9s} {'object':32s} {'best in window':>15s} {'line':>8s} {'ratio':>7s}  when")
for i in [1,2,3,4,12]:
    lo=PK[i]-pd.DateOffset(months=6); hi=PK[i]+pd.DateOffset(months=4)+pd.offsets.MonthEnd(0)
    for nm,gx,ln in OBJS:
        w=gx[(gx.index>=lo)&(gx.index<=hi)].dropna()
        if not len(w): P(f"{PK[i]:%Y-%m}  {nm:32s} {'(no data)':>15s}"); continue
        P(f"{PK[i]:%Y-%m}  {nm:32s} {float(w.max()):15.3f} {ln:8.3f} {float(w.max())/ln:7.2f}  {w.idxmax():%Y-%m}")
    P("")
P("AND THE PROPOSERS in the same five windows (reading divided by its line, so 1.00 is at the line):")
gU=(spl-spl.rolling(91,min_periods=91).min().shift(1)).dropna()/0.45
gL=(spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna()/0.25
m4=ICfp.rolling(4).mean(); gI=((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()/50.0
gI2=((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()/7.5
gX=(g/0.43).dropna()
for i in [1,2,3,4,12]:
    lo=PK[i]-pd.DateOffset(months=6); hi=PK[i]+pd.DateOffset(months=4)+pd.offsets.MonthEnd(0)
    row=[]
    for nm,gx in [('U/0.45',gU),('L/0.25',gL),('claims/50%',gI),('claims/7.5%',gI2),('hub/0.43',gX)]:
        w=gx[(gx.index>=lo)&(gx.index<=hi)].dropna()
        row.append(f"{nm} {float(w.max()):.2f}" if len(w) else f"{nm} -")
    P(f"   {PK[i]:%Y-%m}: "+" | ".join(row))
out.close()
