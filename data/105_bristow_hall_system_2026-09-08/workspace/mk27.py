# builds walk27.py from walk26.py by explicit, asserted replacements (collection 104, 8 September 2026)
s=open('walk26.py').read()
def rep(a,b,count=1):
    global s
    assert s.count(a)==count,(a,s.count(a))
    s=s.replace(a,b)
rep('"""THE THREE SLOW EARLY TURNS.','"""WALK 27 - THE TROUGH CAMPAIGN (collection 104, 8 September 2026). walk26 with closer C on the menu and its three\nnumbers in the grid, safest first; the trough clause and the trough objective changed to the declared acceptance of\n8 September 2026 (a close up to a month early is accepted; a close inside the month after the trough month is\npreferred). Everything else is walk26 verbatim.\n\nwalk26 docstring: THE THREE SLOW EARLY TURNS.')
rep("out=open('walk26_%s.out'%sys.argv[1],'w')","out=open('walk27_%s.out'%sys.argv[1],'w')")
CBLOCK='''
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
        pub=max(pub,dated+pd.offsets.MonthEnd(0))
        calls.append((pub,dated)); last_=t
    return calls
CD_=[8,6,5,4]; CN_=[4,3,2]; CS_=[30,25,20,15]
CMENU={(d_,n_,s_):closer_C(d_,n_,s_) for d_ in CD_ for n_ in CN_ for s_ in CS_}
'''
rep("QC={s_:_qleg(stable=s_) for s_ in (13,10,8,6)}\n","QC={s_:_qleg(stable=s_) for s_ in (13,10,8,6)}\n"+CBLOCK)
rep("    TL=dict(TLH); TL['R']=RC[p['rst']]; TL['T']=TC[p['tst']]; TL['Q']=QC[p['qst']]\n    with contextlib",
    "    TL=dict(TLH); TL['R']=RC[p['rst']]; TL['T']=TC[p['tst']]; TL['Q']=QC[p['qst']]\n    if p.get('cD') is not None: TL['C']=CMENU[(p['cD'],p['cn'],p['cs'])]\n    with contextlib")
rep("sahm=0.43,vl=0.20,hback=6)","sahm=0.43,vl=0.20,hback=6,cD=8,cn=4,cs=30)")
rep("('rst',[8,6,5,4]),('tst',[6,5,4,3]),('qst',[13,10,8,6]),","('rst',[8,6,5,4]),('tst',[6,5,4,3]),('qst',[13,10,8,6]),('cD',[8,6,5,4,None]),('cn',[4,3,2]),('cs',[30,25,20,15]),")
rep("if n in ('wline','wline2','bshare') else g)","if n in ('wline','wline2','bshare','cD') else g)")
rep("SUMF='cache/w26_sum.pkl'","SUMF=f'cache/{sys.argv[3]}_sum.pkl'")
rep("        if lg<0 or abs(er)>1: return None                  # premature, or dated more than a month out",
    "        if lg<-31 or abs(er)>1: return None                # early by more than a month, or dated more than a month out (declared 8 September 2026)")
rep("    return a+(sum(1 for x in w if x>31), float(np.median(w)), float(np.mean(w)))",
    "    # a close inside the month after the trough month is the target; one up to a month early is accepted but counted\n    # against the configuration exactly as a late one is, and distance from the month's end is what the median and mean measure\n    return a+(sum(1 for x in w if x>31 or x<0), float(np.median([abs(x) for x in w])), float(np.mean([abs(x) for x in w])))")
rep("            if name in ('hline','spr','vl'): nv=max(tied,key=lambda gg:grid.index(gg))",
    "            if name in ('hline','spr','vl','cs'): nv=max(tied,key=lambda gg:grid.index(gg))   # C's market bar is a confirmer")
# per-year checkpoint so a run cut short resumes at the next year
rep("LOG=[]; CHOSEN={}\nfor Y in range(Y0,Y1+1):\n",
    "LOG=[]; CHOSEN={}\nPROG=f'cache/{VAR}_prog.pkl'\nif os.path.exists(PROG):\n    _pg=pickle.load(open(PROG,'rb'))\n    if _pg['year']>=Y0: LOG,CHOSEN,Y0=_pg['log'],_pg['chosen'],_pg['year']+1; last=_pg['last']; print('resume at',Y0)\nfor Y in range(Y0,Y1+1):\n")
rep("            LOG.append((x['published'],'OPEN' if x['kind']=='peak' else 'CLOSE',x['date'],x['leg']))\n",
    "            LOG.append((x['published'],'OPEN' if x['kind']=='peak' else 'CLOSE',x['date'],x['leg']))\n    pickle.dump(SUM,open(SUMF,'wb')); pickle.dump(dict(year=Y,log=LOG,chosen=CHOSEN,last=last),open(PROG,'wb')); print('year',Y,'done',len(SUM),flush=True)\n")
open('walk27.py','w').write(s); print('walk27.py written',len(s.splitlines()),'lines')
