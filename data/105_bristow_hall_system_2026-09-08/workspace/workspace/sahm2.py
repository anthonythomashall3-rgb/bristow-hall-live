"""THE NEW RULE ON SAHM'S PROTOCOL, AND WHAT 2024 ACTUALLY OFFERED. First the survey-week and state-breadth rule scored
the way Sahm scored hers. Then every object the tool owns, printed month by month through 2023 and 2024, so that the
2024 lag can be explained by what the objects did rather than asserted."""
import sys,glob,os
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('sahm2.out','w')"))
def crossings_from(t,start):
    return [(x['published'],x['date']) for x in t if x['kind']=='peak' and x['published']>=start]
def sahm_score(nm,cr,start):
    used=set(); hits=[]; fp=[]
    for pub,m in cr:
        k=None
        for i,pk in enumerate(PK):
            if i in used or pk<start: continue
            if m-pd.DateOffset(months=12)<=pk<=m+pd.DateOffset(months=6): k=i; break
        if k is None:
            inside=any(pk-pd.DateOffset(months=6)<=m<=tr+pd.DateOffset(months=3) for pk,tr in zip(PK,TR))
            if not inside: fp.append((pub.strftime('%Y-%m-%d'),m.strftime('%Y-%m')))
        else:
            used.add(k); mo=(m.year-PK[k].year)*12+m.month-PK[k].month; hits.append((k,mo,(pub-me(PK[k])).days))
    miss=[PK[i].strftime('%Y-%m') for i in range(13) if PK[i]>=start and i not in used]
    dd=[d for _,_,d in hits]
    P(f"\n{nm}")
    P("   "+" | ".join(f"{PK[k]:%Y-%m} {d:+d}d" for k,_,d in hits))
    P(f"   detected {len(hits)}/{len(hits)+len(miss)} missed {miss} | median {np.median(dd):.0f}d mean {np.mean(dd):.1f} within the month {sum(1 for x in dd if x<=31)}/{len(dd)} | FALSE POSITIVES {len(fp)} {fp}")
p=dict(BASE); p['deep']=999; p['wline']=0.30; p['wline2']=0.60; p['bshare']=0.50
r,t=build9(p)
sahm_score("v3.6 frozen (survey week 0.30 and 0.50, state breadth 0.50), read real-time, from November 1961",
           crossings_from(t,pd.Timestamp('1961-11-03')),pd.Timestamp('1961-11-03'))
p2=dict(p); p2['bshare']=None
r2,t2=build9(p2)
sahm_score("the same without state breadth",crossings_from(t2,pd.Timestamp('1961-11-03')),pd.Timestamp('1961-11-03'))
P("\n\nWHAT THE OBJECTS DID THROUGH 2023 AND 2024")
G=vgap2(4,4); Hc,MX=mkpair3(29,4,3,18); Hh=mkhours(2.0,1.20)
BRs=BR
rows=pd.date_range('2023-01-01','2025-06-01',freq='MS')
SVgap=(SI-SI.rolling(52,min_periods=52).min().shift(1))
P(f"{'month':8s} {'Sahm gap':>9s} {'vacancy':>8s} {'survey wk':>10s} {'breadth':>8s} {'housing pair':>13s} {'spread':>8s}")
for m in rows:
    sg=g.get(m,float('nan')); vg=G.get(m,float('nan')); sv=SVgap.get(m,float('nan'))
    br=BRs[(BRs.index>=m)&(BRs.index<m+pd.DateOffset(months=1))]
    hp=Hc['gap'].get(m,float('nan')); sp=GSP[(GSP.index>=m)&(GSP.index<m+pd.DateOffset(months=1))]
    P(f"{m:%Y-%m}  {sg:9.3f} {vg:8.3f} {sv:10.3f} {(br.max() if len(br) else float('nan')):8.2f} {hp:13.3f} {(sp.max() if len(sp) else float('nan')):8.3f}")
P("\nlines: Sahm 0.43 (chooser 0.40), vacancy 0.20, survey week 0.30 low / 0.50 high, breadth 0.50, housing pair 1.00, spread 1.323")
out.close()
