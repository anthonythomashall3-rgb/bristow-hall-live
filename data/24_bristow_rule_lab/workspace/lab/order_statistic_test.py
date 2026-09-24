"""Not the median: the k-th channel as the panel's date (Anthony, 3 September 2026).

The panel's date is the median of the channel dates - half the channels must have turned.  Asked:
what if only a certain number of channels need to have turned, k of n, the k-th earliest channel
date being the panel's date?  Two questions, both measured, nothing adopted on its score:

  accuracy   the nine chronologies' monthly ends (monthly_ends_all.nine, everything else shipped)
             with the peak taken as the k-th earliest channel date (k = 1, 2, 3), or the p-quantile
             (0.25, 0.33), against the shipped median (0.5, later middle); the trough likewise;
             leave-one-chronology-out selection as refine_loo.py does it.
  speed      the United States, today's data: for each of the twelve postwar peaks the level clause
             (date_episode, the window opening twelve months before the committee's peak and closing
             at the data edge) is re-read with the data cut at every month from the peak month to
             thirty months after, and two months are recorded for each statistic - when a peak date
             is first available at all and when it first equals the final date and stays there three
             months.  Faster means available and settled sooner; the date it settles on is the
             accuracy column.  (The window is not bounded by the route's next call here, so the
             1980 episode's final value at +30 months is the 1981 peak under every statistic.)

Implementation: bristow_rule_v3's own clauses; the order statistic replaces _trimmed_median's
median through a switch that knows whether the dates being aggregated are peaks or troughs
(channel_peak / channel_trough set a flag as they return).  The trim (24 months from the
statistic) is kept.  Output: order_statistic_test.log.
"""
import sys, math, warnings, collections; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.argv=['x']
import numpy as np, pandas as pd
import bristow_rule_v3 as B
import monthly_ends_all as M
_cp, _ct, _tm, _md_ = B.channel_peak, B.channel_trough, B._trimmed_median, B._median
STAT={'P':('q',0.5),'T':('q',0.5)}
LAST={'k':'T'}
def channel_peak(*a,**k):
    r=_cp(*a,**k); LAST['k']='P'; return r
def channel_trough(*a,**k):
    r=_ct(*a,**k); LAST['k']='T'; return r
def stat(dates, how):
    ds=sorted(d for d in dates if d is not None)
    if not ds: return None
    kind,v=how
    if kind=='k': return ds[min(v,len(ds))-1]
    return _md_(ds,v)
def trimmed(dates_abstain, dates_all, trim=None):
    how=STAT[LAST['k']]
    t=B.TRIM_MONTHS if trim is None else trim
    ds=[d for d in dates_abstain if d is not None]
    if not ds: ds=[d for d in dates_all if d is not None]
    d=stat(ds,how)
    if d is None or t is None or len(ds)<4: return d
    c=d.year*12+(d.month-1)
    keep=[x for x in ds if abs((x.year*12+(x.month-1))-c)<=t]
    return stat(keep,how) if len(keep)>=2 else d
B.channel_peak=channel_peak; B.channel_trough=channel_trough; B._trimmed_median=trimmed
def tally(rows, countries=None):
    e=[x for c,k,x,w in rows if not w and (countries is None or c in countries) and x is not None]
    return (sum(v==0 for v in e),sum(abs(v)<=1 for v in e),sum(abs(v)<=3 for v in e),len(e))
def label(h): return f'{h[1]}th earliest' if h[0]=='k' else ('median' if h[1]==0.5 else f'q={h[1]}')
if __name__=='__main__':
    PEAK=[('k',1),('k',2),('k',3),('q',0.25),('q',0.33),('q',0.5),('q',0.67)]
    TROUGH=[('q',0.33),('q',0.5),('q',0.67),('k',2),('k',3)]
    res={}
    print('== accuracy, the nine chronologies (exact / within one / within three of n), the peak statistic varied, trough = median')
    for hp in PEAK:
        STAT['P']=hp; STAT['T']=('q',0.5); P,T=M.nine(); res[('P',hp)]=(P,T); tp=tally(P); tt=tally(T)
        us=tally(P,['United States'])
        print(f'  peak {label(hp):14s}: peaks {tp[0]:2d}/{tp[1]:2d}/{tp[2]:2d} of {tp[3]}  US peaks {us[0]}/{us[1]}/{us[2]} of {us[3]}  | troughs {tt[0]:2d}/{tt[1]:2d}/{tt[2]:2d} of {tt[3]}',flush=True)
    print('== the trough statistic varied, peak = median')
    for ht in TROUGH:
        STAT['P']=('q',0.5); STAT['T']=ht; P,T=M.nine(); res[('T',ht)]=(P,T); tp=tally(P); tt=tally(T)
        us=tally(T,['United States'])
        print(f'  trough {label(ht):14s}: troughs {tt[0]:2d}/{tt[1]:2d}/{tt[2]:2d} of {tt[3]}  US troughs {us[0]}/{us[1]}/{us[2]} of {us[3]}  | peaks {tp[0]:2d}/{tp[1]:2d}/{tp[2]:2d} of {tp[3]}',flush=True)
    countries=sorted(set(c for c,k,e,w in res[('P',('q',0.5))][0]))
    for end,grid in (('P',PEAK),('T',TROUGH)):
        print(f'\n== leave one chronology out, {"peak" if end=="P" else "trough"} statistic (selection on exact at that end on the other chronologies, then within one, then within three; ties to the median)')
        oos=[]; picks=collections.Counter()
        for held in countries:
            others=[c for c in countries if c!=held]
            def key(h):
                rows=res[(end,h)][0 if end=='P' else 1]; t=tally(rows,others); return (t[0],t[1],t[2])
            best=max(grid,key=key)
            if key(best)==key(('q',0.5)): best=('q',0.5)
            picks[label(best)]+=1
            rows=res[(end,best)][0 if end=='P' else 1]; oos+=[r for r in rows if r[0]==held]
            t=tally(rows,[held]); s=tally(res[(end,('q',0.5))][0 if end=='P' else 1],[held])
            print(f'  held out {held:26s} picks {label(best):14s} -> {t[0]}/{t[1]}/{t[2]} of {t[3]}   (median: {s[0]}/{s[1]}/{s[2]})')
        o=tally(oos); s=tally(res[(end,('q',0.5))][0 if end=='P' else 1])
        print(f'  out of sample {o[0]}/{o[1]}/{o[2]} of {o[3]}; the median {s[0]}/{s[1]}/{s[2]} of {s[3]}; picked {dict(picks)}')
    # ---- speed, the United States on today's data
    import bench
    from bench import PANELS, channels, ep3, ts, quantity, md
    bench.SKIP={'exports','imports','car registrations','unemployment','construction production','construction output','capital goods production','intermediate goods production','consumer durables production'}
    chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
    cfg=PANELS['United States']
    B._median=lambda ds,q=0.5: stat(ds,STAT[LAST['k']])   # date_episode aggregates with _median directly
    print('\n== speed, United States, today\'s data cut month by month: months after the committee\'s peak at which the level clause (date_episode, refinement in force) first gives a peak date at all, and first settles on its final value (three months), with that final value\'s error; the trough statistic stays the median')
    STATS=[('k',1),('k',2),('k',3),('q',0.5)]
    print('  episode  '+'  '.join(f'{label(h):>26s}' for h in STATS))
    agg={label(h):{'avail':[],'settle':[],'err':[]} for h in STATS}
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq']); pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0]
        cells=[]
        for h in STATS:
            STAT['P']=h; STAT['T']=('q',0.5); path=[]
            for m in range(0,31):
                T=pkm+pd.DateOffset(months=m)
                r=B.date_episode([(nm,s[:T]) for nm,s in use],w0,T,band_trough=0.12,band_peak=0.01,smooth=3,lookback=12,peak_cap=18)
                path.append((m,r['peak']))
            final=path[-1][1]
            avail=next((m for m,d in path if d is not None),None)
            settle=None; run=0
            for m,d in path:
                if d is not None and d==final:
                    run+=1
                    if run==1: first=m
                    if run>=3: settle=first; break
                else: run=0
            err=None if final is None else md(final,pkm)
            L=label(h); agg[L]['avail'].append(avail); agg[L]['settle'].append(settle); agg[L]['err'].append(err)
            cells.append(f"avail {avail!s:>4} settle {settle!s:>4} err {'-' if err is None else f'{err:+d}':>3}")
        print(f'  {pk_off[:7]}  '+'  '.join(f'{c:>26s}' for c in cells))
    for L,v in agg.items():
        a=[x for x in v['avail'] if x is not None]; s_=[x for x in v['settle'] if x is not None]; e=[x for x in v['err'] if x is not None]
        print(f'  {L:14s}: available median {np.median(a):.0f} months after the peak (n {len(a)}), settled median {np.median(s_) if s_ else float("nan"):.0f} (n {len(s_)}); final date (data cut at +30) exact {sum(x==0 for x in e)}, within one {sum(abs(x)<=1 for x in e)}, within three {sum(abs(x)<=3 for x in e)} of {len(e)}, mae {np.mean(np.abs(e)):.2f}')
