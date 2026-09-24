exec(open('expose.py').read().split('print(f"\\n{\'object\':52}')[0])
import pandas as pd
WALLS={'1973-11':pd.Timestamp('1974-03-30'),'1981-07':pd.Timestamp('1981-12-20'),'2007-12':pd.Timestamp('2008-05-05')}
PUB={'AWHMAN':5,'PAYEMS':5,'MANEMP':5,'INDPRO':15,'HOUST':17}
rows=[]
for s,v in FP.items():
    for label,o in forms(s,v):
        for line in (0.2,0.3,0.5,0.75,1.0,1.5,2.0,2.5,3.0,4.0):
            at,win,n=exposure(o,line)
            if win>5.8 or at==0: continue
            gains={}
            for pk,callday in WALLS.items():
                w=o[(o.index>=pd.Timestamp(pk+'-01')-pd.DateOffset(months=2))&(o.index<=pd.Timestamp(pk+'-01')+pd.DateOffset(months=8))]
                hit=w[w>=line]
                if len(hit)==0: gains[pk]=None; continue
                m=hit.index[0]
                pub=(m+pd.DateOffset(months=1)).replace(day=PUB[s])
                gains[pk]=(m.strftime('%Y-%m'), pub.date().isoformat(), (pub-callday).days)
            if any(g and g[2]<0 for g in gains.values()):
                rows.append((label,line,win,gains))
rows.sort(key=lambda r: sum(g[2] for g in r[3].values() if g and g[2]<0))
print(f"{'object':50}{'line':>5}{'expo':>7}   gains at the three walls (month -> published, days vs the current call)")
for label,line,win,g in rows[:16]:
    txt=" | ".join(f"{pk}: {v[0]}→{v[1]} {v[2]:+d}d" if v else f"{pk}: none" for pk,v in g.items())
    print(f"{label:50}{line:>5}{win:>6.1f}%  {txt}")
print(f"\ncandidates that move at least one wall: {len(rows)}")
