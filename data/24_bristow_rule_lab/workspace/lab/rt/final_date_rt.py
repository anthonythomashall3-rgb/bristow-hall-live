"""The FINAL date on the data of the time: the panel's retrospective dating replayed on the
vintages in force six, fourteen and twenty-four months after each trough since 1970.

Section 8f's three stages end with the panel's date "once the whole contraction is in hand,
about fourteen months after the trough" - a record measured on today's data (6 of 12 peaks
and 8 of 12 troughs exact).  This script asks what the same clause would have dated on the
data a reader had at the time, from the ALFRED wide vintages on disk (lab/rt/vint, copied
from the Mac's 27_realtime_vintages on 2 September 2026), with two panels:
  shipped analogues   the channels of the shipped American panel that have vintages:
                      industrial production (INDPRO, vintages from 1927), payroll
                      employment (PAYEMS, 1961), real consumption (PCEC96, 1979), real
                      disposable income (DSPIC96, 1979; the nearest real-time analogue of
                      real income less transfers, whose own vintages begin only in 2010),
                      real retail sales (RSAFS deflated by the CPI vintage of the day, 2001)
                      real manufacturing and trade sales (CMRMTSPL, 2013) and household
                      employment (CE16OV, 786 vintages from 1961, fetched from ALFRED's
                      keyless download form on 2 September 2026 - the Mac harvest's copy
                      ended in 1965; lab/acq/alfred/).
  wider               the same plus the unemployment rate (inverted), manufacturing hours
                      (AWHMAN) and manufacturing employment (MANEMP), the set
                      peak_date_rt.py used - a labor-heavy panel a reader of the 1970s had
The window uses no chronology: from thirty months before the union's peak call (union_peaks.
log) to the vintage's last month; date_episode at the shipped bands with the refinement
clause.  Beside each real-time date, the same channels on today's vintage, so that what the
revisions did can be told from what the thinner panel did.  Errors in months against NBER.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/rt')
import numpy as np, pandas as pd
import alfred as al, bristow_rule_v3 as B
PK=[pd.Timestamp(x) for x in ('1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02')]
TR=[pd.Timestamp(x) for x in ('1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04')]
CALL={'1969-12':'1970-01-31','1973-11':'1974-02-16','1980-01':'1980-03-20','1981-07':'1981-12-20','1990-07':'1990-09-20','2001-03':'2001-03-31','2007-12':'2007-12-28','2020-02':'2020-03-28'}
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def real_retail(day):
    r=al.asof('RSAFS',day); c=al.asof('CPIAUCSL',day)
    if r is None or c is None: return None
    x=(r.astype(float)/c.astype(float).reindex(r.index)).dropna(); return x if len(x) else None
SHIPPED=[('INDPRO','level'),('PAYEMS','level'),('CE16OV','level'),('PCEC96','level'),('DSPIC96','level'),('RSAFS_real','level'),('CMRMTSPL','level')]
WIDER=SHIPPED+[('UNRATE','rate'),('AWHMAN','level'),('MANEMP','level')]
# 3 September 2026: real personal income as first published - nominal PI (ALFRED vintages from January
# 1966, fetched through the keyless door) deflated by the CPI vintage of the day (ALFRED vintages from
# July 1972, the full history fetched the same day; the Mac harvest's copy began in 1994; the early
# vintages hold nineteen months, see cpi_deflator).  Transfers are not netted out: PCTR's vintages begin only in 2009.  This is the real-time
# analogue of 'real income less transfers' a reader of 1967-1979 had; DSPIC96 (1979 on) stays beside it.
_CPISA=None
def cpi_deflator(day, index):
    """The CPI (SA) as the vintage of `day` carried it; ALFRED's vintages before 1998 hold only the
    release table's nineteen months, so months before a vintage's own span are filled by chaining
    today's CPIAUCSL backward from the vintage's first month (only the seasonal factors of those
    earlier months can differ between the two, the NSA index being unrevised by construction);
    before the first CPI vintage (July 1972) the deflator is today's series throughout.  Labeled."""
    global _CPISA
    if _CPISA is None:
        x=pd.read_csv('/home/claude/a20/CPIAUCNS.csv'); x.columns=['d','v']; x['d']=pd.to_datetime(x.d)
        ns=x.set_index('d')['v'].astype(float)
        sa=al.asof('CPIAUCSL','2026-08-20'); _CPISA=sa if sa is not None else ns
    v=al.asof('CPIAUCSL',day)
    base=_CPISA.reindex(index)
    if v is None: return base
    v=v.reindex(index); first=v.first_valid_index()
    out=v.copy()
    if first is not None and first in _CPISA.index:
        k=v[first]/_CPISA[first]
        m=out.index<first
        out[m]=(base*k)[m]
    return out
def real_pi(day):
    pi=al.asof('PI',day)
    if pi is None: return None
    c=cpi_deflator(day,pi.index)
    x=(pi.astype(float)/c.astype(float)).dropna(); return x if len(x) else None
WITH_PI=SHIPPED+[('PI_real','level')]
def panel_asof(day, w0, spec):
    chs=[]
    for sid,kind in spec:
        s=real_retail(day) if sid=='RSAFS_real' else (real_pi(day) if sid=='PI_real' else al.asof(sid,day))
        if s is None: continue
        s=s.astype(float).dropna()
        if s.index.min()<=w0 and len(s[w0:])>=6: chs.append((sid,B.procyclical(s,kind)))
    return chs
def dates(day, w0, spec, cut=None):
    chs=panel_asof(day,w0,spec)
    if len(chs)<2: return None,None,[c for c,_ in chs]
    if cut is not None: chs=[(c,s[:cut]) for c,s in chs]
    end=max(s.index.max() for _,s in chs)
    r=B.date_episode(chs,w0,end,band_trough=0.12,band_peak=0.01,smooth=3,lookback=12,peak_cap=18)
    return r['peak'],r['trough'],[c for c,_ in chs]
if __name__=='__main__':
    TODAY='2026-08-20'
    for label,spec in (('shipped analogues',SHIPPED),('wider',WIDER),('shipped analogues + real personal income first print (PI/CPI vintages, 1966 on)',WITH_PI)):
        print(f'\n=== {label}')
        print('episode    +6 months          +14 months         +24 months         today, same channels, data cut at +14   channels at +14')
        tot={k:{'P':[],'T':[]} for k in ('+6','+14','+24','today')}
        for pk,tr in zip(PK,TR):
            k=pk.strftime('%Y-%m'); call=pd.Timestamp(CALL[k]); w0=pd.Timestamp(call.year,call.month,1)-pd.DateOffset(months=30)
            cells=[]; chans=None
            for lab,off in (('+6',6),('+14',14),('+24',24)):
                day=(tr+pd.DateOffset(months=off)); p,t,ch=dates(day.strftime('%Y-%m-%d'),w0,spec)
                if lab=='+14': chans=ch
                ep=None if p is None else md(p,pk); et=None if t is None else md(t,tr)
                cells.append(f"P {p.strftime('%y-%m') if p is not None else 'none '}({ep:+d}) T {t.strftime('%y-%m') if t is not None else 'none '}({et:+d})" if ep is not None and et is not None else f"P {'none' if p is None else p.strftime('%y-%m')} T {'none' if t is None else t.strftime('%y-%m')}")
                if ep is not None: tot[lab]['P'].append(ep)
                if et is not None: tot[lab]['T'].append(et)
            # today's data, the same channels, cut at +14 months so only revisions differ
            cut=tr+pd.DateOffset(months=13)
            p,t,ch=dates(TODAY,w0,[s for s in spec if s[0] in chans],cut=cut)
            ep=None if p is None else md(p,pk); et=None if t is None else md(t,tr)
            cells.append(f"P {p.strftime('%y-%m') if p is not None else 'none '}({ep:+d}) T {t.strftime('%y-%m') if t is not None else 'none '}({et:+d})" if ep is not None and et is not None else 'none')
            if ep is not None: tot['today']['P'].append(ep)
            if et is not None: tot['today']['T'].append(et)
            print(f"{k}    "+'   '.join(f'{c:18s}' for c in cells)+f"   {chans}")
        for lab,v in tot.items():
            print(f"  {lab:6s}: peaks n {len(v['P'])} exact {sum(x==0 for x in v['P'])} w1 {sum(abs(x)<=1 for x in v['P'])} w3 {sum(abs(x)<=3 for x in v['P'])} mae {np.mean(np.abs(v['P'])) if v['P'] else float('nan'):.2f} | troughs n {len(v['T'])} exact {sum(x==0 for x in v['T'])} w1 {sum(abs(x)<=1 for x in v['T'])} w3 {sum(abs(x)<=3 for x in v['T'])} mae {np.mean(np.abs(v['T'])) if v['T'] else float('nan'):.2f}")
