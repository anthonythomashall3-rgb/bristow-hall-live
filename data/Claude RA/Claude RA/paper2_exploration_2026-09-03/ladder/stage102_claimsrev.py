"""Stage 102: does using current-vintage claims instead of first prints ever change the
claims-floor verdict?  If not, the first-print replay -- limited to 2003 only by claims --
can be extended to 1960, where UNRATE, HOUST, PAYEMS and INDPRO all have real vintages."""
import os
import numpy as np, pandas as pd
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
df=pd.read_csv(BASE+"/data_fetched/other/icsa_first_vs_current.csv", parse_dates=["week"])
df["fv"]=pd.to_datetime(df.first_vintage.astype(str), format="%Y%m%d")
gen=df[df.fv>pd.Timestamp("2009-05-28")].copy()      # weeks with a genuine first print
r=(gen.current/gen.first_print-1)*100
print("weeks with a genuine first print: %d (%s -> %s)" % (len(gen),gen.week.min().date(),gen.week.max().date()))
print("revision of the weekly level, percent: mean %.3f  sd %.3f  |max| %.2f  |rev|>1%%: %d (%.1f%%)"
      % (r.mean(),r.std(),r.abs().max(),(r.abs()>1).sum(),100*(r.abs()>1).mean()))
# the object the rule actually uses: 8-week mean over its own 52-week minimum
def floorseries(x):
    s=pd.Series(x.values,index=x.index).sort_index()
    m8=s.rolling(8).mean()
    return (m8/m8.rolling(52).min()-1)
a=df.set_index("week").sort_index()
fp=floorseries(a.first_print); cv=floorseries(a.current)
both=pd.concat([fp.rename("fp"),cv.rename("cv")],axis=1).dropna()
both=both[both.index>=pd.Timestamp("2009-08-01")]
print("\nthe claims-floor statistic (8-week mean over its 52-week minimum), 2009-08 onward: %d weeks" % len(both))
print("  correlation %.5f | mean abs difference %.5f | max abs difference %.4f"
      % (both.fp.corr(both.cv), (both.fp-both.cv).abs().mean(), (both.fp-both.cv).abs().max()))
for th in (0.03,0.12):
    d=( (both.fp>=th) != (both.cv>=th) )
    print("  floor at %2.0f%%: verdict differs in %d of %d weeks (%.2f%%)%s"
          % (100*th,d.sum(),len(d),100*d.mean(),
             "  weeks: "+", ".join(str(x.date()) for x in both.index[d][:8]) if d.sum() else ""))
