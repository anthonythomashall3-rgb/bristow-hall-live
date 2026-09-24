"""Where does the July 1981 call come from, and why is it +142 days here when
the parallel route reaches +122? Print every leg's 1981 call and leg U's gap
week by week through 1981."""
exec(open('legU.py').read().split('U=leg_U()')[0])
import pandas as pd, numpy as np
U=leg_U(); PLU=dict(PL); PLU['U']=U
peak=pd.Timestamp('1981-07-01'); end=pd.Timestamp('1981-07-31')
print("every peak leg's call nearest July 1981 (published, dated, lag in days from 31 Jul 1981)")
for k,v in PLU.items():
    near=[(p,d) for p,d in v if pd.Timestamp('1980-10-01')<=p<=pd.Timestamp('1982-06-30')]
    for p,d in near:
        print(f"   leg {k}: published {p:%Y-%m-%d}  dated {d:%Y-%m}   lag {(p-end).days:+5d} d")
print("\nleg U at other lines (calls in 1981-82 only):")
for line in (0.30,0.35,0.40,0.45,0.50):
    Ux=leg_U(line=line)
    n=[(p,d) for p,d in Ux if pd.Timestamp('1981-01-01')<=p<=pd.Timestamp('1982-06-30')]
    tot=len(Ux)
    print(f"   line {line:.2f}: {tot} calls in the whole record; 1981-82: "
          + (', '.join(f'{p:%Y-%m-%d}>{d:%Y-%m} ({(p-end).days:+d} d)' for p,d in n) or 'none'))
print("\nthe IURSA gap week by week, Mar 1981 - Jan 1982 (line 0.50):")
x=s; gap=x - x.rolling(52,min_periods=52).min().shift(1)
w=gap['1981-03-01':'1982-01-31']
for t,v in w.items():
    mark=' <== 0.50' if v>=0.50 else (' <-- 0.35' if v>=0.35 else '')
    print(f"   {t:%Y-%m-%d}  rate {x[t]:5.2f}  gap {v:+.3f}{mark}")
