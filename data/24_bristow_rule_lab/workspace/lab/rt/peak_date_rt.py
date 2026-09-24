"""The peak's DATE on the data of the time, after the union has made the CALL.

Section 8f's union says a recession has begun (twelve of twelve since 1948, median 40 days
after the peak month) and carries the state diffusion index's date, 6 of 12 exact.  This
script asks what the panel itself would have dated the peak at on the vintages in force at
the time (ALFRED wide files on disk: INDPRO, PAYEMS, UNRATE, AWHMAN, MANEMP from 1961-65;
PCEC96 from 1979), read at the union's call day and at three, six and twelve months after
it, with the rule's own peak clause (date_episode at the shipped bands and the refinement
clause) on a window that uses no chronology: from thirty months before the call's month to
the vintage's last month.  Errors against the NBER peak, in months, for the eight peaks
since 1969.  The state index's real-time date (union_peaks.py, leg A) stands beside it.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/rt'); sys.path.insert(0,'/home/claude/lab/weekly'); sys.path.insert(0,'/home/claude/lab/fh')
import numpy as np, pandas as pd
import alfred as al, bristow_rule_v3 as B
PK=[pd.Timestamp(x) for x in ('1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02')]
CALL={'1969-12':'1970-01-31','1973-11':'1974-02-16','1980-01':'1980-03-20','1981-07':'1981-12-20','1990-07':'1990-09-20','2001-03':'2001-03-31','2007-12':'2007-12-28','2020-02':'2020-03-28'}   # union_peaks.log
INDEX={'1969-12':'1969-12','1973-11':'1973-12','1980-01':'1980-01','1981-07':'1981-10','1990-07':'1990-07','2001-03':'2001-03','2007-12':'2007-12','2020-02':'2020-03'}   # leg A's / the weekly object's date
SPEC=[('INDPRO','level'),('PAYEMS','level'),('UNRATE','rate'),('AWHMAN','level'),('MANEMP','level'),('PCEC96','level')]
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def panel_asof(day, w0):
    chs=[]
    for sid,kind in SPEC:
        s=al.asof(sid,day)
        if s is None: continue
        s=s.astype(float).dropna()
        if s.index.min()<=w0 and len(s[w0:])>=6: chs.append((sid,B.procyclical(s,kind)))
    return chs
def date_at(day, call_month):
    w0=call_month-pd.DateOffset(months=30)
    chs=panel_asof(day,w0)
    if len(chs)<2: return None,[c for c,_ in chs]
    end=max(s.index.max() for _,s in chs)
    r=B.date_episode(chs,w0,end,band_trough=0.12,band_peak=0.01,smooth=3,lookback=12,peak_cap=18)
    return r['peak'],[c for c,_ in chs]
if __name__=='__main__':
    print('peak      index date   panel at the call   +3 months   +6 months   +12 months   (errors in months; channels at the call)')
    tot={k:[] for k in ('index','call','+3','+6','+12')}
    for pk in PK:
        k=pk.strftime('%Y-%m'); call=pd.Timestamp(CALL[k]); cm=pd.Timestamp(call.year,call.month,1)
        ei=md(pd.Timestamp(INDEX[k]+'-01'),pk); tot['index'].append(ei)
        cells=[]; chans=None
        for lab,off in (('call',0),('+3',3),('+6',6),('+12',12)):
            day=(call+pd.DateOffset(months=off)).strftime('%Y-%m-%d')
            d,ch=date_at(day,cm)
            if chans is None: chans=ch
            e=None if d is None else md(d,pk)
            cells.append(f"{d.strftime('%Y-%m') if d is not None else 'none':7s} ({e:+d})" if e is not None else 'none        ')
            if e is not None: tot[lab].append(e)
        print(f"{k}   {INDEX[k]} ({ei:+d})   "+'   '.join(cells)+f'   {chans}')
    for lab,v in tot.items():
        print(f"  {lab:6s}: n {len(v)} exact {sum(x==0 for x in v)} within one {sum(abs(x)<=1 for x in v)} within three {sum(abs(x)<=3 for x in v)} mean abs {np.mean(np.abs(v)):.2f}")
