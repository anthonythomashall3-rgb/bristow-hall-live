"""THE TROUGH-SIDE BINDING TABLE. On the onset side, asking which half of the conjunction the tool was waiting for
reframed the whole speed problem in one run. The closers have never been asked. Each closer's own call for every
episode is printed beside the one the chronology took, so the margin between the winner and the runner-up is visible,
and so the object that is actually holding the tool up is named."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('tbind.out','w')"))
p=dict(BASE); p['deep']=999; p['wline']=0.30; p['wline2']=0.60; p['bshare']=0.50
r,t=build9(p)
took={}
for i in range(13):
    c=[x for x in t if x['kind']=='trough' and TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12)]
    if c: took[i]=c[0]
P(f"{'trough':8s} {'taken':11s} {'leg':4s} {'lag':>5s} {'err':>4s} |  every closer's own call in the window, earliest first")
for i in range(13):
    tr=TR[i]; row=[]
    for k in ['K','J','H','S']:
        cand=[(pp,dd) for pp,dd in TLH.get(k,[]) if tr-pd.DateOffset(months=6)<=dd<=tr+pd.DateOffset(months=12)]
        for pp,dd in cand: row.append(((pp-me(tr)).days,k,pp,dd))
    row.sort()
    tk=took.get(i)
    lead=f"{tr:%Y-%m}  {tk['published']:%Y-%m-%d}  {tk['leg']:4s} {(tk['published']-me(tr)).days:5d} {((tk['date'].year-tr.year)*12+tk['date'].month-tr.month):+4d} | " if tk else f"{tr:%Y-%m}  {'-':11s} {'':4s} {'':5s} {'':4s} | "
    P(lead+"  ".join(f"{k}:{lg:+d}d/{dd:%Y-%m}" for lg,k,pp,dd in row))
P("\nHOW MUCH IS ON THE TABLE: the earliest closer in each window against the one taken")
gap=[]
for i in range(13):
    tr=TR[i]; row=[]
    for k in ['K','J','H','S']:
        for pp,dd in TLH.get(k,[]):
            if tr-pd.DateOffset(months=6)<=dd<=tr+pd.DateOffset(months=12): row.append(((pp-me(tr)).days,k))
    if not row or i not in took: continue
    row.sort(); best=row[0]; tk=(took[i]['published']-me(tr)).days
    gap.append(tk-best[0])
    P(f"   {tr:%Y-%m}  taken {tk:+4d} by {took[i]['leg']}   earliest available {best[0]:+4d} by {best[1]}   gap {tk-best[0]:+d}")
P(f"   total days left on the table across the record: {sum(gap)}, median gap {np.median(gap):.0f}")
P("\nWHAT A CLOSER WOULD HAVE TO BEAT: the date each episode's fastest closer fired, and what the demand side was doing")
out.close()
