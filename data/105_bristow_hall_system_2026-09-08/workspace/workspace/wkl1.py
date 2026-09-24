"""THE PROPOSER MADE WEEKLY. The binding diagnostic shows the proposal, not the confirmation, is what the tool waits
for in eight of eleven conjunction calls. The insured unemployment rate exists weekly: this line's own transcription of
the printed releases from January 1952, and the Department's seasonally adjusted weekly rate from January 1971. Spliced,
they give an unbroken weekly proposer from 1952. Here it is built, checked across the overlap, and swept as a proposer."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk3.py').read().split('CACHE6={}')[0].replace("out=open('walk3_%s.out'%sys.argv[1],'w')","out=open('wkl1.out','w')"))
D=W+'/lab/data/fred_weekly'
own=pd.read_csv('cache/weekly_iur_prewar.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
frd=pd.read_csv(D+'/IURSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
ov=own.index.intersection(frd.index)
P(f"own weekly {own.index.min():%Y-%m-%d}..{own.index.max():%Y-%m-%d} n={len(own)}   IURSA {frd.index.min():%Y-%m-%d}..{frd.index.max():%Y-%m-%d} n={len(frd)}")
if len(ov): d=(own[ov]-frd[ov]); P(f"overlap {len(ov)} weeks: mean difference {d.mean():+.3f}, standard deviation {d.std():.3f}, largest {d.abs().max():.3f}")
IURW=pd.concat([own[own.index<frd.index.min()],frd]).sort_index()
P(f"spliced weekly insured rate: {IURW.index.min():%Y-%m-%d} to {IURW.index.max():%Y-%m-%d}, {len(IURW)} weeks")
def leg_wk(s,line,look=52,pub=12,rearm='window'):
    gap=(s-s.rolling(look,min_periods=look).min().shift(1)).dropna(); c=[]; armed=True; last=None
    for t,v in gap.items():
        if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False; last=t
        elif not armed:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<line and t>=last+pd.DateOffset(months=4): armed=True
    return c
def inwin(dd): return any(pk-pd.DateOffset(months=6)<=dd<=tr for pk,tr in zip(PK,TR))
p=dict(BASE)
G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs); Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hh=mkhours(p['hrs'],p['nd'])
SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1)
P(f"\n{'line':>6s} {'rearm':7s} {'props':>6s} {'quiet props':>12s} {'after confirmation: quiet calls':>32s}   first call in each recession window")
for line in [0.8,0.7,0.6,0.5,0.45,0.4,0.35,0.3,0.25,0.2]:
    for rear in ('window','zero'):
        pr=leg_wk(IURW,line,rearm=rear)
        q=[x for x in pr if not inwin(x[1])]
        cf=confirm_w(pr,[Hc,SP,Vc,Hh],'month')
        qc=[(a,b) for a,b,c in cf if not inwin(b)]
        firsts=[]
        for pk,tr in zip(PK,TR):
            h=[(a,b) for a,b,c in cf if pk-pd.DateOffset(months=6)<=b<=tr]
            firsts.append(f"{pk:%Y-%m}:{(h[0][0]-me(pk)).days:+d}" if h else f"{pk:%Y-%m}:-")
        P(f"{line:6.2f} {rear:7s} {len(pr):6d} {len(q):12d} {len(qc):32d}   "+" ".join(firsts[4:]))
out.close()
