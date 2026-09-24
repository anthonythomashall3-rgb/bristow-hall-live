# patch_v329.py - the live system for v3.29 (the search week on three labour terms), 10 September 2026, evening.
# Run from 105/workspace: python3 s2/patch_v329.py   (idempotent: each edit is skipped if already applied)
import re,os,sys
def patch(path,old,new,label):
    s=open(path).read()
    if new in s: print(f'{label}: already applied'); return
    if old not in s: print(f'{label}: ANCHOR NOT FOUND in {path}'); sys.exit(1)
    open(path,'w').write(s.replace(old,new,1)); print(f'{label}: applied')
# ---- bhs_build.py: the daily KS branch over every term; the readings rows per term; through.search ----
patch('bhs_build.py',
"""if 'GT_REL' in globals() and '_crash2' in globals():
    _ks1=(GT_REL/KC[0]).dropna()                                                                      # the search week over its base, by the datum's day
    _ksc=pd.Series({t:float(_crash2.get(t+pd.Timedelta(days=1),np.nan))/KC[1] for t in _ks1.index})   # the S&P at the close of the day the datum is known (none on a day without a close)
    def _armKS(rel,crash):""",
"""if 'GT_REL' in globals() and '_crash2' in globals():
    _TERMS=(GT_TERMS if 'GT_TERMS' in globals() else {'unemp':(GT_DAY,GT7,GT_REL)})                   # v3.29 (walk55): every labour term; the branch reads the strongest each day
    def _armKS(rel,crash):""",'build: terms block head')
patch('bhs_build.py',
"""    _ksd=lambda s:s.dropna().set_axis(s.dropna().index+pd.Timedelta(days=1))                           # dated by the morning the datum is known
    RAW['KS']=_ksd(pd.concat([_ks1.rename('a'),_ksc.rename('b')],axis=1).min(axis=1,skipna=False))
    gKS=_ksd(_armKS(_ks1,_ksc))""",
"""    _ksd=lambda s:s.dropna().set_axis(s.dropna().index+pd.Timedelta(days=1))                           # dated by the morning the datum is known
    _ksR=[]; _ksA=[]
    for _tag,(_dd,_gg,_rel) in _TERMS.items():
        _ks1=(_rel/KC[0]).dropna()                                                                      # the term's search week over its base, by the datum's day
        _ksc=pd.Series({t:float(_crash2.get(t+pd.Timedelta(days=1),np.nan))/KC[1] for t in _ks1.index})   # the S&P at the close of the day the datum is known (none on a day without a close)
        _ksR.append(_ksd(pd.concat([_ks1.rename('a'),_ksc.rename('b')],axis=1).min(axis=1,skipna=False)).rename(_tag)); _ksA.append(_ksd(_armKS(_ks1,_ksc)).rename(_tag))
    RAW['KS']=pd.concat(_ksR,axis=1).max(axis=1).dropna()                                            # the strongest term's reading each day (the sudden stop fires on the earliest)
    gKS=pd.concat(_ksA,axis=1).max(axis=1).dropna()""",'build: terms block body')
patch('bhs_build.py',
"""if 'GT_REL' in globals(): add('open','sudden stop: the search week - 7-day mean of Google searches for unemployment above its base, percent (fires with the S&P 500 20 percent under its 20-day high at that day\\'s close; known the next morning)',GT_REL.dropna(),float(KC[0]),nxt='daily')""",
"""_TNAME={'unemp':'"unemployment"','layoffs':'"layoffs"','laidoff':'"laid off"'}
for _tag,(_dd,_gg,_rel) in (GT_TERMS.items() if 'GT_TERMS' in globals() else ([('unemp',(GT_DAY,GT7,GT_REL))] if 'GT_REL' in globals() else [])):
    add('open',f'sudden stop: the search week - 7-day mean of Google searches for {_TNAME.get(_tag,_tag)} above its base, percent (fires with the S&P 500 20 percent under its 20-day high at that day\\'s close; known the next morning; the earliest term fires)',_rel.dropna(),float(KC[0]),nxt='daily')""",'build: readings rows per term')
patch('bhs_build.py',
"""search=(lastv(GT_REL)[1] if 'GT_REL' in globals() else None)))""",
"""search=(lastv(GT_REL)[1] if 'GT_REL' in globals() else None),search_terms=({k:lastv(v[2])[1] for k,v in GT_TERMS.items()} if 'GT_TERMS' in globals() else None)))""",'build: through.search_terms')
patch('bhs_build.py',
"""(' ; from v3.27 the sudden stop also reads the search week - the 7-day mean of Google searches for unemployment over the same base, known the next morning, with the S&P 500 at that day\\'s close - and fires on the earlier of the claims week and the search week (the series exists from 2004 and enters there)' if 'GT_REL' in globals() else '')""",
"""(' ; from v3.27 the sudden stop also reads the search week - the 7-day mean of Google searches for unemployment over the same base, known the next morning, with the S&P 500 at that day\\'s close - and fires on the earlier of the claims week and the search week (the series exists from 2004 and enters there)' if 'GT_REL' in globals() else '')+(' ; from v3.29 the search week reads three labour terms - unemployment, layoffs, laid off - each over its own base, and fires on the earliest' if 'GT_TERMS' in globals() and len(GT_TERMS)>1 else '')""",'build: notes objects_added')
# ---- bhs_update.py: log every line of the feed, not the last ----
patch('bhs_update.py',
"""    say((_r.stdout.strip().splitlines() or [_r.stderr.strip()[-120:] or 'search week: no output'])[-1])""",
"""    for _ln in (_r.stdout.strip().splitlines() or [_r.stderr.strip()[-120:] or 'search week: no output']): say(_ln)   # one line per term (v3.29); 'appended' on any of them is new data""",'update: feed lines')
# ---- bhs_verify.py: the WALK map and EXPECTED w55 ----
patch('bhs_verify.py',"'w53':'walk53.py','w54':'walk54.py'}[VAR]","'w53':'walk53.py','w54':'walk54.py','w55':'walk55.py'}[VAR]",'verify: walk map')
patch('bhs_verify.py',
""" 'w54':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=3,peaks_within_one=5,peaks_worst=5,peaks_median_days=-7.0,""",
""" 'w55':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=3,peaks_within_one=5,peaks_worst=5,peaks_median_days=-7.0,
            troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=8,troughs_worst=2,troughs_median_days=7.0,premature_or_unmatched=0,
            open_days=['1969-10-06','1973-09-17','1979-11-29','1981-02-26','1990-07-26','2001-03-29','2007-12-24','2020-03-12','2024-05-03'],
            close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            frozen_peaks=['1948-10-10','1953-10-01','1957-09-05','1960-07-30','1969-07-28','1973-09-17','1979-11-05','1981-02-26','1990-05-16','2001-03-15','2007-12-24','2020-03-12','2024-05-03'],
            frozen_troughs=['1950-03-09','1954-06-03','1958-07-03','1961-05-04','1970-12-24','1975-05-01','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            note='walk55: walk54 with the search week on three labour terms - unemployment, layoffs, laid off - each over its own base with the sudden stop\\'s numbers (35 over the base; the S&P 500 20 under its 20-day high at the close of the day the datum is known), firing on the earliest; the terms chosen after the case (on 11 March 2020 layoffs stood 57 and laid off 55 per cent over their bases against unemployment\\'s 25); with the gate each added term fires 7 October 2008 and 12 March 2020 only. 2020 opens 12 March 2020 (+12) for 16 March (+16); everything else walk54\\'s (10 September 2026, evening)'),
 'w54':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=3,peaks_within_one=5,peaks_worst=5,peaks_median_days=-7.0,""",'verify: EXPECTED w55')
# ---- template.html: the rule statement ----
patch('../site/template.html',
"""the search week does the same — the seven-day mean of Google searches for "unemployment" in the United States 35 percent or more above its own base (built the same way, over days), known the next morning, with the S&amp;P 500 20 percent or more below its twenty-day high at that day's close — so that the sudden stop fires on the earlier of the claims week and the search week (16 March 2020, three days before the claims release of 19 March).""",
"""the search week does the same — the seven-day mean of Google searches in the United States for "unemployment", for "layoffs" or for "laid off", each 35 percent or more above its own base (built the same way, over days), known the next morning, with the S&amp;P 500 20 percent or more below its twenty-day high at that day's close — so that the sudden stop fires on the earliest of the claims week and the search weeks (12 March 2020, a week before the claims release of 19 March; the two added terms were chosen after that case, as the pre-registration states).""",'template: rule statement')
print('patch complete')
