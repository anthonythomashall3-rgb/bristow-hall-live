"""Ratio-to-moving-average seasonal adjustment.

The textbook procedure: divide the series by its centred twelve-month moving
average, average the ratios by calendar month, normalise the twelve factors to
average one, and divide the original series by its month's factor.  Stateless and
one-pass, so a date produced from it in month t uses only data through t.
"""
import pandas as pd, numpy as np
def sa_ratio_ma(s):
    s=s.dropna().astype(float)
    if len(s)<36: return s
    ma=s.rolling(12,center=True).mean().rolling(2,center=True).mean().shift(-1)
    r=(s/ma).dropna()
    f=r.groupby(r.index.month).median()
    f=f/f.mean()
    out=s/ s.index.month.map(f)
    return pd.Series(out.values,index=s.index)
