import sys
sys.argv=['x','2011','2012','wns']
src=open('walk26.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
exec(src)
import pandas as pd
names=[k for k,v in list(globals().items()) if isinstance(v,(pd.Series,pd.DataFrame))]
for k in sorted(names):
    v=globals()[k]
    try: print(f"{k:12s} {type(v).__name__:9s} {v.index.min().date() if len(v) else ''} -> {v.index.max().date() if len(v) else ''} n={len(v)}")
    except Exception as e: print(k,type(v).__name__,len(v))
print("dicts:",[k for k,v in globals().items() if isinstance(v,dict) and k in ('TLH','TLG','TLC','RC','TC','QC','rel','relJ','SEC','o')])
print("W=",W)
out.close()
