#!/usr/bin/env python3
"""THE MAC-BUILT TOOLS' INPUTS, FOR THE /data/ PAGE (15 November 2026, collection 1052; Anthony 05:07 PT: "ALL OF OUR DATA IS
CORRECT AND OUR DATA PAGE IS CORRECT").

Run on the Mac (it reads the Mac's files); writes s2/tool_inputs_mac.json beside it, which bhs_site.py reads at every cloud build.
The ROWS come from each tool's own code, never typed here:
  stress-map  : the INPUTS dict of 1052 code/stress_map_v2_1052.py (v1 and v3 read the same files), evaluated from its source;
  state-onset : every data/ and 03_data/ path literal in the 1032 chain - the scripts named in step 2 of
                doc/ROUTINE-state-page-refresh-1032.md, the modules they import and the scripts that write the out/ files they read;
  shadow      : out/live_state_823.json of the last live run (its feeds and its doors) and the frozen door lists it reads.
Each row's latest observation and refresh time are measured from the file itself at run time. META below only NAMES a file
(publisher, link, frequency); a file the tools read that META does not name is still listed, as 'not classified', and the
run exits 1 so the gap is seen. No AI. Usage: python3 s2/tool_inputs_mac.py [--check]"""
import os, re, sys, ast, glob, gzip, json, datetime as dt
HOME = os.path.expanduser('~'); ROOT = os.path.join(HOME, 'Projects/Onset Detector Data'); DI = os.path.join(HOME, 'Projects/Disturbance Indicator Data')
HERE = os.path.dirname(os.path.abspath(__file__)); OUTF = os.path.join(HERE, 'tool_inputs_mac.json')
C52 = glob.glob(ROOT + '/1052_*')[0]; D32 = glob.glob(ROOT + '/1032_*')[0]; D823 = glob.glob(ROOT + '/823_*')[0]
TODAY = dt.date.today().isoformat()
FR = 'https://fred.stlouisfed.org/series/'
# name, series ids, publisher, link, frequency - keyed by a piece of the path (first match wins)
META = [
 ('coincident-revised.xls', ('State coincident indexes, 50 states', '<ST>PHCI', 'Federal Reserve Bank of Philadelphia', 'https://www.philadelphiafed.org/surveys-and-data/regional-economic-analysis/state-coincident-indexes', 'monthly')),
 ('fred_state_ur', ('State unemployment rates, 50 states and DC', '<ST>UR', 'Bureau of Labor Statistics, LAUS (via FRED)', FR + 'CAUR', 'monthly')),
 ('fred_state_payrolls', ('State payroll employment, 50 states and DC', '<ST>NA', 'Bureau of Labor Statistics, CES State and Metro (via FRED)', FR + 'CANA', 'monthly')),
 ('fred_nsa', ('State payrolls and unemployment rates, not seasonally adjusted', '<ST>NAN, <ST>URN', 'Bureau of Labor Statistics (via FRED)', FR + 'CANAN', 'monthly')),
 ('state_nan', ('State payroll employment, not seasonally adjusted (history layer before 1979-07)', '<ST>NAN', 'Bureau of Labor Statistics, CES State (via FRED)', FR + 'CANAN', 'monthly')),
 ('FH_state_claims', ('State initial claims, not seasonally adjusted (history layer before 1979-07)', 'state IC NSA', 'Department of Labor, ETA (FH history file)', 'https://oui.doleta.gov/unemploy/claims.asp', 'monthly')),
 ('dol/ar539.csv', ('State weekly claims, ETA 539', 'ETA 539 by state', 'Department of Labor, ETA 539', 'https://oui.doleta.gov/unemploy/DataDownloads.asp', 'weekly')),
 ('dol/ar5159.csv', ('State claims and payments, ETA 5159', 'ETA 5159 by state', 'Department of Labor, ETA 5159', 'https://oui.doleta.gov/unemploy/DataDownloads.asp', 'monthly')),
 ('state_ic_weekly', ('State initial claims, weekly, 1945 on', 'state IC weekly', 'Department of Labor, ETA (spliced history)', 'https://oui.doleta.gov/unemploy/claims.asp', 'weekly')),
 ('state_iur_monthly', ('State insured unemployment rates, monthly, 1948 on', 'state IUR', 'Department of Labor, ETA (spliced history)', 'https://oui.doleta.gov/unemploy/claims.asp', 'monthly')),
 ('SQINC4', ('State personal income, quarterly (SQINC4)', 'SQINC4', 'Bureau of Economic Analysis', 'https://apps.bea.gov/regional/downloadzip.htm', 'quarterly')),
 ('bps_state', ('State building permits, units', 'BPS state', 'Census Bureau, Building Permits Survey', 'https://www.census.gov/construction/bps/', 'monthly')),
 ('cps_state', ('State CPS microdata tallies', 'CPS state', 'Census Bureau / BLS, Current Population Survey', 'https://www.census.gov/data/datasets/time-series/demo/cps/cps-basic.html', 'monthly')),
 ('fred/CPIAUCSL', ('Consumer price index', 'CPIAUCSL', 'Bureau of Labor Statistics (via FRED)', FR + 'CPIAUCSL', 'monthly')),
 ('qcew_state_total_monthly', ('QCEW State total covered employment', 'QCEW state', 'Bureau of Labor Statistics, QCEW', 'https://www.bls.gov/cew/downloadable-data-files.htm', 'quarterly')),
 ('qcew_release_dates', ('QCEW release dates', 'QCEW releases', 'Bureau of Labor Statistics, QCEW', 'https://www.bls.gov/schedule/news_release/cew.htm', 'quarterly')),
 ('county_tot', ('QCEW county total covered employment', 'QCEW county', 'Bureau of Labor Statistics, QCEW', 'https://www.bls.gov/cew/downloadable-data-files.htm', 'quarterly')),
 ('qcew_industry', ('QCEW county and industry employment', 'QCEW county/industry', 'Bureau of Labor Statistics, QCEW', 'https://www.bls.gov/cew/downloadable-data-files.htm', 'quarterly')),
 ('state_industry_releases', ('State payrolls by industry, as first published', 'SM first prints', 'Bureau of Labor Statistics, State Employment and Unemployment release', 'https://www.bls.gov/sae/', 'monthly')),
 ('state_payroll_releases', ('State payrolls, as first published 1994-2007', 'SM first prints', 'Bureau of Labor Statistics, State Employment and Unemployment release', 'https://www.bls.gov/sae/', 'monthly')),
 ('county_ur_lf', ('County unemployment rates and labor force, 3,143 counties', 'LAUCN*', 'Bureau of Labor Statistics, LAUS', 'https://www.bls.gov/lau/', 'monthly')),
 ('ces_all.txt', ('National payrolls by supersector', 'CES', 'Bureau of Labor Statistics, CES', 'https://download.bls.gov/pub/time.series/ce/', 'monthly')),
 ('state_metro_payrolls_all', ('State payrolls by supersector', 'SM', 'Bureau of Labor Statistics, CES State and Metro', 'https://download.bls.gov/pub/time.series/sm/', 'monthly')),
 ('cb_2024_us_county', ('County boundaries, 2024', 'cb_2024_us_county_500k', 'Census Bureau, cartographic boundary files', 'https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html', 'static')),
 ('state_shapes_cb2024', ('State boundaries, 2024 (drawn from the Census file)', 'cb_2024_us_state', 'Census Bureau, cartographic boundary files', 'https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html', 'static')),
 ('BH-STATE-CHRONOLOGY-V4', ('Bristow-Hall State chronology v4', 'derived', 'Bristow-Hall (collection 1032)', '/state-onset/', 'monthly')),
 ('damage_line_v4', ('Bristow-Hall State damage line v4', 'derived', 'Bristow-Hall (collection 1032)', '/state-onset/', 'monthly')),
 ('out_v3_2_damage_cut/chronology.csv', ('National disturbance register v3.2', 'derived: PAYEMS, INDPRO, W875RX1, CMRMTSPL, UNRATE, GDPC1', 'Bristow-Hall (Disturbance Indicator)', '/disturbance/', 'monthly')),
 ('bhs_state.json', ('Live recession chronology (the detector)', 'derived', 'Bristow-Hall (the detector)', '/detector/', 'daily')),
 ('claims13_R_612', ('Initial claims, 13-week feed, by release day', 'ICSA', 'Department of Labor, weekly claims release', FR + 'ICSA', 'weekly')),
 ('gap_612', ('Unemployment gap feed, by release day', 'UNRATE', 'Bureau of Labor Statistics, Employment Situation', FR + 'UNRATE', 'monthly')),
 ('michez_612', ('Michaillat-Saez feed, by release day', 'UNRATE, JTSJOL', 'Bureau of Labor Statistics, Employment Situation and JOLTS', FR + 'JTSJOL', 'monthly')),
 ('sp500_612', ('S&P 500 daily close', '^GSPC', 'S&P Dow Jones Indices (via FRED SP500)', FR + 'SP500', 'daily')),
 ('doorlists.json', ('V3.76 door lists (frozen)', 'V376_LAB, V376_P, V376_Y', 'Bristow-Hall (collection 736)', '/shadow/', 'static')),
]

def meta(path):
    for k, m in META:
        if k in path: return m
    return None
def _mtime(fs):
    t = max((os.path.getmtime(f) for f in fs if os.path.exists(f)), default=None)
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat(timespec='minutes').replace('+00:00', 'Z') if t else ''
_DRE = re.compile(r'(?<!\d)((?:19|20)\d{2}-(?:0[1-9]|1[0-2])(?:-[0-3]\d)?)(?!\d)')
def _maxdate_text(t):
    ds = [x for x in _DRE.findall(t) if x[:10] <= TODAY]; return max(ds) if ds else ''
def _bls_flat(p, sid):
    best = ''
    with gzip.open(p, 'rt', errors='replace') as f:
        next(f)
        for ln in f:
            if not ln.startswith(sid): continue
            x = ln.split('\t')
            if x[0].strip() == sid and re.match(r'M(0[1-9]|1[0-2])$', x[2].strip()): best = max(best, '%s-%s' % (x[1].strip(), x[2].strip()[1:]))
    return best
def _qcew_county(fs):
    ys = sorted(fs); f = ys[-1]; best = ''
    for ln in open(f):
        x = ln.rstrip('\n').split(',')
        try:
            if float(x[6] or 0) > 0: best = max(best, '%s-%02d' % (x[3], 3 * (int(x[4]) - 1) + int(x[5])))
        except Exception: pass
    return best
def _csv_last(f):
    import pandas as pd
    op = gzip.open if f.endswith('.gz') else open
    with op(f, 'rt', errors='replace') as h: head = h.readline()
    cols = [c.strip().strip('"') for c in head.split(',')]
    if any(re.match(r'^\d{4}:Q[1-4]$', c) for c in cols):   # BEA wide quarterly
        q = max(c for c in cols if re.match(r'^\d{4}:Q[1-4]$', c)); return '%s-%02d' % (q[:4], 3 * int(q[-1]))
    pick = next((c for c in ('observation_date', 'date', 'week', 'rptdate', 'month', 'ref_month', 'released', 'published') if c in cols), cols[0])
    d = pd.read_csv(f, usecols=[pick], dtype=str)[pick].dropna().astype(str)
    d = [x[:10] for x in d if _DRE.match(x[:10]) and x[:10] <= TODAY]
    if d: return max(d)
    with op(f, 'rt', errors='replace') as h: return _maxdate_text(h.read())   # no date column: the newest date the file carries
def latest(path, key=''):
    """(latest observation held, refreshed) measured from the file(s) at `path` (a file, a directory, or a pattern with * <ST> <YEAR>)"""
    pat = path.replace('<ST>', '*').replace('<YEAR>', '*')
    fs = sorted(glob.glob(pat)) if '*' in pat else ([os.path.join(pat, x) for x in sorted(os.listdir(pat)) if not x.startswith('.')] if os.path.isdir(pat) else ([pat] if os.path.exists(pat) else []))
    if not fs: return 'MISSING', ''
    ref = _mtime(fs)
    try:
        if path.endswith('.zip') or 'state_shapes_cb2024' in path: return 'static (2024 boundaries)', ref
        if path.endswith('.xls'):
            import pandas as pd; X = pd.read_excel(fs[0], sheet_name='Indexes'); return str(pd.to_datetime(X.iloc[:, 0], errors='coerce').max().date())[:7], ref
        if 'county_tot' in path: return _qcew_county(fs), ref
        if path.endswith('.txt.gz'): return _bls_flat(fs[0], 'CES0000000001' if 'ces_all' in path else 'SMS06000000000000001'), ref
        if path.endswith('bhs_state.json'): return str(json.load(open(fs[0])).get('built_at', ''))[:16], ref
        if path.endswith('.json'): return _maxdate_text(open(fs[0], errors='replace').read()), ref
        if len(fs) == 1 and fs[0].endswith(('.csv', '.csv.gz')): return _csv_last(fs[0]), ref
        vals = [v for v in (_csv_last(f) for f in fs if f.endswith(('.csv', '.csv.gz'))) if v]
        if not vals: return '', ref
        per_state = '<ST>' in path or os.path.isdir(pat)   # one file per State: the oldest State matters; one file per year: only the newest
        return (max(vals) if (max(vals) == min(vals) or not per_state) else '%s (oldest of %d files %s)' % (max(vals), len(vals), min(vals))), ref
    except Exception as e:
        return 'ERROR %s' % repr(e)[:80], ref

# ---------------- the inputs, from each tool's own code ----------------
def stress_map_inputs():
    """INPUTS of 1052 code/stress_map_v2_1052.py: its module-level path assignments and the INPUTS dict, evaluated (nothing else runs)"""
    py = os.path.join(C52, 'code/stress_map_v2_1052.py'); T = ast.parse(open(py).read()); G = dict(os=os, sys=sys, __file__=py)
    for n in T.body:
        if isinstance(n, ast.Assign):
            try: exec(compile(ast.Module([n], []), py, 'exec'), G)
            except Exception: pass
            if any(isinstance(t, ast.Name) and t.id == 'INPUTS' for t in n.targets): break
    IN = G['INPUTS']; rows = []
    for k, p in IN.items():
        if str(p).startswith('http') or str(p).endswith(('.py', '.html')): continue   # code, templates and the fetch address of county_laus
        rows.append((k, p))
    return rows, 'INPUTS of 1052 code/stress_map_v2_1052.py (v1 and v3 read the same files)'
def state_onset_inputs():
    CODE = os.path.join(D32, 'code'); rt = open(os.path.join(D32, 'doc/ROUTINE-state-page-refresh-1032.md')).read()
    q = re.findall(r'`([A-Za-z0-9_]+\.py)`', re.search(r'^2\. (.*)$', rt, re.M).group(1)); seen = []
    src = {f: open(os.path.join(CODE, f), errors='replace').read() for f in os.listdir(CODE) if f.endswith('.py') and '_bak' not in f}
    while q:
        f = q.pop(0)
        if f in seen or f not in src: continue
        seen.append(f); s = src[f]
        for m in re.findall(r'^\s*(?:import|from)\s+([A-Za-z0-9_, ]+)', s, re.M):
            q += [x.strip() + '.py' for x in re.split(r'[ ,]+', m) if x.strip().endswith(('_1032', '_lib'))]
        for b in set(re.findall(r"['\"]([A-Za-z0-9_.\-]+\.(?:json|csv|pkl))['\"]", s)):   # the scripts that write the out/ files this one reads
            q += [p for p in sorted(src) if p != f and b in src[p] and re.search(r"(json\.dump|to_csv|pickle\.dump)\([^\n]*" + re.escape(b), src[p])][-1:]
    lits = {}
    for f in seen:
        for lit in re.findall(r"['\"]((?:data|03_data)/[^'\"]+)['\"]", src[f]): lits.setdefault(lit, []).append(f)
    rows = []
    for lit in sorted(lits):
        p = os.path.join(DI if lit.startswith('03_data') else D32, lit)
        if lit.rstrip('/').endswith('qcew_industry'): p = os.path.join(D32, 'data/qcew_industry/<YEAR>_county_tot.csv')
        rows.append((lit, p))
    for k in ('out/BH-STATE-CHRONOLOGY-V4-1032.csv', 'out/damage_line_v4_a198_1032.json'):   # the two derived layers the page draws (read by state_page_1032.py)
        if k.split('/')[-1] in src.get('state_page_1032.py', ''): rows.append((k, os.path.join(D32, k)))
    return rows, '%d scripts of the 1032 chain (ROUTINE step 2, their imports, the writers of the files they read)' % len(seen)
def shadow_inputs():
    L = json.load(open(os.path.join(D823, 'out/live_state_823.json'))); rows = []
    feeds_dir = glob.glob(ROOT + '/612_*/data/feeds')[0]
    for fn in sorted(L.get('feeds') or {}): rows.append((fn, os.path.join(feeds_dir, fn)))
    for d in sorted(L.get('doors') or {}):
        if d.startswith('V376'): continue
        rows.append(('door:' + d, (L['doors'][d][-1] if L['doors'][d] else ''), L.get('run', '')))
    rows.append(('doorlists.json', glob.glob(ROOT + '/736_*/specs/doorlists.json')[0]))
    return rows, '823 out/live_state_823.json (run %s): its feeds and doors' % L.get('run', '')

def build():
    tools = {}; unknown = []
    for tool, fn in (('stress-map', stress_map_inputs), ('state-onset', state_onset_inputs), ('shadow', shadow_inputs)):
        rows, frm = fn(); out = []
        for r in rows:
            if r[0].startswith('door:'):
                d = r[0][5:]
                out.append(dict(key=r[0], name='First-print door ' + d + ' (its last call)', ids=d, source='Bristow-Hall (736 door library, rebuilt from the shadow feeds by 823)', url='/shadow/', freq='daily', through=r[1][:10], refreshed=r[2][:16].replace('+00:00', 'Z'), path=''))
                continue
            k, p = r; m = meta(p) or meta(k)
            th, rf = latest(p, k)
            if m and m[1].startswith('derived') and p.endswith('.csv') and os.path.exists(p): th = _maxdate_text(open(p, errors='replace').read())   # a register: the newest month it carries, not its first column
            if not m: unknown.append((tool, k, p)); m = (k + ' (not classified)', k, 'not classified', '', '')
            if any(o['name'] == m[0] for o in out): continue   # two literals of the tool's code naming the same files (e.g. a folder and a pattern in it)
            out.append(dict(key=k, name=m[0], ids=m[1], source=m[2], url=m[3], freq=m[4], through=th, refreshed=rf, path=p.replace(HOME, '~')))
        tools[tool] = dict(read_from=frm, rows=out)
    J = dict(generated_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'), generator='s2/tool_inputs_mac.py (run on the Mac)', tools=tools, unclassified=unknown)
    return J, unknown

if __name__ == '__main__':
    J, unknown = build()
    for t, v in J['tools'].items():
        print('%-11s %2d rows  (%s)' % (t, len(v['rows']), v['read_from']))
        for r in v['rows']: print('   %-60s %-26s %s' % (r['name'][:60], str(r['through'])[:26], r['refreshed']))
    bad = [(t, r['name']) for t, v in J['tools'].items() for r in v['rows'] if str(r['through']).startswith(('MISSING', 'ERROR'))]
    if '--check' not in sys.argv:
        json.dump(J, open(OUTF, 'w'), indent=1); print('wrote', OUTF)
    if unknown: print('NOT CLASSIFIED (add to META):', unknown)
    if bad: print('MISSING/ERROR:', bad)
    sys.exit(1 if (unknown or bad) else 0)
