"""Stage 75: a last-resort output backstop.  The three foreign misses have no labour or
rate signal at all -- every reading is below that country's own quiet maximum -- so no
threshold on the existing channels can reach them.  The only thing that moved was output.
Price a cumulative-real-GDP backstop: peak-to-trough fall >= X% across a run of two or
more negative quarters.  It cannot be fast; the question is whether it closes the misses
without firing where there was no recession."""
import os
import pandas as pd, numpy as np
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
exec(open(os.path.join(BASE,"ladder","stage51_intl_v2.py")).read().split("NBER = [(")[0])
NBER=[("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),("1960-04","1961-02"),
      ("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
      ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04"),
      ("2024-04","2024-08")]
NBER=[(pd.Timestamp(a+"-01"),pd.Timestamp(b+"-01")) for a,b in NBER]
rows=[]
for iso in sorted(CC):
    g,sid=gdp(iso)
    if g is None or len(g)<60: continue
    r=(g.pct_change()*100).dropna(); neg=(r<0).values; dts=list(r.index)
    i=0
    while i<len(neg):
        if neg[i]:
            j=i
            while j+1<len(neg) and neg[j+1]: j+=1
            if j-i+1>=2 and i>=1:
                lvl=g.loc[dts[i-1]:dts[j]]
                fall=(lvl.min()/lvl.iloc[0]-1)*100
                P=(pd.Timestamp(dts[i-1])+pd.DateOffset(months=2)).replace(day=1)
                T=(pd.Timestamp(dts[j])+pd.DateOffset(months=2)).replace(day=1)
                real = bool(any(a<=T and b>=P for a,b in NBER)) if iso=="USA" else bool(any(a<=T and b>=P for a,b in oecd(iso)))
                rows.append(dict(iso=iso,peak=str(P.date())[:7],trough=str(T.date())[:7],
                                 fall=float(fall),nq=int(j-i+1),real=real))
            i=j+1
        else: i+=1
df=pd.DataFrame(rows)
us=df[df.iso=="USA"]
print("=== US two-negative-quarter runs, cumulative real GDP fall ===")
for _,x in us.iterrows():
    print("  %s..%s  %5.2f%%  %dq  NBER/Paper1 recession: %s" % (x.peak,x.trough,x.fall,x.nq,x.real))
qmax=us[~us.real.astype(bool)].fall.max() if (~us.real.astype(bool)).any() else np.nan
print("  largest US NON-recession run: %s" % ("none on current vintage" if qmax!=qmax else "%.2f%%"%qmax))
noreal=df[~df.real.astype(bool)]
print("\n=== two-negative-quarter runs that overlap NO recession window (all countries) ===")
for _,x in noreal.sort_values("fall").iterrows():
    print("  %-4s %s..%s  %5.2f%%  %dq" % (x.iso,x.peak,x.trough,x.fall,x.nq))
qmax=noreal.fall.max() if len(noreal) else -0.62
print("  deepest such run: %.2f%%   (US 2022H1 on FIRST PRINTS was -0.62%%; current vintage has revised it away)" % qmax)
qmax=min(qmax,-0.62)
MISS=[("DEU","2012-09"),("ITA","2001-03"),("ITA","2002-12")]
print("\n=== the three missed foreign recessions ===")
mv=[]
for iso,pk in MISS:
    x=df[(df.iso==iso)&(df.peak==pk)]
    if len(x): print("  %-4s %s  %5.2f%%" % (iso,pk,x.fall.iloc[0])); mv.append(x.fall.iloc[0])
print("\n  max-margin line between the largest US non-recession (%.2f) and the shallowest miss (%.2f) = %.2f%%"
      % (qmax, max(mv), (qmax+max(mv))/2))
X=(qmax+max(mv))/2
print("\n=== who fires at %.2f%% ===" % X)
fires=df[df.fall<=X]
byc=fires.groupby("iso").size().to_dict()
print("  episodes firing, by country:", byc)
print("  US firings:", [(x.peak,round(x.fall,2),x.real) for _,x in fires[fires.iso=='USA'].iterrows()])
print("  US firings that are NOT recessions:", [(x.peak,round(x.fall,2)) for _,x in fires[(fires.iso=='USA')&(~fires.real.astype(bool))].iterrows()])
print("\n=== coverage of foreign technical recessions after adding it ===")
tot=cov=0
for iso in sorted(CC):
    if iso=="USA": continue
    sub=df[df.iso==iso]
    if len(sub)<2: continue
    tot+=len(sub); cov+=int((sub.fall<=X).sum())
print("  the output backstop alone covers %d of %d foreign technical recessions (%.0f%%)" % (cov,tot,100*cov/max(tot,1)))
df.to_csv(os.path.join(BASE,"ladder","stage75_gdp.csv"),index=False)
