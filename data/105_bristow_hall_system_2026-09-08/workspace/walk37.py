"""WALK 37 - WALK 34 WITH THE PAPER SPREAD CORRECTED AFTER AUGUST 1997 (Rule Zero, collection 105, 8 September
2026). The spread object was built as the prime commercial paper rate (FRED H0RIFSPPFM01NWF, weekly) less the
three-month bill (WTB3MS). That paper series ends on 29 August 1997 and the code carried its last value, 5.49,
forward, so from September 1997 the "spread" was 5.49 less the bill rate - the bill rate falling, not paper widening
(it read 5.5 in December 2008 and March 2020). Found on 8 September while building the live series. From 5 September
1997 the paper leg is the one-month AA nonfinancial commercial paper rate (FRED DCPN30, daily, averaged to the
Friday week) and the object is otherwise unchanged: 13-week mean of the spread above its 39-week minimum. Which
calls the old object confirmed, and what changes, is in the version note.

WALK 34 - ONE CLOCK FOR THE CHRONOLOGY, THE MACHINERY OF WALK30 (collection 104, 8 September 2026). Anthony: when
the rule fires, that is the date. Every call in the diary is dated the calendar month of its firing day, peaks and
troughs alike; closer C's hold to the last day of the month it used to name is removed, so C fires the day its
evidence arrives. Inside the machine nothing else changes: the confirmation windows, the matching of calls to
recessions and the false-alarm test still run on the data months (that is how the rule decides whether to speak,
not what it says), the walk still chooses every line by the day-count objective of walk30, and the trough clause
is the declared acceptance in days (a ratified trough may not be closed more than thirty-one days before its month
ended; the old test on the named month is gone because there is no named month). walk31 to walk33 tried a month
objective and a re-dated matching window; both let the walk sit on lines walk30 had moved off and each produced one
false alarm (August 2002; November 1984) - recorded in the version note, refused. A cut with no clean point keeps
the last configuration and goes on logging.

WALK 30 - WALK 29 WITH THE RUN FIXED AT THREE FALLING WEEKS, NOT WALKED (collection 104, 8 September 2026).
The run of falling weeks is a convention about weekly noise, not a magnitude to be chosen: three consecutive falls is
the conventional minimum for a weekly series to have a direction (the four-week average exists for the same reason).
In walk29 the run began at four, the safest value, and moved to three at the 1972 cut once the 1970 trough was
ratified; the only close that difference touched was 1970 itself, closed by K at +52 under the run of four where C
would have closed it at +24 under the run of three. Fixing the run at three removes a walked number and leaves the
drop D and the market bar s as the only numbers C carries into the grid. Declared after walk29, and logged as such.

WALK 29 - WALK 28 WITH THE RUN OF TWO FALLING WEEKS REMOVED FROM THE GRID (collection 104, 8 September 2026).
walk28 loosened C to a drop of 4 with a run of 2 at the 1977 cut, rewarded by the two ratified troughs of 1970 and
1975, and that configuration closed the 1980 recession on 14 February 1980, 168 days early, on a two-week fall in the
flow with the market fifteen per cent off its low: a false start of the claims rise, a pattern the two ratified troughs
could not show. The frozen screen shows the same run of two closing 2009 five months early. A run of two falling
weeks is inside the week-to-week noise of a weekly series and cannot establish a direction; three is the conventional
minimum, and the other closers on the menu already carry run-length floors declared on the same ground. The grid for
n is therefore [4,3]. Declared after walk28, and logged as such.

WALK 28 - WALK 27 WITH THE PRE-1980 ANNOUNCEMENT DATES SOURCED (collection 104, 8 September 2026).
Every announcement date before 1980 is now the release date of the first issue of Business Conditions Digest (FRASER,
St. Louis Fed) that carries the NBER designation. The four turns of 1948-1961 are in the first issue (October 1961:
the reference-date table 1854-1961 and "February 1961 (current trough)"), so any date before the 1962 cut is equivalent
and 1 October 1961 is used. Peak December 1969 (then November 1969) and trough November 1970: designated by the NBER
in National Bureau Report Supplement No. 8 (May 1971), entered in the June 1971 issue, released 30 June 1971, marked
"tentative and subject to revision". Peak November 1973: in the reference list of the March 1976 issue, released
31 March 1976 (the February 1976 issue, released 2 March 1976, still says "not designated"). Trough March 1975: the
November 1976 issue, released 2 December 1976 ("A new shaded area has been entered ... the most recent recession
designated by the NBER - November 1973 (peak) to March 1975 (trough)"); the October 1976 issue still says "not
designated". The earlier dates in walk26 (1949-06-01, 1954-08-01, 1958-06-01, 1961-02-01, 1970-08-01, 1974-11-01) were
unsourced and are withdrawn. Committee dates from July 1980 on are unchanged. The four troughs of 1949-1961 were
dated before the walk begins but are NOT scored: the trough sample is the nine troughs from 1970 (Rule 25), because the
weekly claims objects the closers are built on begin in 1967, and under the monthly closers of the menu the 1949 and 1954
troughs are dated two months out in every configuration, which would leave the walk without a clean point at any cut.

WALK 27 - THE TROUGH CAMPAIGN (collection 104, 8 September 2026). walk26 with closer C on the menu and its three
numbers in the grid, safest first; the trough clause and the trough objective changed to the declared acceptance of
8 September 2026 (a close up to a month early is accepted; a close inside the month after the trough month is
preferred). Everything else is walk26 verbatim.

walk26 docstring: THE THREE SLOW EARLY TURNS. 1953 at +62, 1957 at +122 and 1960 at +91. First, which side binds each of them under
v3.8. Second, the 1957 regression: it was +5 at a vacancy line of 0.20 and +122 at 0.25, and the only reason the line
was raised was to remove a single call in December 2025 that fires on a vacancy reading of exactly 0.200 in May 2025 -
six months before the Sahm month it confirms. A shorter confirmation window kills that call without touching the line."""
import sys,pickle,os
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('walk37_%s.out'%sys.argv[1],'w')"))

# ---- THE MINIMUM EXPANSION. Bry and Boschan censor any phase shorter than six months; NBER uses the same floor.
# The floor is put on the EXPANSION side only, because the 2020 recession was two months long and no floor on the
# contraction side can survive it. Declared before the run; the shortest expansion in the whole record is twelve
# months (July 1980 to July 1981), so the floor never touches a true peak.
import inspect as _insp
_OLD="            if p <= last_close_pub or d <= last_end: continue"
_NEW="            if p <= last_close_pub or (d <= last_end if last_end==pd.Timestamp.min else d <= last_end + pd.DateOffset(months=_MINEXP)): continue"
_src=_insp.getsource(B.american_chronology)
assert _OLD in _src, 'chronology source line not found'
B.__dict__['_MINEXP']=6
exec(compile(_src.replace(_OLD,_NEW),'<patched-chronology>','exec'),B.__dict__)


# ---- THE PAPER SPREAD, CORRECTED (see the docstring) ----
_cp1=pd.read_csv(os.path.join(C25,'fred_daily','DCPN30.csv')).iloc[:,:2]; _cp1.columns=['d','v']; _cp1['d']=pd.to_datetime(_cp1['d'],errors='coerce')
_cp1=pd.to_numeric(_cp1.set_index('d')['v'],errors='coerce').dropna(); _cp1w=_cp1.resample('W-FRI').mean().dropna()
_aa_old=aa[aa.index<=pd.Timestamp('1997-08-29')]; _aa_new=_cp1w[_cp1w.index>pd.Timestamp('1997-08-29')]
aa=pd.concat([_aa_old,_aa_new]).sort_index(); idx=aa.index.union(bb.index)
CPB=(aa.reindex(idx).ffill()-bb.reindex(idx).ffill()).dropna(); CPB=CPB[CPB.index>=max(aa.index.min(),bb.index.min())]
Sm=CPB.rolling(13).mean().dropna(); GSP=(Sm-Sm.rolling(39).min()).dropna()
def build_v(p):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hc=dict(Hc); Hc['line']=p['hline']; Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1)
    def hubv(sl,back):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=back))&(G.index<=m)]; hit=w[w>=p['vl']]
                # a line touched in one month is not a confirmation: the vacancy must hold its line for two months
                if len(hit)>=2:
                    kk=hit.index[1]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]
    TL=dict(TLH); TL['R']=RC[p['rst']]; TL['T']=TC[p['tst']]; TL['Q']=QC[p['qst']]
    if p.get('cD') is not None: TL['C']=CMENU[(p['cD'],p['cn'],p['cs'])]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return score13(turns),turns

# ---- S REBUILT: Paper 1's closer proposes, two objects confirm the labour market has turned ----
sys.path.insert(0,W+'/lab/slack')
_CL=ICfp.dropna().rolling(4).mean().dropna(); _LCL=np.log(_CL); _BELOW=(_LCL.rolling(52,min_periods=26).max()-_LCL).dropna()
_LH=lh.dropna(); _AW=AWH.dropna()
def _rl(ser,look=12): return ((ser/ser.rolling(look,min_periods=look).min()-1)*100).dropna()
_RS=_rl(_LH); _RH=_rl(_AW)
def _confirm_close(calls,cdrop=0.15,rise=2.0,need=2,fwd=6):
    out_=[]
    for pp,dd in calls:
        hits=[]
        seg=_BELOW[(_BELOW.index>=dd)&(_BELOW.index<=dd+pd.DateOffset(months=fwd))]
        h=seg[seg>=cdrop]
        if len(h): hits.append(h.index[0]+pd.Timedelta(days=5))
        for rl_,pdy in [(_RS,18),(_RH,5)]:
            s2=rl_[(rl_.index>=dd)&(rl_.index<=dd+pd.DateOffset(months=fwd))]; h2=s2[s2>=rise]
            if len(h2): hits.append(pd.Timestamp(h2.index[0].year,h2.index[0].month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pdy-1))
        if len(hits)>=need:
            hits.sort(); out_.append((max(pp,hits[need-1]),dd))
    return out_
TLH=dict(TLH); TLH['S']=_confirm_close(TLH['S'])
# ---- THE SETTLING CLOSER: the Bristow rule run in an expanding window on the insured rate, then confirmed ----
_SPL=(-spl.dropna())
def _settle_calls(band=0.02,n=3,L=12,stable=3,back=48):
    lv=_SPL.rolling(n).mean().dropna()
    out_=[]; run=None; runlen=0; seen=set()
    for m in lv.index:
        w0=m-pd.DateOffset(months=back)
        w=lv[(lv.index>=w0)&(lv.index<=m)]
        if len(w)<8: continue
        d=(w-w.rolling(L).mean()).dropna()
        if not len(d): continue
        dp=d.idxmax(); lo=float(w.min()); i=w.idxmin()
        if i==w.index[-1]: run=None; runlen=0; continue
        hi=float(w[:i].max()) if len(w[:i]) else float(w.max())
        amp=max(hi-lo,1e-9); on=w[w<=lo+band*amp]
        dt=max(dp,on.index[-1]) if len(on) else dp
        mm=pd.Timestamp(dt.year,dt.month,1)
        if run==mm: runlen+=1
        else: run=mm; runlen=1
        if runlen>=stable and mm not in seen:
            seen.add(mm); out_.append((pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=11),mm))
    return out_
TLH['R']=_confirm_close(_settle_calls(stable=6))
# ---- THE STARTS CLOSER: housing starts given the settling test, guarded by the unemployment rate rolling over ----
_LHs=lh.dropna()
def _settle_starts(band=0.02,n=3,L=12,stable=4,back=48):
    lv=_LHs.rolling(n).mean().dropna(); out_=[]; run=None; runlen=0; seen=set()
    for m in pd.date_range('1948-01-01','2026-08-01',freq='MS'):
        avail=lv[lv.index<=m-pd.DateOffset(months=1)]
        if len(avail)<8: continue
        w=avail[(avail.index>=m-pd.DateOffset(months=back))]
        if len(w)<8: continue
        d=(w-w.rolling(L).mean()).dropna()
        if not len(d): run=None; runlen=0; continue
        dp=d.idxmax(); lo=float(w.min()); i=w.idxmin()
        if i==w.index[-1]: run=None; runlen=0; continue
        hi=float(w[:i].max()) if len(w[:i]) else float(w.max())
        amp=max(hi-lo,1e-9); on=w[w<=lo+band*amp]
        dt=max(dp,on.index[-1]) if len(on) else dp
        mm=pd.Timestamp(dt.year,dt.month,1)
        if run==mm: runlen+=1
        else: run=mm; runlen=1
        if runlen>=stable and mm not in seen:
            seen.add(mm); out_.append((pd.Timestamp(avail.index[-1].year,avail.index[-1].month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=16),mm))
    return out_
_U3=UR.dropna().rolling(3).mean().dropna()
def _ur_rolled(k=1):
    o={}
    for m,v in _U3.items():
        p_=m-pd.DateOffset(months=k)
        if p_ in _U3.index and v<=_U3[p_]:
            o[m]=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
    return o
def _guard_ur(calls,k=1,fwd=6):
    RO=_ur_rolled(k); out_=[]
    for pp,dd in calls:
        hits=[p_ for m,p_ in RO.items() if dd<=m<=dd+pd.DateOffset(months=fwd)]
        if hits: out_.append((max(pp,min(hits)),dd))
    return out_
TLH['T']=_guard_ur(_settle_starts())

# ---- THE WEEKLY TRIGGER WITH THE MONTHLY DATE. Initial claims are public five days after the week they cover, so a
# settling test on the weekly series knows the fall has stopped weeks before any monthly series does. It dates the
# trough badly, because a weekly series wanders, so the date is taken from the Bristow rule run on the monthly
# insured rate as published at that moment: the fast object says WHEN, the object with the dating record says WHICH
# MONTH. The close still has to clear the same two confirmations as every other closer on the menu.
_ICW=pd.read_csv(W+'/lab/data/fred_weekly/ICSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
_MIm=(-spl.dropna()).rolling(3).mean().dropna()
_MIP=pd.Series([pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=11) for m in _MIm.index],index=_MIm.index)
def _bris_date(asof,back=48,L=12,band=0.02):
    k=int(_MIP.searchsorted(asof,side='right')); av=_MIm.iloc[:k]
    if len(av)<8: return None
    w=av[av.index>=av.index[-1]-pd.DateOffset(months=back)]
    if len(w)<8: return None
    d=(w-w.rolling(L).mean()).dropna()
    if not len(d): return None
    dp=d.idxmax(); lo=float(w.min()); i=w.idxmin()
    if i==w.index[-1]: return None
    hi=float(w[:i].max()) if len(w[:i]) else float(w.max())
    amp=max(hi-lo,1e-9); on=w[w<=lo+band*amp]
    dt=max(dp,on.index[-1]) if len(on) else dp
    return pd.Timestamp(dt.year,dt.month,1)
def _wsettle(lv,stable,back_w,pub,band=0.02,L=52):
    out_=[];run=None;runlen=0;seen=set()
    for t in lv.index:
        w=lv[(lv.index>t-pd.Timedelta(weeks=back_w))&(lv.index<=t)]
        if len(w)<8: continue
        d=(w-w.rolling(L).mean()).dropna()
        if not len(d): run=None;runlen=0;continue
        dp=d.idxmax(); lo=float(w.min()); i=w.idxmin()
        if i==w.index[-1]: run=None;runlen=0;continue
        hi=float(w[:i].max()) if len(w[:i]) else float(w.max())
        amp=max(hi-lo,1e-9); on=w[w<=lo+band*amp]
        dt=max(dp,on.index[-1]) if len(on) else dp
        m=pd.Timestamp(dt.year,dt.month,1)
        if run==m: runlen+=1
        else: run=m;runlen=1
        if runlen>=stable and m not in seen:
            seen.add(m); out_.append((t+pd.Timedelta(days=pub),m))
    return out_
def _qleg(stable=8,back_w=156):
    raw=_wsettle((-_ICW).rolling(4).mean().dropna(),stable,back_w,5); out_=[];seen=set()
    for p_,_w in raw:
        dd=_bris_date(p_)
        if dd is None or dd>=pd.Timestamp(p_.year,p_.month,1) or dd in seen: continue
        seen.add(dd); out_.append((p_,dd))
    return _confirm_close(out_)
TLH['Q']=_qleg()


# ---- THE TROUGH NUMBERS GO INTO THE WALK. Until now the walk-forward chose the peak side's numbers from the past
# and the trough side's were frozen by hand, so the trough record was not causal in the sense the peak record is.
# The three settling closers' run lengths now sit in the same grid as every other number, ordered SAFEST FIRST
# (a longer run fires later and is the safer choice), and the walk picks them by the same criterion. The menus are
# built once per run length and looked up, so the search costs no more than before.
RC={s_:_confirm_close(_settle_calls(stable=s_)) for s_ in (8,6,5,4)}
TC={s_:_guard_ur(_settle_starts(stable=s_)) for s_ in (6,5,4,3)}
QC={s_:_qleg(stable=s_) for s_ in (13,10,8,6)}

# ---- CLOSER C: THE FLOW PROPOSES, THE STOCK OR THE MARKET CONFIRMS (collection 104, 8 September 2026) ----
# Proposer: the three-week mean of initial claims (first prints where they exist) stands D log points below its
# maximum of the previous twenty-six weeks, that hump at least twenty log points above the fifty-two-week minimum,
# and it has fallen n weeks running. Confirmer, counted the same week, one of three: the S&P 500 at least s per cent
# above its lowest close of the previous twenty-six weeks on the day of the claims release; continued claims' four-week
# mean 3.0 log points below its own twenty-six-week maximum; the insured rate's four-week mean three tenths below its
# own (each public twelve days after its week). Dated the later of the months in which the three-week and the four-week
# means peaked, plus one, or the month continued claims peaked once they have turned; never published before the dated
# month's last day; twenty-six weeks between calls. Structural reading: the inflow to unemployment falls first at a
# trough, but it also falls at every mid-episode pause; the stock of insured unemployment turning is what a pause never
# does, and the market standing well off its low is what a pause never has, because a pause is a false dawn in
# activity and not in the outlook for earnings. D, n and s go into the grid, safest first.
_IC3=ICfp.dropna().rolling(3).mean().dropna(); _LIC=np.log(_IC3)*100
_LIC4=np.log(ICfp.dropna().rolling(4).mean().dropna())*100
_CCw=pd.read_csv(W+'/lab/data/fred_weekly/CCSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
_LCC=np.log(_CCw.rolling(4).mean().dropna())*100
_IURw=frd.dropna()
_SPX=pd.read_csv(W+'/lab/speed2/data/sp500_daily_yahoo.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
_SP26=(_SPX/_SPX.rolling(130,min_periods=60).min()-1)*100
def _spike_drop(L,back=26,look=52):
    mx=L.rolling(back,min_periods=8).max(); mn=L.rolling(look,min_periods=look//2).min()
    df=pd.concat([L.rename('n'),mx.rename('x'),mn.rename('m')],axis=1).dropna()
    n=df['n'].values; run=np.zeros(len(n),int); fall=0
    for i in range(1,len(n)):
        fall=fall+1 if n[i]<n[i-1] else 0; run[i]=fall
    return pd.DataFrame({'drop':df['x'].values-n,'amp':df['x'].values-df['m'].values,'run':run},index=df.index)
_FI=_spike_drop(_LIC); _FC=_spike_drop(_LCC)
def _iur_drop(s_,back=26):
    t=(s_.rolling(4).mean()*10).round(); mx=t.rolling(back,min_periods=8).max(); return (mx-t).dropna()
_DU=_iur_drop(_IURw)
_CW=_FI.index; _CpI=_CW+pd.Timedelta(days=5); _Csp=_SP26.reindex(_CpI,method='ffill').values
_Ctc=_CW-pd.Timedelta(days=7); _Cfc=_FC['drop'].reindex(_Ctc).values; _Cdu=_DU.reindex(_Ctc).values.astype(float)
_Cpk={}
def _c_peak(t,back=26):
    if t not in _Cpk:
        seg=_LIC[(_LIC.index<=t)&(_LIC.index>t-pd.Timedelta(weeks=back))]; a=seg.idxmax()
        seg4=_LIC4[(_LIC4.index<=t)&(_LIC4.index>t-pd.Timedelta(weeks=back))]; b=seg4.idxmax() if len(seg4) else a
        _Cpk[t]=max(a,b)
    return _Cpk[t]
def closer_C(D,n,s,A=20.0,c=3.0,u=3,need=1,k=1,pub_cc=12,cool=26):
    prop=(_FI['drop'].values>=D)&(_FI['amp'].values>=A)&(_FI['run'].values>=n)
    sp_=np.nan_to_num(_Csp,nan=-99); fc_=np.nan_to_num(_Cfc,nan=-99); du_=np.nan_to_num(_Cdu,nan=-99)
    hs=(sp_>=s).astype(int)+(fc_>=c).astype(int)+(du_>=u).astype(int)
    ok=np.where(prop&(hs>=need))[0]; calls=[]; last_=None
    for i in ok:
        t=_CW[i]
        if last_ is not None and t<last_+pd.Timedelta(weeks=cool): continue
        pI=_CpI[i]; hits=[]
        if sp_[i]>=s: hits.append(pI)
        if fc_[i]>=c: hits.append(_Ctc[i]+pd.Timedelta(days=pub_cc))
        if du_[i]>=u: hits.append(_Ctc[i]+pd.Timedelta(days=pub_cc))
        hits.sort(); pub=max(pI,hits[need-1])
        pm=_c_peak(t); dated=pd.Timestamp(pm.year,pm.month,1)+pd.DateOffset(months=k)
        if fc_[i]>=c:
            seg=_LCC[(_LCC.index<=_Ctc[i])&(_LCC.index>_Ctc[i]-pd.Timedelta(weeks=26))]
            if len(seg):
                cm=seg.idxmax(); cmm=pd.Timestamp(cm.year,cm.month,1)
                if cmm>dated: dated=cmm
        calls.append((pub,dated)); last_=t   # one clock: no hold
    return calls
CD_=[8,6,5,4]; CN_=[3]; CS_=[30,25,20,15]
CMENU={(d_,n_,s_):closer_C(d_,n_,s_) for d_ in CD_ for n_ in CN_ for s_ in CS_}

BASE15=dict(BASE); BASE15.update(rst=6,tst=4,qst=8,deep=999,wline=None,wline2=None,bshare=None,hline=1.00,spr=round(LINE,3),sahm=0.43,vl=0.20,hback=6,cD=8,cn=3,cs=30)
GRID=[('sahm',[0.55,0.50,0.45,0.43,0.40,0.3667,0.35]),('vl',[0.36,0.30,0.25,0.20,0.15,0.12]),('hline',[1.10,1.00,0.95,0.90,0.85,0.80]),
      ('spr',[1.9,1.6,round(LINE,3),1.1,0.9]),('hback',[12,9,6,5,4,3]),('u45',[0.70,0.55,0.45,0.35,0.30]),('low',[0.35,0.30,0.25,0.20,0.15]),
      ('look',[52,78,91,130]),('ic',[60,50,45]),('rst',[8,6,5,4]),('tst',[6,5,4,3]),('qst',[13,10,8,6]),('cD',[8,6,5,4,None]),('cn',[3]),('cs',[30,25,20,15]),
      ('wline',[0.40,0.35,0.30,0.25,None]),('wline2',[0.60,0.50,0.45,None]),('bshare',[0.60,0.50,0.40,None])]
NAMES=[n for n,_ in GRID]; GD=dict(GRID)
ANN={'1948-11':'1961-10-01','1953-07':'1961-10-01','1957-08':'1961-10-01','1960-04':'1961-10-01','1969-12':'1971-06-30',
     '1973-11':'1976-03-31','1980-01':'1980-06-03','1981-07':'1982-01-06','1990-07':'1991-04-25','2001-03':'2001-11-26',
     '2007-12':'2008-12-01','2020-02':'2020-06-08','2024-04':None}
ANNT=[pd.Timestamp(ANN[PK[i].strftime('%Y-%m')]) if ANN[PK[i].strftime('%Y-%m')] else pd.Timestamp('2100-01-01') for i in range(13)]

# THE TROUGH ANNOUNCEMENTS. Rule Zero, 7 September 2026: the invented pre-1980 dates were withdrawn. 8 September 2026:
# the pre-1980 dates below are sourced from Business Conditions Digest (see the docstring); July 1980 on are the
# committee's own memoranda.
TANN={'1970-11':'1971-06-30','1975-03':'1976-12-02','1980-07':'1981-07-08','1982-11':'1983-07-08','1991-03':'1992-12-22','2001-11':'2003-07-17',
      '2009-06':'2010-09-20','2020-04':'2021-07-19','2024-08':None}
TANNT=[pd.Timestamp(TANN[TR[i].strftime('%Y-%m')]) if TANN.get(TR[i].strftime('%Y-%m')) else pd.Timestamp('2100-01-01') for i in range(13)]

SUMF=f'cache/{sys.argv[3]}_sum.pkl'; SUM=pickle.load(open(SUMF,'rb')) if os.path.exists(SUMF) else {}
def summary(p):
    k=tuple(p[n] for n in NAMES)
    if k in SUM: return SUM[k]
    r,t=build_v(p)
    s={'lags':dict(r['lags_p']),'early':bool([x for x in t if x['kind']=='peak' and x['published']<pd.Timestamp('1948-06-01')]),
       'fa':[x['published'] for x in t if x['kind']=='peak' and x['published'].strftime('%Y-%m-%d') in [d for d,_,_ in r['other']]
             and not any(pk-pd.DateOffset(months=6)<=x['date']<=tr for pk,tr in zip(PK,TR))],
       'tro':{},'opens':{i:r['opens'][i]['published'] for i in r['opens']}}
    for i in range(13):
        c=[x for x in t if x['kind']=='trough' and TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12)]
        if c: s['tro'][i]=(c[0]['published'],(c[0]['published']-me(TR[i])).days)
    # the episode's own close: the first trough call published after the peak call that opened it
    s['pair']={}
    for j,x in enumerate(t):
        if x['kind']!='peak': continue
        nxt=next((y for y in t[j+1:] if y['kind']=='trough'),None)
        if nxt is None: continue
        hit=[i for i in range(13) if abs((x['date'].year-PK[i].year)*12+(x['date'].month-PK[i].month))<=9]
        if not hit: continue
        i=hit[0]
        s['pair'][i]=(nxt['published'],(nxt['published']-me(TR[i])).days,
                      (nxt['date'].year-TR[i].year)*12+(nxt['date'].month-TR[i].month))
    SUM[k]=s
    if len(SUM)%100==0: pickle.dump(SUM,open(SUMF,'wb'))
    return s
def clean(q,cut,ks,kt=()):
    s=summary(q)
    if s['early'] or [o for o in s['fa'] if o<cut]: return None
    v=[s['lags'][j] for j in ks if j in s['lags']]
    if len(v)!=len(ks): return None
    w=[]
    for i in kt:
        if i not in s['pair']: return None                 # a ratified episode the rule never closed
        pub_,lg,er=s['pair'][i]
        if lg<-31: return None                             # the declared acceptance, in days; there is no named month to test
        w.append(lg)
    return (v,w)
def obj(vw):
    v,w=vw
    a=(sum(1 for x in v if x>31), float(np.median(v)), float(np.mean(v)))
    if not w: return a+(0,0.0,0.0)
    # a close inside the month after the trough month is the target; one up to a month early is accepted but counted
    # against the configuration exactly as a late one is, and distance from the month's end is what the median and mean measure
    return a+(sum(1 for x in w if x>31 or x<0), float(np.median([abs(x) for x in w])), float(np.mean([abs(x) for x in w])))
def neighbours(p):
    for n in NAMES:
        gr=GD[n]; i=gr.index(p[n])
        for j in (i-1,i+1):
            if 0<=j<len(gr): q=dict(p); q[n]=gr[j]; yield q
Y0,Y1,VAR=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
GRID=[(n,([x for x in g if x is not None]+[None]) if n in ('wline','wline2','bshare','cD') else g) for n,g in GRID]
GD=dict(GRID)
CF=f'cache/{VAR}_carry.pkl'; last=pickle.load(open(CF,'rb')) if os.path.exists(CF) else None
LOG=[]; CHOSEN={}; STALL=[]
PROG=f'cache/{VAR}_prog.pkl'
if os.path.exists(PROG):
    _pg=pickle.load(open(PROG,'rb'))
    if _pg['year']>=Y0: LOG,CHOSEN,Y0=_pg['log'],_pg['chosen'],_pg['year']+1; last=_pg['last']; print('resume at',Y0)
for Y in range(Y0,Y1+1):
    cut=pd.Timestamp(Y,1,1); ks=[i for i in range(13) if ANNT[i]<cut]; kt=[i for i in range(13) if TANNT[i]<cut]
    if not ks: continue
    memo={}
    def depth(p):
        k=tuple(p[n] for n in NAMES)
        if k in memo: return memo[k]
        d=sum(1 for q in neighbours(p) if clean(q,cut,ks,kt) is not None); memo[k]=d; return d
    p=dict(BASE15) if last is None else dict(last)
    for _ in range(2):
        ch=False
        for name,grid in GRID:
            ok={}
            for gv in grid:
                q=dict(p); q[name]=gv; v=clean(q,cut,ks,kt)
                if v is not None: ok[gv]=obj(v)
            if not ok: continue
            # A CONFIRMER CANNOT CAUSE A CALL BY ITSELF. It only speeds a call a proposer has already made, so where
            # two lines leave the past record identical the LOOSER one is taken for a confirmer and the SAFER one for
            # a proposer. Declared before the run.
            best=min(ok.values())
            tied=[gg for gg in ok if ok[gg]==best]
            if name in ('hline','spr','vl','cs'): nv=max(tied,key=lambda gg:grid.index(gg))   # C's market bar is a confirmer
            else: nv=min(tied,key=lambda gg:grid.index(gg))
            if nv!=p[name]: ch=True
            p[name]=nv
        if not ch: break
    if clean(p,cut,ks,kt) is None:
        STALL.append(Y); p=dict(last) if last is not None else dict(p)   # no clean point at this cut: the rule keeps its last configuration
    here=depth(p); best=None
    for q in neighbours(p):
        v=clean(q,cut,ks,kt)
        if v is None: continue
        sc=(-depth(q),obj(v))
        if best is None or sc<best[0]: best=(sc,q)
    if best is not None and -best[0][0]>here: p=best[1]
    last=dict(p); CHOSEN[cut]=dict(p); r,t=build_v(p)
    for x in t:
        if x['kind'] in ('peak','trough') and cut<=x['published']<pd.Timestamp(Y+1,1,1):
            LOG.append((x['published'],'OPEN' if x['kind']=='peak' else 'CLOSE',pd.Timestamp(x['published'].year,x['published'].month,1),x['leg']))   # ONE CLOCK
    pickle.dump(SUM,open(SUMF,'wb')); pickle.dump(dict(year=Y,log=LOG,chosen=CHOSEN,last=last),open(PROG,'wb')); print('year',Y,'done',len(SUM),flush=True)
LOG.sort(key=lambda z:z[0])
for pub,kind,dt,leg in LOG: P(f"   {pub:%Y-%m-%d}  {kind:5s} dated {dt:%Y-%m}  by {leg}")
pickle.dump(SUM,open(SUMF,'wb')); pickle.dump(LOG,open(f'cache/{VAR}_{Y0}.pkl','wb'))
pickle.dump(CHOSEN,open(f'cache/{VAR}_chosen_{Y0}.pkl','wb'))
if last is not None: pickle.dump(last,open(CF,'wb'))
P(f"   summaries {len(SUM)}  stalled cuts {STALL}")
out.close()
