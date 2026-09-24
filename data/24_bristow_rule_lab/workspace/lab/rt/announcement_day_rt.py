"""The rule on the committee's own announcement days: same day, same data, rule against committee.

The NBER announced its twelve dates of 1980-2021 on the days listed in memo section 8 (1980 peak
3 June 1980 ... 2020 trough 19 July 2021).  This script replays the panel's retrospective dating
(final_date_rt.dates: date_episode at the shipped bands with the refinement clause) on the ALFRED
vintages in force on each announcement day, so that the rule's date and the committee's date rest
on the same information set.  Two panels as in final_date_rt.py: the shipped analogues (INDPRO,
PAYEMS, CE16OV, PCEC96, DSPIC96, real RSAFS, CMRMTSPL - each when its vintages exist) and the
wider labor-heavy panel (plus UNRATE inverted, AWHMAN, MANEMP).  The window opens thirty months
before the union's real-time peak call (union_peaks.log) and closes at the vintage's last month;
for a peak announcement only the peak is scored (the trough has not happened), for a trough
announcement both ends are read and the trough is scored.  Errors in months against the
committee's date.  Run 3 September 2026; output announcement_day_rt.log.  A test, not a clause.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/rt')
import numpy as np, pandas as pd
import final_date_rt as F
ANN=[  # (episode peak, kind, committee date, announcement day)
 ('1980-01','P','1980-01','1980-06-03'),('1980-01','T','1980-07','1981-07-08'),
 ('1981-07','P','1981-07','1982-01-06'),('1981-07','T','1982-11','1983-07-08'),
 ('1990-07','P','1990-07','1991-04-25'),('1990-07','T','1991-03','1992-12-22'),
 ('2001-03','P','2001-03','2001-11-26'),('2001-03','T','2001-11','2003-07-17'),
 ('2007-12','P','2007-12','2008-12-01'),('2007-12','T','2009-06','2010-09-20'),
 ('2020-02','P','2020-02','2020-06-08'),('2020-02','T','2020-04','2021-07-19')]
def fmt(d): return 'none ' if d is None else d.strftime('%y-%m')
if __name__=='__main__':
    for label,spec in (('shipped analogues',F.SHIPPED),('wider',F.WIDER)):
        print(f'\n=== {label}')
        print('episode  end  committee  announced     rule on that day: peak      trough     scored err   channels')
        errs={'P':[],'T':[]}
        for ep,kind,cd,day in ANN:
            call=pd.Timestamp(F.CALL[ep]); w0=pd.Timestamp(call.year,call.month,1)-pd.DateOffset(months=30)
            p,t,ch=F.dates(day,w0,spec)
            ref=pd.Timestamp(cd+'-01'); got=p if kind=='P' else t
            e=None if got is None else F.md(got,ref)
            if e is not None: errs[kind].append(e)
            print(f"{ep}   {kind}    {cd}    {day}    P {fmt(p)}  T {fmt(t if kind=='T' else None)}      {'none' if e is None else f'{e:+d}':>5}   {ch}")
        for k,v in errs.items():
            print(f"  {'peaks' if k=='P' else 'troughs'}: n {len(v)} exact {sum(x==0 for x in v)} w1 {sum(abs(x)<=1 for x in v)} w3 {sum(abs(x)<=3 for x in v)} mae {np.mean(np.abs(v)) if v else float('nan'):.2f}")
