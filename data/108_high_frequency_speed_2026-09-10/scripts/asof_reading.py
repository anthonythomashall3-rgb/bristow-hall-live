# The search week's reading on each day of March 2020 as a user would have seen it, from the as-of windows
# (google_trends/asof/<tag>_asof_2020-03-DD.csv: a daily window 1 July 2019 -> DD, normalized to its own maximum).
# Reading on day DD = 7-day mean of the index through DD, over its base: the 28-day mean's low over the window
# (shifted one day; the window is shorter than a year, so the low is over what the window holds) - the 0.85 x median
# half of the base needs three years and is absent. Prints the reading for every tag and day found.
# Run: .venv/bin/python scripts/asof_reading.py [asof_dir]   (default google_trends/asof)
import os,sys,glob,re
import pandas as pd, numpy as np
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
d=sys.argv[1] if len(sys.argv)>1 else 'google_trends/asof'
rows=[]
for f in sorted(glob.glob(os.path.join(d,'*_asof_2020-03-*.csv'))):
    tag=os.path.basename(f).split('_asof_')[0]; day=re.search(r'(2020-03-\d\d)',f).group(1)
    s=pd.read_csv(f,index_col=0,parse_dates=True).iloc[:,0].astype(float)
    s=s[s.index<=pd.Timestamp(day)]
    m7=s.rolling(7,min_periods=7).mean(); m28=s.rolling(28,min_periods=20).mean(); lo=m28.expanding(min_periods=60).min().shift(1)
    rel=(m7/lo-1)*100
    v=rel.iloc[-1]; rows.append((tag,day,round(float(v),1) if not np.isnan(v) else None,int(s.iloc[-1]),round(float(m7.iloc[-1]),1),round(float(lo.iloc[-1]),1)))
df=pd.DataFrame(rows,columns=['term','as of','7-day mean over base, %','index that day','7-day mean','base'])
print(df.to_string(index=False))
