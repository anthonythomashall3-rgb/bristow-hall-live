#!/usr/bin/env python3
"""1161 (21 Nov 2026; no AI): months of State payrolls printed before the State's BLS series begins.

BLS's own series of total nonfarm payrolls starts late for four States (Minnesota January 1950). For Minnesota the months of January 1947
to December 1949 were printed in the BLS monthly report "Employment and Payrolls" (FRASER; collection
1161_chain_cells_minnesota_1947_49_2026-11-21, every reading by eye). data/payroll_prints_1161/<ST>.csv holds them on one basis
(the series printed from July 1949; before June 1948 the old and the new prints agree), with the 12 months of the first BLS year as overlap.

extend(st, s): s is the State's BLS series (thousands, not seasonally adjusted, monthly). Each printed month before s begins is put on the
BLS series' basis by the ratio BLS / print of the same calendar month of the overlap year (the two series differ by a seasonal pattern:
0.99 in January to 1.03 in July 1950), and joined in front of s. A State with no file is returned unchanged."""
import os
import pandas as pd
D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'payroll_prints_1161')
def extend(st, s):
    f = os.path.join(D, f'{st}.csv')
    if not os.path.isfile(f): return s
    p = pd.read_csv(f); p = pd.Series(p.employees_thousands.astype(float).values, index=pd.to_datetime(p.month + '-01'))
    t0 = s.index[0]; ov = p[(p.index >= t0) & (p.index < t0 + pd.DateOffset(months=12))]
    assert len(ov) == 12 and t0.month == 1, (st, 'the overlap must be the 12 months of the first BLS year')
    r = (s.reindex(ov.index) / ov); r.index = r.index.month
    pre = p[p.index < t0]; assert (pre.index == pd.date_range(pre.index[0], t0 - pd.DateOffset(months=1), freq='MS')).all(), st
    add = pd.Series([v * r[m.month] for m, v in pre.items()], index=pre.index).round(1)
    return pd.concat([add, s])
