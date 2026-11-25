# trends_live.py - THE SEARCH WEEK'S DAILY FEED (collection 108; v3.29 form, 10 September 2026, evening: one feed per
# labour term). For each term the stitched history google_trends/live/<tag>_stitched_daily.csv is extended by a 250-day
# daily pull from Google Trends, scaled onto the history by the mean ratio over their overlap (at least 28 days) and
# appended day by day; on Google's refusal the history stands and the caller states its last day. Prints one line per
# term; the runner (bhs_run.sh) treats "appended" as new data. Run from the collection root with the venv:
#     .venv/bin/python scripts/trends_live.py
import os,sys,time,datetime
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
import pandas as pd, numpy as np
TERMS=[('unemployment','unemp'),('layoffs','layoffs'),('laid off','laidoff')]
try:
    from pytrends.request import TrendReq
except Exception as e:
    print(f'search week: pytrends missing ({e})'); sys.exit(1)
pt=TrendReq(hl='en-US',tz=0,timeout=(10,30)); rc=0
# 1167 (24 Nov 2026; Anthony: "under 3 minutes of data releases"): a TIME BUDGET and WHOLE-FILE WRITES. Google's refusals (429) and the
# backoff below once held a run's build for 274 s (the caller's limit is 300 s, and a kill could cut a file mid-write). Now no new try starts
# once TRENDS_BUDGET_S (default 240 s) has passed - the history stands, as on any refusal - and every file is written to a temporary name and
# moved into place, so a reader never sees half a file and a stopped pull never leaves one.
_T0=time.time(); BUDGET=float(os.environ.get('TRENDS_BUDGET_S') or 240)
def _left(): return BUDGET-(time.time()-_T0)
def _write_csv(df,path,**kw):
    tmp=path+'.tmp'; df.to_csv(tmp,**kw); os.replace(tmp,path)
for kw,tag in TERMS:
    F=f'google_trends/live/{tag}_stitched_daily.csv'
    if not os.path.exists(F): print(f'search week ({tag}): no stitched history file; run search_week.py first'); rc=1; continue
    H=pd.read_csv(F,index_col=0,parse_dates=True).iloc[:,0].astype(float).sort_index()
    df=None; err=''
    for k in range(3):
        if _left()<=0: err=err or 'the time budget is spent'; break
        try:
            end=datetime.date.today(); start=end-datetime.timedelta(days=250)
            pt.build_payload([kw],geo='US',timeframe=f'{start.isoformat()} {end.isoformat()}'); df=pt.interest_over_time(); break
        except Exception as e: err=str(e)[:80]; time.sleep(max(0,min(20*(k+1),_left())))
    if df is None or not len(df): print(f'search week ({tag}): pull failed ({err or "empty"}); history through {H.index.max().date()}'); rc=1; continue
    d=df.iloc[:,0].astype(float); d=d[~df.get('isPartial',pd.Series(False,index=df.index)).astype(bool)] if 'isPartial' in df else d
    o=d.index.intersection(H.index)
    if len(o)<28 or d.loc[o].mean()<=0: print(f'search week ({tag}): overlap too short ({len(o)} days); history through {H.index.max().date()}'); rc=1; continue
    fac=H.loc[o].mean()/d.loc[o].mean(); new=(d*fac)[d.index>H.index.max()]
    # R2 (23 September 2026, collection 337): the window's SHAPE must agree with the history on the overlap, not only its mean - Google
    # re-normalizes and re-samples each download; a drift in the ratios would rescale the search week's base in silence. The mean
    # absolute relative deviation of the scaled window from the history over the overlap must be under 0.15 (a fifth of the 35 per cent
    # line); past it nothing is appended, the last reading stands and the line says so (the claims week alone carries the sudden stop).
    _dev=float(((d.loc[o]*fac-H.loc[o]).abs()/H.loc[o].clip(lower=1e-9)).mean())
    try:
        with open(os.path.join(os.path.dirname(F),'pull_log.csv'),'a') as _pl: _pl.write('%s,%s,%s,%s,%d,%.4f,%.4f\n'%(datetime.date.today().isoformat(),tag,start.isoformat(),end.isoformat(),len(o),fac,_dev))
    except Exception: pass
    if _dev>0.15: print(f'search week ({tag}): the window disagrees with the history on the overlap (mean relative deviation {_dev:.3f} > 0.15); NOT appended, history through {H.index.max().date()}'); rc=1; continue
    if len(new)==0: print(f'search week ({tag}): nothing new (history through {H.index.max().date()})')
    else:
        H2=pd.concat([H,new]).sort_index(); _write_csv(H2,F,header=[tag])
        print(f'search week ({tag}): {len(new)} day(s) appended, through {new.index.max().date()} (scale {fac:.3f} on {len(o)} overlap days)')
    time.sleep(max(0,min(5,_left())))
    # 17 September 2026: the index as Google shows it - the past-90-days view the data page links to (0-100 on that
    # window; the stitched history above is on its own scale). Written whole each run with Google's partial-day flag;
    # the page shows the last complete day. A refusal keeps the previous file.
    try:
        if _left()<=0: raise RuntimeError('the time budget is spent')
        G=f'google_trends/live/{tag}_google90_daily.csv'
        pt.build_payload([kw],geo='US',timeframe='today 3-m'); g=pt.interest_over_time()
        if g is not None and len(g):
            out=pd.DataFrame({'date':g.index.strftime('%Y-%m-%d'),'value':g.iloc[:,0].astype(float).values,'partial':(g['isPartial'].astype(bool).values if 'isPartial' in g else False)})
            _write_csv(out,G,index=False); c=out[~out['partial']]
            print(f'search week ({tag}): Google\'s 90-day view through {c["date"].iloc[-1]} = {c["value"].iloc[-1]:.0f}')
    except Exception as e: print(f'search week ({tag}): 90-day view not refreshed ({str(e)[:60]})')
    time.sleep(max(0,min(5,_left())))
sys.exit(rc)
