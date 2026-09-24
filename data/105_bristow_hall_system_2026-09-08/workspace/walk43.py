"""WALK 43 - WALK 42 WITH THE CLAIMS OBJECT'S MOVING BASE (the frozen sweeps of 9 September 2026, `ml/famF.py`).
The initial-claims proposer measures its rise from its 52-week low. Here the base is the higher of that low and 85 per
cent of the four-week mean's trailing five-year median (as published): a rise off a base that is abnormally low
against the object's own recent norm is a return toward the norm, not a turn (August 2022: claims 43.9 per cent above
a 52-week low - the four-week mean's low of April 2022, 178,750, the lowest since May 1969 and 22 per cent under its
five-year median; against the floored base, 31.4). Everything else is walk42's: the
co-signer, the grid (claims 60/50/45/40/35), the release days, the walk. Structural reason stated (Rule 20); declared
after the 2022 case was seen (Rule Zero).
Run:  python3 walk43.py 1962 2026 w43"""
import sys,pickle,os
_MARK="# ---- the walk "+"itself"
exec(open('walk42.py').read().split(_MARK)[0].replace("walk42_%s.out","walk43_%s.out"))
import pandas as pd, numpy as np
ALPHA=0.85; MED_W=260
def leg_ic_c(s,pct,band=IC_BAND,look=52):
    m4=s.rolling(4).mean(); low=m4.rolling(look,min_periods=look).min().shift(1); med=m4.rolling(MED_W,min_periods=156).median().shift(1)
    base=np.maximum(low,ALPHA*med); rel_=(m4/base-1)*100
    c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pct:
            day=rel_ic(t)
            if v>=pct+band or cosign(day): c.append((day,pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return c
# ---- the walk itself: walk39's loop, verbatim ----
exec(open('walk39.py').read().split(_MARK)[1].split("\n",1)[1])
