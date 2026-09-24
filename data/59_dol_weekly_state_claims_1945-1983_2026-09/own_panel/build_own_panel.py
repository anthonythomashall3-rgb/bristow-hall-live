"""One monthly state claims field from the Department's own releases, 1945 to date (5 September 2026, v2).

Sources, all Department of Labor:
  1945-09 .. 1983-05  the weekly release as first printed (bound volumes; weekly_ic/cc_1945_1983.csv from
                      26_dol_weekly_claims_1946-1983/parsed/assemble_weekly.py): state initial claims and state
                      insured unemployment (= continued weeks claimed), weeks ending Saturday
  1971-01 .. today    ETA 5159 monthly report, State UI (ar5159.csv): c1 initial claims total; c21 + c22
                      continued weeks claimed, intrastate + interstate liable
  1984-06 .. today    ETA 539 weekly report (ar539.csv): c3 initial claims, c8 continued weeks claimed
Every series is an AVERAGE WEEKLY COUNT for the month (weekly sources: mean of the weeks ending in the month;
the monthly 5159 total divided by weekdays/5), so four- and five-week months are on one footing.

Concept checks measured on the overlaps (this file prints them):
  initial claims: release = 5159 = 539 (median log ratio within 0.003) - no factor
  continued weeks claimed: 539 = 5159 c21+c22 (0.011); release = 5159 from 1977 (0.03); in 1971-76 the 5159 file
  understates fifteen jurisdictions by 0.2-0.8 log points (CA NJ MI IL MN VA KY WA WV AZ DC FL CT OK PR...), where
  the release and the Fieldhouse transcription agree with each other - the 5159 is not used for those state-years.
Assembly per state-month:
  release era (to 1983-05): the release mean over >=2 weeks; screened against the 5159 where the 5159 is trusted
  (|log ratio| > 0.25 -> the release cell is an OCR error, replaced by the 5159) and against the same month a year
  earlier and a year later otherwise (more than 1.1 log points from both -> dropped); a single-week mean is used only when no
  other source has the month; remaining gaps from the 5159 (1971 on)
  1983-06 .. 1984-05: 5159;  1984-06 on: 539 weekly means, gaps from 5159
Per-state level factors release -> Department file: initial claims none; continued weeks claimed from the 1977-83
overlap without 1979 (the 1978-79 volume's OCR is unusable) - printed below, applied to the release era.
Output: OWN_state_claims_nsa_weeklyavg.csv ('ST | initial claims', 'ST | continued weeks claimed'; NSA levels),
OWN_national_claims_nsa_weeklyavg.csv (sum over the 51 jurisdictions of the tool's field, states with a missing
month carried by their own log-interpolated value, never chained), BUILD_LOG.txt.
"""
import pandas as pd, numpy as np
R="/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Onset Detector Data/"
LAB=R+"24_bristow_rule_lab/workspace/lab/dol/"; REL=R+"26_dol_weekly_claims_1946-1983/parsed/"
log=[]
def say(s): print(s); log.append(s)
def wk(m): return np.busday_count(m.date(),(m+pd.offsets.MonthEnd(0)+pd.Timedelta(days=1)).date())/5.0
def monthly(W,min_weeks):
    g=W.groupby(W.index.to_period('M')); m=g.mean(); n=g.count(); m=m.where(n>=min_weeks); m.index=m.index.to_timestamp(); return m
# 1. release
ic_w=pd.read_csv(REL+'weekly_ic_1945_1983.csv',index_col=0,parse_dates=True); cc_w=pd.read_csv(REL+'weekly_cc_1945_1983.csv',index_col=0,parse_dates=True)
ic_rel2,ic_rel1=monthly(ic_w,2),monthly(ic_w,1); cc_rel2,cc_rel1=monthly(cc_w,2),monthly(cc_w,1)
# 2. 5159
d=pd.read_csv(LAB+'ar5159.csv',low_memory=False); d['m']=pd.to_datetime(d['rptdate'],errors='coerce').dt.to_period('M').dt.to_timestamp(); d=d.dropna(subset=['m'])
for c in ('c1','c21','c22'): d[c]=pd.to_numeric(d[c],errors='coerce')
d['cw']=d[['c21','c22']].sum(axis=1,min_count=1)
def piv59(col):
    P=d.dropna(subset=[col]).pivot_table(index='m',columns='st',values=col,aggfunc='sum').sort_index().where(lambda x:x>0)
    return P.div(pd.Series([wk(m) for m in P.index],index=P.index),axis=0)
ic_59,cc_59=piv59('c1'),piv59('cw')
# 3. 539
e=pd.read_csv(LAB+'ar539.csv',low_memory=False); e['w']=pd.to_datetime(e['rptdate'],errors='coerce'); e=e.dropna(subset=['w'])
def piv39(col):
    e[col]=pd.to_numeric(e[col],errors='coerce')
    return monthly(e.dropna(subset=[col]).pivot_table(index='w',columns='st',values=col,aggfunc='sum').sort_index().where(lambda x:x>0),1)
ic_39,cc_39=piv39('c3'),piv39('c8')
ST=[s for s in ic_59.columns if s not in ('PR','VI')]
idx=pd.date_range('1945-09-01',max(ic_39.index.max(),ic_59.index.max()),freq='MS')
def R_(X): return X.reindex(index=idx,columns=ST)
ic_rel2,ic_rel1,cc_rel2,cc_rel1,ic_59,cc_59,ic_39,cc_39=map(R_,(ic_rel2,ic_rel1,cc_rel2,cc_rel1,ic_59,cc_59,ic_39,cc_39))
# where is the 5159 trusted for continued weeks claimed? state-years whose 1971-76 median log ratio to the release is beyond 0.15
r=(np.log(cc_59)-np.log(cc_rel2)).loc['1971':'1976']; byy=r.groupby(r.index.year).median()
trust_cc=pd.DataFrame(True,index=idx,columns=ST)
for st in ST:
    for y,v in byy[st].items():
        if pd.notna(v) and abs(v)>0.15: trust_cc.loc[str(y),st]=False
say(f"5159 continued-weeks cells not trusted (1971-76 understatement): {int((~trust_cc).sum().sum())} state-months in {sorted(set(trust_cc.columns[(~trust_cc).any()]))}")
trust_ic=pd.DataFrame(True,index=idx,columns=ST)
for nm,a,b in (('IC release vs 5159 1971-83',ic_rel2,ic_59),('CC release vs 5159 1977-83 ex 1979',cc_rel2,cc_59),('IC 539 vs 5159 1984-2026',ic_39,ic_59),('CC 539 vs 5159 1984-2026',cc_39,cc_59)):
    lo,hi=('1971','1983') if 'release' in nm and 'IC' in nm else (('1977','1983') if 'release' in nm else ('1984','2026'))
    rr=(np.log(a)-np.log(b)).loc[lo:hi]
    if 'ex 1979' in nm: rr=rr[rr.index.year!=1979]
    med=rr.median(); say(f"{nm}: median log ratio {med.median():+.3f}, IQR {med.quantile(.25):+.3f}..{med.quantile(.75):+.3f}, states beyond 5%: {int((med.abs()>0.05).sum())}")
def M(mask1d): return pd.DataFrame(np.repeat(np.asarray(mask1d)[:,None],len(ST),axis=1),index=idx,columns=ST)
def assemble(rel2,rel1,x59,x39,trust,name,factor):
    rel2=rel2*np.exp(factor); rel1=rel1*np.exp(factor)
    era=M(idx<=pd.Timestamp('1983-05-01')); m2=M((idx>=pd.Timestamp('1983-06-01'))&(idx<=pd.Timestamp('1984-05-01'))); m3=M(idx>=pd.Timestamp('1984-06-01'))
    lr=np.log(rel2)-np.log(x59); bad59=(lr.abs()>0.25)&trust
    # own screen where the 5159 cannot be used: a cell more than 1.1 log points from the SAME month a year earlier AND a year later
    # (an OCR error is a wrong column or a dropped digit, x3 to x10; a recession year moves a state's claims by 0.7 at most)
    L=np.log(rel2); dm=(L-L.shift(12)).abs(); dp=(L-L.shift(-12)).abs()
    far=(dm>1.1)&(dp>1.1)|((dm>1.1)&dp.isna())|((dp>1.1)&dm.isna())
    badown=far&(x59.isna()|~trust)
    keep=rel2.where(~(bad59|badown))
    n_bad59=int((bad59&era).sum().sum()); n_badown=int((badown&era).sum().sum())
    out=keep.where(era); src=pd.DataFrame('',index=idx,columns=ST); src=src.mask(out.notna(),'release')
    def fill(cand,tag):
        nonlocal out,src
        c=cand.where(out.isna()); out=out.where(out.notna(),c); src=src.mask(c.notna()&(src==''),tag)
    fill(x59.where(era&trust),'5159 fill'); fill(rel1.where(era),'release 1wk'); fill(x59.where(m2),'5159'); fill(x39.where(m3),'539'); fill(x59.where(m3),'5159 fill')
    say(f"{name}: release cells screened out vs 5159 {n_bad59}, vs own median {n_badown}; sources {src.stack().value_counts().to_dict()}")
    cov=out.loc[:'1970-12'].notna().mean(axis=1); say(f"   coverage 1945-70 by year (share of 51 jurisdictions): {cov.groupby(cov.index.year).mean().round(2).to_dict()}")
    return out,src
fac_ic=pd.Series(0.0,index=ST)
rr=(np.log(cc_59)-np.log(cc_rel2)).loc['1977':'1983']; rr=rr[rr.index.year!=1979]; fac_cc=rr.median().reindex(ST).fillna(0.0)
say(f"continued-weeks factors release->file (log): median {fac_cc.median():+.3f}, min {fac_cc.min():+.3f} ({fac_cc.idxmin()}), max {fac_cc.max():+.3f} ({fac_cc.idxmax()})")
IC,SIC=assemble(ic_rel2,ic_rel1,ic_59,ic_39,trust_ic,'initial claims',fac_ic)
CC,SCC=assemble(cc_rel2,cc_rel1,cc_59,cc_39,trust_cc,'continued weeks claimed',fac_cc)
PAN=pd.concat([IC.add_suffix(' | initial claims'),CC.add_suffix(' | continued weeks claimed')],axis=1).dropna(how='all')
PAN.to_csv('OWN_state_claims_nsa_weeklyavg.csv')
pd.concat([SIC.add_suffix(' | initial claims'),SCC.add_suffix(' | continued weeks claimed')],axis=1).reindex(PAN.index).to_csv('OWN_state_claims_sources.csv')
# national: sum over the 51 with missing state-months interpolated in logs (gaps up to 6 months), never chained
def national(X):
    L=np.log(X); Li=L.interpolate(limit=6,limit_area='inside'); Xi=np.exp(Li)
    n_obs=X.notna().sum(axis=1); n_used=Xi.notna().sum(axis=1)
    s=Xi.sum(axis=1).where(n_used>=48); return s,n_obs,n_used
nat={}
for nm,X in (('initial claims',IC),('continued weeks claimed',CC)):
    s,n_obs,n_used=national(X); nat[nm]=s; nat[nm+' | states observed']=n_obs; nat[nm+' | states used']=n_used
    say(f"national {nm}: first month {s.dropna().index.min().date()}, months with all 51 observed {int((n_obs==51).sum())}, months carried by interpolation {int(((n_used>=48)&(n_obs<51)).sum())}, months missing {int(s.isna().sum())}")
NAT=pd.DataFrame(nat); NAT.to_csv('OWN_national_claims_nsa_weeklyavg.csv')
say(f"panel {PAN.shape} {PAN.index.min().date()} {PAN.index.max().date()}")
open('BUILD_LOG.txt','w').write('\n'.join(log)+'\n')
