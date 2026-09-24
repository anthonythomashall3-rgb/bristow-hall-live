#!/usr/bin/env python3
"""CH-R26 high-frequency universe survey. READ-ONLY. Writes research/ only.
Five axes per candidate: route, rights rung, true depth, revision class, correlation.
FRED-resolvable rows are measured live; non-FRED rows carry roster-knowledge route/rights.
"""
import sys, os, csv, json, time, urllib.request, urllib.error, statistics
sys.path.insert(0, '.')
from tools.rmv2_data_cloudflare.rmv2_connectors import engine

K = engine._read_credential('FRED_API_KEY')
BASE = 'https://api.stlouisfed.org/fred'
OUT = 'research'

# ---- held member set (diff hold vs miss) ----
HELD = set()
with open('data_vault/catalog/metric_catalog.csv') as f:
    for row in csv.DictReader(f):
        HELD.add(row['series_id'].strip())

def _get(url, timeout=25):
    return json.load(urllib.request.urlopen(url, timeout=timeout))

def meta(sid):
    u = f'{BASE}/series?series_id={sid}&api_key={K}&file_type=json'
    try:
        s = _get(u)['seriess'][0]
        return dict(start=s['observation_start'], end=s['observation_end'],
                    freq=s['frequency_short'], title=s['title'][:60],
                    last_updated=s.get('last_updated','')[:10])
    except urllib.error.HTTPError as e:
        return dict(err=f'HTTP{e.code}')
    except Exception as e:
        return dict(err=type(e).__name__)

def latest_val(sid, dt):
    u = (f'{BASE}/series/observations?series_id={sid}'
         f'&observation_start={dt}&observation_end={dt}&limit=1&api_key={K}&file_type=json')
    try:
        o = _get(u)['observations']
        return o[0]['value'] if o and o[0]['value'] not in ('.','') else None
    except Exception:
        return None

def _asof(sid, obs, rt):
    """Value of observation `obs` as seen in vintage `rt`. Two ALFRED snapshots
    beat output_type=4 for daily series (whose per-day append explodes vintage count)."""
    u = (f'{BASE}/series/observations?series_id={sid}'
         f'&observation_start={obs}&observation_end={obs}'
         f'&realtime_start={rt}&realtime_end={rt}&api_key={K}&file_type=json')
    try:
        o = _get(u)['observations']
        return o[0]['value'] if o and o[0]['value'] not in ('.','') else None
    except urllib.error.HTTPError as e:
        return 'NOTALFRED' if 'does not exist in ALFRED' in e.read().decode() else f'HTTP{e.code}'

def _plusdays(dt, n):
    import datetime
    y,m,d = (int(x) for x in dt.split('-'))
    return (datetime.date(y,m,d) + datetime.timedelta(days=n)).isoformat()

ERR = lambda v: v is None or (isinstance(v, str) and (v == 'NOTALFRED' or v.startswith('HTTP')))

def _real_obs_date(sid, around):
    """A real observation date on/before `around` (latest vintage). Handles weekly/holiday gaps."""
    lo = _plusdays(around, -20)
    u = (f'{BASE}/series/observations?series_id={sid}'
         f'&observation_start={lo}&observation_end={around}&api_key={K}&file_type=json')
    try:
        o = [x for x in _get(u)['observations'] if x['value'] not in ('.','')]
        return o[-1]['date'] if o else None
    except Exception:
        return None

def _first_val(sid, obs, rt_hi):
    """Earliest known value of `obs` in realtime window [obs .. rt_hi] (range, not single day)."""
    u = (f'{BASE}/series/observations?series_id={sid}'
         f'&observation_start={obs}&observation_end={obs}'
         f'&realtime_start={obs}&realtime_end={rt_hi}&sort_order=asc&api_key={K}&file_type=json')
    try:
        o = [x for x in _get(u)['observations'] if x['value'] not in ('.','')]
        return o[0]['value'] if o else None
    except urllib.error.HTTPError as e:
        return 'NOTALFRED' if 'does not exist in ALFRED' in e.read().decode() else f'HTTP{e.code}'

def revision_class(sid, dt, monthly):
    d = _real_obs_date(sid, dt)
    if d is None:                       # series starts after probe date -> use a recent window
        d = _real_obs_date(sid, '2024-06-17')
    if d is None:
        return 'unknown', 'no_obs_any_window'
    near = _plusdays(d, 60 if monthly else 12)   # first-availability window end
    first = _first_val(sid, d, near)
    if first == 'NOTALFRED':
        return 'never-revised', 'not_in_ALFRED(price/rate obs stable)'
    latest = _asof(sid, d, '2026-08-01')
    if ERR(first) or ERR(latest):
        return 'unknown', f'first={first} latest={latest}'
    try:
        a, b = float(first), float(latest)
        if a == b:
            return 'never/negligible', f'{d}: first==latest={a}'
        rel = abs(a-b)/max(abs(b), 1e-9)
        cls = 'negligible-revised' if rel < 0.002 else 'revised'
        return cls, f'{d}: first={a} latest={b} rel={rel:.4f}'
    except Exception:
        return 'unknown', f'first={first} latest={latest}'

# ---- correlation helper (monthly-mean aggregation, +/-12wk lead/lag reported in months) ----
def monthly_series(sid, start='1990-01-01'):
    u = (f'{BASE}/series/observations?series_id={sid}'
         f'&observation_start={start}&api_key={K}&file_type=json')
    try:
        obs = _get(u, timeout=40)['observations']
    except Exception:
        return {}
    buck = {}
    for o in obs:
        v = o['value']
        if v in ('.',''): continue
        ym = o['date'][:7]
        buck.setdefault(ym, []).append(float(v))
    return {ym: statistics.mean(v) for ym, v in buck.items()}

def pearson(xs, ys):
    n = len(xs)
    if n < 12: return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((a-mx)*(b-my) for a,b in zip(xs,ys))
    dx = sum((a-mx)**2 for a in xs)**0.5
    dy = sum((b-my)**2 for b in ys)**0.5
    return num/(dx*dy) if dx and dy else None

def corr_leadlag(a_sid, b_sid, maxlag=6):
    A = monthly_series(a_sid); B = monthly_series(b_sid)
    if not A or not B: return None
    keys = sorted(set(A) & set(B))
    if len(keys) < 24: return None
    best = (0.0, 0)
    idx = {k:i for i,k in enumerate(keys)}
    av = [A[k] for k in keys]; bv = [B[k] for k in keys]
    for lag in range(-maxlag, maxlag+1):
        xs, ys = [], []
        for i in range(len(keys)):
            j = i + lag
            if 0 <= j < len(keys):
                xs.append(av[i]); ys.append(bv[j])
        r = pearson(xs, ys)
        if r is not None and abs(r) > abs(best[0]):
            best = (r, lag)
    return dict(r=round(best[0],3), lead_lag_months=best[1], overlap_months=len(keys),
                window=f'{keys[0]}..{keys[-1]}')

# ============ CANDIDATE ROSTER ============
# fred_id set => measured live. non-fred => route/rights recorded from roster knowledge.
REV_DATE = '2015-06-15'  # daily-safe mid date
MREV_DATE = '2015-06-01'  # monthly

# (name, tier, fred_id, cadence_expected, route, keyless, rights_rung, corr_anchor)
ROSTER = [
 # ---- MODERN DAILY ----
 ('Treasury 1mo yield','daily','DGS1MO','daily','H.15/FRED',True,'public',None),
 ('Treasury 3mo yield','daily','DGS3MO','daily','H.15/FRED',True,'public',None),
 ('Treasury 6mo yield','daily','DGS6MO','daily','H.15/FRED',True,'public',None),
 ('Treasury 1y yield','daily','DGS1','daily','H.15/FRED',True,'public',None),
 ('Treasury 2y yield','daily','DGS2','daily','H.15/FRED',True,'public',None),
 ('Treasury 3y yield','daily','DGS3','daily','H.15/FRED',True,'public',None),
 ('Treasury 5y yield','daily','DGS5','daily','H.15/FRED',True,'public',None),
 ('Treasury 7y yield','daily','DGS7','daily','H.15/FRED',True,'public',None),
 ('Treasury 10y yield','daily','DGS10','daily','H.15/FRED',True,'public',None),
 ('Treasury 20y yield','daily','DGS20','daily','H.15/FRED',True,'public',None),
 ('Treasury 30y yield','daily','DGS30','daily','H.15/FRED',True,'public',None),
 ('10y-2y spread','daily','T10Y2Y','daily','H.15/FRED',True,'public',None),
 ('10y-3mo spread','daily','T10Y3M','daily','H.15/FRED',True,'public','UNRATE'),
 ('Fed funds effective','daily','DFF','daily','H.15/FRED',True,'public',None),
 ('SOFR','daily','SOFR','daily','NYFed/FRED',True,'public',None),
 ('CP 3mo financial rate','daily','DCPF3M','daily','Fed CP/FRED',True,'public',None),
 ('CP 3mo nonfinancial rate','daily','DCPN3M','daily','Fed CP/FRED',True,'public',None),
 ("Moody's AAA daily","daily",'DAAA','daily','Moodys/FRED',True,'public',None),
 ("Moody's BAA daily","daily",'DBAA','daily','Moodys/FRED',True,'public',None),
 ('HY OAS (ICE BofA)','daily','BAMLH0A0HYM2','daily','ICE/FRED [RIGHTS: history truncated to 2023-08 on FRED]',True,'public_index_truncated','UNRATE'),
 ('IG OAS (ICE BofA)','daily','BAMLC0A0CM','daily','ICE/FRED [RIGHTS: truncated to 2023-08]',True,'public_index_truncated',None),
 ('Broad dollar index','daily','DTWEXBGS','daily','H.10/FRED',True,'public','INDPRO'),
 ('AFE dollar index','daily','DTWEXAFEGS','daily','H.10/FRED',True,'public',None),
 ('WTI crude spot','daily','DCOILWTICO','daily','EIA/FRED',True,'public','INDPRO'),
 ('Indeed job postings US (national)','daily','IHLIDXUS','daily','Indeed/FRED',True,'public_partner','UNRATE'),
 ('VIX close','daily','VIXCLS','daily','CBOE/FRED',True,'public_index','UNRATE'),
 ('VXO close','daily','VXOCLS','daily','CBOE/FRED',True,'public_index',None),
 ('S&P 500 level','daily','SP500','daily','S&P/FRED(10y only)',True,'LICENSED_index','UNRATE'),
 # ---- MODERN WEEKLY ----
 ('Initial claims','weekly','ICSA','weekly','DOL/FRED',True,'public','UNRATE'),
 ('Continued claims','weekly','CCSA','weekly','DOL/FRED',True,'public','UNRATE'),
 ('Initial claims NSA','weekly','ICNSA','weekly','DOL/FRED',True,'public',None),
 ('Fed H.8 bank credit','weekly','TOTBKCR','weekly','H.8/FRED',True,'public',None),
 ('Fed H.8 C&I loans','weekly','BUSLOANS','monthly','H.8/FRED',True,'public',None),
 ('Fed H.4.1 total assets (WALCL)','weekly','WALCL','weekly','H.4.1/FRED',True,'public',None),
 ('Fed reserve balances','weekly','WRESBAL','weekly','H.4.1/FRED',True,'public',None),
 ('Commercial paper outstanding','weekly','COMPOUT','weekly','Fed CP/FRED',True,'public',None),
 # ---- DEEP HISTORY / NBER MACROHISTORY ----
 ('NBER rail freight tons (q) 1920','deep','Q03068USQ455SNBR','quarterly','NBER/FRED',True,'public',None),
 ('NBER retail trade index (m) 1914','deep','M0601AUSM327NNBR','monthly','NBER/FRED',True,'public',None),
 ('NBER call money rate (m) 1914','deep','M13009USM156NNBR','monthly','NBER/FRED',True,'public',None),
 ('NBER commercial paper rate 1857','deep','M13002US35620M156NNBR','monthly','NBER/FRED',True,'public',None),
 ('NBER steel ingot production 1899','deep','M0135AUSM577NNBR','monthly','NBER/FRED',True,'public',None),
 ('NBER pig iron production 1877','deep','M010ADUSM561SNBR','monthly','NBER/FRED',True,'public',None),
 # ---- TIER 4 CENTURY LANES (FRED-resolvable) ----
 ("Moody's AAA monthly 1919","century",'AAA','monthly','Moodys/FRED',True,'public','BAA'),
 ("Moody's BAA monthly 1919","century",'BAA','monthly','Moodys/FRED',True,'public',None),
 ('CPI all items NSA 1913','century','CPIAUCNS','monthly','BLS/FRED',True,'public',None),
 ('PPI all commodities 1913','century','PPIACO','monthly','BLS/FRED',True,'public',None),
 ('Industrial production 1919','century','INDPRO','monthly','FRB G.17/FRED',True,'public',None),
 ('M2 money stock','century','M2SL','monthly','H.6/FRED',True,'public',None),
 ('Long-term govt bond yield 1919','century','IRLTLT01USM156N','monthly','OECD/FRED',True,'public',None),
 ('1yr treasury constant (m) 1953','century','GS1','monthly','H.15/FRED',True,'public',None),
 ('Auto production (motor veh)','century','DAUPSA','monthly','FRB/FRED',True,'public',None),
 ('Building permits','century','PERMIT','monthly','Census/FRED',True,'public',None),
 ('Unemployment rate lineage','century','UNRATE','monthly','BLS/FRED',True,'public',None),
]

# non-FRED / rights-blocked roster rows (no fetch; recorded from knowledge)
NONFRED = [
 # name, tier, route, keyless, rights_rung, depth, cadence, revision_class, note
 ('Gold London AM/PM fix','daily','GOLDAMGBD228NLBM (FRED 400 / removed)',True,'LICENSED_LBMA','1968+ (pulled from FRED)','daily','never-revised','RIGHTS: LBMA series returns HTTP400 on FRED now; licensed feed needed'),
 ('ADS business conditions index','daily','PhillyFed ADS xlsx',True,'public_model_output','1960+','daily','model_output(revised)','comparator class, not a raw series'),
 ('AAR rail carloads (modern)','weekly','AAR Rail Traffic (login/PDF)',False,'PROPRIETARY_AAR','2000s+','weekly','never-revised','splice twin for NBER carloadings 1918+; AAR gate'),
 ('AISI raw steel output','weekly','AISI weekly (subscriber)',False,'PROPRIETARY_AISI','1910s scan+','weekly','never-revised','splice twin; AISI paywall, historical via NBER/FRASER'),
 ('EIA electricity output (weekly)','weekly','EIA API v2',True,'public','2018+ weekly','weekly','revised','EEI weekly 1920s is the deep twin'),
 ('EIA gasoline demand','weekly','EIA API v2 (WGFUPUS2)',True,'public','1991+','weekly','revised','product supplied proxy'),
 ('Baker Hughes rig count','weekly','BKR site xlsx',True,'public','1987+ (US), 1940s intl','weekly','never-revised','free download, machine-readable'),
 ('MBA mortgage apps index','weekly','MBA (subscriber)',False,'PROPRIETARY_MBA','1990+','weekly','never-revised','do not scrape; license required'),
 ('Redbook retail sales','weekly','Redbook (subscriber)',False,'PROPRIETARY_Redbook','2005+','weekly','never-revised','license required'),
 ('WARN layoff notices','weekly','50 state portals (mixed)',True,'public_mixed','varies by state','weekly/daily','never-revised','machine-readable inventory needed per state'),
 ('TSA checkpoint throughput','daily','TSA.gov table',True,'public','2019+','daily','never-revised','scrape HTML table'),
 ('DJIA daily 1896','century','S&P DJI (LICENSED)',False,'LICENSED_SPDJI','1896+','daily','never-revised','values vs licensed feed; Stooq/free mirrors uncertain rights'),
 ('S&P composite Cowles/Shiller 1871','century','Shiller ie_data.xls',True,'public_academic','1871+ (m), 1928+ daily','monthly','never-revised','Shiller data free; canonical deep equity lane'),
 ('Call money rate 1890s (NBER)','century','NBER Macrohistory/FRED',True,'public','1890s+','monthly','never-revised','lineage->DFF; may have FRED m-series'),
 ('Fed H.4.1 weekly 1914 (FRASER)','century','FRASER scans + FRED WALCL',True,'public_scan','1914+ weekly','weekly','revised','deepest still-weekly series; FRASER digitize'),
 ('Dept store sales 1919 (NBER)','century','NBER/FRED + FRASER SCB',True,'public','1919+','weekly/monthly','never-revised','splice twin: modern retail sales (revised)'),
 ('Business failures Dun 1857','century','NBER hist + D&B (prop today)',False,'MIXED_DnB','1857-1990s free; modern proprietary','weekly/monthly','never-revised','historical free via NBER; modern D&B paywall'),
 ('Money stock Friedman-Schwartz 1907','century','NBER Macrohistory',True,'public','1907+','monthly','never-revised(historical)','splice twin: Fed M2/H.6'),
 ('Unemployment Lebergott/Weir 1890','century','academic tables',True,'public_academic','1890+ annual','annual','estimate(research)','splice twin: UNRATE; research class only'),
]

rows = []
t0 = time.time()
for i,(name,tier,sid,cad,route,keyless,rights,anchor) in enumerate(ROSTER):
    m = meta(sid); time.sleep(0.35)
    if 'err' in m:
        rows.append(dict(candidate=name,tier=tier,fred_id=sid,measured='no',
            route=route,keyless=keyless,rights_rung=rights,depth_start=m['err'],
            depth_end='',cadence=cad,last_updated='',held='held' if sid in HELD else 'MISS',
            revision_class='fetch_err',revision_evidence=m['err'],corr='',title=''))
        continue
    is_monthly = m['freq'] in ('M','Q','A')
    if m['end'] < '2000-01-01':
        rc, rev_ev = 'never-revised', 'frozen historical scan (obs end %s)' % m['end']
    else:
        rc, rev_ev = revision_class(sid, MREV_DATE if is_monthly else REV_DATE, is_monthly)
    time.sleep(0.35)
    corr = ''
    if anchor:
        c = corr_leadlag(sid, anchor); time.sleep(0.35)
        if c: corr = f"vs {anchor}: r={c['r']} lag={c['lead_lag_months']}m n={c['overlap_months']} [{c['window']}]"
        else: corr = f'vs {anchor}: insufficient_overlap'
    rows.append(dict(candidate=name,tier=tier,fred_id=sid,measured='yes',
        route=route,keyless=keyless,rights_rung=rights,depth_start=m['start'],
        depth_end=m['end'],cadence=m['freq'],last_updated=m['last_updated'],
        held='held' if sid in HELD else 'MISS',revision_class=rc,revision_evidence=rev_ev,
        corr=corr,title=m['title']))
    print(f'[{i+1}/{len(ROSTER)}] {sid:16} {m["start"]} {m["freq"]:2} {rc:16} {"HELD" if sid in HELD else "MISS"}')

for (name,tier,route,keyless,rights,depth,cad,rc,note) in NONFRED:
    rows.append(dict(candidate=name,tier=tier,fred_id='',measured='no_roster_knowledge',
        route=route,keyless=keyless,rights_rung=rights,depth_start=depth,depth_end='',
        cadence=cad,last_updated='',held='MISS',revision_class=rc,revision_evidence='domain_prior',
        corr='',title=note))

cols = ['candidate','tier','fred_id','measured','route','keyless','rights_rung','depth_start',
        'depth_end','cadence','last_updated','held','revision_class','revision_evidence','corr','title']
with open(f'{OUT}/hf_universe_survey_v1.csv','w',newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for r in rows: w.writerow(r)

# summary json
summ = dict(total=len(rows),
    measured=sum(1 for r in rows if r['measured']=='yes'),
    held=sum(1 for r in rows if r['held']=='held'),
    miss=sum(1 for r in rows if r['held']=='MISS'),
    never_revised=sum(1 for r in rows if 'never' in r['revision_class']),
    revised=sum(1 for r in rows if r['revision_class']=='revised'),
    rights_proprietary=sum(1 for r in rows if 'PROPRIETARY' in r['rights_rung'] or 'LICENSED' in r['rights_rung']),
    elapsed_s=round(time.time()-t0,1))
with open(f'{OUT}/ch_r26_summary.json','w') as f: json.dump(summ,f,indent=2)
print('SUMMARY', json.dumps(summ))
