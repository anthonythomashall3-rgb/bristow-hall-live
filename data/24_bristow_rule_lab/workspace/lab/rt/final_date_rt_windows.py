"""final_date_rt.py with the episode window bounded by the route's own calls.

final_date_rt.py opens every episode's window thirty months before the union's peak call and
closes it at the vintage's last month.  On the vintages twenty-four months after the July 1980
trough that window still holds the 1981-82 contraction, and on the 6 January 1982 vintage the
1981 peak's window still holds the 1980 contraction; date_episode then dates the deeper of the
two (final_date_rt.log: 1980 at +24 months P +19 T +21; announcement_day_rt.log: the 1981 peak
P -17).  A reader of the time had already closed the 1980 episode - its trough was called on 10
August 1980 and dated July by the continued-claims leg on 13 November 1980 - and would not have
reopened it, and once the 1981 peak was called (20 December 1981, dated October) the 1980 episode's
window ended.  This script applies exactly that information set and nothing else:

  window opens   at the later of thirty months before the union's peak call and the month after
                 the route's final date for the PREVIOUS trough (union_troughs log, leg K)
  window closes  at the vintage's last month, or, if the union has since called the NEXT peak,
                 the month before the date that call carried (the call month if it carried none)

On a PEAK announcement day the trough has not happened, so the panel is read peak-only: the
peak clause (composite crossing, peak_cap, channel_peak, median) with the search running to the
vintage's last month - date_episode's own peak block with no trough to close it.  On the 6 January
1982 vintage the bounded window otherwise finds the July 1980 trough's residual D at its opening
month and closes the peak search before the 1981 peak (P none in the first run of this script).
Everything else is final_date_rt.py: the same vintages, panels, bands and refinement clause.
Both the six/fourteen/twenty-four-month replay and the announcement-day replay are printed.  Run
3 September 2026; output final_date_rt_windows.log.  The route's own calls are the only chronology
used; the committee's dates enter only as the thing scored against.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/rt')
import numpy as np, pandas as pd
import os
import final_date_rt as F
import bristow_rule_v3 as B
from announcement_day_rt import ANN, fmt
# BR_RT_AGG=tool reads the panel through the shipped aggregator (date_turning_points, level concept: abstaining
# channels preferred, far-out votes trimmed, composite as the last resort) instead of final_date_rt's date_episode
# (the level clause on its own: a plain median of every channel's date, no trim, no preference)
AGG=os.environ.get('BR_RT_AGG','episode')
def dates_tool(day, w0, spec, cut=None):
    chs=F.panel_asof(day,w0,spec)
    if len(chs)<2: return None,None,[c for c,_ in chs]
    if cut is not None: chs=[(c,s[:cut]) for c,s in chs]
    end=max(s.index.max() for _,s in chs)
    r=B.date_turning_points(chs,w0,end,volume_channels=chs,concept='level',lam=500000.0,band_trough=0.12,band_peak=0.01,peak_cap=18,smooth=3,lookback=12)
    return r['peak'],r['trough'],[c for c,_ in chs]
if AGG=='tool': F.dates=dates_tool
# the route's record (lab/weekly/union_peaks.log, union_troughs_2026-09-03.log): peak calls with the date carried,
# and the final trough dates (leg K) - no committee date in either
PEAK_CALLS=[('1970-01-31',None),('1974-02-16',None),('1980-03-20','1980-01'),('1981-12-20','1981-10'),('1990-09-20','1990-07'),
            ('2001-03-31',None),('2007-12-28','2007-12'),('2020-03-28','2020-03'),('2023-11-20','2023-09')]
TROUGH_FINAL=['1960-12','1970-11','1975-05','1980-07','1982-11','1991-06','2001-11','2009-05','2020-05']
def peak_only(day, w0, spec, cut=None):
    """the panel's peak with the search open to the vintage's last month (no trough yet)"""
    import bristow_rule_v3 as B
    chs=F.panel_asof(day,w0,spec)
    if len(chs)<2: return None,[c for c,_ in chs]
    if cut is not None: chs=[(c,s[:cut]) for c,s in chs]
    end=max(s.index.max() for _,s in chs)
    comp=B.composite_deviation(chs,12,3,1)[w0:end].dropna()
    cross=next((d for d,v in comp.items() if v>=2.0),None)
    p0=w0 if cross is None else max(w0,cross-pd.DateOffset(months=18))
    return B._median([B.channel_peak(s,p0,end,0.01,3,True) for nm,s in chs]),[c for c,_ in chs]
def window(ep_call, day):
    """(w0, cut) for the episode whose union peak call is ep_call, read on `day`"""
    call=pd.Timestamp(ep_call); day=pd.Timestamp(day)
    w0=pd.Timestamp(call.year,call.month,1)-pd.DateOffset(months=30)
    prev=[pd.Timestamp(t+'-01') for t in TROUGH_FINAL if pd.Timestamp(t+'-01')<call-pd.DateOffset(months=6)]
    if prev: w0=max(w0,prev[-1]+pd.DateOffset(months=1))
    cut=None
    for c,d in PEAK_CALLS:
        c=pd.Timestamp(c)
        if c>call and c<=day:
            m=pd.Timestamp(d+'-01') if d else pd.Timestamp(c.year,c.month,1)
            cut=m-pd.DateOffset(months=1)+pd.offsets.MonthEnd(0); break
    return w0,cut
if __name__=='__main__':
    TODAY='2026-08-20'
    print(f'aggregator: {AGG} ({"date_turning_points" if AGG=="tool" else "date_episode"}); trough opening-edge abstention: {B.TROUGH_EDGE_ABSTAIN}')
    for label,spec in (('shipped analogues',F.SHIPPED),('wider',F.WIDER)):
        print(f'\n=== {label}: six, fourteen and twenty-four months after the trough, window bounded by the route')
        print('episode    +6 months          +14 months         +24 months         today, same channels, cut at +14   window at +24')
        tot={k:{'P':[],'T':[]} for k in ('+6','+14','+24','today')}
        for pk,tr in zip(F.PK,F.TR):
            k=pk.strftime('%Y-%m'); cells=[]; chans=None
            for lab,off in (('+6',6),('+14',14),('+24',24)):
                day=tr+pd.DateOffset(months=off); w0,cut=window(F.CALL[k],day)
                p,t,ch=F.dates(day.strftime('%Y-%m-%d'),w0,spec,cut=cut)
                if lab=='+14': chans=ch
                ep=None if p is None else F.md(p,pk); et=None if t is None else F.md(t,tr)
                cells.append(f"P {fmt(p)}({ep:+d}) T {fmt(t)}({et:+d})" if ep is not None and et is not None else f"P {fmt(p)} T {fmt(t)}")
                if ep is not None: tot[lab]['P'].append(ep)
                if et is not None: tot[lab]['T'].append(et)
            w0,_=window(F.CALL[k],TODAY); cut14=tr+pd.DateOffset(months=13)
            p,t,ch=F.dates(TODAY,w0,[s for s in spec if s[0] in chans],cut=cut14)
            ep=None if p is None else F.md(p,pk); et=None if t is None else F.md(t,tr)
            cells.append(f"P {fmt(p)}({ep:+d}) T {fmt(t)}({et:+d})" if ep is not None and et is not None else 'none')
            if ep is not None: tot['today']['P'].append(ep)
            if et is not None: tot['today']['T'].append(et)
            w0,cut=window(F.CALL[k],tr+pd.DateOffset(months=24))
            print(f"{k}    "+'   '.join(f'{c:18s}' for c in cells)+f"   {w0:%Y-%m} to {'open' if cut is None else cut.strftime('%Y-%m')}")
        for lab,v in tot.items():
            print(f"  {lab:6s}: peaks n {len(v['P'])} exact {sum(x==0 for x in v['P'])} w1 {sum(abs(x)<=1 for x in v['P'])} w3 {sum(abs(x)<=3 for x in v['P'])} mae {np.mean(np.abs(v['P'])) if v['P'] else float('nan'):.2f} | troughs n {len(v['T'])} exact {sum(x==0 for x in v['T'])} w1 {sum(abs(x)<=1 for x in v['T'])} w3 {sum(abs(x)<=3 for x in v['T'])} mae {np.mean(np.abs(v['T'])) if v['T'] else float('nan'):.2f}")
        print(f'\n=== {label}: on the committee\'s announcement days, window bounded by the route')
        print('episode  end  committee  announced     rule on that day: peak      trough     scored err   window   (peak rows read peak-only)')
        errs={'P':[],'T':[]}
        for ep,kind,cd,day in ANN:
            w0,cut=window(F.CALL[ep],day)
            if kind=='P': p,ch=peak_only(day,w0,spec,cut=cut); t=None
            else: p,t,ch=F.dates(day,w0,spec,cut=cut)
            ref=pd.Timestamp(cd+'-01'); got=p if kind=='P' else t
            e=None if got is None else F.md(got,ref)
            if e is not None: errs[kind].append(e)
            print(f"{ep}   {kind}    {cd}    {day}    P {fmt(p)}  T {fmt(t if kind=='T' else None)}      {'none' if e is None else f'{e:+d}':>5}   {w0:%Y-%m} to {'open' if cut is None else cut.strftime('%Y-%m')}")
        for k,v in errs.items():
            print(f"  {'peaks' if k=='P' else 'troughs'}: n {len(v)} exact {sum(x==0 for x in v)} w1 {sum(abs(x)<=1 for x in v)} w3 {sum(abs(x)<=3 for x in v)} mae {np.mean(np.abs(v)) if v else float('nan'):.2f}")
