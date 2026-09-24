"""Finding 2's trough detector on weekly continued claims (real-time SA, 1969 on), and the
price of a shorter confirmation - Rule 17's 'called within the month'.

Detector: N(t) = 100 x log of the nsm-week mean of SA continued claims.  Armed when N stands
nth log points above its trailing 52-week minimum.  Fires when N has fallen rt consecutive
weeks and delta log points from its running maximum; the trough is the month of that
maximum; published pub days after the week that fired (the Department's Thursday release).
One call per episode: re-arms only after the arming condition has been false for mp weeks.
"""
import pandas as pd, numpy as np, itertools, warnings, sys; warnings.filterwarnings('ignore')
W=pd.read_csv('/home/claude/lab/weekly/DOL_national_weekly_claims_sa_rt.csv',index_col=0,parse_dates=True)
TR=['1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
def series(nsm, col='cc_sa_rt'):
    N=(np.log(W[col])*100.0).rolling(nsm).mean()
    G=N-N.rolling(52,min_periods=26).min()
    return pd.concat([N.rename('n'),G.rename('g')],axis=1).dropna()
def calls(D, rt, delta, nth, mp=13, pub=5, rearm=None):
    """record.py's state machine: quiet -> armed once the gap g reaches nth; fires on rt falling
    weeks and a drop of delta from the running maximum; then 'called' until g has been below
    rearm (default nth/2) for mp weeks."""
    rearm = nth/2 if rearm is None else rearm
    n=D['n'].values; g=D['g'].values; idx=D.index; out=[]
    state='quiet'; off=0; nmax=-1e9; nmax_i=0; fall=0; prev=n[0]
    for i in range(1,len(n)):
        if n[i]>nmax: nmax=n[i]; nmax_i=i; fall=0
        elif n[i]<prev: fall+=1
        else: fall=0
        prev=n[i]
        if state=='called':
            off = off+1 if g[i]<rearm else 0
            if off>=mp: state='quiet'; off=0
            continue
        if state=='quiet':
            if g[i]>=nth: state='armed'; nmax=n[i]; nmax_i=i; fall=0
            continue
        if fall>=rt and (nmax-n[i])>=delta and g[nmax_i]>=nth:
            out.append((idx[i]+pd.Timedelta(days=pub), mo(idx[nmax_i]))); state='called'; off=0
    return out
def score(cl, start='1969-06-01'):
    got={}; fa=[]
    for pub,dt in cl:
        if pub<pd.Timestamp(start): continue
        best=None
        for k in TR:
            if k in got: continue
            t=pd.Timestamp(k+'-01'); err=md(dt,t); lag=(pub-t).days
            if abs(err)<=3 and -60<=lag<=400 and (best is None or abs(err)<abs(best[1])): best=(k,err,lag)
        if best: got[best[0]]=(best[1],best[2])
        else: fa.append((pub.strftime('%Y-%m-%d'),dt.strftime('%Y-%m')))
    return got,fa
def summ(got):
    e=[v[0] for v in got.values()]; L=[v[1] for v in got.values()]
    within=sum(1 for v in got.values() if v[1]<=61)   # published by the end of the month after the trough month
    return dict(hit=len(got),exact=sum(x==0 for x in e),w1=sum(abs(x)<=1 for x in e),
                lag_min=min(L) if L else None,lag_max=max(L) if L else None,lag_mean=(np.mean(L) if L else None),within_month=within)
if __name__=='__main__':
    print('=== the memo\'s Finding 2 setting: nsm 4, rt 6, delta 4, nth 30')
    D=series(4); cl=calls(D,6,4.,30.); got,fa=score(cl)
    for k in TR: print('  ',k, got.get(k,'--'))
    print('   other calls:',fa); print('  ',summ(got))
    print()
    print('=== grid: confirmation weeks rt, drop delta, arm nth, smoothing nsm; sorted by (hits, -false alarms, within-month, exact)')
    rows=[]
    for nsm,rt,delta,nth,mp in itertools.product((2,3,4,6,8),(1,2,3,4,5,6),(1.,2.,3.,4.,6.,8.),(20.,25.,30.,40.),(13,26)):
        D=series(nsm); cl=calls(D,rt,delta,nth,mp); got,fa=score(cl); s=summ(got)
        rows.append((s['hit'],-len(fa),s['within_month'],s['exact'],s['w1'],nsm,rt,delta,nth,mp,s['lag_min'],s['lag_max'],s['lag_mean'],fa))
    rows.sort(reverse=True)
    print(f'{"hit":>3s} {"fa":>3s} {"inM":>3s} {"ex":>3s} {"w1":>3s} | {"nsm":>3s} {"rt":>2s} {"del":>4s} {"nth":>4s} {"mp":>2s} | lag min/max/mean')
    for r in rows[:40]:
        print(f'{r[0]:3d} {-r[1]:3d} {r[2]:3d} {r[3]:3d} {r[4]:3d} | {r[5]:3d} {r[6]:2d} {r[7]:4.1f} {r[8]:4.0f} {r[9]:2d} | {r[10]} / {r[11]} / {r[12]:.0f}' + (f'   other: {r[13][:4]}' if r[13] else ''))
    print()
    print('=== zero-false-alarm settings with the most calls inside the month after the trough')
    z=[r for r in rows if r[1]==0]; z.sort(key=lambda r:(-r[2],-r[0],-r[3],r[12]))
    for r in z[:15]:
        print(f'{r[0]:3d} {-r[1]:3d} {r[2]:3d} {r[3]:3d} {r[4]:3d} | {r[5]:3d} {r[6]:2d} {r[7]:4.1f} {r[8]:4.0f} {r[9]:2d} | {r[10]} / {r[11]} / {r[12]:.0f}')
