"""Leg U's 1981 silence is a 365-DAY CALENDAR LOCKOUT, not the data.

The insured-unemployment gap crosses 0.50 in the week ending 24 October 1981
-- published 29 October, +90 days after the peak month ended, which is exactly
where the parallel route's worst call sits.  This route never sees it, because
leg U suppresses any firing within 365 days of the last one and the 1980
episode's firings run late enough into 1980 to swallow it.

365 is a number nobody chose.  The principled re-arm is the object's own: the
leg re-arms when the gap falls back below a reset line.  Priced here on quiet
calls, which is what Rule 21 asks."""
exec(open('legU.py').read().split('U=leg_U()')[0])
import pandas as pd, numpy as np
PEAKS=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2023-07']
TROUGHS=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04','2024-08']
M=lambda x: pd.Timestamp(x+'-01')
def quiet_month(d):
    return not any((d>=M(p)-pd.DateOffset(months=9)) and (d<=M(t)+pd.DateOffset(months=18))
                   for p,t in zip(PEAKS,TROUGHS))
def leg_U2(line=0.50, reset=None, lockout=None, smooth=1, look=52, pub=5):
    x=s.rolling(smooth).mean()
    gap=x - x.rolling(look,min_periods=look).min().shift(1)
    calls=[]; armed=True; last=None
    for t,v in gap.dropna().items():
        if reset is not None:
            if armed and v>=line:
                calls.append((t+pd.Timedelta(days=pub), pd.Timestamp(t.year,t.month,1))); armed=False
            elif not armed and v<reset:
                armed=True
        else:
            if v>=line and (last is None or (t-last).days>lockout):
                calls.append((t+pd.Timedelta(days=pub), pd.Timestamp(t.year,t.month,1)))
            if v>=line: last=t
    return calls
def show(nm,calls):
    q=[(p,d) for p,d in calls if quiet_month(d)]
    hit=set()
    for p,d in calls:
        for pk in PEAKS:
            if -9<=(d.year-M(pk).year)*12+d.month-M(pk).month<=12: hit.add(pk)
    e81=[p for p,d in calls if pd.Timestamp('1981-08-01')<=p<=pd.Timestamp('1982-03-01')]
    print(f"{nm:44} {len(calls):3d} calls  {len(hit):2d}/13 recessions reached  "
          f"QUIET CALLS {len(q):2d}   1981: " + (f"{e81[0]:%Y-%m-%d} ({(e81[0]-pd.Timestamp('1981-07-31')).days:+d} d)" if e81 else "none"))
    if q: print("      quiet:", ', '.join(f'{d:%Y-%m}' for _,d in q[:12]))
print("shipped and calendar variants")
for lo in (365,270,180,120,90):
    show(f"  lockout {lo} days", leg_U2(lockout=lo))
print("\nre-arm on the object's own return, no calendar at all")
for r in (0.50,0.40,0.30,0.20,0.10,0.0):
    show(f"  re-arm when the gap falls below {r:.2f}", leg_U2(reset=r))
