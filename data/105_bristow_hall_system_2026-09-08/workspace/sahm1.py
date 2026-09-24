"""TESTED THE WAY SAHM TESTED HERS. Sahm's protocol, in her own terms: fix the line once, compute the indicator from the
unemployment rate AS PUBLISHED at each date, run it forward continuously, and count two things - how long after each
peak the line was crossed, and how many times it was crossed when no recession followed. No windows around a peak are
drawn in advance; every crossing counts, and a crossing with no recession behind it is a false positive. Her own
published series SAHMREALTIME is run here on exactly that protocol, and this rule is run beside it on the same clock."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk3.py').read().split('CACHE6={}')[0].replace("out=open('walk3_%s.out'%sys.argv[1],'w')","out=open('sahm1.out','w')"))
DD=os.environ['HOME']+'/mnt/Onset Detector Data/22_recession_chronologies/monthly'
SR=pd.read_csv(DD+'/SAHMREALTIME.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
SC=pd.read_csv(DD+'/SAHMCURRENT.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
P(f"SAHMREALTIME {SR.index.min():%Y-%m} to {SR.index.max():%Y-%m}, {len(SR)} months | SAHMCURRENT {SC.index.min():%Y-%m} to {SC.index.max():%Y-%m}")
def crossings(s,line,start):
    """every crossing of the line, re-armed when the indicator falls back below it, published on the employment report"""
    out_=[]; armed=True
    for m,v in s.items():
        if m<start: continue
        if armed and v>=line:
            pub=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
            out_.append((pub,m)); armed=False
        elif not armed and v<line: armed=True
    return out_
def sahm_score(nm,cr,start,fwd=12):
    """a crossing is a hit if a peak falls in [crossing month - 6, crossing month + 12]; anything else is a false positive"""
    used=set(); hits=[]; fp=[]
    for pub,m in cr:
        k=None
        for i,pk in enumerate(PK):
            if i in used or pk<start: continue
            if m-pd.DateOffset(months=fwd)<=pk<=m+pd.DateOffset(months=6): k=i; break
        if k is None:
            inside=any(pk-pd.DateOffset(months=6)<=m<=tr+pd.DateOffset(months=3) for pk,tr in zip(PK,TR))
            if not inside: fp.append((pub.strftime('%Y-%m-%d'),m.strftime('%Y-%m')))
        else:
            used.add(k); mo=(m.year-PK[k].year)*12+m.month-PK[k].month
            hits.append((k,mo,(pub-me(PK[k])).days))
    miss=[PK[i].strftime('%Y-%m') for i in range(13) if PK[i]>=start and i not in used]
    P(f"\n{nm}")
    P("   "+" | ".join(f"{PK[k]:%Y-%m} +{mo}mo ({d:+d}d)" for k,mo,d in hits))
    P(f"   detected {len(hits)}/{len(hits)+len(miss)}  missed {miss}")
    if hits:
        mm=[mo for _,mo,_ in hits]; dd=[d for _,_,d in hits]
        P(f"   months after the peak: median {np.median(mm):.1f}, mean {np.mean(mm):.1f}, worst {max(mm)}")
        P(f"   days after the peak month ended: median {np.median(dd):.0f}, mean {np.mean(dd):.1f}, within the month {sum(1 for x in dd if x<=31)}/{len(dd)}")
    P(f"   FALSE POSITIVES (crossings outside every recession episode): {len(fp)} {fp}")
    return hits,fp
ST=pd.Timestamp('1959-12-01')
sahm_score("Sahm's own published real-time indicator, line 0.50, from December 1959",crossings(SR,0.50,ST),ST)
sahm_score("the same indicator on the current file (SAHMCURRENT), line 0.50",crossings(SC,0.50,ST),ST)
ST70=pd.Timestamp('1970-01-01')
sahm_score("SAHMREALTIME from January 1970, the sample of her paper",crossings(SR,0.50,ST70),ST70)
p=dict(BASE); p['deep']=999
r,t=build6(p)
cr=[(x['published'],x['date']) for x in t if x['kind']=='peak' and x['published']>=ST]
sahm_score("this rule, frozen at v3.5, read real-time, on the same protocol from December 1959",cr,ST)
cr61=[(a,b) for a,b in cr if a>=pd.Timestamp('1961-11-03')]
sahm_score("this rule from November 1961, the date every object exists",cr61,pd.Timestamp('1961-11-03'))
out.close()
