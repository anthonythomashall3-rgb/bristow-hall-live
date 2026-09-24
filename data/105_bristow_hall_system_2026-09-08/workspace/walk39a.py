"""WALK 39a - WALK 39 WITHOUT ITEM 4 (the vacancy rate on the level file, as walk38): the dating corrections alone.
WALK 39 - WALK 38 ON THE ACTUAL RELEASE DAYS AND ON FIRST PRINTS THROUGHOUT (Rule Zero; the audit of the Bristow
Hall System, collection 105, 8 September 2026). Nothing in the rule changes: the objects, the lines, the grid, the
windows and the walk are walk38's verbatim. What changes is WHEN each number is taken to be public, and which print
of it is read, in the five places the audit found a convention standing in for a fact:

1. THE WEEKLY CLAIMS. walk38 dated every claims week five days after its Saturday (the insured rate twelve, the
   state rates nineteen): the Thursday release. The Department releases on Wednesday when that Thursday is a federal
   holiday, and it did not release at all during the lapse in appropriations of 1 October to 12 November 2025 - the
   seven weeks of that autumn were first published together on 20 November 2025. From October 2002 every week is
   dated the day its release appeared (collection 45, the Department's own release archive, corrected 8 September
   2026); before that, the Thursday, or the Wednesday before a federal-holiday Thursday. One call in the diary is
   touched: the close of 22 November 2001 (Thanksgiving) was published on Wednesday 21 November 2001.
2. THE PAPER SPREAD. walk38 dated the H.15 week a day after its Friday. The weekly H.15 of the 1970s and 1980s was
   released on Monday (FRASER: the issue of 17 September 1973 carries the week ending 14 September 1973), and the
   daily H.15 posts each day's rates on the next business day at 4:15 PM (the release of 4 September 2026 carries
   rates through 3 September). The week is therefore public on the first business day after its Friday. One call is
   touched: the opening of 15 September 1973, a Saturday, was public on Monday 17 September 1973.
3. THE MONTHLY CLAIMS CLOSERS H AND J. The lab dated the monthly initial-claims closer H the sixth of the month after
   the data month (a Saturday in June 2020) and the continued-claims closer J the seventeenth. A month's claims are
   public when its last week is: H is dated the release of the last initial-claims week ending in the data month, J
   the release carrying the last continued-claims week ending in it. One call is touched: the close of 6 June 2020
   (H, on May 2020's claims) was public on Thursday 4 June 2020, the release of the week ending 30 May 2020.
4. THE VACANCY RATE ON FIRST PRINTS. The composite read JOLTS openings over the labour force from the current print.
   From July 2010, where ALFRED's vintages exist, both are first prints (Rule 23 clause 1); the level file before.
   JOLTS's own release days: ALFRED's first vintage from August 2010, the BLS release archive from February 2004,
   and the lab's convention (thirty days after the month) only for December 2000 to January 2004, the program's
   first years, whose release dates the BLS archive does not carry.
5. CLOSER C'S STOCK CONFIRMERS ON FIRST PRINTS. The continued-claims and insured-rate confirmers read the current
   file; from October 2002 they read the advance figures (collection 45). They never bound a close in the record.

Run:  python3 walk39a.py 1962 2026 w39a   (the diary from the 1962 cut; ~20 minutes)"""
import sys,pickle,os
exec(open('walk38.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0].replace("walk38_%s.out","walk39a_%s.out"))
import datetime as _dt
import pandas as pd, numpy as np

# ---- 1. THE RELEASE DAYS OF THE WEEKLY CLAIMS ----
def _obs(d):
    if d.weekday()==5: return d-_dt.timedelta(days=1)
    if d.weekday()==6: return d+_dt.timedelta(days=1)
    return d
def _nth(y,m,wd,n):
    d=_dt.date(y,m,1); d+=_dt.timedelta(days=(wd-d.weekday())%7); return d+_dt.timedelta(weeks=n-1)
def _lastwd(y,m,wd):
    d=_dt.date(y+(m==12),(m%12)+1,1)-_dt.timedelta(days=1); return d-_dt.timedelta(days=(d.weekday()-wd)%7)
def fedhol(y):
    """federal holidays as they stood in year y (the Monday-holiday law of 1971, Martin Luther King Day 1986, Juneteenth 2021)"""
    H={_obs(_dt.date(y,1,1)),_obs(_dt.date(y,7,4)),_obs(_dt.date(y,12,25)),_nth(y,11,3,4),_nth(y,9,0,1)}
    if y>=1971: H|={_nth(y,2,0,3),_lastwd(y,5,0),_nth(y,10,0,2)}
    else: H|={_obs(_dt.date(y,2,22)),_obs(_dt.date(y,5,30))}
    if 1971<=y<=1977: H.add(_nth(y,10,0,4))
    else: H.add(_obs(_dt.date(y,11,11)))
    if y>=1986: H.add(_nth(y,1,0,3))
    if y>=2021: H.add(_obs(_dt.date(y,6,19)))
    return H
_N45=pd.read_csv(W.replace('24_bristow_rule_lab/workspace','45_dol_first_prints_2026-09/national_first_prints.csv'),parse_dates=['release_date','ic_week_ended','iu_week_ended'])
_REL_IC={w:r for w,r in zip(_N45.dropna(subset=['icsa']).ic_week_ended,_N45.dropna(subset=['icsa']).release_date)}
_REL_IU={w:r for w,r in zip(_N45.dropna(subset=['iur_sa']).iu_week_ended,_N45.dropna(subset=['iur_sa']).release_date)}
def _thu_rule(w):
    d=(w+pd.Timedelta(days=5)).date()
    if d in fedhol(d.year): d-=_dt.timedelta(days=1)
    return pd.Timestamp(d)
def rel_ic(w):
    """the release day of the initial-claims week ending Saturday w"""
    w=pd.Timestamp(w); return _REL_IC.get(w,_thu_rule(w))
def rel_iu(w):
    """the release day of the insured-unemployment (continued claims, insured rate) week ending Saturday w: with the initial-claims week after it"""
    w=pd.Timestamp(w); return _REL_IU.get(w,rel_ic(w+pd.Timedelta(days=7)))
def rel_state(w):
    """the release day of the states' insured rates for the week ending w: with the initial-claims week two after it"""
    return rel_ic(pd.Timestamp(w)+pd.Timedelta(days=14))
def rel_h15(f):
    """the H.15 week ending Friday f is public on the first business day after it"""
    d=(pd.Timestamp(f)+pd.Timedelta(days=1)).date()
    while d.weekday()>=5 or d in fedhol(d.year): d+=_dt.timedelta(days=1)
    return pd.Timestamp(d)
def _last_sat(m):
    e=(pd.Timestamp(m)+pd.offsets.MonthEnd(0)); return e-pd.Timedelta(days=(e.weekday()-5)%7)

# ---- the proposers, dated by the release days (the bodies are walk38's; only the day changes) ----
def leg_gapL(s,line,look,pub=12,rearm='zero'):
    gap=(s-s.rolling(look,min_periods=look).min().shift(1)).dropna(); c=[]; armed=True; last=None
    for t,v in gap.items():
        if armed and v>=line: c.append((rel_iu(t),pd.Timestamp(t.year,t.month,1))); armed=False; last=t
        elif not armed:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<line and t>=last+pd.DateOffset(months=4): armed=True
    return c
def leg_ic(s,pct,pub=5,look=52,rearm='zero'):
    m4=s.rolling(4).mean(); rel_=(m4/m4.rolling(look,min_periods=look).min().shift(1)-1)*100
    c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pct: c.append((rel_ic(t),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return c
def leg_sv(line,look=52,pub=12,rearm='zero'):
    gap=(SI-SI.rolling(look,min_periods=look).min().shift(1)).dropna(); c=[]; armed=True; last=None
    for t,v in gap.items():
        if armed and v>=line: c.append((rel_iu(SW[t]),t)); armed=False; last=t
        elif not armed:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<line and t>=last+pd.DateOffset(months=4): armed=True
    return c
def leg_br(share):
    c=[]; armed=True
    for t,v in BR.items():
        if armed and v>=share: c.append((rel_state(t),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<share*0.5: armed=True
    return c
def leg_rt(s,pct,look=52,pub=12,stop='1971-01-01'):
    m=s.rolling(look,min_periods=look).min().shift(1); rel_=s-m; c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pct: c.append((rel_iu(t),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return [x for x in c if x[1]<pd.Timestamp(stop)]

# ---- 2. the spread's release days ----
SP_PUBS=pd.Series({t:rel_h15(t) for t in GSP.index})

# ---- 4. the vacancy rate on first prints from July 2010; JOLTS's release days from 2004 ----
# (ALFRED's initial releases, cache/alfred_first_*.csv, written by bhs_update.py: the vintage table of the labour force
# in collection 27 stops in 1996, so the first prints are taken from ALFRED's output_type=4 for both series)
_JF=pd.read_csv('cache/alfred_first_JTSJOL.csv',index_col=0,parse_dates=True)['first']; _CF=pd.read_csv('cache/alfred_first_CLF16OV.csv',index_col=0,parse_dates=True)['first']
# WALK 39a: the dating corrections alone - the vacancy rate stays on the level file (walk38's), so that the effect of
# the release days and the effect of the first prints can be told apart. (V0 unchanged.)
_bls=pd.read_csv('cache/jolts_release_calendar_2004_2026.csv',parse_dates=['reference_month','release_date'])
_bls=_bls[_bls.source.str.startswith('BLS')].set_index('reference_month')['release_date']
relJ=pd.concat([_bls[_bls.index<pd.Timestamp('2010-07-01')],relJ[relJ.index>=pd.Timestamp('2010-07-01')]]).sort_index()

# ---- 5. closer C: the release days, and the stock confirmers on first prints ----
_CCfp=_CCw.copy()
_iusa=_N45.dropna(subset=['iusa']).drop_duplicates('iu_week_ended',keep='first').set_index('iu_week_ended')['iusa'].sort_index()
_CCfp=pd.concat([_CCw[_CCw.index<_iusa.index.min()],_iusa]).sort_index()
_LCC=np.log(_CCfp.rolling(4).mean().dropna())*100
_IURw=spl.dropna()
_FC=_spike_drop(_LCC); _DU=_iur_drop(_IURw)
_CpI=pd.DatetimeIndex([rel_ic(t) for t in _CW]); _Csp=_SP26.reindex(_CpI,method='ffill').values
_Cfc=_FC['drop'].reindex(_Ctc).values; _Cdu=_DU.reindex(_Ctc).values.astype(float)
def closer_C(D,n,s,A=20.0,c=3.0,u=3,need=1,k=1,pub_cc=12,cool=26):
    prop=(_FI['drop'].values>=D)&(_FI['amp'].values>=A)&(_FI['run'].values>=n)
    sp_=np.nan_to_num(_Csp,nan=-99); fc_=np.nan_to_num(_Cfc,nan=-99); du_=np.nan_to_num(_Cdu,nan=-99)
    hs=(sp_>=s).astype(int)+(fc_>=c).astype(int)+(du_>=u).astype(int)
    ok=np.where(prop&(hs>=need))[0]; calls=[]; last_=None
    for i in ok:
        t=_CW[i]
        if last_ is not None and t<last_+pd.Timedelta(weeks=cool): continue
        pub=_CpI[i]                                   # the flow, the stock and the market are all in the same release
        pm=_c_peak(t); dated=pd.Timestamp(pm.year,pm.month,1)+pd.DateOffset(months=k)
        if fc_[i]>=c:
            seg=_LCC[(_LCC.index<=_Ctc[i])&(_LCC.index>_Ctc[i]-pd.Timedelta(weeks=26))]
            if len(seg):
                cm=seg.idxmax(); cmm=pd.Timestamp(cm.year,cm.month,1)
                if cmm>dated: dated=cmm
        calls.append((pub,dated)); last_=t
    return calls
CMENU={(d_,n_,s_):closer_C(d_,n_,s_) for d_ in CD_ for n_ in CN_ for s_ in CS_}

# ---- 3. the monthly claims closers H and J; the settling closers' confirmations on the release days ----
def _redate_month(calls,fn):
    out_=[]
    for pub,dd in calls:
        M=pub-pd.DateOffset(months=1); out_.append((fn(_last_sat(pd.Timestamp(M.year,M.month,1))),dd))
    return out_
TLH=dict(TLH); TLH['H']=_redate_month(TLH['H'],rel_ic); TLH['J']=_redate_month(TLH['J'],rel_iu)
def _confirm_close(calls,cdrop=0.15,rise=2.0,need=2,fwd=6):
    out_=[]
    for pp,dd in calls:
        hits=[]
        seg=_BELOW[(_BELOW.index>=dd)&(_BELOW.index<=dd+pd.DateOffset(months=fwd))]
        h=seg[seg>=cdrop]
        if len(h): hits.append(rel_ic(h.index[0]))
        for rl_,pdy in [(_RS,18),(_RH,5)]:
            s2=rl_[(rl_.index>=dd)&(rl_.index<=dd+pd.DateOffset(months=fwd))]; h2=s2[s2>=rise]
            if len(h2):
                m_=h2.index[0]; cal=relH if pdy==18 else relU
                hits.append(cal[m_] if m_ in cal.index else pd.Timestamp(m_.year,m_.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pdy-1))
        if len(hits)>=need:
            hits.sort(); out_.append((max(pp,hits[need-1]),dd))
    return out_
_MIP=pd.Series([rel_iu(_last_sat(m)) for m in _MIm.index],index=_MIm.index)
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
            seen.add(mm); out_.append((rel_iu(_last_sat(m)),mm))
    return out_
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
            seen.add(m); out_.append((rel_ic(t),m))
    return out_
RC={s_:_confirm_close(_settle_calls(stable=s_)) for s_ in (8,6,5,4)}
TC={s_:_guard_ur(_settle_starts(stable=s_)) for s_ in (6,5,4,3)}
QC={s_:_qleg(stable=s_) for s_ in (13,10,8,6)}
TLH['S']=_confirm_close(TLH['S']); TLH['R']=RC[6]; TLH['T']=TC[4]; TLH['Q']=QC[8]

# ---- the rule, walk38's build_v with the spread on its release days ----
def build_v(p):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hc=dict(Hc); Hc['line']=p['hline']; Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pubs=SP_PUBS)
    def hubv(sl,back):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=back))&(G.index<=m)]; hit=w[w>=p['vl']]
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

# ---- the walk itself: walk38's loop, verbatim, with one clause added before the diary is written ----
# 6. AN EPISODE IS FOLLOWED TO ITS CLOSE BY THE LINES THAT OPENED IT. Declared 8 September 2026, the day the case
#    first arose: the lines chosen at a cut can fail to contain an episode the previous cut's lines had opened (the
#    2026 cut, after the call of 16 December 2025). The diary cannot leave a recession open that the rule no longer
#    sees, and the new lines cannot close what they never opened; so an open call is followed to its close by the
#    lines that made it, and new calls come from the new lines. The close is marked with an asterisk in the log.
_TAIL=open('walk38.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[1]
_AMEND='''
_L=sorted(LOG,key=lambda z:z[0]); _add=[]
for _i,(_opub,_okind,_odt,_oleg) in enumerate(_L):
    if _okind!='OPEN': continue
    _nxt=_L[_i+1] if _i+1<len(_L) else None
    if _nxt is not None and _nxt[1]=='CLOSE': continue
    _cp=CHOSEN[max(c for c in CHOSEN if c<=_opub)]; _r,_t=build_v(_cp)
    _tr=[x for x in _t if x['kind']=='trough' and x['published']>_opub]
    if _tr:
        x=min(_tr,key=lambda z:z['published']); _add.append((x['published'],'CLOSE',pd.Timestamp(x['published'].year,x['published'].month,1),x['leg']+'*'))
LOG+=_add
if _add: pickle.dump(dict(year=Y1,log=sorted(LOG,key=lambda z:z[0]),chosen=CHOSEN,last=last),open(PROG,'wb'))
'''
assert _TAIL.count("LOG.sort(key=lambda z:z[0])")==1
exec("Y0,Y1,VAR=int(sys.argv[1])"+_TAIL.replace("LOG.sort(key=lambda z:z[0])",_AMEND+"LOG.sort(key=lambda z:z[0])"))
