"""The American 1969 peak, +4 on current data, dated on the vintages of the time (ALFRED wide
files on disk: INDPRO, PAYEMS, UNRATE, AWHMAN, MANEMP; the income, consumption, household and
sales vintages begin 1961-65 or 2010, so the panel of the time is production, payrolls,
unemployment, manufacturing hours and manufacturing employment).  Shipped level clauses, the
memo's window (peak - 12 to trough + 12, closed at the vintage's last month)."""
import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/rt')
import alfred as al, bristow_rule_v3 as B, pandas as pd
pk=pd.Timestamp('1969-12-01'); tr=pd.Timestamp('1970-11-01'); w0=pk-pd.DateOffset(months=12); w1=tr+pd.DateOffset(months=12)
for day in ('1970-12-31','1971-06-30','1971-12-31','1972-12-31','1975-12-31','1980-12-31','1990-12-31','2000-12-31','2010-12-31','2026-08-31'):
    chs=[]
    for sid,kind in (('INDPRO','level'),('PAYEMS','level'),('UNRATE','rate'),('AWHMAN','level'),('MANEMP','level')):
        s=al.asof(sid,day)
        if s is not None and s.index.min()<=w0 and s.index.max()>=tr: chs.append((sid,B.procyclical(s.astype(float),kind)))
    end=min(w1,max(s.index.max() for _,s in chs))
    r=B.date_episode(chs,w0,end,band_trough=0.12,band_peak=0.01,smooth=3,lookback=12,peak_cap=18)
    e1=B._md(r['peak'],pk) if r['peak'] is not None else None; e2=B._md(r['trough'],tr) if r['trough'] is not None else None
    print(f'vintage {day}: peak {r["peak"]:%Y-%m} ({e1:+d})  trough {r["trough"]:%Y-%m} ({e2:+d})  channels {[c for c,_ in chs]}')
