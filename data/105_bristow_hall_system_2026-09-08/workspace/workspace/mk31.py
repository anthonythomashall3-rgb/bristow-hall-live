# walk31 = walk30 on ONE CLOCK: a call is dated the month in which the rule speaks (collection 104, 8 September 2026)
s=open('walk30.py').read()
def rep(a,b):
    global s
    assert s.count(a)==1,(a,s.count(a)); s=s.replace(a,b)
rep('"""WALK 30 - WALK 29 WITH THE RUN FIXED AT THREE FALLING WEEKS, NOT WALKED','"""WALK 31 - ONE CLOCK (collection 104, 8 September 2026). Anthony: "When the rule fires, that is the date. Nothing more\ncomplicated than that." Every call, peak or trough, is dated the calendar month of its own publication day; the\nproposer-month dating of the peak legs, the hub leg\'s three-months-back rule, closer C\'s flow-peak dating and its\nhold to the dated month\'s last day are all gone. Accuracy and speed are now the same number: the error in months\nbetween the month the rule spoke and the committee\'s month. The walk\'s objective on each side is (turns off by more\nthan a month, median absolute error, mean absolute error) in months; zero false alarms and every announced peak\ncalled remain the cleanliness conditions; a ratified trough closed more than a month before its month is refused.\nEverything else is walk30 verbatim.\n\nWALK 30 - WALK 29 WITH THE RUN FIXED AT THREE FALLING WEEKS, NOT WALKED')
rep("        pub=max(pub,dated+pd.offsets.MonthEnd(0))\n        calls.append((pub,dated)); last_=t","        calls.append((pub,dated)); last_=t   # one clock: no hold; the date is overridden by the month of publication")
rep("    if p.get('cD') is not None: TL['C']=CMENU[(p['cD'],p['cn'],p['cs'])]\n    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)",
    "    if p.get('cD') is not None: TL['C']=CMENU[(p['cD'],p['cn'],p['cs'])]\n    # ONE CLOCK: every call is dated the month of its own publication day\n    legs={k_:[(c_[0],pd.Timestamp(c_[0].year,c_[0].month,1)) for c_ in v_] for k_,v_ in legs.items()}\n    TL={k_:[(c_[0],pd.Timestamp(c_[0].year,c_[0].month,1)) for c_ in v_] for k_,v_ in TL.items()}\n    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)")
rep("       'tro':{},'opens':{i:r['opens'][i]['published'] for i in r['opens']}}\n",
    "       'tro':{},'opens':{i:r['opens'][i]['published'] for i in r['opens']}}\n    s['errp']={i:(pb.year-PK[i].year)*12+pb.month-PK[i].month for i,pb in s['opens'].items()}   # one clock: months\n")
rep("    v=[s['lags'][j] for j in ks if j in s['lags']]\n    if len(v)!=len(ks): return None\n",
    "    v=[s['lags'][j] for j in ks if j in s['lags']]\n    if len(v)!=len(ks): return None\n    if any(j not in s['errp'] for j in ks): return None\n    v=[s['errp'][j] for j in ks]                        # ONE CLOCK: the error, in months, of the month the rule spoke\n")
rep("        if lg<-31 or abs(er)>1: return None                # early by more than a month, or dated more than a month out (declared 8 September 2026)\n        w.append(lg)",
    "        if er<-1: return None                              # ONE CLOCK: closed more than a month before the trough month\n        w.append(er)")
rep("    a=(sum(1 for x in v if x>31), float(np.median(v)), float(np.mean(v)))",
    "    a=(sum(1 for x in v if abs(x)>1), float(np.median([abs(x) for x in v])), float(np.mean([abs(x) for x in v])))")
rep("    return a+(sum(1 for x in w if x>31 or x<0), float(np.median([abs(x) for x in w])), float(np.mean([abs(x) for x in w])))",
    "    return a+(sum(1 for x in w if abs(x)>1), float(np.median([abs(x) for x in w])), float(np.mean([abs(x) for x in w])))")
rep("out=open('walk30_%s.out'%sys.argv[1],'w')","out=open('walk31_%s.out'%sys.argv[1],'w')")
# the closer menu can be restricted (declared per walk): MENU=None keeps every closer
rep("    TL={k_:[(c_[0],pd.Timestamp(c_[0].year,c_[0].month,1)) for c_ in v_] for k_,v_ in TL.items()}\n",
    "    TL={k_:[(c_[0],pd.Timestamp(c_[0].year,c_[0].month,1)) for c_ in v_] for k_,v_ in TL.items()}\n    if MENU is not None: TL={k_:v_ for k_,v_ in TL.items() if k_ in MENU}\n")
rep("def build_v(p):\n","MENU=None\ndef build_v(p):\n")
# a call published inside the recession or up to three months after its trough month belongs to that recession (a
# late detection with a bad date, not a false alarm); the two windows that match calls to episodes are widened so
rep("exec(compile(_src.replace(_OLD,_NEW),'<patched-chronology>','exec'),B.__dict__)\n",
    "exec(compile(_src.replace(_OLD,_NEW),'<patched-chronology>','exec'),B.__dict__)\n# ONE CLOCK: a peak call published up to three months after the trough month still belongs to that recession\n_S13='def score13'+open('mini.py').read().split('def score13')[1].split('def rep(')[0]\n_A13=\"if p-pd.DateOffset(months=6)<=t['date']<=q and i not in used_p]\"\nassert _A13 in _S13, 'score13 window not found'\nexec(_S13.replace(_A13,\"if p-pd.DateOffset(months=6)<=t['date']<=q+pd.DateOffset(months=3) and i not in used_p]\"))\n")
rep("             and not any(pk-pd.DateOffset(months=6)<=x['date']<=tr for pk,tr in zip(PK,TR))],",
    "             and not any(pk-pd.DateOffset(months=6)<=x['date']<=tr+pd.DateOffset(months=3) for pk,tr in zip(PK,TR))],")
open('walk31.py','w').write(s); print('walk31 written')
