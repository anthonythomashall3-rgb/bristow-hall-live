"""v2.1 = v2 on data-month windows with the housing pair off the 0.45 branch. (a) leg A (state diffusion, HYB/Fieldhouse field)
confirmed by Sahm priced as a pre-1971 speed lever; (b) last-bit audit of every line on its object; (c) hazard of v2.1 on Paper 1's quiet set."""
from mini import *
from legu_min import s_cur, spl
from scipy import stats
exec(open('fast21.py').read().split("FHz=[x for x in leg_gap_mx(gm,0.45,rearm='window')")[0].replace("out=open('fast21.out','w')","out=open('fast22.out','w')"))
FHz=[x for x in leg_gap_mx(gm,0.45,rearm='window') if x[1]<pd.Timestamp('1971-01-01')]
Sg=dict(name='sahm50',gap=g,line=0.50); Sg43=dict(name='sahm43',gap=g,line=0.43)
def pubof(cf,t):
    if cf['name'].startswith('sahm'): return rel.get(t,pd.Timestamp(t.year,t.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
    return (t+pd.Timedelta(days=cf['pub_lag_days'])) if 'pub_lag_days' in cf else (pd.Timestamp(t.year,t.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=cf['pub_day']-1))
A=[(p,dd) for p,dd in PL['A']]
P("\n(a) LEG A (v8's state diffusion 36/8 on the Fieldhouse field) as a proposer confirmed by Sahm only, month windows")
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    for lab_,Vc,sl,Sc in [('a-priori (vac .36, Sahm .50)',V36,0.50,Sg),('construction-grade (vac .30, Sahm .43)',V30,0.43,Sg43)]:
        X=hub(sl,vr,Vc['line']); U2=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc,Pp],'month'); L=confirm_w(leg_gapx(s,0.25,rearm='window'),[HpX2],'month')
        base=run3(f"v2.1 {lab_}",{'U':U2,'L':L,'X':X})
        AS=confirm_w(A,[Sc],'month'); run3(f"v2.1 + A{{Sahm {sl}}} {lab_}",{'U':U2,'L':L,'X':X,'A':AS})
        P("      A proposals and their Sahm confirmation:",[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m'),c) for p,dd,c in AS])
P("\n(b) LAST-BIT AUDIT: readings within 1e-9 of a line (exact comparisons on quantities the binary representation cannot hold)")
def audit(nm,ser,lines):
    ser=ser.dropna()
    for l in lines:
        near=ser[(ser-l).abs()<1e-9]; P(f"   {nm} at line {l}: {len(near)} readings within 1e-9 -> {[m.strftime('%Y-%m') for m in near.index][:12]}{'...' if len(near)>12 else ''}")
audit('Sahm first prints (hub)',g,[0.50,0.43]); audit('vacancy (2,6) gap',vr,[0.36,0.30]); audit('housing x rate pair (exact tenths)',PAIRX2,[1.0]); audit('hours x nondurable pair',P1,[1.0])
gi=(s_cur-s_cur.rolling(52,min_periods=52).min().shift(1)).dropna(); audit('IURSA 52-wk gap (current)',gi,[0.45,0.25])
gs=(spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna(); audit('IURSA 52-wk gap (first prints)',gs,[0.45,0.25]); audit('Fieldhouse IUR gap',gm,[0.45])
# exact Sahm in thirtieths: 3-mo sum of tenths minus 3 x (12-mo min of 3-mo means in tenths) — compare the sign of the last bit decisions
def sahm_exact(u):
    t=(u*10).round().astype(int); s3=t.rolling(3).sum(); m3=s3.rolling(12,min_periods=1).min().shift(0)
    # lab convention: gap = 3-mo mean minus min of the prior 12 months' 3-mo means (incl. current?) — we only flag near-line readings, so use the same series g
    return None
near50=g[(g-0.50).abs()<1e-9]
P("   Sahm readings within 1e-9 of 0.50 and whether the float value is >= 0.50:",[(m.strftime('%Y-%m'),bool(v>=0.50)) for m,v in near50.items()])
P("\n(c) HAZARD of v2.1 on Paper 1's quiet set (outside peak-9 .. trough+18), month windows (7 back incl. own month, 5 forward)")
def quiet(idx):
    q=pd.Series(True,index=idx)
    for p,t in zip(PK,TR): q[(idx>=p-pd.DateOffset(months=9))&(idx<=t+pd.DateOffset(months=18))]=False
    return q
def hits(o,line): o=o.dropna(); return (o>=line).reindex(pd.date_range('1949-01-01','2026-07-01',freq='MS')).fillna(False)
def win_expo(hitlist, back=7, fwd=5, start='1960-01-01'):
    idx=pd.date_range(start,'2026-07-01',freq='MS'); h=np.zeros(len(idx),bool)
    for x in hitlist: h|=x.reindex(idx).fillna(False).values.astype(bool)
    s=pd.Series(h,index=idx); q=quiet(idx)
    f=s[::-1].rolling(fwd,min_periods=1).max()[::-1].astype(bool); b=s.rolling(back,min_periods=1).max().astype(bool)
    return (f|b)[q].mean()*100, int(q.sum())
H=hits(PAIRX2,1.0); eH,nq=win_expo([H]); P(f"   housing pair (exact tenths, both halves) window exposure {eH:.2f}% of {nq} quiet months 1960-2026; quiet months at the line: {[m.strftime('%Y-%m') for m,v in H.items() if v and quiet(H.index)[m] and m>=pd.Timestamp('1960-01-01')]}")
for vl in [0.36,0.30]:
    V=hits(vr,vl); Pq=hits(P1,1.0); eVP,_=win_expo([V,Pq]); eVHP,_=win_expo([V,H,Pq]); eVb,_=win_expo([V],back=7,fwd=1,start='1949-01-01')
    P(f"   vacancy {vl}: V|P window exposure {eVP:.2f}% (was V|H|P {eVHP:.2f}%); six-back vacancy exposure (hub) {eVb:.2f}%")
idx=pd.date_range('1972-01-01','2026-07-01',freq='MS'); q=quiet(idx); QY=q.sum()/12
for vint,s in [('current file',s_cur),('first prints',spl)]:
    n25=sum(1 for p,dd in leg_gapx(s,0.25,rearm='window') if q.reindex([dd]).fillna(False).iloc[0]); n45=sum(1 for p,dd in leg_gapx(s,0.45,rearm='zero') if q.reindex([dd]).fillna(False).iloc[0])
    r25=n25/QY; b25=stats.chi2.ppf(0.95,2*(n25+1))/2/QY; b45=stats.chi2.ppf(0.95,2*(n45+1))/2/QY
    P(f"   {vint}: U25 quiet proposals {n25}/{QY:.1f} quiet yrs -> x housing {eH:.2f}% = {r25*eH:.3f}%/yr observed (one in {1/(r25*eH/100):.0f}), bound {b25*eH:.3f}%; U45 quiet proposals {n45} -> bound {b45:.2f}%/yr x V|P")
idx2=pd.date_range('1949-01-01','2026-07-01',freq='MS'); q2=quiet(idx2); QY2=q2.sum()/12
for sl,vl in [(0.50,0.36),(0.43,0.30)]:
    eps=[]; armed=True
    for m,v in g.items():
        if m<idx2[0]: continue
        if armed and v>=sl:
            armed=False
            if q2.reindex([m]).fillna(False).iloc[0]: eps.append(m.strftime('%Y-%m'))
        elif not armed and v<sl: armed=True
    eVb,_=win_expo([hits(vr,vl)],back=7,fwd=1,start='1949-01-01'); r=len(eps)/QY2
    P(f"   hub Sahm {sl}: quiet crossings {eps} in {QY2:.1f} quiet yrs = {r*100:.2f}%/yr x six-back vacancy {eVb:.2f}% = {r*eVb:.3f}%/yr (one in {1/(r*eVb/100):.0f})")
out.close()
