#!/usr/bin/env python3
"""TOOL 4 - THE REAL-TIME NATIONAL RECESSION FORECASTER (rule H2, collection 1118; Anthony 15 Nov 2026 13:03 PT: "h2", published in
place of the damage index, live on GitHub). Standard library only; no AI.

The rule (H2). A recession warning is issued on a day when either
  route 1: the 10-year minus 3-month Treasury spread (monthly means, GS10 - TB3MS, known the 1st of the next month) is below zero, or
  route 2: the 10-year minus 1-year spread (GS10 - GS1) was below zero within the past 365 days and the insured unemployment rate
           (seasonally adjusted, first print, known on its release day) is above its level for the week 52 weeks earlier,
unless the war-surge veto is on (federal defense spending growing 10 or more points faster than CPI inflation over four quarters,
latest vintage on the day; collection 561). After each recession end called by the live Recession Indicator (its close day), a curve
counts again only once it has been at or above zero, route 2 needs a new curve signal after the close, and insured unemployment must
have fallen to or below its year-earlier level once. Calls within 182 days form one warning.
Record (in sample, collection 1118): every recession 1957-2024 warned 28 to 516 days before the end of its peak month, no false alarm
1953-2026. 1948 and 1953 lie before the rule's data (no unpegged short-term Treasury rate before April 1953).

Inputs: FRED API (GS10, GS1, TB3MS; FDEFX, CPIAUCNS for the veto's live days) with FRED_API_KEY from the environment; the live tool's
claims first prints (workspace/cache/national_first_prints_1985_live.csv); the 1949-75 first prints (collection 59) and the veto
history 1965-08-19..2026-10-04 (collection 561) kept in data/tool4_forecaster/. Writes site/public/forecaster/ (index.html,
state.json), turns /damage-index/ into a pointer to it, and renames the menu entry and home card on every built page.
Usage: python3 ops/tool4/forecaster.py [--offline] [--prefetch: fetch and keep the inputs only, before the site build]"""
import os, re, sys, csv, json, glob, calendar, datetime as dt, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYS = os.path.join(ROOT, 'data', '105_bristow_hall_system_2026-09-08')
SITE = os.path.join(SYS, 'site', 'public'); WS = os.path.join(SYS, 'workspace')
DATA = os.path.join(ROOT, 'data', 'tool4_forecaster')
OFFLINE = '--offline' in sys.argv
VETO_LINE = 10.0
d = dt.date.fromisoformat
NOW = dt.datetime.now(dt.timezone.utc); TODAY = NOW.date()
LOG = []
def log(*a): LOG.append(' '.join(str(x) for x in a)); print(*a)

def add(m, k):
    y, mo = map(int, m.split('-')); t = y * 12 + mo - 1 + k; return f'{t // 12}-{t % 12 + 1:02d}'
def me(m):
    y, mo = map(int, m.split('-')); return dt.date(y, mo, calendar.monthrange(y, mo)[1])

# ---------- FRED ----------
LATEST_F = os.path.join(DATA, 'latest.json')   # the newest observation of each series as FRED holds it now (the data page reads it)
LATEST = json.load(open(LATEST_F)) if os.path.exists(LATEST_F) else {}
def fred(sid, start='1950-01-01'):
    key = os.environ.get('FRED_API_KEY', '')
    if OFFLINE or not key: return None
    q = urllib.parse.urlencode(dict(series_id=sid, api_key=key, file_type='json', observation_start=start))
    for i in range(3):
        try:
            with urllib.request.urlopen('https://api.stlouisfed.org/fred/series/observations?' + q, timeout=60) as r:
                obs = json.load(r)['observations']
            out = {o['date'][:10]: float(o['value']) for o in obs if o['value'] not in ('.', '')}
            if out: LATEST[sid] = [max(out), out[max(out)]]
            return out
        except Exception as e:
            err = type(e).__name__
    log('FRED', sid, 'failed:', err); return None

# ---------- monthly rates ----------
RATES = os.path.join(DATA, 'rates_monthly.csv')
rates = {r['month']: r for r in csv.DictReader(open(RATES))}
fresh = {}
for sid in ('GS10', 'GS1', 'TB3MS'):
    s = fred(sid, '1953-01-01')
    if s:
        fresh[sid] = True
        for k, v in s.items():
            m = k[:7]
            if m >= '1953-04': rates.setdefault(m, {'month': m, 'GS10': '', 'GS1': '', 'TB3MS': ''})[sid] = repr(v)
with open(RATES, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['month', 'GS10', 'GS1', 'TB3MS'])
    for m in sorted(rates): w.writerow([m, rates[m]['GS10'], rates[m]['GS1'], rates[m]['TB3MS']])
def num(x):
    try: return float(x)
    except Exception: return None
sp3 = {m: num(r['GS10']) - num(r['TB3MS']) for m, r in rates.items() if num(r['GS10']) is not None and num(r['TB3MS']) is not None}
spb = {m: num(r['GS10']) - num(r['GS1']) for m, r in rates.items() if num(r['GS10']) is not None and num(r['GS1']) is not None}
# a month's mean is known the 1st of the next month: drop the current (unfinished) month
cur = f'{TODAY.year}-{TODAY.month:02d}'
sp3 = {m: v for m, v in sp3.items() if m < cur}; spb = {m: v for m, v in spb.items() if m < cur}
log('rates through', max(sp3), max(spb), 'fresh from FRED' if fresh else 'FROM THE KEPT COPY (FRED not reached)')

# ---------- insured unemployment, first prints ----------
iu = []
for r in csv.DictReader(open(os.path.join(DATA, 'iur_sa_first_prints_1949_1983_59.csv'))):
    w_ = d(r['']) if '' in r else d(list(r.values())[0])
    if w_ < d('1975-07-26') and r['iur_rt_sa']: iu.append((w_, w_ + dt.timedelta(14), float(r['iur_rt_sa'])))
for r in csv.DictReader(open(os.path.join(WS, 'cache', 'national_first_prints_1985_live.csv'))):
    if r.get('iur_sa') and r.get('iu_week_ended') and r.get('release_date'):
        w_ = d(r['iu_week_ended'])
        if w_ >= d('1975-07-26'): iu.append((w_, d(r['release_date']), float(r['iur_sa'])))
iu.sort(); byw = {w_: (rel, v) for w_, rel, v in iu}
Con, offs = [], []
for w_, rel, v in iu:
    p = byw.get(w_ - dt.timedelta(364))
    if not p: continue
    (Con if v > p[1] else offs).append(rel)
Con = sorted(set(Con)); offs = sorted(set(offs))
iu_last = iu[-1]; iu_prev = byw.get(iu_last[0] - dt.timedelta(364))
log('insured unemployment through week', iu_last[0], 'released', iu_last[1])

# ---------- war-surge veto ----------
V = {}
for r in csv.DictReader(open(os.path.join(DATA, 'war_surge_daily_561.csv'))):
    k = r.get('') or list(r.values())[0]
    if r['surge']: V[k] = float(r['surge'])
LIVE_V = os.path.join(DATA, 'war_surge_live.csv')
live_rows = list(csv.DictReader(open(LIVE_V))) if os.path.exists(LIVE_V) else []
f_ = fred('FDEFX', '1990-01-01'); c_ = fred('CPIAUCNS', '1990-01-01')
if f_ and c_:
    fq = sorted(f_); q = fq[-1]; g = 100 * (f_[q] / f_[fq[-5]] - 1)
    qd = d(q); qm = [f'{qd.year}-{qd.month + k:02d}-01' for k in range(3)]; qy = [f'{qd.year - 1}{x[4:]}' for x in qm]
    have = [k for k in range(3) if qm[k] in c_ and qy[k] in c_]
    if have:
        infl = 100 * (sum(c_[qm[k]] for k in have) / len(have) / (sum(c_[qy[k]] for k in have) / len(have)) - 1)
        if not live_rows or live_rows[-1]['date'] != TODAY.isoformat():
            live_rows.append(dict(date=TODAY.isoformat(), surge=f'{g - infl:.4f}', quarter=q[:7], defense_g4=f'{g:.4f}', cpi_g4=f'{infl:.4f}'))
        with open(LIVE_V, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['date', 'surge', 'quarter', 'defense_g4', 'cpi_g4']); w.writeheader(); w.writerows(live_rows)
json.dump(LATEST, open(LATEST_F, 'w'), indent=1)
if '--prefetch' in sys.argv:   # before the site build: the data page's rows read these files (1118, 16 Nov 2026)
    print('prefetch done:', {k: v[0] for k, v in LATEST.items()}); sys.exit(0)
# days after the 561 history: each day takes the newest live reading made on or before it (the first live reading also covers the gap
# between the end of the 561 history and the first live run)
lr = sorted((r['date'], float(r['surge'])) for r in live_rows)
def surge(day):
    k = day.isoformat()
    if k in V: return V[k]
    if not lr or k < '2026-10-05': return None
    best = lr[0][1]
    for dd, s in lr:
        if dd <= k: best = s
    return best
def vetoed(day):
    s = surge(day); return s is not None and s >= VETO_LINE
surge_now = surge(TODAY)

# ---------- closes (the live Recession Indicator's real-time recession ends) ----------
bhs = json.load(open(os.path.join(SITE, 'bhs_state.json')))
closes = sorted(d(e['close_pub']) for e in bhs['chronology'] if e.get('close_pub'))
standing = bhs.get('standing', {})
NBER = [(e['peak'], e['trough']) for e in bhs['nber']]

# ---------- the rule ----------
def rearmed(c, sp):
    lc = max([x for x in closes if x <= c], default=None)
    if lc is None: return True
    lm = f'{lc.year}-{lc.month:02d}'
    return any(v >= 0 for m, v in sp.items() if m >= lm and d(add(m, 1) + '-01') <= c)
r1 = [d(add(m, 1) + '-01') for m in sorted(sp3) if sp3[m] < 0]
r1 = [c for c in r1 if c >= d('1953-05-01') and not vetoed(c) and rearmed(c, sp3)]
arm = [d(add(m, 1) + '-01') for m in sorted(spb) if spb[m] < 0]
arm = sorted(c for c in arm if rearmed(c, spb))
r2 = []
for c in Con:
    lc = max([x for x in closes if x < c], default=dt.date(1900, 1, 1))
    if not any(lc < a <= c and (c - a).days <= 365 for a in arm): continue
    lc2 = max([x for x in closes if x < c], default=None)
    if lc2 is not None and not any(lc2 < o < c for o in offs): continue
    if vetoed(c): continue
    r2.append(c)
calls = sorted(set(r1) | set(r2)); route = {c: ('1' if c in r1 else '') + ('2' if c in r2 else '') for c in calls}

# episodes (one warning = calls <= 182 days apart with no close between) and the record
eps = []
for c in calls:
    if eps and (c - eps[-1][-1]).days <= 182 and not any(eps[-1][-1] <= x < c for x in closes): eps[-1].append(c)
    else: eps.append([c])
ZONES = [(p, me(p) - dt.timedelta(730), me(t), me(p)) for p, t in NBER]
hits, fas, pending = {}, [], []
for e in eps:
    z = next((z for z in ZONES if z[1] <= e[0] <= z[2]), None)
    if z is None:
        # a warning with no recession yet: pending until 730 days after it, a false alarm after that
        (pending if (TODAY - e[0]).days <= 730 and e[0] > closes[-1] else fas).append(e)
        continue
    hits.setdefault(z[0], e)
record = []
for p, t in NBER:
    if p <= '1953-07':   # 1948 and 1953: no unpegged short-term Treasury rate before April 1953
        record.append(dict(peak=p, trough=t, warning=None, lag=None, note='before the data begin')); continue
    e = hits.get(p)
    record.append(dict(peak=p, trough=t, warning=e[0].isoformat() if e else None, lag=(e[0] - me(p)).days if e else None,
                       route=route[e[0]] if e else None, note='' if e else 'missed'))
reach = [r for r in record if r['note'] != 'before the data begin']
early = [r for r in reach if r['lag'] is not None and r['lag'] <= 0]
log('record:', len(early), 'of', len(reach), 'early;', len(fas), 'false alarms;', len(pending), 'pending')

# the warning now
last_close = closes[-1]
open_ep = next((e for e in reversed(eps) if e[0] > last_close), None)
if standing.get('state') == 'open':
    status, status_line = 'recession', 'The Recession Indicator has called a recession; the forecaster stands down until it ends.'
elif open_ep and (TODAY - open_ep[0]).days <= 730:
    status, status_line = 'warning', f'Recession warning since {open_ep[0]:%B %-d, %Y}.'
else:
    status, status_line = 'clear', 'No recession warning.'
m3, mb = max(sp3), max(spb)
arm_now = any(0 <= (TODAY - a).days <= 365 and a > last_close for a in arm)
state = dict(tool='Real-Time National Recession Forecaster (Tool 4, rule H2, collection 1118)', built=NOW.strftime('%Y-%m-%d %H:%M UTC'),
             status=status, status_line=status_line,
             readings=dict(spread_10y_3m=dict(month=m3, value=round(sp3[m3], 2), on=sp3[m3] < 0),
                           spread_10y_1y=dict(month=mb, value=round(spb[mb], 2), on=spb[mb] < 0, armed_within_365d=arm_now),
                           insured_unemployment=dict(week=iu_last[0].isoformat(), released=iu_last[1].isoformat(), rate=iu_last[2],
                                                     year_earlier=iu_prev[1] if iu_prev else None,
                                                     on=bool(iu_prev and iu_last[2] > iu_prev[1])),
                           war_surge=dict(value=None if surge_now is None else round(surge_now, 2), veto_on=bool(surge_now is not None and surge_now >= VETO_LINE))),
             last_close=last_close.isoformat(), record=record, false_alarms=[e[0].isoformat() for e in fas],
             pending=[e[0].isoformat() for e in pending], warnings=[dict(start=e[0].isoformat(), end=e[-1].isoformat()) for e in eps],
             inputs_fresh=dict(fred=sorted(fresh)), log=LOG)

# ---------- the page ----------
shell = open(os.path.join(SITE, 'chronology', 'index.html'), encoding='utf-8').read()
style = re.search(r'<style>.*?</style>', shell, re.S).group(0)
header = re.search(r'<header class="bh">.*?</header>', shell, re.S).group(0)
footer = re.search(r'<div class="foot">.*?</div></div>', shell, re.S).group(0)
def nav_fix(h):
    h = h.replace('href="/damage-index/"', 'href="/forecaster/"').replace('>Damage Index<', '>Recession Forecaster<')
    return h
header = nav_fix(header).replace(' aria-current="page"', '').replace('href="/forecaster/"', 'href="/forecaster/" aria-current="page"')

def chart():
    W, H, L, R, T, B = 1100, 380, 46, 14, 16, 30
    ms = sorted(set(sp3) | set(spb)); x0, x1 = d(ms[0] + '-01'), TODAY
    vals = [v for v in list(sp3.values()) + list(spb.values())]
    lo, hi = min(-3.0, min(vals)), max(4.5, max(vals))
    X = lambda day: L + (W - L - R) * (day - x0).days / (x1 - x0).days
    Y = lambda v: T + (H - T - B) * (hi - v) / (hi - lo)
    out = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Treasury yield spreads since 1953 with recessions and warnings">',
           f'<rect x="{L}" y="{T}" width="{W-L-R}" height="{H-T-B}" fill="#fff" stroke="#ddd"/>']
    for p, t in NBER:
        a, b = max(X(d(p + '-01')), L), X(me(t))
        if b > L: out.append(f'<rect x="{a:.1f}" y="{T}" width="{max(b-a,1.5):.1f}" height="{H-T-B}" fill="#e6e6e6"/>')
    for e in eps:
        a, b = X(e[0]), X(e[-1])
        out.append(f'<rect x="{a:.1f}" y="{T}" width="{max(b-a,2):.1f}" height="8" fill="#990000"/>')
    for v in range(int(lo), int(hi) + 1):
        out.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{"#333" if v == 0 else "#f0f0f0"}" stroke-width="{1 if v == 0 else 0.7}"/>'
                   f'<text x="{L-6}" y="{Y(v)+4:.1f}" font-size="11" text-anchor="end" fill="#555">{v:+d}</text>')
    for y in range(1955, TODAY.year + 1, 5):
        out.append(f'<text x="{X(dt.date(y,1,1)):.1f}" y="{H-10}" font-size="11" text-anchor="middle" fill="#555">{y}</text>')
    for sp, col in ((sp3, '#1f4e79'), (spb, '#c47a00')):
        pts = ' '.join(f'{X(d(m + "-15")):.1f},{Y(sp[m]):.1f}' for m in sorted(sp))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.3"/>')
    out.append('</svg>'); return '\n'.join(out)

def fmt_day(s): return dt.date.fromisoformat(s).strftime('%b %-d, %Y') if s else ''
rows = []
for r in record:
    y = r['peak'][:4]
    if r['note'] == 'before the data begin': rows.append(f'<tr><td>{y}</td><td>{r["peak"]}</td><td colspan="2" class="muted">Before the data begin</td></tr>')
    elif r['warning']: rows.append(f'<tr><td>{y}</td><td>{r["peak"]}</td><td>{fmt_day(r["warning"])}</td><td>{-r["lag"]} days early</td></tr>')
    else: rows.append(f'<tr><td>{y}</td><td>{r["peak"]}</td><td colspan="2"><b>Missed</b></td></tr>')
rd = state['readings']
def onoff(b): return '<b style="color:#990000">on</b>' if b else 'off'
cls = {'warning': 'warn', 'recession': 'warn', 'clear': 'clear'}[status]
page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bristow-Hall Business Cycle Program — Real-Time National Recession Forecaster</title>
{style}
<style>
.fc{{margin:30px 0 0}} .fc h1{{font-size:30px;color:#990000;margin:0 0 8px;line-height:1.2}} .fc .tag{{font-size:17px;color:#333;margin:0 0 16px}}
.fc .status{{font-size:22px;font-weight:700;padding:12px 16px;border-radius:6px;margin:0 0 18px;display:inline-block}}
.fc .status.clear{{background:#eef6ee;color:#1d5e20}} .fc .status.warn{{background:#fbeaea;color:#990000}}
.fc table{{border-collapse:collapse;margin:8px 0 18px;font-size:14px}} .fc td,.fc th{{border-bottom:1px solid #e5e5e5;padding:5px 12px 5px 0;text-align:left}}
.fc .muted{{color:#888}} .fc .key span{{display:inline-block;margin-right:18px;font-size:13px}} .fc p{{color:#333;max-width:none}}
#chart svg{{width:100%;height:auto;display:block}}
</style>
</head>
<body>
{header}
<div class="inner"><div class="fc">
<span class="badge">LIVE</span>
<h1>Real-Time National Recession Forecaster</h1>
<p class="tag">Warns of a U.S. recession up to two years before it starts, from the Treasury yield curve and insured unemployment.</p>
<div class="status {cls}">{status_line}</div>
<div id="chart">{chart()}</div>
<p class="key"><span style="color:#1f4e79">&#9644; 10-year minus 3-month</span><span style="color:#c47a00">&#9644; 10-year minus 1-year</span><span style="color:#999">&#9632; recessions</span><span style="color:#990000">&#9632; warnings</span></p>
<p>The forecaster issues a warning when the 10-year Treasury yield falls below the 3-month yield, or when it has fallen below the 1-year yield within the past year and insured unemployment is higher than a year earlier. No warning is issued while defense spending is surging far ahead of inflation, as in the Vietnam buildup. Every reading is the one published on the day.</p>
<table><tr><th>Now</th><th>Reading</th><th>Signal</th></tr>
<tr><td>10-year minus 3-month ({rd['spread_10y_3m']['month']})</td><td>{rd['spread_10y_3m']['value']:+.2f} pts</td><td>{onoff(rd['spread_10y_3m']['on'])}</td></tr>
<tr><td>10-year minus 1-year ({rd['spread_10y_1y']['month']})</td><td>{rd['spread_10y_1y']['value']:+.2f} pts</td><td>{onoff(rd['spread_10y_1y']['on'])}</td></tr>
<tr><td>Insured unemployment rate (week of {fmt_day(rd['insured_unemployment']['week'])})</td><td>{rd['insured_unemployment']['rate']:.1f}% (a year earlier {rd['insured_unemployment']['year_earlier']}%)</td><td>{onoff(rd['insured_unemployment']['on'])}</td></tr>
<tr><td>Defense surge over inflation</td><td>{'' if rd['war_surge']['value'] is None else f"{rd['war_surge']['value']:+.1f} pts"}</td><td>{'veto on' if rd['war_surge']['veto_on'] else 'no veto'}</td></tr></table>
<h2 style="font-size:20px;margin:22px 0 4px">Record</h2>
<table><tr><th>Recession</th><th>Peak month</th><th>Warning</th><th>Lead</th></tr>{''.join(rows)}</table>
<p class="muted">Every recession from 1957 to 2024 warned early; no false alarm since 1953. The record covers the whole history the rule was built from; it is not a blind test. Built {state['built']}.</p>
<p class="back"><a href="/">&larr; Back to the program</a></p>
</div></div>
{nav_fix(footer)}
</body>
</html>
'''
os.makedirs(os.path.join(SITE, 'forecaster'), exist_ok=True)
open(os.path.join(SITE, 'forecaster', 'index.html'), 'w', encoding='utf-8').write(page)
json.dump(state, open(os.path.join(SITE, 'forecaster', 'state.json'), 'w'), indent=1)
os.makedirs(os.path.join(SITE, 'damage-index'), exist_ok=True)
open(os.path.join(SITE, 'damage-index', 'index.html'), 'w').write(
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=/forecaster/">'
    '<link rel="canonical" href="/forecaster/"><title>Moved</title></head><body><a href="/forecaster/">The Recession Forecaster</a></body></html>\n')

# ---------- the menu and the home card on every built page ----------
CARD = ("{n:'Real-Time National Recession Forecaster',s:'live',href:'/forecaster/',img:'/forecaster/card.png',"
        "d:'Warns of a recession up to two years ahead from the Treasury yield curve and insured unemployment.'}")
n = 0
for f in glob.glob(os.path.join(SITE, '**', '*.html'), recursive=True):
    if f.endswith(os.path.join('damage-index', 'index.html')): continue
    t = open(f, encoding='utf-8').read(); t2 = nav_fix(t)
    t2 = re.sub(r"\{n:'Damage Index',[^}]*\}", CARD, t2)
    if t2 != t: open(f, 'w', encoding='utf-8').write(t2); n += 1
log('pages renamed:', n)
home = open(os.path.join(SITE, 'index.html'), encoding='utf-8').read()
assert "href:'/forecaster/'" in home and 'damage-index' not in home, 'home page: the forecaster card is not in place'
print(json.dumps(dict(status=status, early=len(early), reachable=len(reach), false_alarms=len(fas), pending=len(pending))))
