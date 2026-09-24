"""THE THREE PEAKS STILL OUTSIDE THE MONTH. 1969, 2020 and 2024. For 1969 the binding table says the CONFIRMER binds -
the proposal was ready on 10 December 1969 and the housing pair did not confirm until 6 February 1970 - so a demand
object available before 10 December 1969 would put the call at minus twenty-one days. What every demand object was
doing through 1969 is printed here, with its line, so the gap is measured rather than guessed. The same is done for
2020 and 2024."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('p69.out','w')"))
p=dict(BASE)
G=vgap2(p['vk'],p['vb']); VPUB=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hh=mkhours(p['hrs'],p['nd'])
for tag,a,b,lines in [('1969 peak, window opens 1969-06','1969-01','1970-04',None),
                      ('2020 peak, window opens 2019-08','2019-09','2020-05',None),
                      ('2024 peak, window opens 2023-10','2023-10','2024-08',None)]:
    P(f"\n{tag}")
    P(f"{'month':8s} {'vacancy gap':>12s} {'line':>6s} {'housing pair':>13s} {'line':>6s} {'hours pair':>11s} {'spread max':>11s} {'line':>6s}")
    for m in pd.date_range(a,b,freq='MS'):
        sp=GSP[(GSP.index>=m)&(GSP.index<m+pd.DateOffset(months=1))]
        P(f"{m:%Y-%m}  {G.get(m,float('nan')):12.3f} {p['vl']:6.2f} {Hc['gap'].get(m,float('nan')):13.3f} {Hc['line']:6.2f} {Hh['gap'].get(m,float('nan')):11.1f} {(sp.max() if len(sp) else float('nan')):11.3f} {p['spr']:6.3f}")
P("\nHOW LOW WOULD EACH LINE HAVE TO GO to confirm 1969 before 10 December 1969, and what else fires at that line")
def others_at(obj,line,pubf,name):
    hits=[(m,pubf(m)) for m,v in obj.items() if v>=line]
    quiet=[(m,pp) for m,pp in hits if not any(pk-pd.DateOffset(months=6)<=m<=tr for pk,tr in zip(PK,TR))]
    return len(hits),len(quiet),quiet[:6]
for name,obj,pubf,cur,grid in [('vacancy',G,(lambda m: VPUB[m]),p['vl'],[0.20,0.15,0.12,0.10,0.08,0.05]),
                               ('housing pair',Hc['gap'],(lambda m: pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=17)),Hc['line'],[1.0,0.8,0.7,0.6,0.5])]:
    P(f"\n   {name} (line now {cur})")
    for L in grid:
        w=obj[(obj.index>=pd.Timestamp('1969-06-01'))&(obj.index<=pd.Timestamp('1970-04-01'))]
        h=w[w>=L]
        first=f"{h.index[0]:%Y-%m} published {pubf(h.index[0]):%Y-%m-%d}" if len(h) else "never in the window"
        n,q,qs=others_at(obj,L,pubf,name)
        P(f"      line {L:5.2f}: 1969 window {first:38s} | quiet months at or above this line: {q}")
out.close()
