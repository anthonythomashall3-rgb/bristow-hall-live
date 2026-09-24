"""Stage 87: the anti-overfitting test.  The claims floor was chosen on the US record.
Does the same idea -- no call without a rise on a second, layoff-side series -- also cut
false alarms abroad, where it was never fitted?  Registered unemployment is the closest
foreign analogue of insured claims."""
import os
import pandas as pd, numpy as np
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
exec(open(os.path.join(BASE,"ladder","stage51_intl_v2.py")).read().split("NBER = [(")[0])
def run(floor):
    cov=tot=fa=0; yrs=0.0; nc=0
    for iso in sorted(CC):
        ur=first("LRHUTTTT%sM156S"%CC[iso],"LRUNTTTT%sM156S"%CC[iso],"LRHUTTTT%sM156N"%CC[iso])
        iu=first("LMUNRRTT%sM156S"%CC[iso],"LMUNRRTT%sM156N"%CC[iso])
        if ur is None or iu is None: continue
        st=first("IR3TIB01%sM156N"%CC[iso],"IRSTCI01%sM156N"%CC[iso]); lt=first("IRLTLT01%sM156N"%CC[iso])
        ip=first("%sPROINDMISMEI"%iso)
        idx=pd.DatetimeIndex(pd.date_range(ur.index[0],ur.index[-1],freq="MS"))
        u=ur.reindex(idx).interpolate(limit_area="inside")
        v=iu.reindex(idx).interpolate(limit_area="inside")
        lay=(v/v.rolling(12).min()-1)*100            # registered unemployment above its 12-month floor, %
        co=(lay>=floor) if floor is not None else pd.Series(True,index=idx)
        gate=pd.Series(False,index=idx)
        if st is not None and lt is not None:
            sp=lt.reindex(idx,method="ffill")-st.reindex(idx,method="ffill")
            gate=(sp<0).rolling(12,min_periods=1).max().fillna(0).astype(bool)
        ug=u.rolling(3).mean()-u.rolling(12).min()
        g2=v.rolling(3).mean()-v.rolling(12).min()
        f=(ug>=0.36)&gate; f|=(g2>=0.40)&gate; f|=(ug>=0.55)&(~gate)
        if st is not None:
            s=st.reindex(idx,method="ffill"); f|=((s-s.shift(3))<=-1.45)&gate
        if ip is not None:
            p=ip.reindex(idx,method="ffill"); d=(p/p.shift(1)-1)*100
            f|=(d<=-2.0)&(d.shift(1)<=-2.0)
        f=(f&co).fillna(False)
        eps,_=technical(iso); eps=[(a,b) for a,b in eps if a>=idx[0] and b<=idx[-1]]
        oec=[(a,b) for a,b in oecd(iso) if a>=idx[0] and b<=idx[-1]]
        allw=eps+oec; yrs+=(idx[-1]-idx[0]).days/365.25; nc+=1
        runs=[]; on=False
        for d0,val in f.items():
            if val and not on: on=True; runs.append(d0)
            elif not val: on=False
        for a,b in eps:
            tot+=1
            if any(a-pd.DateOffset(months=6)<=x<=b for x in runs): cov+=1
        for x in runs:
            if not any(a-pd.DateOffset(months=6)<=x<=b+pd.DateOffset(months=3) for a,b in allw): fa+=1
    return cov,tot,fa,yrs,nc
print("%-38s %-12s %-9s %s" % ("layoff floor (registered unemployment)","covered","false","rate"))
for fl,lab in [(None,"none (v8 structure)"),(0.0,">= 0% above its 12-month floor"),
               (1.0,">= 1%"),(2.0,">= 2%"),(3.0,">= 3%"),(5.0,">= 5%")]:
    c,t,fa,y,nc=run(fl)
    print("%-38s %2d/%-9d %-9d %.1f%%/yr (1 per %.0f yr, %d countries)" % (lab,c,t,fa,100*fa/y,y/max(fa,1),nc))
