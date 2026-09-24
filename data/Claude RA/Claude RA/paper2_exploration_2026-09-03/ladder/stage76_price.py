"""Stage 76: what would it cost to catch the three misses?  Lower each channel's line
just far enough to reach them, and count the false episodes that appear."""
import os
import pandas as pd, numpy as np
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
exec(open(os.path.join(BASE,"ladder","stage51_intl_v2.py")).read().split("NBER = [(")[0])
NEED={"u_gap":0.067,"iu_gap":0.100,"rate_fall":0.568,"ip_2x":1.270}   # Germany 2012, the shallowest
def panel(th_u, th_r, th_ip):
    fa=0; yrs=0.0
    for iso in sorted(CC):
        ur=first("LRHUTTTT%sM156S"%CC[iso],"LRUNTTTT%sM156S"%CC[iso],"LRHUTTTT%sM156N"%CC[iso])
        if ur is None: continue
        st=first("IR3TIB01%sM156N"%CC[iso],"IRSTCI01%sM156N"%CC[iso])
        ip=first("%sPROINDMISMEI"%iso)
        idx=pd.DatetimeIndex(pd.date_range(ur.index[0],ur.index[-1],freq="MS"))
        u=ur.reindex(idx).interpolate(limit_area="inside")
        on=(u.rolling(3).mean()-u.rolling(12).min())>=th_u
        if st is not None:
            s=st.reindex(idx,method="ffill"); on|=(-(s-s.shift(3))>=th_r)
        if ip is not None:
            p=ip.reindex(idx,method="ffill"); d=-(p/p.shift(1)-1)*100
            on|=(pd.concat([d,d.shift(1)],axis=1).min(axis=1)>=th_ip)
        on=on.fillna(False)
        eps,_=technical(iso); eps=[(a,b) for a,b in eps if a>=idx[0] and b<=idx[-1]]
        oec=[(a,b) for a,b in oecd(iso) if a>=idx[0] and b<=idx[-1]]
        allw=eps+oec
        yrs+=(idx[-1]-idx[0]).days/365.25
        # count runs of `on` that overlap no window
        run=False
        for d0,v in on.items():
            if v and not run:
                run=True
                if not any(a-pd.DateOffset(months=6)<=d0<=b+pd.DateOffset(months=3) for a,b in allw): fa+=1
            elif not v: run=False
    return fa,yrs
print("%-34s %-10s %s" % ("thresholds (u / rate / IP)","false eps","rate"))
for lab,tu,tr,ti in [("v8 as frozen (0.36 / 1.45 / 2.0)",0.36,1.45,2.0),
                     ("reach Italy 2002 (0.33)",0.33,1.45,2.0),
                     ("reach Italy 2001 (0.23)",0.23,1.45,2.0),
                     ("reach Germany 2012 (0.067)",0.067,0.57,1.27)]:
    fa,yrs=panel(tu,tr,ti)
    print("%-34s %-10d %.1f%%/yr  (1 per %.1f yr)" % (lab,fa,100*fa/yrs,yrs/max(fa,1)))
