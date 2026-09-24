"""HOW BIG IS THE CLEAN REGION? The route-v16 line reports that 693 of its 2,160 configurations catch every turn with
no false alarm - zero false alarms is a plateau, not a knife-edge, and that is the anti-fitting evidence a referee
wants. The same statistic has never been computed for this rule. The grid here has 414,720 points, so a random sample
is drawn and each point is run over the whole record."""
import sys,random,pickle,os
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('plateau1.out','w')"))
GRID=[('sahm',[0.50,0.45,0.43,0.40]),('vl',[0.30,0.25,0.20,0.15]),('u45',[0.55,0.45,0.35]),('low',[0.30,0.25,0.20]),
      ('look',[52,78,91,130]),('spr',[1.6,round(LINE,3),1.1]),('ic',[60,50,45]),
      ('wline',[0.40,0.35,0.30,0.25,None]),('wline2',[0.60,0.50,0.45,None]),('bshare',[0.60,0.50,0.40,None])]
tot=1
for _,gr in GRID: tot*=len(gr)
P(f"grid points: {tot}")
random.seed(11); N=int(sys.argv[3]) if len(sys.argv)>3 else 400
res=[]
for _ in range(N):
    p=dict(BASE); p['deep']=15
    for n,gr in GRID: p[n]=random.choice(gr)
    r,t=build9(p)
    allc=len(r['lags_p'])==13; oth=len(r['other'])
    early=bool([x for x in t if x['kind']=='peak' and x['published']<pd.Timestamp('1948-06-01')])
    v=[r['lags_p'][i] for i in range(4,13) if i in r['lags_p']]
    res.append((allc,oth,early,float(np.median(v)) if len(v)==9 else None))
n=len(res)
full=[x for x in res if x[0] and not x[2]]
clean=[x for x in full if x[1]==0]
P(f"\nsampled {n} configurations at random from the grid")
P(f"   catch every turn with nothing before June 1948: {len(full)} ({100*len(full)/n:.1f} per cent)")
P(f"   of those, ZERO other calls anywhere in the record: {len(clean)} ({100*len(clean)/n:.1f} per cent of all sampled)")
if clean:
    md=[x[3] for x in clean if x[3] is not None]
    P(f"   among the clean, the median onset lag from 1969 runs {min(md):.0f} to {max(md):.0f} days, median of medians {np.median(md):.0f}")
    P(f"   share of the clean that are inside a month on the median: {100*sum(1 for x in md if x<=31)/len(md):.0f} per cent")
P(f"   configurations with one other call: {sum(1 for x in full if x[1]==1)}; two or more: {sum(1 for x in full if x[1]>=2)}")
out.close()
