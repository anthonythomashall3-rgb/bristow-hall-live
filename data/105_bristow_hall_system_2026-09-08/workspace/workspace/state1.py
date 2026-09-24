"""BREADTH ACROSS THE STATES. The Department publishes an insured unemployment rate for every state each week, from
February 1986. Breadth is the share of states whose own rate stands a given distance above its own fifty-two-week
minimum; the object proposes when that share crosses a line. State figures reach the public a week behind the national
ones, so the clock here is nineteen days after the week ends - still ahead of the employment report."""
import sys,glob,os
sys.argv=['x','1962','2026']
exec(open('walk3.py').read().split('CACHE6={}')[0].replace("out=open('walk3_%s.out'%sys.argv[1],'w')","out=open('state1.out','w')"))
D=W+'/lab/data/fred_weekly'
fs=sorted(glob.glob(D+'/*INSUREDUR.csv'))
cols={}
for f in fs:
    st=os.path.basename(f)[:2]
    cols[st]=pd.read_csv(f,index_col=0,parse_dates=True).iloc[:,0].dropna()
ST=pd.DataFrame(cols).sort_index()
P(f"state insured rates: {ST.shape[1]} units, {ST.index.min():%Y-%m-%d} to {ST.index.max():%Y-%m-%d}, {len(ST)} weeks")
MN=ST.rolling(52,min_periods=52).min().shift(1)
def inwin(dd): return any(pk-pd.DateOffset(months=6)<=dd<=tr for pk,tr in zip(PK,TR))
p=dict(BASE)
Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1)
C2=[Hc,SP]
P(f"\n{'rise':>5s} {'share':>6s} {'props':>6s} {'quiet':>6s} {'quiet calls':>11s}   first call in each window from 1986")
for X in [0.2,0.3,0.5,0.8]:
    B=((ST-MN)>=X).sum(axis=1)/ST.notna().sum(axis=1)
    B=B.dropna()
    for sh in [0.3,0.4,0.5,0.6,0.7,0.8]:
        c=[]; armed=True
        for t,v in B.items():
            if armed and v>=sh: c.append((t+pd.Timedelta(days=19),pd.Timestamp(t.year,t.month,1))); armed=False
            elif not armed and v<sh*0.5: armed=True
        q=[x for x in c if not inwin(x[1])]
        cf=confirm_w(c,C2,'month'); qc=[(a,b) for a,b,cc in cf if not inwin(b)]
        firsts=[]
        for pk,tr in zip(PK,TR):
            if pk<pd.Timestamp('1987-01-01'): continue
            h=[(a,b) for a,b,cc in cf if pk-pd.DateOffset(months=6)<=b<=tr]
            firsts.append(f"{pk:%Y-%m}:{(h[0][0]-me(pk)).days:+d}" if h else f"{pk:%Y-%m}:-")
        P(f"{X:5.2f} {sh:6.2f} {len(c):6d} {len(q):6d} {len(qc):11d}   "+" ".join(firsts))
out.close()
