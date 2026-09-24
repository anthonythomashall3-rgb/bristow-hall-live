# -*- coding: utf-8 -*-
"""The data inventory (idempotent; run from workspace/).

Every feed the site stands on now carries, in the state file, three things a reader needs and did not have: a link to
the source's own page, the latest value as it stands, and the day the source next publishes. `bhs_site.py` builds
`/data/` from that block and from the front page's tiles, so the inventory is generated from the same objects the rule
and the front page read - it cannot say one thing while the pages say another."""
import os,io,sys,re
B=os.path.abspath('bhs_build.py'); s=io.open(B,encoding='utf-8').read()
if '_fval(' in s: print('bhs_build already carries values and links'); sys.exit(0)
anchor="def _fthr(x):\n    try: return lastv(x)[1]\n    except Exception: return None\n"
assert s.count(anchor)==1
s=s.replace(anchor, anchor+"""def _fval(x,fmt='{:,.0f}',suf=''):
    # the latest value of a feed, as it stands, for the data inventory
    try: return fmt.format(lastv(x)[0])+suf
    except Exception: return None
""",1)
# a link and a value on every feed
def setf(name,extra):
    global s
    pat="dict(name='"+name
    i=s.index(pat); j=s.index("auto='yes'",i)
    s=s[:j]+extra+s[j:]
setf('Initial claims, continued claims, insured unemployment rate',
     "url='https://www.dol.gov/ui/data.pdf',value=_fval(ICfp,'{:,.0f}',' initial claims, week ending '+str(_fthr(ICfp))),")
setf('State insured unemployment rates',
     "url='https://oui.doleta.gov/unemploy/claims.asp',value=(_fval(RAW['B'],'{:.2f}')+' of the line 0.60 (share of states with the insured rate up year over year)' if _fthr(RAW['B']) else None),")
setf('Unemployment rate, factory hours, nondurable employment',
     "url='https://www.bls.gov/news.release/empsit.toc.htm',value=_fval(g_asof,'{:.2f}',' Sahm gap, points (the unemployment rate object the rule reads)'),")
setf('Job openings (the vacancy rate)',
     "url='https://www.bls.gov/jlt/',value=_fval(G,'{:.2f}',' per cent of the labor force'),")
setf('Housing starts and building permits',
     "url='https://www.census.gov/construction/nrc/index.html',value=_fval(MX,'{:.1f}',' log points below the 12-month high (the line is 29)'),")
setf('Commercial paper and three-month bill rates',
     "url='https://www.federalreserve.gov/releases/h15/',value=_fval(cS,'{:.2f}',' points, the wider paper market over the 3-month bill (the line is 0.90)'),")
setf('S&P 500 daily close',
     "url='https://finance.yahoo.com/quote/%5EGSPC/',value=_fval(_SPX,'{:,.2f}'),")
setf('Sahm rule, real time',
     "url='https://fred.stlouisfed.org/series/SAHMREALTIME',value=(lambda: (lambda _c: '{:.2f}'.format(float(_c.iloc[-1,1]))+' (the rule fires at 0.50)' if len(_c) else None)(__import__('pandas').read_csv('cache/SAHMREALTIME.csv')) if os.path.exists('cache/SAHMREALTIME.csv') else None)(),")
# the three search terms
old=("FEEDS.append(dict(name=f'Search week: Google searches for {_TSRC.get(_tg,_tg)} (the sudden stop\\'s second labour datum)',"
     "source='Google Trends, United States, daily index stitched onto one scale and extended each day',"
     "every=\"Daily - the day's index is known the next morning; read at every weekday close\",through=_fthr(_r),next='the next weekday close',auto='yes'))")
assert s.count(old)==1
s=s.replace(old, old[:-2]+",url='https://trends.google.com/trends/explore?date=today%203-m&geo=US&q='+_TQ.get(_tg,_tg),"
            "value=_fval(_r,'{:.1f}',' index, 7-day mean over its base')))")
s=s.replace("_TSRC={'unemp':'\"unemployment\"','layoffs':'\"layoffs\"','laidoff':'\"laid off\"'}",
            "_TSRC={'unemp':'\"unemployment\"','layoffs':'\"layoffs\"','laidoff':'\"laid off\"'}\n"
            "_TQ={'unemp':'unemployment','layoffs':'layoffs','laidoff':'laid%20off'}",1)
io.open(B,'w',encoding='utf-8').write(s); print('bhs_build.py: feeds carry url and value')
