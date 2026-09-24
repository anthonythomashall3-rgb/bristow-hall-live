import sys; sys.path.insert(0,'/home/claude/lab')
from us import *
import pandas as pd, numpy as np

rows=[]
def peak_rule(stat, thr, tail=12, anchor='episode'):
    def f(pk,tk):
        w=window(None,stat,pk,tk,thr,tail,anchor)
        if w is None: return None
        seg=stat[w[0]:w[1]].dropna()
        return seg.idxmax() if len(seg) else None
    return f

# --- A. lookback length, difference form ---
for L in (6,9,12,15,18,24,36):
    st=sahm(U,L)
    rows.append(score(f'A. difference, lookback {L}m (peak)', peak_rule(st,0.50), PK,TR))
show(rows,'A. Does a different lookback help? (US postwar, threshold 0.50)')

# --- B. functional form at L=12 ---
rows=[]
rows.append(score('B0. difference  u3 - min12            ', peak_rule(sahm(U,12),0.50), PK,TR))
rows.append(score('B1. ratio       u3/min12 - 1          ', peak_rule(sahm_ratio(U,12),0.10), PK,TR))
rows.append(score('B2. z-scored difference (10y sd)      ', peak_rule(sahm_z(U,12),1.0), PK,TR))
rows.append(score('B3. difference / 10y max              ', peak_rule(sahm_relmax(U,12),0.30), PK,TR))
rows.append(score('B4. 3-month change of u3              ', peak_rule(delta(U,3),0.30), PK,TR))
rows.append(score('B5. 12-month change of u3             ', peak_rule(delta(U,12),0.50), PK,TR))
show(rows,'B. Functional form (peak of the statistic)')
