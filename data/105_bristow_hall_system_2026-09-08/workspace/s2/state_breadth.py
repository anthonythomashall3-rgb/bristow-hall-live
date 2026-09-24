"""s2/state_breadth.py - THE STATE SAHM BREADTH, the rule's second opener (v3.72, collection 311, E31).

The share of states whose own Sahm gap - the three-month average of the state's unemployment rate minus its lowest three-month
average of the prior twelve months - stands at or above 0.70, read on the states' FIRST PRINTS (ALFRED's initial release of each
month, with the day it was published) and dated by the day the month was public for every state. The rule's opener fires when at
least 40 per cent of the states are at or above that gap; bhs_build then asks the vacancy condition the national hub asks (the
vacancy gap at its line in two of the prior months) and the backstop's quarter rule (the rule must have stood closed for thirteen
weeks) before an episode opens.

Run before bhs_build.py. Writes cache/state_ur_firstprints.csv (appended, never rewritten) and out/state_breadth.json.
    python3 s2/state_breadth.py
"""
import os, sys, json, time, datetime, re, urllib.request
import pandas as pd, numpy as np
HOME = os.path.expanduser('~'); MNT = os.path.join(HOME, 'mnt', 'Onset Detector Data')
ENV = os.path.join(MNT, 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env')
KEY = os.environ.get('FRED_API_KEY', '') or None   # the cloud passes the key in the environment; the Mac keeps it in local.env
if not KEY and os.path.exists(ENV):
    for line in open(ENV):
        if line.startswith('FRED_API_KEY='): KEY = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
ST = ['AL','AK','AZ','AR','CA','CO','CT','DE','DC','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN',
      'MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']
S_LINE, B_LINE = 0.70, 0.40
R_LINE = 0.25   # v3.73 (23 September 2026, collection 333; E31b, collection 326): the opener re-arms only once the share has fallen below this, not merely below B_LINE
COVER = 45   # a month whose panel is thin cannot fire: the share of a handful of states is not the breadth of the states
CACHE = os.path.join('cache', 'state_ur_firstprints.csv')
OUT = os.path.join('out', 'state_breadth.json')
def _get(u, tries=3):
    """None when the archive holds no vintage in the window asked for (FRED answers 400 to that, and it means nothing new)"""
    for k in range(tries):
        try:
            with urllib.request.urlopen(u, timeout=60) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            body = ''
            try: body = e.read().decode('utf-8', 'ignore')
            except Exception: pass
            if e.code == 400 and 'No vintage dates exist' in body: return None
            if e.code == 400 or k == tries - 1: raise
            time.sleep(2 * (k + 1))
        except Exception:
            if k == tries - 1: raise
            time.sleep(2 * (k + 1))
def refresh():
    """append any first print published since the last one held; a full pull if nothing is held"""
    have = pd.DataFrame(columns=['date', 'published', 'state', 'value'])
    if os.path.exists(CACHE):
        have = pd.read_csv(CACHE)
    rows, added = [], 0
    for s in ST:
        last = None
        if len(have):
            h = have[have['state'] == s]
            if len(h): last = str(pd.to_datetime(h['published']).max().date())
        q = 'realtime_start=%s&realtime_end=9999-12-31' % ((pd.Timestamp(last) + pd.Timedelta(days=1)).date().isoformat() if last else '1776-07-04')
        if not KEY: break
        u = 'https://api.stlouisfed.org/fred/series/observations?series_id=%sUR&api_key=%s&file_type=json&%s&output_type=4' % (s, KEY, q)
        try: j = _get(u)
        except Exception as e: print('state breadth: %sUR not refreshed (%s)' % (s, e)); continue
        if j is None: continue
        for o in j.get('observations', []):
            if o['value'] in ('.', '', None): continue
            rows.append((o['date'][:10], o['realtime_start'][:10], s, float(o['value']))); added += 1
    if rows:
        new = pd.DataFrame(rows, columns=['date', 'published', 'state', 'value'])
        have = pd.concat([have, new], ignore_index=True).drop_duplicates(subset=['date', 'state'], keep='first')
        os.makedirs('cache', exist_ok=True); have.sort_values(['date', 'state']).to_csv(CACHE, index=False)
    print('state breadth: %d first prints held, %d added' % (len(have), added))
    return have
# ---- collection 336 (23 September 2026; plan Step 5 item 12, the states' own substitute): THE STATE-RATE BRIDGE. When the Bureau's state
# ---- release has not printed a month three days after its day (a shutdown), at most two missing months are carried by the states'
# ---- insured-rate acceleration from the Department's ETA 539 weekly file (37's panel: the 13-week average insured rate 0.20 above a year
# ---- earlier), the share of states over 0.60 standing in for the Sahm-gap share over 0.40 (1994-2026: 389 months, correlation 0.91,
# ---- agreement at the line 97.9 per cent; the one call it does not reproduce is April 2024, where the insured rate barely rose).
# ---- Flagged; a third missing month reads dark. Drill: BHS_LAUS_DARK_MONTHS=n cuts the last n printed months.
SUB_LINE, SUB_SHARE, SUB_MAX = 0.20, 0.60, 2
def substitute_shares(months):
    """{month: (share, reporting, published)} from the 539 weekly panel, the last week of each month, public the Thursday after the report week"""
    p37 = None
    for r in (os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')):
        c = os.path.join(r, '37_dol_eta5159_2026-09', 'panel', 'panel_539_weekly.csv')
        if os.path.exists(c): p37 = c; break
    if p37 is None: return {}
    P = pd.read_csv(p37, parse_dates=['week']); W = P.pivot_table(index='week', columns='st', values='iur13', aggfunc='first').sort_index()
    W = W.drop(columns=[c for c in ('PR', 'VI') if c in W.columns])
    acc = W - W.shift(52); rep = (W.notna() & W.shift(52).notna()).sum(axis=1); share = (acc >= SUB_LINE - 1e-9).sum(axis=1) / rep.replace(0, np.nan)
    out = {}
    for m in months:
        mm = pd.Timestamp(m); wk = share[(share.index >= mm) & (share.index <= mm + pd.offsets.MonthEnd(0))]
        if not len(wk): continue
        last = wk.index[-1]
        if np.isnan(share[last]): continue
        pub = (last + pd.Timedelta(days=7)) + pd.Timedelta(days=(3 - (last + pd.Timedelta(days=7)).weekday()) % 7)   # the report week's Thursday release
        out[mm] = (round(float(share[last]), 4), int(rep[last]), pub)
    return out
def next_release():
    """the next State Employment and Unemployment release day: FRED's calendar for the Bureau's release (release 112, the
    Bureau's own schedule as FRED carries it) first; the Bureau's schedule page second; the third week of the next month last"""
    if KEY:
        try:
            t0 = datetime.date.today().isoformat()
            u = ('https://api.stlouisfed.org/fred/release/dates?release_id=112&api_key=%s&file_type=json'
                 '&include_release_dates_with_no_data=true&realtime_start=%s&realtime_end=9999-12-31' % (KEY, t0))
            j = _get(u)
            ds = sorted({o['date'][:10] for o in (j or {}).get('release_dates', [])})
            nxt = [d for d in ds if d > t0]
            if nxt: return nxt[0], 'BLS schedule (FRED release 112), 10:00 AM ET'
        except Exception as e:
            print('state breadth: the FRED release calendar was not read (%s)' % e)
    try:
        for ua in ({'User-Agent': 'BristowHallResearch/1.0'}, {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36'}):
            try:
                with urllib.request.urlopen(urllib.request.Request('https://www.bls.gov/schedule/news_release/laus.htm', headers=ua), timeout=45) as r:
                    h = r.read().decode('utf-8', 'ignore')
                break
            except Exception: h = None
        if h:
            ds = sorted({m for m in re.findall(r'(\d{4}-\d{2}-\d{2})', h)})
            nxt = [d for d in ds if d > datetime.date.today().isoformat()]
            if nxt: return nxt[0], 'BLS schedule'
    except Exception as e:
        print('state breadth: the schedule was not read (%s)' % e)
    t = pd.Timestamp(datetime.date.today()) + pd.DateOffset(months=1)
    return (pd.Timestamp(t.year, t.month, 21)).date().isoformat(), 'about this date, not read from the schedule'
def main():
    have = refresh()
    if not len(have): print('state breadth: nothing held; the opener is silent this run'); json.dump({}, open(OUT, 'w')); return
    d = have.copy(); d['date'] = pd.to_datetime(d['date']); d['published'] = pd.to_datetime(d['published'])
    _dark = os.environ.get('BHS_LAUS_DARK_MONTHS')
    if _dark:   # the drill: the last n printed months never arrived
        _cutm = sorted(d['date'].unique())[-int(_dark):]; d = d[d['date'] < min(_cutm)]
    X = d.pivot_table(index='date', columns='state', values='value', aggfunc='first').sort_index()
    P = d.groupby('date')['published'].max().sort_index()
    A3 = X.rolling(3).mean(); GAP = A3 - A3.rolling(12).min()
    cov = X.notna().sum(axis=1)
    share = ((GAP >= S_LINE - 1e-9).sum(axis=1) / cov.clip(lower=1)).dropna()
    # collection 336: the months the Bureau should have printed and has not - at most two carried by the states' insured-rate acceleration
    SUBST = {}; SUB_NOTE = 'every scheduled state month has printed'
    try:
        today_ = pd.Timestamp(datetime.date.today()); lastm = share.index.max(); missing = []; m = lastm + pd.DateOffset(months=1)
        while (m + pd.DateOffset(months=1) + pd.Timedelta(days=21 + 3)) < today_ and len(missing) < SUB_MAX + 1:   # a month is due about three weeks after the next month ends
            missing.append(m); m = m + pd.DateOffset(months=1)
        if _dark: missing = [pd.Timestamp(x) for x in _cutm]
        if len(missing) > SUB_MAX: SUB_NOTE = '%d state months missing: more than the bridge carries (%d); the channel reads dark' % (len(missing), SUB_MAX)
        elif missing:
            SUBST = substitute_shares(missing)
            SUB_NOTE = 'state months %s carried by the states\' insured-rate acceleration (ETA 539; share over %.2f stands in for the Sahm-gap share over %.2f)' % ([x.strftime('%Y-%m') for x in SUBST], SUB_SHARE, B_LINE) if SUBST else 'state months missing but the 539 panel does not cover them'
    except Exception as e: SUB_NOTE = 'the substitute was not computed (%r)' % (e,)
    for mm, (sh, rp, pub) in SUBST.items():
        # the substitute month enters the share series at the line's equivalent: at or above SUB_SHARE reads as B_LINE, below it as B_LINE * sh / SUB_SHARE
        share.loc[mm] = float(B_LINE if sh >= SUB_SHARE - 1e-9 else B_LINE * sh / SUB_SHARE); cov.loc[mm] = rp; P.loc[mm] = pub
    share = share.sort_index(); cov = cov.sort_index(); P = P.sort_index()
    thin = sorted(str(m.date()) for m in share.index if cov.get(m, 0) < COVER)
    fires, armed = [], True
    for m, x in share.items():
        if m not in P.index: continue
        if cov.get(m, 0) < COVER: continue
        if x >= B_LINE - 1e-9 and armed: fires.append([str(P[m].date()), str(m.date()), round(float(x), 4)]); armed = False
        elif x < R_LINE - 1e-9 and not armed: armed = True   # v3.73: E31b
    nxt, how = next_release()
    last_m = share.index.max()
    out = dict(cell=dict(gap=S_LINE, share=B_LINE, rearm=R_LINE), states=int(X.notna().sum(axis=1).iloc[-1]),
               through=str(last_m.date()), published=str(P[last_m].date()), latest_share=round(float(share.iloc[-1]), 4),
               next_release=nxt, next_release_source=how, fires=fires,
               cover=COVER, thin_months=thin, coverage={str(k.date()): int(v) for k, v in cov.items()},
               series={str(k.date()): round(float(v), 4) for k, v in share.items()},
               publications={str(k.date()): str(v.date()) for k, v in P.items() if k in share.index},
               substitute=dict(months=[k.strftime('%Y-%m') for k in SUBST], shares={k.strftime('%Y-%m'): v[0] for k, v in SUBST.items()}, line=SUB_LINE, share_line=SUB_SHARE, note=SUB_NOTE, drill=bool(_dark)),
               note=('the share of states whose own Sahm gap (three-month average unemployment rate above its twelve-month low, '
                     'on first prints) stands at or above %.2f; the opener fires at %.0f per cent of states, with the vacancy '
                     'condition and the quarter rule applied in the build; it re-arms only once the share has fallen below %.2f (E31b); a month '
                     'reporting fewer than %d states cannot fire' % (S_LINE, 100 * B_LINE, R_LINE, COVER)))
    os.makedirs('out', exist_ok=True); json.dump(out, open(OUT, 'w'), indent=1)
    print('state breadth: %s through %s (published %s), share %.3f, %d fires, %d thin months, next release %s (%s)' % (
        out['states'], out['through'], out['published'], out['latest_share'], len(fires), len(thin), nxt, how))
if __name__ == '__main__':
    main()
