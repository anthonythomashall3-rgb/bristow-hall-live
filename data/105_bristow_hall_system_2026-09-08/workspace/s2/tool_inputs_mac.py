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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import held_values as HV
HOME = os.path.expanduser('~'); ROOT = os.path.join(HOME, 'Projects/Onset Detector Data'); DI = os.path.join(HOME, 'Projects/Disturbance Indicator Data')
HERE = os.path.dirname(os.path.abspath(__file__)); OUTF = os.path.join(HERE, 'tool_inputs_mac.json')
C52 = glob.glob(ROOT + '/1052_*')[0]; D32 = glob.glob(ROOT + '/1032_*')[0]; D823 = glob.glob(ROOT + '/823_*')[0]
TODAY = dt.date.today().isoformat()
FR = 'https://fred.stlouisfed.org/series/'
# name, series ids, publisher, link, frequency - keyed by a piece of the path (first match wins)
META = [
 ('coincident-revised.xls', ('State coincident indexes, 50 states', 'ALPHCI ... WYPHCI', 'Federal Reserve Bank of Philadelphia', 'https://www.philadelphiafed.org/surveys-and-data/regional-economic-analysis/state-coincident-indexes', 'monthly', 'fred:109')),
 ('fred_state_ur', ('State unemployment rates, 50 states and DC', 'ALUR ... WYUR', 'Bureau of Labor Statistics, LAUS (via FRED)', FR + 'CAUR', 'monthly', 'bls_state')),
 ('fred_state_payrolls', ('State payroll employment, 50 states and DC', 'ALNA ... WYNA', 'Bureau of Labor Statistics, CES State and Metro (via FRED)', FR + 'CANA', 'monthly', 'bls_state')),
 ('fred_nsa', ('State payrolls and unemployment rates, not seasonally adjusted', 'ALNAN ... WYNAN, ALURN ... WYURN', 'Bureau of Labor Statistics (via FRED)', FR + 'CANAN', 'monthly', 'bls_state')),
 ('state_nan', ('State payroll employment, not seasonally adjusted (history layer before 1979-07)', 'ALNAN ... WYNAN', 'Bureau of Labor Statistics, CES State (via FRED)', FR + 'CANAN', 'monthly', 'bls_state')),
 ('FH_state_claims', ('State initial claims, not seasonally adjusted (history layer before 1979-07)', 'ALICLAIMS ... WYICLAIMS', 'Department of Labor, ETA (FH history file)', 'https://oui.doleta.gov/unemploy/claims.asp', 'monthly', 'eta539')),
 ('dol/ar539.csv', ('State weekly claims, ETA 539', 'ALICLAIMS ... WYICLAIMS, ALCCLAIMS ... WYCCLAIMS', 'Department of Labor, ETA 539', 'https://oui.doleta.gov/unemploy/DataDownloads.asp', 'weekly', 'eta539')),
 ('dol/ar5159.csv', ('State claims and payments, ETA 5159', '', 'Department of Labor, ETA 5159', 'https://oui.doleta.gov/unemploy/DataDownloads.asp', 'monthly', 'eta5159')),
 ('state_ic_weekly', ('State initial claims, weekly, 1945 on', 'ALICLAIMS ... WYICLAIMS', 'Department of Labor, ETA (spliced history)', 'https://oui.doleta.gov/unemploy/claims.asp', 'weekly', 'eta539')),
 ('state_iur_monthly', ('State insured unemployment rates, monthly, 1948 on', 'ALINSUREDUR ... WYINSUREDUR', 'Department of Labor, ETA (spliced history)', 'https://oui.doleta.gov/unemploy/claims.asp', 'monthly', 'eta539')),
 ('SQINC4', ('State personal income, quarterly (SQINC4)', 'ALOTOT ... WYOTOT, ALWTOT ... WYWTOT', 'Bureau of Economic Analysis', 'https://apps.bea.gov/regional/downloadzip.htm', 'quarterly', 'bea_spi')),
 ('bps_state', ('State building permits, units', 'ALBPPRIV ... WYBPPRIV', 'Census Bureau, Building Permits Survey', 'https://www.census.gov/construction/bps/', 'monthly', 'census_bps')),
 ('cps_state', ('State CPS microdata tallies', '', 'Census Bureau / BLS, Current Population Survey', 'https://www.census.gov/data/datasets/time-series/demo/cps/cps-basic.html', 'monthly', 'census_cps')),
 ('fred/CPIAUCSL', ('Consumer price index', 'CPIAUCSL', 'Bureau of Labor Statistics (via FRED)', FR + 'CPIAUCSL', 'monthly', 'bls_cpi')),
 ('qcew_state_total_monthly', ('QCEW State total covered employment', '', 'Bureau of Labor Statistics, QCEW', 'https://www.bls.gov/cew/downloadable-data-files.htm', 'quarterly', 'bls_qcew')),
 ('qcew_release_dates', ('QCEW release dates', '', 'Bureau of Labor Statistics, QCEW', 'https://www.bls.gov/schedule/news_release/cew.htm', 'quarterly', 'bls_qcew')),
 ('county_tot', ('QCEW county total covered employment', '', 'Bureau of Labor Statistics, QCEW', 'https://www.bls.gov/cew/downloadable-data-files.htm', 'quarterly', 'bls_qcew')),
 ('qcew_industry', ('QCEW county and industry employment', '', 'Bureau of Labor Statistics, QCEW', 'https://www.bls.gov/cew/downloadable-data-files.htm', 'quarterly', 'bls_qcew')),
 ('state_industry_releases', ('State payrolls by industry, as first published', 'ALNA ... WYNA', 'Bureau of Labor Statistics, State Employment and Unemployment release', 'https://www.bls.gov/sae/', 'monthly', 'bls_state')),
 ('state_payroll_releases', ('State payrolls, as first published 1994-2007', 'ALNA ... WYNA', 'Bureau of Labor Statistics, State Employment and Unemployment release', 'https://www.bls.gov/sae/', 'monthly', 'bls_state')),
 ('laus_county.txt', ('County unemployment rates and labor force, 3,143 counties (BLS flat file)', '', 'Bureau of Labor Statistics, LAUS', 'https://download.bls.gov/pub/time.series/la/', 'monthly', 'bls_metro')),
 ('county_ur_lf', ('County unemployment rates and labor force, 3,143 counties (held base file; each stress-map run merges the newest BLS county file over it)', '', 'Bureau of Labor Statistics, LAUS', 'https://www.bls.gov/lau/', 'monthly', 'bls_metro')),
 ('ces_all.txt', ('National payrolls by supersector', 'PAYEMS, USMINE, USCONS, MANEMP, USTPU, USINFO, USFIRE, USPBS, USEHS, USLAH, USSERV, USGOVT', 'Bureau of Labor Statistics, CES', 'https://download.bls.gov/pub/time.series/ce/', 'monthly', 'fred:50')),
 ('state_metro_payrolls_all', ('State payrolls by supersector', '', 'Bureau of Labor Statistics, CES State and Metro', 'https://download.bls.gov/pub/time.series/sm/', 'monthly', 'bls_state')),
 ('cb_2024_us_county', ('County boundaries, 2024', '', 'Census Bureau, cartographic boundary files', 'https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html', 'static', 'static')),
 ('state_shapes_cb2024', ('State boundaries, 2024 (drawn from the Census file)', '', 'Census Bureau, cartographic boundary files', 'https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html', 'static', 'static')),
 ('spi_state_monthly_benchmarked_1167', ('State production index, 50 States (mining, manufacturing and utilities; 2017 = 100)', 'ALMFGN ... WYMFGN, ALNRMNN ... WYNRMNN, IPMAN, IPMINE, IPUTIL', 'Bristow-Hall (collection 1167), from BLS State payrolls, the Federal Reserve G.17 and BEA real output', '/state-onset/', 'monthly', 'derived_state')),   # 1167j (27 Nov 2026): the State grade's production dimension (c2f1d5e3)
 ('BH-STATE-CHRONOLOGY-V4', ('Bristow-Hall State chronology v4', '', 'Bristow-Hall (collection 1032)', '/state-onset/', 'monthly', 'derived_state')),
 ('damage_line_v4', ('Bristow-Hall State damage line v4', '', 'Bristow-Hall (collection 1032)', '/state-onset/', 'monthly', 'derived_state')),
 ('out_v3_2_damage_cut/chronology.csv', ('National disturbance register v3.2', 'PAYEMS, INDPRO, W875RX1, CMRMTSPL, UNRATE, GDPC1', 'Bristow-Hall (Disturbance Indicator)', '/disturbance/', 'monthly', 'inputs')),
 ('bhs_state', ('Live recession chronology (the detector)', '', 'Bristow-Hall (the detector)', '/detector/', 'daily', 'derived_detector')),
 ('claims13_R_612', ('Initial claims, 13-week feed, by release day', 'ICSA', 'Department of Labor, weekly claims release', FR + 'ICSA', 'weekly')),
 ('gap_612', ('Unemployment gap feed, by release day', 'UNRATE', 'Bureau of Labor Statistics, Employment Situation', FR + 'UNRATE', 'monthly')),
 ('michez_612', ('Michaillat-Saez feed, by release day', 'UNRATE, JTSJOL', 'Bureau of Labor Statistics, Employment Situation and JOLTS', FR + 'JTSJOL', 'monthly')),
 ('sp500_612', ('S&P 500 daily close', 'SP500', 'S&P Dow Jones Indices (via FRED SP500)', FR + 'SP500', 'daily')),
 ('doorlists.json', ('V3.76 door lists (frozen)', 'V376_LAB, V376_P, V376_Y', 'Bristow-Hall (collection 736)', '/shadow/', 'static')),
]

LAST_N = [0]
def refresher(p):
    """how the file is refreshed, from where it lives (the job that writes that folder)"""
    if os.environ.get('LT_RUNNER') == 'github':   # 15 Nov 2026 (1052): these tools now run on GitHub Actions (.github/workflows/live-tools.yml), not the Mac
        if '191_standing_collector' in p: return 'each live-tools run on GitHub: BLS API v2 (add-only below a 5-year window)'
        if '/612_' in p: return 'each live-tools run on GitHub: 824 feed refresher (add-only) + live_union_823'
        if any(k in p for k in ('coincident-revised', 'fred_state_ur', 'fred_state_payrolls', 'county_tot', '/dol/ar5')): return 'each live-tools run on GitHub: publisher fetch (held file kept, dated copy)'
        if 'qcew_industry_county' in p: return 'each live-tools run on GitHub: BLS QCEW open data, newest quarter added (add-only, code/qcew_county_ind_refresh_1150.py)'
        if any(k in p for k in ('BH-STATE-CHRONOLOGY-V4', 'damage_line_v4')): return 'each live-tools run on GitHub: rebuilt (1032 routine step 2)'
        if 'data/spi/' in p: return 'each live-tools run on GitHub: inputs from the BLS and FRED, the index rebuilt when they change (ops/live_tools/spi_refresh_1167.py)'
    if '191_standing_collector' in p: return 'continuous: Mac launchd collector191new'
    if '/612_' in p: return 'release days: Mac 612 feeds + launchd liveunion823'
    if 'bhs_state' in p: return 'each cloud run (a Mac copy of the published state)'
    if p.endswith('.zip') or 'state_shapes_cb2024' in p or 'doorlists.json' in p: return 'never (static)'
    if 'state_nan' in p or 'FH_state_claims' in p or 'payroll_releases_1994_2007' in p: return 'never (history layer)'
    return 'manual: Mac rebuild of the tool'
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
def _qcew_county_ind(fs):   # 1164: the newest month with a county total (ownership 0, industry 10) in the newest year file (gz, fips,own,ind,year,qtr,m1,m2,m3,disc)
    best = ''
    with gzip.open(sorted(fs)[-1], 'rt', newline='') as h:
        for ln in h:
            x = ln.rstrip('\n').split(',')
            if len(x) < 8 or x[1] != '0' or x[2] != '10': continue
            for i in (1, 2, 3):
                try:
                    if float(x[4 + i] or 0) > 0: best = max(best, '%s-%02d' % (x[3], 3 * (int(x[4]) - 1) + i))
                except ValueError: pass
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
    ref = _mtime(fs); LAST_N[0] = len(fs)
    try:
        if path.endswith('.zip') or 'state_shapes_cb2024' in path: return 'static (2024 boundaries)', ref
        if path.endswith('.xls'):
            import pandas as pd; X = pd.read_excel(fs[0], sheet_name='Indexes'); return str(pd.to_datetime(X.iloc[:, 0], errors='coerce').max().date())[:7], ref
        if 'qcew_industry_county' in path: return _qcew_county_ind(fs), ref
        if 'county_tot' in path: return _qcew_county(fs), ref
        if path.endswith('.txt.gz'): return _bls_flat(fs[0], 'CES0000000001' if 'ces_all' in path else 'LAUCN060370000000003' if 'laus_county' in path else 'SMS06000000000000001'), ref
        if 'BH-STATE-CHRONOLOGY-V4' in path:   # 15 Nov 2026 (1052 audit): the chronology is built through its damage line's month - the stress map reads that month (V4L['through'])
            return json.load(open(os.path.join(os.path.dirname(fs[0]), 'damage_line_v4_a198_1032.json')))['through'], ref
        if 'damage_line_v4' in path and path.endswith('.json'):   # 1166 (23 Nov 2026): the line's own month (its 'through'), as the row's value says; the newest date
            return json.load(open(fs[0]))['through'], ref               # in the file was a State unemployment month (Oct 2026), so the row read "Oct 31" beside "Sep 2026"
        if 'bhs_state' in os.path.basename(path) and path.endswith('.json'): return str(json.load(open(fs[0])).get('built_at', ''))[:16], ref
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
    # 1164 (22 Nov 2026; open item of RECORD-1150): the county view's jobs by industry are read by code/stress_map_detail_1150.py (its QD), not by
    # stress_map_v2_1052.py, so the row comes from that script's own module-level paths, evaluated the same way
    py2 = os.path.join(C52, 'code/stress_map_detail_1150.py')
    if os.path.exists(py2):
        G2 = dict(os=os, sys=sys, __file__=py2)
        for n in ast.parse(open(py2).read()).body:
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('C', 'ROOT', 'QD') for t in n.targets):
                try: exec(compile(ast.Module([n], []), py2, 'exec'), G2)
                except Exception: pass
        if 'QD' in G2: rows.append(('qcew_industry_county', os.path.join(G2['QD'], '<YEAR>.csv.gz')))
    return rows, 'INPUTS of 1052 code/stress_map_v2_1052.py (v1 and v3 read the same files) and the folder code/stress_map_detail_1150.py reads'
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
        rows.append(('door:' + d, (L['doors'][d][-1] if L['doors'][d] else ''), L.get('run', ''), len(L['doors'][d])))
    rows.append(('doorlists.json', glob.glob(ROOT + '/736_*/specs/doorlists.json')[0]))
    return rows, '823 out/live_state_823.json (run %s): its feeds and doors' % L.get('run', '')

def build():
    tools = {}; unknown = []
    for tool, fn in (('stress-map', stress_map_inputs), ('state-onset', state_onset_inputs)):   # 15 Nov 2026 11:00 PT: no shadow rows on the data page (Anthony)
        rows, frm = fn(); out = []
        for r in rows:
            if r[0].startswith('door:'):
                d = r[0][5:]
                out.append(dict(key=r[0], name='First-print door ' + d + ' (its last call)', ids=d, source='Bristow-Hall (736 door library, rebuilt from the shadow feeds by 823)', url='/shadow/', freq='daily', through=r[1][:10] or 'no call', refreshed=r[2][:16].replace('+00:00', 'Z'), path='',
                                held='%d calls' % r[3], refresh='release days: Mac launchd liveunion823'))
                continue
            k, p = r; m = meta(p) or meta(k)
            LAST_N[0] = 0; th, rf = latest(p, k)
            if m and (m[1].startswith('derived') or 'out_v3_2_damage_cut' in p) and p.endswith('.csv') and os.path.exists(p): th = _maxdate_text(open(p, errors='replace').read())   # a register: the newest month it carries, not its first column (1052: the v3.2 register's payroll_latest_month)
            if not m: unknown.append((tool, k, p)); m = (k + ' (not classified)', k, 'not classified', '', '')
            if any(o['name'] == m[0] for o in out): continue   # two literals of the tool's code naming the same files (e.g. a folder and a pattern in it)
            if m[4] == 'static' and not th: th = 'static'
            pat = p.replace('<ST>', '*').replace('<YEAR>', '*')
            fs = sorted(glob.glob(pat)) if '*' in pat else ([os.path.join(pat, x) for x in sorted(os.listdir(pat)) if not x.startswith('.')] if os.path.isdir(pat) else ([pat] if os.path.exists(pat) else []))
            try: hv = HV.held(p, fs)
            except Exception as e: hv = None; print('HELD VALUE NOT READ:', m[0], repr(e)[:120])
            if not hv: unknown.append((tool, k, 'no held value read'))
            out.append(dict(key=k, name=m[0], ids=m[1], source=m[2], url=m[3], freq=m[4], release=(m[5] if len(m) > 5 else ''), through=th, refreshed=rf, path=p.replace(HOME, '~'),
                            held=hv, refresh=refresher(p)))
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
