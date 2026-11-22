#!/usr/bin/env python3
"""1052 NATIONAL STRESS MAP V2 (doc/PREREG-1052-national-stress-map-v2-register-bands-exact-state--2026-11-15.md) + Anthony's requests of 15 Nov 03:54-04:04 PT.
One command rebuilds everything:   python3 code/stress_map_v2_1052.py --all
  1. re-runs code/stress_map_v1_1052.py unchanged (State layer = v1: State chronology v4 from 1979-07, L0 before; v1 tests rerun) and keeps its page as
     web/stress-map/index_v1.html; the v2 State layer is read from that page's data block, so it is v1's byte for byte (colours exactly v4's through v4's last month);
  2. county outlines: Census cartographic boundary file cb_2024_us_county_500k (Sandisk G), simplified to SVG per State (own Albers projection per State);
  3. county layer C0: the v4 code path (run_v4, sa_log, colour functions taken from the v1 script's source, unchanged) on each county:
       index = QCEW county total covered employment, monthly levels (1032 data/qcew_industry/<year>_county_tot.csv), seasonally adjusted as v1;
       labour = county unemployment rate (BLS LAUS county, 1032 data/laus_county/county_ur_lf_1990_2026.csv.gz; not seasonally adjusted at source),
       seasonally adjusted as v1 (log; the 27 county-months with a published rate of 0.0 enter the log as 0.1, stated);
       months 1990-01 .. the latest month held in BOTH inputs. A county-month missing in either input (absent, or QCEW not disclosed: flag N or a level of 0)
       is a gap: grey for the gap, never filled. The code path runs on the county's months held in both inputs with the missing months left out (not filled);
       a county with fewer than 60 such months is grey throughout.
       Renamed counties are one county (QCEW 02270 -> 02158 Kusilvak, 46113 -> 46102 Oglala Lakota; LAUS already uses the new codes).
  4. industry panels: nation = CES payroll jobs by supersector, seasonally adjusted, current vintage (191 warehouse bls_flat_files/ces_all.txt.gz, the whole-country
     CES file); State = BLS State payrolls by supersector, seasonally adjusted (191 warehouse bls_flat_files/state_metro_payrolls_all.txt.gz, the whole SM file).
     Colour = 12-month percent change at the month on the map's scale, fixed cut points -3, -1, 0, +1, +3 percent.
  5. bands: national register v3.2 (Disturbance Indicator Data/10_chronology_site/out_v3_2_damage_cut/chronology.csv) drawn row by row: recession grey,
     class-1 disturbance dashed, class-2 (jobless recovery) disturbance hatched, nested; open recession to the end of the data.
  6. tests Q1-Q4 (+ v1 tests rerun) -> out/STRESS-MAP-V2-TESTS-1052.txt; the page checked in headless Chrome (hover outlines, strip geometry, clicks).
No AI: every number is computed here. Reads only; writes only the v2 outputs listed in OUTPUTS."""
import os, sys, io, re, ast, json, gzip, base64, math, struct, zipfile, shutil, subprocess, argparse, time
import numpy as np, pandas as pd
C = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.join(C, 'out'); WEB = os.path.join(C, 'web', 'stress-map')
ROOT = os.path.dirname(C); DI = os.path.expanduser('~/Projects/Disturbance Indicator Data'); D32 = os.path.join(ROOT, '1032_state_recession_indicator_all_states_dc_2026-11-09')
sys.path.insert(0, os.path.join(DI, '10_chronology_site/code')); import disturbance_chronology as dc, damage_dimensions_live_v376 as dd
sys.path.insert(0, os.path.join(C, 'code')); import payroll_prints_1161   # 1161
V1PY = os.path.join(C, 'code', 'stress_map_v1_1052.py')
# 15 Nov 2026 05:30 PT (Anthony: "ENSURE THAT EVERYTHING IS LIVE UPDATING"): the DEFAULT build is v3.1 (PREREG-1052 v3, Amendment 1: C1, C3, C4 kept, C2 withdrawn,
# pre-1979 State layer = v1's). --v2 builds v2 as before; --v3 builds the withdrawn v3 (kept for the record).
_V2 = ('--v2' in sys.argv) or os.environ.get('SM_V2') == '1'; _V3X = ('--v3' in sys.argv) or os.environ.get('SM_V3') == '1'
V31 = not _V2 and not _V3X
V3 = _V3X or V31   # the county changes C3, C4 apply in v3 and v3.1; the v1/v2 test code and bars are unchanged
if _V3X: os.environ['SM_V3'] = '1'
TAG = 'v3_1' if V31 else ('v3' if V3 else 'v2')
V3PY = os.path.join(C, 'code', 'stress_map_v3_1_1052.py' if V31 else 'stress_map_v3_1052.py')
STATE_LAYER_HTML = 'state_layer_v3_1.html' if V31 else 'state_layer_v3.html'
STATE_CSV = ('stress_map_v3_1_state_month.csv' if V31 else 'stress_map_v3_state_month.csv') if V3 else 'stress_map_v1_state_month.csv'
STATE_TESTS = ('STRESS-MAP-V3_1-STATE-TESTS-1052.txt' if V31 else 'STRESS-MAP-V3-STATE-TESTS-1052.txt') if V3 else 'STRESS-MAP-V1-TESTS-1052.txt'
# the live recession chronology: read from origin/main of bristow-hall-live (git show of the published bhs_state.json), never from a branch clone
LIVE_REPO = os.path.join(ROOT, '105_bristow_hall_system_2026-09-08', 'cloud'); LIVE_PATH = 'data/105_bristow_hall_system_2026-09-08/site/public/detector/bhs_state.json'
LIVE_COPY = os.path.join(C, 'data', 'live_chronology', 'bhs_state_origin_main.json'); LIVENOTE = {'text': 'not read'}
def refresh_live_chronology():
    """git fetch origin; git show origin/main:<LIVE_PATH> -> data/live_chronology/bhs_state_origin_main.json (read-only on the repo; the previous copy kept as .prev).
    If git fails, the last copy read from origin/main is used and that is said."""
    os.makedirs(os.path.dirname(LIVE_COPY), exist_ok=True)
    try:
        for _i in range(6):   # another git process on the same clone holds its lock for a moment: wait and retry
            if subprocess.run(['git', '-C', LIVE_REPO, 'fetch', '-q', 'origin', 'main'], capture_output=True, timeout=120).returncode == 0: break
            time.sleep(10)
        else: raise RuntimeError('git fetch failed 6 times')
        sha = subprocess.run(['git', '-C', LIVE_REPO, 'log', '-1', '--format=%h %cI', 'origin/main'], check=True, capture_output=True, text=True, timeout=30).stdout.strip()
        b = subprocess.run(['git', '-C', LIVE_REPO, 'show', 'origin/main:' + LIVE_PATH], check=True, capture_output=True, timeout=60).stdout
        assert 'nber' in json.loads(b)
        if os.path.exists(LIVE_COPY): shutil.copyfile(LIVE_COPY, LIVE_COPY + '.prev')
        open(LIVE_COPY + '.tmp', 'wb').write(b); os.replace(LIVE_COPY + '.tmp', LIVE_COPY); LIVENOTE['text'] = f"origin/main {sha} ({LIVE_PATH})"
    except Exception as e:
        assert os.path.exists(LIVE_COPY), f'live chronology: git failed ({e}) and no earlier copy'
        LIVENOTE['text'] = f"git read of origin/main failed ({type(e).__name__}); the copy read from origin/main at {time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(LIVE_COPY)))} is used"
    log('live chronology:', LIVENOTE['text'])
# county LAUS (15 Nov 2026, data-page fix): INPUTS['county_laus'] names the file actually used - the 191 standing collector's copy of
# la.data.64.County once it exists, else the held 1032 file; the held file stays the merge base (county_laus_held)
LAUS_191 = os.path.join(ROOT, '191_standing_collector_2026-09-16/warehouse/bls_flat_files/laus_county.txt.gz')
LAUS_HELD = os.path.join(D32, 'data/laus_county/county_ur_lf_1990_2026.csv.gz')
LAUS_USED = LAUS_191 if os.path.exists(LAUS_191) else LAUS_HELD
INPUTS = dict(
    v1_script=V1PY, v1_template=os.path.join(C, 'code', 'stress_map_template_1052.html'), v1_state_shapes=os.path.join(OUT, 'state_shapes_cb2024_svg_1052.json'),
    v4_chronology=os.path.join(D32, 'out/BH-STATE-CHRONOLOGY-V4-1032.csv'), v4_line=os.path.join(D32, 'out/damage_line_v4_a198_1032.json'),
    v4_index=os.path.join(D32, 'data/philly/coincident-revised.xls'), v4_state_ur=os.path.join(DI, '03_data/state/fred_state_ur/<ST>UR.csv'),
    l0_payrolls=os.path.join(ROOT, '954_state_chronology_1939_bry_boschan_2026-10-31/data/state_nan/<ST>NAN.csv'),
    l0_claims=os.path.join(ROOT, '24_bristow_rule_lab/workspace/lab/fh/FH_state_claims_nsa_log.csv'),
    register=os.path.join(DI, '10_chronology_site/out_v3_2_damage_cut/chronology.csv'),
    live_chronology=LIVE_COPY,   # 15 Nov: origin/main's published bhs_state.json (refresh_live_chronology), was the branch clone ~/bh/fix_disturbance_1114
    county_laus_fetch='https://download.bls.gov/pub/time.series/la/la.data.64.County',
    county_laus=LAUS_USED, county_laus_held=LAUS_HELD, county_qcew=os.path.join(D32, 'data/qcew_industry/<YEAR>_county_tot.csv'),
    county_shapes='/Volumes/Sandisk G/Recession Data/06 Tool 5 - National Stress Map/Map boundaries through time (Census cartographic boundary files 2010-2024)/cb_2024_us_county_500k.zip',
    ces_national=os.path.join(ROOT, '191_standing_collector_2026-09-16/warehouse/bls_flat_files/ces_all.txt.gz'),
    ces_state=os.path.join(ROOT, '191_standing_collector_2026-09-16/warehouse/bls_flat_files/state_metro_payrolls_all.txt.gz'),
    v2_template=os.path.join(C, 'code', 'stress_map_template_v2_1052.html'))
OUTPUTS = ['web/stress-map/index_v1.html (copy of the v1 page)', 'out/county_shapes_cb2024_svg_v2_1052.json', 'out/stress_map_v2_county_month.csv.gz', 'out/stress_map_v2_county_periods.csv',
           'out/stress_map_v2_industry_national.csv', 'out/stress_map_v2_industry_state.csv', 'out/stress_map_v2_hover_{MI,HI,RI}.png', 'out/stress_map_v2_click_{MI_2009-06,TX_2016-03}.png', 'out/stress_map_v2_tests_1052.json', 'out/STRESS-MAP-V2-TESTS-1052.txt', 'web/stress-map/index.html (v2)']

# ---------------- the v1 functions, taken from the v1 script's source (not retyped) -------------
_T = ast.parse(open(V1PY).read()); G1 = dict(dc=dc, dd=dd, np=np, pd=pd, math=math)
_want_f = {'run_v4', 'sa_log', 'colour_value', 'band', 'hexof', 'in_period'}; _want_a = {'CUT', 'NODMG', 'ANCH', 'mdiff', 'ym'}
for n in _T.body:
    if (isinstance(n, ast.FunctionDef) and n.name in _want_f) or (isinstance(n, ast.Assign) and all(isinstance(t, ast.Name) and t.id in _want_a for t in n.targets)):
        exec(compile(ast.Module([n], []), V1PY, 'exec'), G1)
assert _want_f | _want_a <= set(G1), (_want_f | _want_a) - set(G1)
run_v4, sa_log, colour_value, band_of, hexof, in_period, CUT, NODMG, ym = (G1[k] for k in ('run_v4', 'sa_log', 'colour_value', 'band', 'hexof', 'in_period', 'CUT', 'NODMG', 'ym'))
# 19 Nov 2026: a period starts where the State page starts it (damage_start, taken from the State-layer script's source, not retyped); used for counties below
_T3 = ast.parse(open(V3PY).read()); exec(compile(ast.Module([n for n in _T3.body if isinstance(n, ast.FunctionDef) and n.name == 'damage_start'], []), V3PY, 'exec'), G1); damage_start = G1['damage_start']
# C3 (v3 only): the same code path for counties with the floor 2/2/6 windows removed (OECD 5/5/15 windows only); built from the v1 source by one textual change
_src = ast.get_source_segment(open(V1PY).read(), [n for n in _T.body if isinstance(n, ast.FunctionDef) and n.name == 'run_v4'][0])
assert _src.count("w2, _ = dc.windows(dev, 2, 2, 6)") == 1
_G3 = dict(G1); exec(_src.replace("def run_v4(", "def run_v4_main(").replace("w2, _ = dc.windows(dev, 2, 2, 6)", "w2 = []"), _G3); run_v4_main = _G3['run_v4_main']
FIPS = {'01': 'AL', '02': 'AK', '04': 'AZ', '05': 'AR', '06': 'CA', '08': 'CO', '09': 'CT', '10': 'DE', '12': 'FL', '13': 'GA', '15': 'HI', '16': 'ID', '17': 'IL', '18': 'IN', '19': 'IA', '20': 'KS',
        '21': 'KY', '22': 'LA', '23': 'ME', '24': 'MD', '25': 'MA', '26': 'MI', '27': 'MN', '28': 'MS', '29': 'MO', '30': 'MT', '31': 'NE', '32': 'NV', '33': 'NH', '34': 'NJ', '35': 'NM', '36': 'NY',
        '37': 'NC', '38': 'ND', '39': 'OH', '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI', '45': 'SC', '46': 'SD', '47': 'TN', '48': 'TX', '49': 'UT', '50': 'VT', '51': 'VA', '53': 'WA', '54': 'WV',
        '55': 'WI', '56': 'WY'}
STF = {v: k for k, v in FIPS.items()}; STS = sorted(FIPS.values())
RENAME = {'02270': '02158', '46113': '46102'}; MINSEG = 60
CSTART = pd.Timestamp('1990-01-01')
BCODE = {'deep red': 'D', 'red': 'r', 'orange': 'o', 'yellow': 'y', 'light green': 'l', 'green': 'g', 'grey': 'x'}
def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
def _pg(s): return re.sub(r'/(?:Users|Volumes)/[^()]*?\.(?:csv|txt|json|zip|xls)(?:\.gz)?', lambda m: os.path.basename(m.group(0)), s)   # page text: file names only, no local paths (15 Nov 2026)

# ---------------- step 1: v1 rerun (unchanged script) and its page kept as index_v1.html -------------
def step_v1(rerun=True):
    if V3:   # the v3 State layer: stress_map_v3_1052.py (v1 code with C1, C2; v1 tests unchanged) writes web/stress-map/state_layer_v3.html
        if rerun:
            log('running the v3 State layer (C1, C2) and the v1 tests on it ...')
            r = subprocess.run([sys.executable, V3PY], cwd=C, capture_output=True, text=True)
            if r.returncode: print(r.stdout[-3000:], r.stderr[-3000:]); raise SystemExit('v3 State layer failed')
        h = open(os.path.join(WEB, STATE_LAYER_HTML)).read()
        m = re.search(r'<script id="data" type="application/json">(.*?)</script>', h, re.S); return json.loads(m.group(1).replace('<\\/', '</'))
    if rerun:
        log('running v1 (State layer and v1 tests) ...')
        r = subprocess.run([sys.executable, V1PY], cwd=C, capture_output=True, text=True)
        if r.returncode: print(r.stdout[-3000:], r.stderr[-3000:]); raise SystemExit('v1 failed')
        shutil.copyfile(os.path.join(WEB, 'index.html'), os.path.join(WEB, 'index_v1.html'))
    elif not os.path.exists(os.path.join(WEB, 'index_v1.html')):
        shutil.copyfile(os.path.join(WEB, 'index.html'), os.path.join(WEB, 'index_v1.html'))
    h = open(os.path.join(WEB, 'index_v1.html')).read()
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', h, re.S); J1 = json.loads(m.group(1).replace('<\\/', '</'))
    assert 'v2' not in J1, 'index_v1.html is not a v1 page'
    return J1

# ---------------- step 2: county outlines per State -------------
def read_shp(path):
    Z = zipfile.ZipFile(path); nm = {n.rsplit('.', 1)[-1].lower(): n for n in Z.namelist()}; shp = Z.read(nm['shp']); dbf = Z.read(nm['dbf'])
    nrec, hlen, rlen = struct.unpack('<IHH', dbf[4:12]); fields = []; o = 32
    while dbf[o] != 0x0D: fields.append((dbf[o:o + 11].split(b'\0')[0].decode(), dbf[o + 16])); o += 32
    recs = []
    for i in range(nrec):
        r = dbf[hlen + i * rlen + 1: hlen + (i + 1) * rlen]; d = {}; p = 0
        for name, ln in fields: d[name] = r[p:p + ln].decode('utf-8', 'replace').strip(); p += ln
        recs.append(d)
    shapes = []; o = 100
    while o < len(shp):
        _, clen = struct.unpack('>ii', shp[o:o + 8]); c = shp[o + 8: o + 8 + clen * 2]; o += 8 + clen * 2; t = struct.unpack('<i', c[:4])[0]
        if t == 0: shapes.append([]); continue
        assert t == 5, t
        npart, npt = struct.unpack('<ii', c[36:44]); parts = list(struct.unpack('<%di' % npart, c[44:44 + 4 * npart])); b = 44 + 4 * npart
        pts = list(struct.iter_unpack('<dd', c[b:b + 16 * npt])); parts.append(npt); shapes.append([pts[parts[k]:parts[k + 1]] for k in range(npart)])
    assert len(shapes) == len(recs); return recs, shapes
def dp(pts, eps):
    if len(pts) < 3: return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True; stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop(); (ax, ay), (bx, by) = pts[a], pts[b]; dx, dy = bx - ax, by - ay; L = math.hypot(dx, dy); best, bi = -1, None
        for i in range(a + 1, b):
            px, py = pts[i]; d_ = abs(dy * (px - ax) - dx * (py - ay)) / L if L > 0 else math.hypot(px - ax, py - ay)
            if d_ > best: best, bi = d_, i
        if bi is not None and best > eps: keep[bi] = True; stack += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]
def ring_area(r): return abs(sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))) / 2
def step_county_shapes():
    """Albers equal-area (sphere) per State: standard parallels at 1/6 and 5/6 of the State's latitude span, origin at its centre; fitted into 960 x 600 (10 px margin);
    Douglas-Peucker at 0.35 px; rings under 0.4 square px dropped (a county never loses its largest ring). Hawaii: the eight main islands (as v1);
    Alaska: longitudes east of 180 shifted by -360 (Aleutians)."""
    recs, shapes = read_shp(INPUTS['county_shapes']); by = {}
    for d, rings in zip(recs, shapes):
        st = FIPS.get(d['STATEFP'])
        if not st or not rings: continue
        rings = [[((lon - 360 if lon > 0 else lon), lat) for lon, lat in r] for r in rings]
        if st == 'HI': rings = [r for r in rings if max(lon for lon, _ in r) > -161]
        if rings: by.setdefault(st, []).append((d['GEOID'], d['NAMELSAD'], rings))
    out = {}
    for st, L_ in sorted(by.items()):
        lons = [p[0] for _, _, R in L_ for r in R for p in r]; lats = [p[1] for _, _, R in L_ for r in R for p in r]; a, b = min(lats), max(lats)
        p1, p2, p0, l0 = map(math.radians, (a + (b - a) / 6, b - (b - a) / 6, (a + b) / 2, (min(lons) + max(lons)) / 2))
        n = (math.sin(p1) + math.sin(p2)) / 2; Cc = math.cos(p1) ** 2 + 2 * n * math.sin(p1); r0 = math.sqrt(Cc - 2 * n * math.sin(p0)) / n
        def f(lon, lat):
            r = math.sqrt(Cc - 2 * n * math.sin(math.radians(lat))) / n; t = n * (math.radians(lon) - l0); return r * math.sin(t), -(r0 - r * math.cos(t))
        P = [(g, nm, [[f(*p) for p in r] for r in R]) for g, nm, R in L_]
        xs = [x for _, _, R in P for r in R for x, _ in r]; ys = [y for _, _, R in P for r in R for _, y in r]
        s = min(940 / (max(xs) - min(xs)), 580 / (max(ys) - min(ys))); tx = 10 - min(xs) * s + (940 - (max(xs) - min(xs)) * s) / 2; ty = 10 - min(ys) * s + (580 - (max(ys) - min(ys)) * s) / 2
        cs = {}
        for g, nm, R in P:
            d_ = []; RR = [[(x * s + tx, y * s + ty) for x, y in r] for r in R]
            for r in RR:
                q = dp(r, 0.35)
                if len(q) >= 4 and ring_area(q) >= 0.4: d_.append('M' + 'L'.join('%.1f %.1f' % p for p in q[:-1]) + 'Z')
            if not d_:
                r = max(RR, key=ring_area); q = dp(r, 0.05); d_.append('M' + 'L'.join('%.1f %.1f' % p for p in q[:-1]) + 'Z')
            cs[g] = [nm, ''.join(d_)]
        out[st] = cs
    assert sorted(out) == STS
    json.dump({'source': os.path.basename(INPUTS['county_shapes']), 'viewBox': '0 0 960 600', 'states': out}, open(os.path.join(OUT, 'county_shapes_cb2024_svg_v2_1052.json'), 'w'), separators=(',', ':'))
    log('county shapes:', sum(len(v) for v in out.values()), 'counties')
    return out

# ---------------- step 3: county layer C0 -------------
def c0_county(a):
    """One county: the v4 code path on the county's months held in both inputs (a missing month is left out, not filled, and is grey); colour exactly as v1 colours a State-month.
    segs (reported only): the unbroken runs of months held in both inputs."""
    fips, e, u, t0, t1, tq = a; idx = pd.date_range(t0, t1, freq='MS'); T = len(idx)
    ok = np.isfinite(e) & (e > 0) & np.isfinite(u); okL = np.isfinite(u)
    # labour input: the county rate seasonally adjusted once over every LAUS month held (missing months left out), used both inside the v4 path and after it
    UF = np.exp(sa_log(np.log(pd.Series(np.maximum(u[okL], 0.1), index=idx[okL])))) if okL.sum() >= 36 else None
    S = ['G'] * T; GR = [np.nan] * T; DV = [np.nan] * T; DS = [np.nan] * T; CV = [np.nan] * T; BD = ['grey'] * T; PK = [''] * T; TR = [''] * T; SG = [-1] * T
    segs = []; i = 0
    while i < T:
        if not ok[i]: i += 1; continue
        j = i
        while j < T and ok[j]: j += 1
        segs.append((i, j)); i = j
    per = []; nrun = 0
    # one series per county: every month held in both inputs, a missing month left out (not filled; it stays grey); fewer than MINSEG months held -> grey throughout
    held = np.flatnonzero(ok); RUNS = [(held, 0)] if len(held) >= MINSEG else []
    for pos, si in RUNS:
        nrun += 1; ix = idx[pos]; last = ix[-1]; i = 0
        y = np.exp(sa_log(np.log(pd.Series(e[pos], index=ix)))); U = UF[ix]
        R, ln, dv = run_v4(fips, y, U, last, allow_short=True)
        opn = [r for r in R if r['status'] in ('recession', 'disturbance') and r['t'] is None]
        P = [dict(p=r['p'], t=r['t'], te=r['te'], status=r['status'], grade=round(r['g'], 2), provisional=r['provisional']) for r in R if r['status'] in ('recession', 'disturbance')]
        damage_start(P, ln)
        for q in P: per.append([fips, si, ym(q['p']), ym(q['t']) if q['t'] is not None else 'open', q['status'], q['grade'], bool(q['provisional'])])
        quiet = np.array([in_period(P, m, last) is None for m in ix]); qsd = float(pd.Series(np.asarray(dv, float))[quiet].std()) if quiet.sum() > 2 else float('nan')
        for k, m in enumerate(ix):
            q = in_period(P, m, last); g = float(ln.get(ym(m), 0.0)) if q is not None else 0.0; d = float(dv.iloc[k]); ds = d / qsd if qsd > 0 else 0.0
            s = colour_value(q is not None, g, ds); stt = q['status'] if q is not None else 'none'; n_ = int(pos[k])
            S[n_] = {'recession': 'R', 'disturbance': 'D', 'none': 'N'}[stt]; GR[n_] = round(g, 2); DV[n_] = round(d, 3); DS[n_] = round(ds, 3); CV[n_] = round(s, 3)
            BD[n_] = band_of(stt, g, s); SG[n_] = si
            if q is not None: PK[n_] = ym(q['p']); TR[n_] = ym(q['t']) if q['t'] is not None else 'open'
        # Amendment 1 (as decided 15 Nov 04:4x PT): months after the last county-jobs month, through the latest LAUS month. No period state is carried forward
        # (without county jobs no period could close). Each month is coloured fresh from the labour dimension alone: L = the national labour_score of the rise of
        # the county's (seasonally adjusted) unemployment rate that month over its lowest rate in the 12 months before it; yellow when L < 0.05 (no green side:
        # a rate below its 12-month low is not measured). Periods resume when QCEW adds the next quarter.
        after = [k for k in range(T) if idx[k] > last and idx[k] > tq and okL[k]]
        for k in after:
            m = idx[k]; pre = UF[(UF.index < m) & (UF.index >= m - pd.DateOffset(months=12))]
            if not len(pre): continue
            ex = max(0.0, float(UF[m]) - float(pre.min())); g = round(float(dd.labour_score(ex, ex)), 2)
            inp = g >= NODMG; s = colour_value(inp, g, 0.0)
            S[k] = 'U' if inp else 'V'; GR[k] = g; CV[k] = round(s, 3); BD[k] = band_of('disturbance' if inp else 'none', g, s); SG[k] = 1
    return dict(fips=fips, S=S, GR=GR, DV=DV, DS=DS, CV=CV, BD=BD, PK=PK, TR=TR, SG=SG, per=per, segs=[(ym(idx[i]), ym(idx[j - 1]), j - i) for i, j in segs], nrun=nrun)

def c0_county_v3(a):
    """v3 county: C3 (5/5/15 windows only) and C4 (a month with one input missing uses the other alone).
    Index = QCEW months held (missing months left out); labour = the LAUS months held. Month with both: as v2. Month with QCEW but no rate: inside a period the grade
    is the output dimension alone; outside, the deviation colour as v2 (it needs only jobs). Month with a rate but no QCEW (gaps and months after the last QCEW month):
    the labour-alone rule of the unemployment-only months (fresh 12-month rise each month)."""
    fips, e, u, t0, t1, tq = a; idx = pd.date_range(t0, t1, freq='MS'); T = len(idx)
    okE = np.isfinite(e) & (e > 0); okL = np.isfinite(u); ok = okE & okL
    S = ['G'] * T; GR = [np.nan] * T; DV = [np.nan] * T; DS = [np.nan] * T; CV = [np.nan] * T; BD = ['grey'] * T; PK = [''] * T; TR = [''] * T; SG = [-1] * T; DIM = [''] * T
    segs = []; i = 0
    while i < T:
        if not ok[i]: i += 1; continue
        j = i
        while j < T and ok[j]: j += 1
        segs.append((i, j)); i = j
    per = []; nrun = 0
    UF = np.exp(sa_log(np.log(pd.Series(np.maximum(u[okL], 0.1), index=idx[okL])))) if okL.sum() >= 36 else None
    posE = np.flatnonzero(okE)
    if len(posE) >= MINSEG and UF is not None:
        nrun = 1; ix = idx[posE]; last = ix[-1]
        y = np.exp(sa_log(np.log(pd.Series(e[posE], index=ix)))); Gq = y.resample('QS').mean()
        R, ln, dv = run_v4_main(fips, y, UF, last, allow_short=True)
        P = [dict(p=r['p'], t=r['t'], te=r['te'], status=r['status'], grade=round(r['g'], 2), provisional=r['provisional']) for r in R if r['status'] in ('recession', 'disturbance')]
        damage_start(P, ln)
        for q in P: per.append([fips, 0, ym(q['p']), ym(q['t']) if q['t'] is not None else 'open', q['status'], q['grade'], bool(q['provisional'])])
        quiet = np.array([in_period(P, m, last) is None for m in ix]); qsd = float(pd.Series(np.asarray(dv, float))[quiet].std()) if quiet.sum() > 2 else float('nan')
        for k, m in enumerate(ix):
            n_ = int(posE[k]); q = in_period(P, m, last); d = float(dv.iloc[k]); ds = d / qsd if qsd > 0 else 0.0
            if q is not None:
                g = float(ln.get(ym(m), 0.0)) if okL[n_] else round(float(dd.output_dimension(Gq, q['p0'], m)['score']), 2)
            else: g = 0.0
            s = colour_value(q is not None, g, ds); stt = q['status'] if q is not None else 'none'
            S[n_] = {'recession': 'R', 'disturbance': 'D', 'none': 'N'}[stt]; GR[n_] = round(g, 2); DV[n_] = round(d, 3); DS[n_] = round(ds, 3); CV[n_] = round(s, 3)
            BD[n_] = band_of(stt, g, s); SG[n_] = 0; DIM[n_] = 'both' if okL[n_] else 'jobs_only'
            if q is not None: PK[n_] = ym(q['p']); TR[n_] = ym(q['t']) if q['t'] is not None else 'open'
    if UF is not None:
        for k in range(T):
            if okE[k] and nrun or not okL[k]: continue
            m = idx[k]; pre = UF[(UF.index < m) & (UF.index >= m - pd.DateOffset(months=12))]
            if not len(pre): continue
            ex = max(0.0, float(UF[m]) - float(pre.min())); g = round(float(dd.labour_score(ex, ex)), 2); inp = g >= NODMG; s = colour_value(inp, g, 0.0)
            S[k] = 'U' if inp else 'V'; GR[k] = g; CV[k] = round(s, 3); BD[k] = band_of('disturbance' if inp else 'none', g, s); SG[k] = 1; DIM[k] = 'labour_only'
    return dict(fips=fips, S=S, GR=GR, DV=DV, DS=DS, CV=CV, BD=BD, PK=PK, TR=TR, SG=SG, DIM=DIM, per=per, segs=[(ym(idx[i]), ym(idx[j - 1]), j - i) for i, j in segs], nrun=nrun)

def load_county_inputs():
    L = pd.read_csv(INPUTS['county_laus_held'], dtype={'fips5': str}); L = L[L.fips5.str[:2].isin(FIPS)]
    F = []
    y = 1990
    while os.path.exists(INPUTS['county_qcew'].replace('<YEAR>', str(y))):
        d = pd.read_csv(INPUTS['county_qcew'].replace('<YEAR>', str(y)), header=None, dtype={0: str, 7: str}, names=['fips', 'own', 'ind', 'y', 'q', 'mq', 'e', 'disc'])
        assert set(d.own) == {0} and set(d.ind) == {'tot'}; F.append(d); y += 1
    Q = pd.concat(F); Q = Q[Q.fips.str[:2].isin(FIPS)].copy()
    Q['month'] = Q.y.astype(str) + '-' + ((Q.q - 1) * 3 + Q.mq).astype(str).str.zfill(2)
    Q['valid'] = (Q.disc.fillna('') != 'N') & (Q.e > 0)
    Q['renamed'] = Q.fips.isin(list(RENAME)).astype(int); Q['fips'] = Q.fips.replace(RENAME)
    Q = Q.sort_values(['fips', 'month', 'renamed']).drop_duplicates(['fips', 'month'], keep='first')
    return L, Q, y - 1

# Amendment 5 (PREREG-1052 v3; Anthony 15 Nov 12:05 PT "check the counties as well"): no county is grey in a month shown.
# (1) a county BLS publishes only inside another area takes that area's series; (2) an area before it existed takes the series of the area it was part of (the
# predecessor's own figures, months before the county's own series begins, each input separately); (3) a gap inside a county's unemployment-rate or labour-force
# series is filled by straight-line interpolation between the months on each side. Every filled cell is marked (source area or 'interpolated').
BORROW = [('15005', '15009', 'Kalawao <- Maui (BLS publishes Kalawao inside Maui)'), ('02063', '02261', 'Chugach <- Valdez-Cordova'), ('02066', '02261', 'Copper River <- Valdez-Cordova'),
          ('02195', '02280', 'Petersburg <- Wrangell-Petersburg'), ('02275', '02280', 'Wrangell <- Wrangell-Petersburg'), ('02198', '02201', 'Prince of Wales-Hyder <- Prince of Wales-Outer Ketchikan'),
          ('02105', '02232', 'Hoonah-Angoon <- Skagway-Hoonah-Angoon'), ('02230', '02232', 'Skagway <- Skagway-Hoonah-Angoon'), ('02282', '02231', 'Yakutat <- Skagway-Yakutat-Angoon')]
AMEND5 = {}
def amend5_fill(Lp, Lf, Qv, mapf_fips):
    FILL = {}; notes = []; missing = []
    for D in (Lp, Lf, Qv):
        for g in mapf_fips:
            if g not in D.index: D.loc[g] = np.nan
    for tgt, src, nm in BORROW:
        got = []
        for lab, D in (('rate', Lp), ('labour force', Lf), ('jobs (QCEW)', Qv)):
            if src not in D.index or not D.loc[src].notna().any(): missing.append(f'{nm}: no {lab} series for {src} held'); continue
            row = D.loc[tgt]; first = row.first_valid_index(); cols = [c for c in D.columns if (first is None or c < first) and pd.isna(row[c]) and pd.notna(D.loc[src, c])]
            for c in cols: D.loc[tgt, c] = D.loc[src, c]; FILL[(tgt, c)] = 'from ' + src
            if cols: got.append(f'{lab} {cols[0]}..{cols[-1]}')
        if got: notes.append(f"{nm} ({src}): " + '; '.join(got))
    for lab, D in (('rate', Lp), ('labour force', Lf)):
        for g in mapf_fips:
            row = D.loc[g]; fil = row.astype(float).interpolate(limit_area='inside'); new = [c for c in D.columns if pd.isna(row[c]) and pd.notna(fil[c])]
            if new:
                D.loc[g, new] = fil[new].values
                for c in new: FILL.setdefault((g, c), 'interpolated')
    interp = sorted({(g, c) for (g, c), v in FILL.items() if v == 'interpolated'})
    by_m = {}
    for g, c in interp: by_m.setdefault(c, []).append(g)
    if interp: notes.append('interpolated between neighbouring months: ' + '; '.join(f"{c} ({len(v)} counties: {', '.join(v[:9])}{'...' if len(v) > 9 else ''})" for c, v in sorted(by_m.items())))
    AMEND5.update(filled=len(FILL), notes=notes, missing=missing)
    log('Amendment 5:', len(FILL), 'cells filled;', '; '.join(notes)[:600], '| missing predecessor series:', missing)
    return FILL, '; '.join(notes) + (('. Not held (no figures to borrow): ' + '; '.join(missing)) if missing else '')

def step_counties(CSH, procs, L_override=None):
    L, Q, qy = load_county_inputs()
    if L_override is not None: L = L_override
    lastL = L.month.max(); lastQ = Q[Q.valid].month.max(); LASTC = pd.Timestamp(lastL + '-01')   # Amendment 1: counties run to the latest LAUS month
    idx = pd.date_range(CSTART, LASTC, freq='MS'); K = [ym(m) for m in idx]; T = len(idx)
    mapf = {g: (st, v[0]) for st, cs in CSH.items() for g, v in cs.items()}
    Lp = L.pivot(index='fips5', columns='month', values='ur').reindex(columns=K); Lf = L.pivot(index='fips5', columns='month', values='lf').reindex(columns=K); Qv = Q[Q.valid].pivot(index='fips', columns='month', values='e').reindex(columns=K)
    FILL, fillnote = amend5_fill(Lp, Lf, Qv, sorted(mapf))
    args = [(g, Qv.loc[g].values.astype(float) if g in Qv.index else np.full(T, np.nan), Lp.loc[g].values.astype(float) if g in Lp.index else np.full(T, np.nan), CSTART, LASTC, pd.Timestamp(lastQ + '-01')) for g in sorted(mapf)]
    log(f'county C0: {len(args)} map counties, months {K[0]}..{K[-1]} (LAUS through {lastL}, QCEW through {lastQ}); {procs} processes')
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(procs) as ex: RES = list(ex.map(c0_county_v3 if V3 else c0_county, args, chunksize=16))
    # Amendment 5 rule (4): the county timeline starts at the first month in which every county can be coloured (display: earlier months are not shown)
    k0 = next((k for k in range(T) if all(r['BD'][k] != 'grey' for r in RES)), 0); trimmed = K[:k0]
    if k0:
        for r in RES:
            for f_ in ('S', 'GR', 'DV', 'DS', 'CV', 'BD', 'PK', 'TR', 'SG', 'DIM'): r[f_] = r[f_][k0:]
        K = K[k0:]; T = len(K); Lp = Lp[K]; Lf = Lf[K]; Qv = Qv[K]
    log(f'Amendment 5: county timeline starts {K[0]} (months before it not shown: {len(trimmed)}); filled cells {len(FILL)}; grey county-months left',
        sum(1 for r in RES for b in r['BD'] if b == 'grey'))
    info = dict(LASTC=ym(LASTC), lastL=lastL, lastQ=lastQ, months=K, fillnote=fillnote, fill_n=len(FILL), timeline_start=K[0], months_not_shown=trimmed, laus_zero=int((L.ur <= 0).sum()),
                data_not_on_map=sorted((set(Lp.index) | set(Qv.index)) - set(mapf)), qcew_suppressed=int((~Q.valid).sum()))
    rows = []
    for r in RES:
        st, nm = mapf[r['fips']]; e = Qv.loc[r['fips']].values if r['fips'] in Qv.index else np.full(T, np.nan); u = Lp.loc[r['fips']].values if r['fips'] in Lp.index else np.full(T, np.nan)
        rows.append(pd.DataFrame(dict(fips=r['fips'], st=st, county=nm, month=K, segment=r['SG'], period_status=[{'R': 'recession', 'D': 'disturbance', 'N': 'none', 'G': 'no_data', 'U': 'labour_damage', 'V': 'labour_none'}[s] for s in r['S']],
                                      dimensions=r['DIM'] if 'DIM' in r else ['both' if mm <= lastQ else 'labour_only' for mm in K],
                                      period_peak=r['PK'], period_trough=r['TR'], grade=r['GR'], deviation_pp=r['DV'], deviation_sd=r['DS'], colour_value=r['CV'], band=r['BD'],
                                      colour_hex=[hexof(v) if np.isfinite(v) else '#d5d9de' for v in r['CV']], qcew_employment=e, laus_ur=u, laus_lf=Lf.loc[r['fips']].values if r['fips'] in Lf.index else np.full(T, np.nan), filled=[FILL.get((r['fips'], mm), '') for mm in K])))
    CM = pd.concat(rows, ignore_index=True)
    CM.to_csv(os.path.join(OUT, 'stress_map_' + TAG + '_county_month.csv.gz'), index=False, compression='gzip')
    PER = pd.DataFrame([p for r in RES for p in r['per']], columns=['fips', 'segment', 'peak', 'trough', 'status', 'grade', 'provisional'])
    PER['st'] = PER.fips.map(lambda g: mapf[g][0]); PER.to_csv(os.path.join(OUT, 'stress_map_' + TAG + '_county_periods.csv'), index=False)
    info['segs'] = {r['fips']: r['segs'] for r in RES}; info['nrun'] = {r['fips']: r['nrun'] for r in RES}
    log('county layer written:', len(CM), 'county-months')
    return CM, PER, info

# ---------------- county unemployment refresh (Amendment 1) -------------
LAUSNOTE = {'text': 'not fetched'}; JOINED = {}
LAUS_DIR = os.path.join(C, 'data', 'laus_county_bls')
def step_fetch_laus():
    """Fetch the whole-country LAUS county file from BLS through _shared/fastfetch.py (who='1052') on every run. On success the fetched rates and labour
    forces replace the held ones month by month (held months the file lacks are kept); on a refusal the held file is used and the refusal is reported."""
    sys.path.insert(0, os.path.join(ROOT, '_shared')); import fastfetch
    UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
    url = INPUTS['county_laus_fetch']; b = None; src = None
    try:
        import sqlite3; row = sqlite3.connect(os.path.join(ROOT, '_shared', 'collector_ledger.sqlite')).execute(
            "select owner,state,at,path from t where k=?", ('url:' + url.split('://', 1)[1],)).fetchone()
    except Exception: row = None
    # 15 Nov 2026 (task: "read the newest copy the 191 collector has saved if its claim is done, else the held file"): no fetch of our own (BLS answers this
    # Mac's browser string with 403). The 191 standing collector fetches la.data.64.County into its BLS flat-file warehouse (added 15 Nov, checked daily).
    cands = []
    if row and row[1] == 'done' and row[3] and os.path.exists(row[3]): cands.append((os.path.getmtime(row[3]), row[3], f"{row[0]}'s saved copy (ledger: done)"))
    if os.path.exists(LAUS_191): cands.append((os.path.getmtime(LAUS_191), LAUS_191, "the 191 standing collector's saved copy"))
    if not cands:
        LAUSNOTE['text'] = f"no saved copy of {url} from the 191 collector yet; the held file is used ({INPUTS['county_laus_held']})"; log(LAUSNOTE['text']); return None
    mt, pth, who_ = max(cands); b = open(pth, 'rb').read()
    if pth.endswith('.gz'): b = gzip.decompress(b)
    src = f"read from {who_} {pth} (saved {time.strftime('%Y-%m-%d %H:%M', time.localtime(mt))}; not fetched)"
    try:
        if b is not None: raise StopIteration

        b = fastfetch.fetch_job(url, who='1052', fresh_days=0, timeout=170, headers={'User-Agent': UA})
    except StopIteration: pass
    except Exception as e:
        msg = f"{type(e).__name__}: {getattr(e, 'code', '')} {e}".strip()
        if row: msg += f" [ledger: {row[0]} {row[1]} since {time.strftime('%Y-%m-%d %H:%M', time.localtime(row[2]))}, no saved copy]"
        LAUSNOTE['text'] = f"BLS refused the fetch of {url} on {time.strftime('%Y-%m-%d %H:%M')} ({msg[:160]}); the held file is used ({INPUTS['county_laus_held']})"
        log('LAUS county fetch failed:', msg[:200]); return None
    if src is None:
        os.makedirs(LAUS_DIR, exist_ok=True); open(os.path.join(LAUS_DIR, 'la.data.64.County'), 'wb').write(b); src = f"fetched from BLS {time.strftime('%Y-%m-%d %H:%M')}, saved {os.path.join(LAUS_DIR, 'la.data.64.County')}"
    rows = []
    for line in b.decode('latin-1').splitlines()[1:]:
        q = line.split('\t')
        if len(q) < 4: continue
        sid = q[0].strip(); per = q[2].strip()
        if not sid.startswith('LAUCN') or per == 'M13' or sid[-2:] not in ('03', '06'): continue
        try: v = float(q[3].strip())
        except ValueError: continue
        rows.append((sid[5:10], f"{q[1].strip()}-{per[1:]}", sid[-2:], v))
    F = pd.DataFrame(rows, columns=['fips5', 'month', 'm', 'v']).pivot_table(index=['fips5', 'month'], columns='m', values='v', aggfunc='first').reset_index()
    F = F.rename(columns={'03': 'ur', '06': 'lf'}); F = F[F.fips5.str[:2].isin(FIPS)]
    H = pd.read_csv(INPUTS['county_laus_held'], dtype={'fips5': str}); H = H[H.fips5.str[:2].isin(FIPS)]
    M_ = pd.concat([F[['fips5', 'month', 'ur', 'lf']].assign(src=0), H[['fips5', 'month', 'ur', 'lf']].assign(src=1)]).sort_values(['fips5', 'month', 'src']).drop_duplicates(['fips5', 'month'])
    LAUSNOTE['text'] = f"{src} ({len(b)} bytes, {F.month.min()}..{F.month.max()}, {F.fips5.nunique()} counties), merged over the held file (held through {H.month.max()})"
    return M_.drop(columns='src')
def gap_months(cov):
    """Months missing from an input for the whole country (every county grey). The cause is named only where it is known."""
    KNOWN = {'2025-10': 'not surveyed by BLS (federal shutdown)'}
    return {m: KNOWN.get(m, 'no published county input this month') for m in cov['months_grey_everywhere']}

# ---------------- step 4: industry panels -------------
SUPER = [('00', 'Total nonfarm'), ('10', 'Mining and logging'), ('20', 'Construction'), ('15', 'Mining, logging and construction'), ('30', 'Manufacturing'),
         ('40', 'Trade, transportation and utilities'), ('50', 'Information'), ('55', 'Financial activities'), ('60', 'Professional and business services'),
         ('65', 'Education and health services'), ('70', 'Leisure and hospitality'), ('80', 'Other services'), ('90', 'Government')]
def ind_s(p):
    """12-month percent change -> the map's colour value. Fixed cut points (prereg): -3, -1, 0, +1, +3 percent -> red (-3), orange (-2), yellow (0), light green (+1),
    deep green (+2); linear between; above +3 deep green; below -3 the red deepens to deep red at -6 (display shading only)."""
    if p is None or not np.isfinite(p): return float('nan')
    if p <= -3: return max(-4.0, -3.0 + (p + 3.0) / 3.0)
    if p >= 3: return 2.0
    return float(np.interp(p, [-3, -1, 0, 1, 3], [-3, -2, 0, 1, 2]))
def ind_band(p):
    if not np.isfinite(p): return 'grey'
    return 'red' if p <= -3 else ('orange' if p <= -1 else ('yellow' if p < 1 else ('light green' if p < 3 else 'green')))
def read_bls_flat(path, keep):
    rows = []
    with gzip.open(path, 'rt') as f:
        next(f)
        for line in f:
            sid = line[:line.index('\t')].strip()
            if not keep(sid): continue
            p = line.rstrip('\n').split('\t'); per = p[2].strip()
            if per == 'M13': continue
            v = p[3].strip(); rows.append((sid, int(p[1]), int(per[1:]), float(v) if v not in ('', '-') else np.nan, p[4].strip() if len(p) > 4 else ''))
    D = pd.DataFrame(rows, columns=['series_id', 'year', 'm', 'level', 'footnote']); D['month'] = D.year.astype(str) + '-' + D.m.astype(str).str.zfill(2)
    return D.drop(columns=['year', 'm'])
def pct12(D):
    D = D.sort_values(['series_id', 'month']).copy(); D['t'] = pd.to_datetime(D.month + '-01')
    prev = D.assign(t=D.t + pd.DateOffset(years=1))[['series_id', 't', 'level']].rename(columns={'level': 'level_12m_before'})
    D = D.merge(prev, on=['series_id', 't'], how='left'); D['pct12'] = (D.level / D.level_12m_before - 1) * 100
    D['colour_value'] = D.pct12.map(ind_s); D['band'] = D.pct12.map(ind_band); return D.drop(columns=['t'])
def step_industry():
    NAT = {f'CES{c}00000001': (c, n) for c, n in SUPER if c != '15'}
    N = read_bls_flat(INPUTS['ces_national'], lambda s: s in NAT); N['code'] = N.series_id.map(lambda s: NAT[s][0]); N['supersector'] = N.series_id.map(lambda s: NAT[s][1])
    N = pct12(N); N.to_csv(os.path.join(OUT, 'stress_map_' + TAG + '_industry_national.csv'), index=False)
    SM = {f'SMS{STF[st]}00000{c}00000001': (st, c, n) for st in STS for c, n in SUPER}
    S = read_bls_flat(INPUTS['ces_state'], lambda s: s in SM)
    S['st'] = S.series_id.map(lambda s: SM[s][0]); S['code'] = S.series_id.map(lambda s: SM[s][1]); S['supersector'] = S.series_id.map(lambda s: SM[s][2])
    S = pct12(S); S.to_csv(os.path.join(OUT, 'stress_map_' + TAG + '_industry_state.csv'), index=False)
    log('industry: national', N.month.min(), '..', N.month.max(), '; State', S.month.min(), '..', S.month.max())
    return N, S

# ---------------- step 5: register bands -------------
KIND = {'recession': 'R', 'disturbance_class1': 'D1', 'disturbance_class2': 'D2'}
MSN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
def mlab(k): return MSN[int(k[5:7]) - 1] + ' ' + k[:4]
def step_bands():
    """Strip bands (Anthony 15 Nov 04:34 PT): RECESSIONS = the live site's national chronology (the 'nber' list of the live Recession Indicator's
    bhs_state.json; rows from 2024 on are the program's own dating, drawn hatched as on the live page: kind RB); DISTURBANCES = the register v3.2 rows
    with status disturbance_class1 or disturbance_class2 (dashed). The register's recession rows are not drawn (State and county colours unchanged)."""
    NB = json.load(open(INPUTS['live_chronology']))['nber']; B = []
    for r in NB:
        k = 'R' if r['peak'] < '2024' else 'RB'; tr = r.get('trough') or None
        nm = 'Recession (NBER dates)' if k == 'R' else 'Recession dated by the program (hatched, as on the live Recession Indicator)'
        B.append([k, r['peak'], tr, None, f"{nm}: {mlab(r['peak'])} to {mlab(tr)}" if tr else f"{nm}: from {mlab(r['peak'])}, open", False])
    NR = pd.read_csv(INPUTS['register']); bad = set(NR.status) - set(KIND); assert not bad, bad
    for r in NR.itertuples():
        if r.status == 'recession': continue
        tr = r.trough if isinstance(r.trough, str) else None; k = KIND[r.status]
        nm = {'D1': 'Disturbance (class 1)', 'D2': 'Jobless-recovery disturbance (class 2)'}[k]
        B.append([k, r.peak, tr, round(float(r.grade), 2), f"{nm}: {mlab(r.peak)} to {mlab(tr)}, grade {r.grade:.2f}" if tr else f"{nm}: from {mlab(r.peak)}, open (running grade {r.grade:.2f})", bool(r.provisional)])
    return B
def register_months(B, months):
    """month -> set of band kinds covering it (the month after the peak through the trough month, the NBER's months of contraction, as on the
    Time Machine; 1163, 22 Nov 2026; an open period runs to the last month shown)."""
    out = {m: set() for m in months}
    for k, p, t, *_ in B:
        for m in months:
            if p < m and (t is None or m <= t): out[m].add(k)
    return out

# ---------------- step 6: tests -------------
def _q1(CM, a, b, wcol, inset, label):
    S = pd.read_csv(os.path.join(OUT, STATE_CSV)); S = S[(S.month >= a) & (S.month <= b)]
    S['s_in'] = S.period_status.isin(['recession', 'disturbance'])
    c = CM[(CM.month >= a) & (CM.month <= b) & ~CM.period_status.isin(['no_data'])].copy(); c['inp'] = c.period_status.isin(inset); c['w'] = c[wcol]; c = c[c.w.notna()]; c['wi'] = c.w * c.inp
    g = c.groupby(['st', 'month'])[['wi', 'w']].sum().reset_index(); g['share'] = g.wi / g.w
    m = S[['st', 'month', 's_in']].merge(g, on=['st', 'month'], how='left'); held = m[m.share.notna()].copy(); held['c_in'] = held.share >= 0.5; held['agree'] = held.c_in == held.s_in
    if not len(held): return None, f"{label} {a}..{b}: no State-month with county data and a State value", {}
    r = float(held.agree.mean()); fs = float(held.s_in.mean()); fc = float(held.c_in.mean()); per = held.groupby('st').agree.mean().sort_values()
    corr = float(held.share.corr(held.s_in.astype(float))) if held.share.nunique() > 1 and held.s_in.nunique() > 1 else float('nan')
    txt = (f"{label} {a}..{b}: State-months with county data {len(held)} of {len(m)} (none: {', '.join(sorted(set(m.st) - set(held.st))) or 'none'}). "
           f"Agreement {r:.3f} ({int(held.agree.sum())} of {len(held)}); bar 0.75. In a period: State map {fs:.3f}, county majority {fc:.3f}; chance {fs * fc + (1 - fs) * (1 - fc):.3f}; "
           f"correlation {corr:.3f}. Lowest States: " + ', '.join(f"{k} {v:.2f}" for k, v in per.head(5).items()) + '; highest: ' + ', '.join(f"{k} {v:.2f}" for k, v in per.tail(3).items()))
    return r, txt, dict(agreement=r, n=len(held), per_state={k: round(float(v), 3) for k, v in per.items()})
def test_q1(CM, lastQ, lastS):
    """A State-month agrees when (weighted share of its counties in a period >= 0.5) equals (the State map has the State in a period).
    Both-input months (1990-01..last county-jobs month): weights = county QCEW employment, in a period = recession or disturbance (the prereg's Q1).
    Unemployment-only months (Amendment 1; after the last jobs month, through the last month both the State map and LAUS hold): weights = county labour force
    (LAUS), in a period = a continuing recession or disturbance or labour damage (grade >= 0.05)."""
    a = _q1(CM, '1990-01', lastQ, 'qcew_employment', ['recession', 'disturbance'], 'Both-input months')
    nxt = ym(pd.Timestamp(lastQ + '-01') + pd.DateOffset(months=1))
    b = _q1(CM, nxt, lastS, 'laus_lf', ['labour_damage'], 'Unemployment-only months (reported separately, Amendment 1; county in a period = labour damage grade >= 0.05)')
    txt = "A State-month agrees when (weighted share of its counties in a period >= 0.5) equals (the State map has the State in a period). " + a[1] + ' || ' + b[1]
    return (a[0] is not None and a[0] >= 0.75), txt, dict(both=a[2], labour_only=b[2])
Q2EP = [('Orleans Parish LA', '22071', '2005-09', '2005-09'), ('Wayne MI', '26163', '2008-01', '2009-12'), ('Genesee MI', '26049', '2008-01', '2009-12'),
        ('Williams ND', '38105', '2015-01', '2016-12'), ('McKenzie ND', '38053', '2015-01', '2016-12'), ('Elkhart IN', '18039', '2008-01', '2009-12'),
        ('Clark NV (Las Vegas)', '32003', '2008-01', '2010-12'), ('San Francisco CA', '06075', '2001-01', '2002-12'), ('Harris TX', '48201', '2015-01', '2016-12')]
def test_q2(CM):
    ok = True; L_ = []
    for nm, f, a, b in Q2EP:
        x = CM[(CM.fips == f) & (CM.month >= a) & (CM.month <= b)]; ro = x.band.isin(['red', 'deep red', 'orange']); good = bool(ro.any()); ok &= good
        red = int(x.band.isin(['red', 'deep red']).sum()); grey = int((x.band == 'grey').sum())
        L_.append(f"  {nm} {f} [{a}..{b}]: {'yes' if good else 'NO'} (red/orange {int(ro.sum())}/{len(x)} months, red {red}, grey {grey}, highest grade {pd.to_numeric(x.grade, errors='coerce').max():.2f}"
                  + (f"; bands {', '.join(x.band)}" if len(x) <= 3 else '') + ')')
    x = CM[(CM.fips == '22071') & (CM.month >= '2005-01') & (CM.month <= '2006-12')]
    L_.append(f"  (information, not the test) Orleans Parish 2005-01..2006-12: months grey {int((x.band == 'grey').sum())} ({', '.join(x[x.band == 'grey'].month.iloc[[0, -1]]) if (x.band == 'grey').any() else '-'}); "
              f"red/orange {int(x.band.isin(['red', 'deep red', 'orange']).sum())}; bands Jan-Aug 2005: {''.join(BCODE[v] for v in x.band.iloc[:8])}")
    L_.append("  Harris TX 1986: n/a (the county layer begins 1990-01), as the prereg states")
    return ok, 'named county episodes red or orange (at least one month red, deep red or orange in the window; same rule as v1 P6)\n' + '\n'.join(L_)
def test_q4(N):
    def at(m):
        x = N[(N.month == m) & (N.code != '00')].set_index('code'); return x
    a = at('2009-06'); b = at('2020-04')
    ok_a = a.loc['30', 'band'] == 'red' and a.loc['20', 'band'] == 'red'; mn = b.pct12.idxmin(); ok_b = mn == '70'
    txt = (f"2009-06: manufacturing {a.loc['30', 'pct12']:+.1f}% ({a.loc['30', 'band']}), construction {a.loc['20', 'pct12']:+.1f}% ({a.loc['20', 'band']}) -> {'yes' if ok_a else 'NO'}; "
           f"2020-04: lowest 12-month change {b.loc[mn, 'supersector']} {b.loc[mn, 'pct12']:+.1f}% (next: " + ', '.join(f"{b.loc[k, 'supersector']} {b.loc[k, 'pct12']:+.1f}%" for k in b.pct12.sort_values().index[1:3]) + f") -> {'yes' if ok_b else 'NO'}")
    return ok_a and ok_b, txt
def drill_summary(CM, PER, S, J1, st, month):
    x = CM[(CM.st == st) & (CM.month == month)]; cnt = x.band.value_counts().to_dict()
    i = (int(month[:4]) * 12 + int(month[5:7]) - 1) - (int(J1['start'][:4]) * 12 + int(J1['start'][5:7]) - 1); sb = {v: k for k, v in BCODE.items()}[J1['states'][st]['b'][i]]
    w = x[x.period_status.isin(['recession', 'disturbance'])].copy(); w['g'] = pd.to_numeric(w.grade); w = w.sort_values('g', ascending=False)
    ind = S[(S.st == st) & (S.month == month)].sort_values('code')
    return (f"{J1['names'][st]} at {month}: State colour (v1/v4) {sb}, grade {J1['states'][st]['g'][i] / 100:.2f}. Counties {len(x)}: " + ', '.join(f"{k} {cnt.get(k, 0)}" for k in ['deep red', 'red', 'orange', 'yellow', 'light green', 'green', 'grey'])
            + f"; in a period {len(w)} (recession {int((w.period_status == 'recession').sum())}, disturbance {int((w.period_status == 'disturbance').sum())}); highest running grades: "
            + ', '.join(f"{r.county} {r.g:.2f}" for r in w.head(5).itertuples())
            + '. Industry (12-month change): ' + ', '.join(f"{r.supersector} {r.pct12:+.1f}%" for r in ind.itertuples() if np.isfinite(r.pct12)))

# ---------------- step 7: the page -------------
def i10(v): return None if v is None or not np.isfinite(v) else int(round(v * 10))
def cidx(v): return -1 if not np.isfinite(v) else int(round((v + 4) / 0.05))
def ind_block(D, months):
    codes = [c for c, _ in SUPER if c in set(D.code)]; P = D.pivot(index='month', columns='code', values='pct12').reindex(months); Lv = D.pivot(index='month', columns='code', values='level').reindex(months)
    lm = D[D.level.notna()].month.max(); lat = D[D.month == lm].set_index('code')
    return dict(codes=codes, pct={c: [i10(v) for v in P[c].values] for c in codes}, lvl={c: [i10(v) for v in Lv[c].values] for c in codes},
                latest=dict(month=lm, pct={c: i10(lat.loc[c, 'pct12']) if c in lat.index else None for c in codes}, lvl={c: i10(lat.loc[c, 'level']) if c in lat.index else None for c in codes},
                            prelim=sorted(set(D[D.footnote.str.contains('P', na=False)].month))))
BRIT = [('colours', 'colors'), ('Colours', 'Colors'), ('coloured', 'colored'), ('Coloured', 'Colored'), ('colouring', 'coloring'), ('colour', 'color'), ('Colour', 'Color'),
        ('greys', 'grays'), ('grey', 'gray'), ('Grey', 'Gray'), ('labour', 'labor'), ('Labour', 'Labor'), ('centred', 'centered'), ('centre', 'center'), ('Centre', 'Center'),
        ('programme', 'program'), ('behaviour', 'behavior'), ('favour', 'favor'), ('analyse', 'analyze'), ('seasonalis', 'seasonaliz'), ('modelled', 'modeled'), ('per cent', 'percent')]
def amer(t):
    for a, b in BRIT: t = t.replace(a, b)
    return t
SHORT = ['']
def depth_nation(J1):
    """Nation line: mean of the 50 States' running damage grade each month (grade 0 outside periods), weighted by State payroll jobs (the v1 input,
    954 data/state_nan, thousands, not seasonally adjusted); a State without payroll data that month is left out."""
    months = pd.date_range(J1['start'] + '-01', periods=J1['n'], freq='MS'); num = np.zeros(len(months)); den = np.zeros(len(months))
    for st in J1['states']:
        w = pd.read_csv(INPUTS['l0_payrolls'].replace('<ST>', st), index_col=0, parse_dates=True).iloc[:, 0]; w = pd.to_numeric(w, errors='coerce'); w = payroll_prints_1161.extend(st, w.dropna()) if w.dropna().index[0] > months[0] else w   # 1161: the weight of the months printed before the BLS series begins
        w0 = w
        pv = (J1.get('prov') or {}).get('first')   # provisional months (PREREG v3 Amendments 2-3): the State's last payroll weight carried forward; grade 0 outside an open period, as in v4 months
        w = np.array((w.reindex(w.index.union(months)).ffill().reindex(months) if pv else w.reindex(months)).values, dtype=float)
        if pv: w[np.array([m < pd.Timestamp(pv + '-01') for m in months]) & ~np.isfinite(w0.reindex(months).values)] = np.nan
        g = np.array(J1['states'][st]['g'], float) / 100
        if pv: g = np.where(np.array([c in 'RD' for c in J1['states'][st]['s']]) | (np.arange(len(months)) < len(months) - len(J1['prov']['months'])), g, 0.0)
        ok = np.isfinite(w) & np.array([c != 'G' for c in J1['states'][st]['s']])
        num[ok] += w[ok] * g[ok]; den[ok] += w[ok]
    return list(num / den)
def b64gz(obj): return base64.b64encode(gzip.compress(json.dumps(obj, separators=(',', ':')).encode(), 9, mtime=0)).decode()
def step_page(J1, CSH, CM, PER, N, S, B, info, TESTS2, DESC2, gapm):
    nat_months = [ym(m) for m in pd.date_range(J1['start'] + '-01', J1['last'] + '-01', freq='MS')]; assert len(nat_months) == J1['n']
    K = info['months']; T = len(K); ST = {}; sizes = {}
    for st in STS:
        x = CM[CM.st == st]; order = sorted(CSH[st], key=lambda g: CSH[st][g][0])
        gb = {g: d for g, d in x.groupby('fips')}
        delta = lambda L_: [L_[0]] + [b - a for a, b in zip(L_, L_[1:])]   # stored as month-to-month differences (undone in the page) so the blob compresses
        c = {g: delta([cidx(v) for v in gb[g].colour_value.values]) for g in order}; s = {g: ''.join({'recession': 'R', 'disturbance': 'D', 'none': 'N', 'no_data': 'G', 'labour_damage': 'U', 'labour_none': 'V'}[v] for v in gb[g].period_status) for g in order}
        # v: the running grade x 100 inside a period, the deviation in quiet-record SDs x 100 outside one, 0 when grey
        vv = {g: delta([int(round(gr_ * 100)) if st_ in ('recession', 'disturbance', 'labour_damage') else (int(round(ds_ * 100)) if st_ == 'none' else 0)
                        for st_, gr_, ds_ in zip(gb[g].period_status, gb[g].grade.values, gb[g].deviation_sd.values)]) for g in order}
        bd = {g: ''.join(BCODE[v] for v in gb[g].band) for g in order}
        P = PER[PER.st == st]; per = {g: [[r.peak, r.trough, r.status, r.grade, bool(r.provisional)] for r in d.itertuples()] for g, d in P.groupby('fips')}
        # depth line: labor-force-weighted mean of the counties' running grade (0 outside periods; unemployment-only months: their labor grade); gray counties left out
        xx = x[(x.band != 'grey') & x.laus_lf.notna()].copy(); xx['gg'] = np.where(xx.period_status.isin(['recession', 'disturbance', 'labour_damage']), xx.grade, 0.0)
        xx['wg'] = xx.gg * xx.laus_lf; agg = xx.groupby('month')[['wg', 'laus_lf']].sum(); red = (agg.wg / agg.laus_lf).reindex(K)
        # the line is computed for every month; a month with no county value anywhere in the State is joined by a straight segment (display only)
        miss = [k for k, v in zip(K, red.values) if not np.isfinite(v)]
        if red.notna().sum() >= 2:
            inner = red.interpolate(limit_area='inside'); JOINED[st] = [k for k, v0, v1 in zip(K, red.values, inner.values) if not np.isfinite(v0) and np.isfinite(v1)]; red = inner
        else: JOINED[st] = 'no county value in any month' if red.notna().sum() == 0 else miss
        obj = dict(order=order, shapes=CSH[st], c=c, s=s, v=vv, b=bd, per=per, red=[None if not np.isfinite(v) else int(round(v * 100)) for v in red.values],
                   segs={g: info['segs'][g] for g in order}, ind=ind_block(S[S.st == st], K))
        ST[st] = b64gz(obj); sizes[st] = len(ST[st])
    J = dict(J1)   # the v1 data block; its State colours are untouched. Display text only: v1's description goes to the collapsed Method section (American spelling),
    J['desc'] = amer(re.sub(r'<p><b>Bands on the timeline</b>.*?</p>', '', J1['desc']).replace('County drill-down (click a State to see its counties) is not part of version 1. ', ''))
    J.pop('tests', None)   # no tests on the page (Anthony 04:58 PT); they stay in the tests file and json
    DN = depth_nation(J1); J['red'] = [int(round(v * 100)) for v in DN]   # nation line: payroll-weighted mean State running grade x 100
    J['v2'] = dict(bands=B, cstart=K[0], cn=T, clast=K[-1], cqlast=info['lastQ'], gapm=gapm, lausnote=_pg(LAUSNOTE['text']), fillnote=info.get('fillnote', ''), ctrim=info.get('months_not_shown', []), built=pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d'),
                   thru=dict(state=J1.get('last_v4', J1['last']), state_prov=((J1.get('prov') or {}).get('last')), county=info['LASTC'], county_laus=info['lastL'], county_qcew=info['lastQ'], ind_nat=N[N.level.notna()].month.max(), ind_st=S[S.level.notna()].month.max()),
                   ind_names=dict(SUPER), ind_nat=ind_block(N, nat_months), st=ST, desc=amer(DESC2), short=amer(SHORT[0]))
    tpl = open(INPUTS['v2_template']).read(); assert tpl.count('__DATA__') == 1
    html = tpl.replace('__DATA__', json.dumps(J, separators=(',', ':')).replace('</', '<\\/'))
    assert not re.search(r'(src|href)\s*=\s*["\']?https?://|url\(\s*["\']?https?:|@import|fetch\(|XMLHttpRequest', html)   # self-contained: works from disk
    open(os.path.join(WEB, 'index.html'), 'w').write(html); log('wrote', os.path.join(WEB, 'index.html'), len(html.encode()), 'bytes')
    return len(html.encode()), sizes

# ---------------- step 8: headless Chrome checks (own temporary profile; the program's CDP Chrome on 9333 is not touched) -------------
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
FINDPT = """(sel)=>{const el=document.querySelector(sel); if(!el) return null; el.scrollIntoView({block:'center'}); const r=el.getBoundingClientRect();
 for(let n=6;n<=60;n+=6){for(let i=1;i<n;i++)for(let j=1;j<n;j++){const x=r.left+r.width*i/n,y=r.top+r.height*j/n; if(document.elementFromPoint(x,y)===el) return [x,y];}} return null;}"""
HLSTATE = """(sel)=>{const svg=document.getElementById('map'), hl=document.getElementById('hl'), el=document.querySelector(sel); const p=hl?hl.querySelector('path'):null;
 if(!p) return {outline:false, hl_children: hl?hl.children.length:-1};
 const cs=getComputedStyle(p); return {outline:true, top: svg.lastElementChild===hl, same_d: p.getAttribute('d')===el.getAttribute('d'), rings:(p.getAttribute('d').match(/M/g)||[]).length,
 rings_shape:(el.getAttribute('d').match(/M/g)||[]).length, stroke:cs.stroke, width:cs.strokeWidth, vector:cs.vectorEffect||p.getAttribute('vector-effect'), fill:cs.fill, hl_children:hl.children.length};}"""
STRIPGEOM = """()=>{const W=window.__SM.geom.W,L=window.__SM.geom.L,R=window.__SM.geom.R; const N=window.__SM.view().n; return Array.from(document.querySelectorAll('#strip [data-k]')).map(r=>{const x=+r.getAttribute('x'), w=+r.getAttribute('width');
 return [r.getAttribute('data-k'), Math.round((x-L)/(W-L-R)*N), Math.round((x+w-L)/(W-L-R)*N)-1];});}"""
DRAWN = ('R', 'RB', 'D1', 'D2')   # every register row is drawn (Anthony 04:32 PT: class 2 drawn as a dashed disturbance band like class 1)
def strip_check(geom, B, months):
    reg = register_months([b for b in B if b[0] in DRAWN], months); drawn = {m: set() for m in months}
    for k, a, b in geom:
        for i in range(max(0, a), min(len(months) - 1, b) + 1): drawn[months[i]].add(k)
    bad = [m for m in months if drawn[m] != reg[m]]
    return bad, sum(1 for m in months if reg[m])
def step_browser(B, J1, info):
    from playwright.sync_api import sync_playwright
    R = {}; url = 'file://' + os.path.join(WEB, 'index.html')
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=CHROME, headless=True); pg = br.new_page(viewport={'width': 1500, 'height': 1100}); errs = []
        pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None); pg.on('pageerror', lambda e: errs.append(str(e)))
        t0 = time.time(); pg.goto(url, wait_until='load'); pg.wait_for_function('window.__SM && window.__SM.ready'); R['load_s'] = round(time.time() - t0, 2)
        R['nav_ms'] = pg.evaluate("()=>{const e=performance.getEntriesByType('navigation')[0]; return {dom:Math.round(e.domContentLoadedEventEnd), load:Math.round(e.loadEventEnd)}}")
        nat_months = [ym(m) for m in pd.date_range(J1['start'] + '-01', J1['last'] + '-01', freq='MS')]
        bad, nb = strip_check(pg.evaluate(STRIPGEOM), B, nat_months); R['strip_nation'] = dict(months=len(nat_months), banded=nb, mismatched=bad[:20], n_bad=len(bad))
        R['thru_text'] = pg.inner_text('#thru')
        # floating elements: the set of visible absolutely/fixed positioned elements must not change while hovering the strip or the map
        POS = "()=>Array.from(document.querySelectorAll('body *')).filter(e=>{const c=getComputedStyle(e);return (c.position==='absolute'||c.position==='fixed')&&c.display!=='none'&&c.visibility!=='hidden'&&e.getClientRects().length>0}).map(e=>(e.id||e.className||e.tagName)+':'+(e.textContent||'').slice(0,20)).join('|')"
        SINFO = "()=>{const s=document.getElementById('strip'); const d2=Array.from(s.querySelectorAll('[data-k=D2]')); return {d2_rects:d2.length, d2_style:d2.map(r=>[r.getAttribute('fill'),r.getAttribute('fill-opacity'),r.getAttribute('stroke-dasharray')]), patterns:s.querySelectorAll('pattern').length, titles:s.querySelectorAll('title').length, texts:Array.from(s.querySelectorAll('text')).map(x=>x.textContent).filter(x=>!/^\\d{4}$/.test(x)), tooltip_divs:document.querySelectorAll('.tip,#tip,#stip').length, binfo:document.getElementById('binfo').innerText}}"
        pg.evaluate("()=>window.__SM.setMonth('2002-12')"); pg.evaluate("()=>document.getElementById('strip').scrollIntoView({block:'center'})"); pg.mouse.move(2, 2); pg.wait_for_timeout(80)
        base_pos = pg.evaluate(POS); G_ = pg.evaluate("()=>window.__SM.geom")
        bx = pg.evaluate("()=>{const r=document.getElementById('strip').getBoundingClientRect();return [r.left,r.top,r.width,r.height]}")
        i22 = (2002 - int(J1['start'][:4])) * 12 + 11 - (int(J1['start'][5:7]) - 1) + 0.5
        xm = bx[0] + bx[2] * (G_['L'] + i22 / J1['n'] * (G_['W'] - G_['L'] - G_['R'])) / G_['W']
        pg.mouse.move(xm, bx[1] + bx[3] * 0.3); pg.wait_for_timeout(150); over = pg.evaluate(SINFO); over['positioned_changed'] = pg.evaluate(POS) != base_pos
        pg.screenshot(path=os.path.join(OUT, 'stress_map_' + TAG + '_strip_2002-12_over.png'), clip=dict(x=0, y=max(0, bx[1] - 60), width=1500, height=bx[3] + 150))
        pg.mouse.move(bx[0] + bx[2] / 2, bx[1] - 120); pg.wait_for_timeout(150); away = pg.evaluate(SINFO); away['positioned_changed'] = pg.evaluate(POS) != base_pos
        pg.screenshot(path=os.path.join(OUT, 'stress_map_' + TAG + '_strip_2002-12_away.png'), clip=dict(x=0, y=max(0, bx[1] - 60), width=1500, height=bx[3] + 150))
        R['strip_2002_12'] = dict(over=over, away=away)
        # map hover: no floating element appears (info goes to the side panel)
        pt = pg.evaluate(FINDPT, '#map path[data-id="TX"]'); pg.mouse.move(*pt); pg.wait_for_timeout(100)
        R['map_hover_floating'] = dict(positioned_changed=pg.evaluate(POS) != base_pos, side_panel=pg.inner_text('#pick')[:160]); pg.mouse.move(2, 2)
        # lines: one continuous path in every view; axis labels inside the strip at the narrowest and the default widths
        LINEM = "()=>{const p=document.querySelector('#strip path[data-line]');if(!p)return {path:false};const d=p.getAttribute('d');return {path:true,M:(d.match(/M/g)||[]).length,points:(d.match(/[ML]/g)||[]).length,n:window.__SM.view().n}}"
        AXIS = "()=>{const s=document.getElementById('strip').getBoundingClientRect();const L_=Array.from(document.querySelectorAll('#strip text')).map(t=>{const r=t.getBoundingClientRect();return [t.textContent,r.left>=s.left-0.5&&r.right<=s.right+0.5]});const m=document.getElementById('mlabel').getBoundingClientRect(),tl=document.querySelector('.tl').getBoundingClientRect();return {labels:L_.map(x=>x[0]),clipped:L_.filter(x=>!x[1]).map(x=>x[0]),readout:document.getElementById('mlabel').innerText,readout_inside:m.left>=tl.left&&m.right<=tl.right}}"
        R['lines'] = {}; R['axis'] = {}
        for w in (760, 1500):
            pg.set_viewport_size({'width': w, 'height': 1100}); pg.wait_for_timeout(100)
            for vv in ['US', 'MI', 'TX', 'CA', 'HI']:
                if vv == 'US': pg.evaluate("()=>window.__SM.view().mode==='state'&&window.__SM.closeState()")
                else: pg.evaluate(f"()=>window.__SM.openState('{vv}')"); pg.wait_for_function(f"()=>window.__SM.view().st==='{vv}'")
                pg.wait_for_timeout(60); R['axis'][f'{vv}@{w}'] = pg.evaluate(AXIS)
                if w == 1500: R['lines'][vv] = pg.evaluate(LINEM)
            pg.evaluate("()=>window.__SM.closeState()")
        pg.set_viewport_size({'width': 1500, 'height': 1100})
        # the not-surveyed month in a State view: the note above the map and the line under the slider
        gm = sorted(json.loads(pg.evaluate("()=>JSON.stringify(Object.keys(window.__SM.gapm||{}))")))
        if gm:
            pg.evaluate("()=>window.__SM.openState('MI')"); pg.wait_for_function("()=>window.__SM.view().st==='MI'"); pg.evaluate(f"()=>window.__SM.setMonth('{gm[0]}')")
            R['gap_month'] = dict(month=gm[0], note=pg.inner_text('#mapnote'), binfo=pg.inner_text('#binfo'), side_head=pg.inner_text('#shh')); pg.evaluate("()=>window.__SM.closeState()")
        # Back button: open Michigan from the top of the page (no scrolling), the button is in the first screen; click returns to the nation at the same month; Escape too
        pg.evaluate("()=>{window.scrollTo(0,0);window.__SM.setMonth('2009-06')}"); pt = pg.evaluate(FINDPT.replace("el.scrollIntoView({block:'center'}); ", ''), '#map path[data-id="MI"]')
        bk = {}
        if pt: pg.mouse.click(*pt)
        else: pg.evaluate("()=>window.__SM.openState('MI')")
        pg.wait_for_function("()=>window.__SM.view().mode==='state'"); pg.wait_for_timeout(100)
        bk['opened_by'] = 'click' if pt else 'openState (Michigan not in the first screen)'
        bk['button'] = pg.evaluate("()=>{const b=document.getElementById('back'),r=b.getBoundingClientRect(),m=document.getElementById('map').getBoundingClientRect();return {text:b.innerText,visible:getComputedStyle(b).display!=='none'&&r.width>0,top:Math.round(r.top),bottom:Math.round(r.bottom),left:Math.round(r.left),viewport_h:innerHeight,scrollY:scrollY,in_first_screen:r.top>=0&&r.bottom<=innerHeight&&scrollY===0,above_map:r.bottom<=m.top+1,map_left:Math.round(m.left),cls:b.className}}")
        pg.screenshot(path=os.path.join(OUT, 'stress_map_' + TAG + '_back_button_MI.png'))
        pg.click('#back'); pg.wait_for_function("()=>window.__SM.view().mode==='nation'")
        bk['after_click'] = pg.evaluate("()=>({mode:window.__SM.view().mode,paths:document.querySelectorAll('#layer path').length,month:document.getElementById('mlabel').innerText,button_hidden:getComputedStyle(document.getElementById('back')).display==='none'})")
        pg.evaluate("()=>window.__SM.openState('MI')"); pg.wait_for_function("()=>window.__SM.view().mode==='state'"); pg.keyboard.press('Escape'); pg.wait_for_function("()=>window.__SM.view().mode==='nation'")
        bk['after_escape'] = pg.evaluate("()=>({mode:window.__SM.view().mode,paths:document.querySelectorAll('#layer path').length,month:document.getElementById('mlabel').innerText})")
        R['back_button'] = bk
        for st in ['MI', 'HI', 'RI']:
            sel = f'#map path[data-id="{st}"]'; pt = pg.evaluate(FINDPT, sel); pg.mouse.move(*pt); pg.wait_for_timeout(80); a = pg.evaluate(HLSTATE, sel)
            box = pg.evaluate("(s)=>{const r=document.querySelector(s).getBoundingClientRect();return [r.left,r.top,r.width,r.height]}", sel)
            pg.screenshot(path=os.path.join(OUT, f'stress_map_{TAG}_hover_{st}.png'), clip=dict(x=max(0, box[0] - 30), y=max(0, box[1] - 30), width=box[2] + 60, height=box[3] + 60))
            pg.mouse.move(2, 2); pg.wait_for_timeout(80); b_ = pg.evaluate(HLSTATE, sel); R['hover_' + st] = dict(over=a, after_out=b_, point=[round(v) for v in pt])
        for st, mo, cf in [('MI', '2009-06', '26163'), ('TX', '2016-03', '48201')]:
            pg.evaluate(f"()=>window.__SM.setMonth('{mo}')"); pt = pg.evaluate(FINDPT, f'#map path[data-id="{st}"]'); pg.mouse.click(*pt)
            pg.wait_for_function(f"()=>window.__SM.view().mode==='state' && window.__SM.view().st==='{st}'"); pg.wait_for_timeout(150)
            v = pg.evaluate("()=>window.__SM.view()"); pg.evaluate(f"()=>window.__SM.setMonth('{mo}')"); pg.wait_for_timeout(100)
            cm = [ym(m) for m in pd.date_range(v['start'] + '-01', periods=v['n'], freq='MS')]; bad, nb = strip_check(pg.evaluate(STRIPGEOM), B, cm)
            sel = f'#map path[data-id="{cf}"]'; pt2 = pg.evaluate(FINDPT, sel); pg.mouse.move(*pt2); pg.wait_for_timeout(80); hc = pg.evaluate(HLSTATE, sel); pg.mouse.move(2, 2); pg.wait_for_timeout(60)
            hc2 = pg.evaluate(HLSTATE, sel)
            pg.screenshot(path=os.path.join(OUT, f'stress_map_{TAG}_click_{st}_{mo}.png'), full_page=False)
            R['click_' + st] = dict(view=v, month_label=pg.inner_text('#mlabel'), side=pg.inner_text('#shares'), side_head=pg.inner_text('#shh'), state_line=pg.inner_text('#stline'),
                                    industry=pg.inner_text('#indtab'), ind_head=pg.inner_text('#indh'), strip=dict(months=len(cm), banded=nb, n_bad=len(bad), mismatched=bad[:10]),
                                    county_hover=hc, county_after_out=hc2, ncounty_paths=pg.evaluate("()=>document.querySelectorAll('#layer path').length"))
            pg.click('#back'); pg.wait_for_function("()=>window.__SM.view().mode==='nation'"); R['back_' + st] = dict(mode=pg.evaluate("()=>window.__SM.view().mode"), state_paths=pg.evaluate("()=>document.querySelectorAll('#layer path').length"), month=pg.inner_text('#mlabel'))
        pg.evaluate("()=>window.__SM.setMonth('2009-06')"); R['nat_industry_2009_06'] = pg.inner_text('#indtab')
        R['status_line'] = {}
        for mo in ('2026-07', '2009-06'):
            pg.evaluate("()=>window.__SM.view().mode==='state'&&window.__SM.closeState()"); pg.evaluate(f"()=>window.__SM.setMonth('{mo}')"); R['status_line'][f'US {mo}'] = pg.inner_text('#binfo')
            pg.evaluate("()=>window.__SM.openState('ME')"); pg.wait_for_function("()=>window.__SM.view().st==='ME'"); pg.evaluate(f"()=>window.__SM.setMonth('{mo}')")
            R['status_line'][f'ME {mo}'] = dict(under_slider=pg.inner_text('#binfo'), side_panel=pg.inner_text('#stline')); pg.evaluate("()=>window.__SM.closeState()")
        # every State at both months, checked against the State chronology v4 files (periods table and line), and the nation counts
        V4T = pd.read_csv(INPUTS['v4_chronology']); V4L = json.load(open(INPUTS['v4_line'])); lastv4 = V4L['through']
        def expect(st, mo):
            rows = V4T[(V4T.st == st) & V4T.status.isin(['recession', 'disturbance'])]
            ln = dict(V4L['states'][st]['line'])
            for r in rows.itertuples():   # 19 Nov 2026: a period starts where the State page starts it (the month after max(peak, first damage month - 1))
                te = r.trough if isinstance(r.trough, str) else lastv4
                on = [str(x) for x in pd.period_range(r.peak, te, freq='M') if (ln.get(str(x)) or 0) >= NODMG]
                s = min(te, str(pd.Period(max(r.peak, str(pd.Period(on[0], 'M') - 1)) if on else r.peak, 'M') + 1))
                if s <= mo <= te: return r.status, s, float(ln.get(mo, 0.0))
            return 'none', None, None
        chk = dict(states_checked=0, mismatches=[], nation={})
        for mo in ('2026-07', '2009-06'):
            pg.evaluate("()=>window.__SM.view().mode==='state'&&window.__SM.closeState()"); pg.evaluate(f"()=>window.__SM.setMonth('{mo}')"); nat = pg.inner_text('#binfo')
            ex = [expect(st, mo)[0] for st in sorted(J1['names'])]; nr, nd = ex.count('recession'), ex.count('disturbance')
            want = f"{nr} States in a recession, {nd} in a disturbance"; chk['nation'][mo] = dict(line=nat, expected=want, ok=want in nat)
            for st in sorted(J1['names']):
                pg.evaluate(f"()=>window.__SM.openState('{st}')"); pg.wait_for_function(f"()=>window.__SM.view().st==='{st}'"); pg.evaluate(f"()=>window.__SM.setMonth('{mo}')")
                ln, sp = pg.inner_text('#binfo'), pg.inner_text('#stline'); stt, pk, g = expect(st, mo); nm = J1['names'][st]
                if stt == 'none': w = 'in no recession or disturbance'
                else: w = f"in a {stt} since {mlab(pk)} (State chronology v4, running grade {g:.2f})"
                ok = ln.startswith(f"{nm}, {mlab(mo)}") and w in ln and sp.startswith(f"{nm}, {mlab(mo)}") and w in sp
                chk['states_checked'] += 1
                if not ok: chk['mismatches'].append(dict(st=st, month=mo, expected=w, line=ln[:200], side=sp[:200]))
                pg.evaluate("()=>window.__SM.closeState()")
        R['status_all'] = chk
        # cursor line and slider knob share one x-scale: centre x of each, at four months, three widths, nation and Michigan
        al = {}
        for w in (760, 1200, 1500):
            pg.set_viewport_size({'width': w, 'height': 1100}); pg.wait_for_timeout(80)
            for vv in ('US', 'MI'):
                if vv == 'MI': pg.evaluate("()=>window.__SM.openState('MI')"); pg.wait_for_function("()=>window.__SM.view().st==='MI'")
                v = pg.evaluate("()=>window.__SM.view()"); lastm = ym(pd.Timestamp(v['start'] + '-01') + pd.DateOffset(months=v['n'] - 1))
                for mo in (('1948-01' if vv == 'US' else '1990-01'), '2001-11', '2020-04', lastm):
                    pg.evaluate(f"()=>window.__SM.setMonth('{mo}')"); x = pg.evaluate("()=>window.__SM.align()"); al[f'{vv}@{w} {mo}'] = round(x['knob'] - x['line'], 3)
                if vv == 'MI': pg.evaluate("()=>window.__SM.closeState()")
        pg.set_viewport_size({'width': 1500, 'height': 1100}); R['knob_align'] = al
        TXT = "()=>{const d=document.querySelector('details.method'); if(d) d.open=true; const c=document.body.cloneNode(true); c.querySelectorAll('script').forEach(x=>x.remove()); const t=c.textContent+' '+document.title; if(d) d.open=false; return t;}"
        txt = {}
        pg.evaluate("()=>window.__SM.view().mode==='state'&&window.__SM.closeState()"); txt['nation'] = pg.evaluate(TXT)
        for st in ('MI', 'TX'):
            pg.evaluate(f"()=>window.__SM.openState('{st}')"); pg.wait_for_function(f"()=>window.__SM.view().st==='{st}'"); pg.evaluate("()=>window.__SM.setMonth('2026-07')")
            pt = pg.evaluate(FINDPT, '#map path[data-id]'); pg.mouse.move(*pt); pg.wait_for_timeout(60); txt[st] = pg.evaluate(TXT); pg.mouse.move(2, 2); pg.evaluate("()=>window.__SM.closeState()")
        R['text_check'] = {k: dict(british=sorted(set(m.lower() for m in re.findall(r'colou?r\w*(?<=colou\w)|\b\w*colour\w*|\bgrey\w*|\blabour\w*|\bcentre\w*|\bprogramme\w*|\bbehaviour\w*|\bfavour\w*|\banalys\w*', v, re.I))),
                                       tests=sorted(set(re.findall(r'\bPASS\b|\bFAIL\b|\bQ[1-4]\b|\bP[1-7]\b', v))), chars=len(v)) for k, v in txt.items()}
        R['console_errors'] = errs; br.close()
    return R

# ---------------- main -------------
def coverage(CM, info):
    g = CM.groupby('fips'); hasd = g.band.apply(lambda b: (b != 'grey').sum()); T = len(info['months'])
    allgrey = sorted(hasd[hasd == 0].index); full = int((hasd == T).sum()); part = sorted(hasd[(hasd > 0) & (hasd < T)].index)
    nm = CM.drop_duplicates('fips').set_index('fips'); gm = CM.groupby('month').band.apply(lambda b: float((b == 'grey').mean()))
    return dict(months_grey_everywhere=sorted(gm[gm == 1.0].index), months_grey_over_half=sorted(gm[gm > 0.5].index), counties=int(len(hasd)), months=T, county_months=int(len(CM)), grey_share=round(float((CM.band == 'grey').mean()), 4), full=full,
                partial=len(part), allgrey=[f"{f} {nm.loc[f, 'county']} {nm.loc[f, 'st']}" for f in allgrey],
                partial_list=[f"{f} {nm.loc[f, 'county']} {nm.loc[f, 'st']}: {int(hasd[f])} of {T} months; runs {info['segs'][f]}" for f in part])
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--all', action='store_true', help='re-run v1 and rebuild everything (the one command)')
    ap.add_argument('--skip-v1', action='store_true'); ap.add_argument('--v3', action='store_true', help='the withdrawn PREREG-1052 v3 (C1-C4)'); ap.add_argument('--v2', action='store_true', help='v2 (default is v3.1)'); ap.add_argument('--no-browser', action='store_true'); ap.add_argument('--procs', type=int, default=max(2, (os.cpu_count() or 4) - 4))
    a = ap.parse_args()
    if not a.all and not a.skip_v1: ap.error('use --all (or --skip-v1 to reuse the v1 page already built)')
    log('build', TAG); refresh_live_chronology()
    miss = [k for k, v in INPUTS.items() if '<' not in v and not v.startswith('http') and not os.path.exists(v)]; assert not miss, miss
    v1_before = open(os.path.join(OUT, STATE_TESTS)).read() if os.path.exists(os.path.join(OUT, STATE_TESTS)) else ''
    J1 = step_v1(rerun=not a.skip_v1); v1_after = open(os.path.join(OUT, STATE_TESTS)).read()
    strip_ts = lambda s: [l for l in s.splitlines() if not l.startswith('STRESS MAP V1 TESTS')]
    v1_same = strip_ts(v1_before) == strip_ts(v1_after)
    CSH = step_county_shapes(); Lnew = step_fetch_laus(); CM, PER, info = step_counties(CSH, a.procs, Lnew); N, S = step_industry(); B = step_bands()
    q1 = test_q1(CM, info['lastQ'], min(J1['last'], info['LASTC'])); q2 = test_q2(CM); q4 = test_q4(N); cov = coverage(CM, info)
    REG = pd.read_csv(INPUTS['register']); nat_months = [ym(m) for m in pd.date_range(J1['start'] + '-01', J1['last'] + '-01', freq='MS')]
    NBL = json.load(open(INPUTS['live_chronology']))['nber']
    want = [['recession', r['peak'], r.get('trough') or None] for r in NBL] + [[r.status, r.peak, r.trough if isinstance(r.trough, str) else None] for r in REG.itertuples() if r.status != 'recession']
    rows_eq = want == [[('recession' if b[0] in ('R', 'RB') else {v: k for k, v in KIND.items()}[b[0]]), b[1], b[2]] for b in B]
    regm = register_months(B, nat_months)
    q3_data = f"strip rows: the live chronology's {len(NBL)} recession rows ({INPUTS['live_chronology']}, 'nber'; from 2024 hatched) and the register's {len(REG) - int((REG.status == 'recession').sum())} disturbance rows; data block equals them {'exactly' if rows_eq else 'NOT exactly'}; " \
              f"{sum(1 for m in nat_months if regm[m])} of {len(nat_months)} months {nat_months[0]}..{nat_months[-1]} lie in a register period " \
              f"(recession {sum(1 for m in nat_months if 'R' in regm[m] or 'RB' in regm[m])}, class-1 {sum(1 for m in nat_months if 'D1' in regm[m])}, class-2 {sum(1 for m in nat_months if 'D2' in regm[m])}, " \
              f"class-2 inside a recession {sum(1 for m in nat_months if 'D2' in regm[m] and ('R' in regm[m] or 'RB' in regm[m]))})"
    sh = J1.get('last_v4', J1['last']); thru = dict(state=sh, state_prov=((J1.get('prov') or {}).get('last')), county=info['LASTC'], laus=info['lastL'], qcew=info['lastQ'], ind_nat=N[N.level.notna()].month.max(), ind_st=S[S.level.notna()].month.max())
    nlat = N[N.month == thru['ind_nat']]; prel = sorted(set(N[N.footnote.str.contains('P', na=False)].month))
    d2s = [b for b in B if b[0] == 'D2']
    gapm = gap_months(cov)
    DESC2 = ''.join('<p>' + p + '</p>' for p in [
        "<b>Version 2.</b> The timeline's bands follow the program's live national chronology, read at build time: recessions are the live Recession Indicator's list "
        f"(NBER dates grey; the program's own dating from 2024 hatched, as on the live page: {'; '.join(mlab(b[1]) + ' to ' + (mlab(b[2]) if b[2] else 'open') for b in B if b[0] == 'RB')}); "
        "disturbances are the register v3.2 rows of class 1 and class 2, dashed. Each band runs from its peak month through its trough month. No text and no pop-up sit on the strip; "
        "the line under the slider names the period of the month shown. "
        + ' '.join(f"The register's class-2 (jobless-recovery) disturbance, {mlab(b[1])} to {mlab(b[2])}, is drawn dashed like the other disturbances." for b in d2s)
        + ' ' + ' '.join(b[4] + ', drawn to the end of the data.' for b in B if b[2] is None) + " Click a State to open its counties; the Back button above the county map (or Escape) returns to the United States.",
        f"<b>Click a State</b> to open it: its counties coloured by the same method and scale (county layer C0), the timeline cut to the counties' common range "
        f"({mlab(info['months'][0])} to {mlab(info['LASTC'])}), and the State's payroll jobs by industry. For each county the State chronology v4 code runs unchanged "
        f"with two county inputs: QCEW total covered employment (monthly levels, seasonally adjusted here exactly as the pre-1979 State layer is) as the index, and the "
        f"county unemployment rate (BLS LAUS, seasonally adjusted the same way) as the labour measure. A county-month missing in either input is grey, never filled; "
        f"the code runs on the months held in both, a missing month simply left out (a county with fewer than {MINSEG} such months is grey throughout). "
        f"County jobs are published through {mlab(info['lastQ'])}; after {mlab(info['lastQ'])} counties are coloured from the rise in their unemployment rate alone, through "
        f"{mlab(info['lastL'])} (Amendment 1): each month fresh, the national labour score of the rise of the county's rate over its lowest rate in the 12 months before that month, "
        f"on the same colour scale (yellow when under 0.05); no period is dated or carried in those months, and periods resume when QCEW publishes the next quarter. Counties are drawn from the Census cartographic boundary file of 2024. "
        f"Counties grey throughout ({len(cov['allgrey'])}): {', '.join(cov['allgrey']) or 'none'}. "
        + ' '.join(f"{mlab(m)}: {t}. In the data files it stays missing; on the page the share line is joined across it by a straight segment and the county map shows "
                   f"the latest month before it (display only, said in a note above the map)." for m, t in gapm.items()),
        *([("<b>Version 3</b> (PREREG-1052 v3, four changes fixed together before running). Inside a State recession period every month is at least red. "
            "Before July 1979 the State index is a two-input coincident index built like the Philadelphia Fed's (one dynamic factor of payroll growth and the change in the "
            "insured unemployment rate, estimated on 1947-1978 only for each State). County periods are dated with the main OECD 5/5/15 windows only. A county month with "
            "one input missing uses the other alone: county jobs alone (the output dimension inside a period) when the unemployment rate is missing, the unemployment "
            "rate alone when county jobs are missing.")] if (V3 and not V31) else []),
        *([("<b>Version 3.1</b> (PREREG-1052 v3 with its Amendment 1: three of the four changes fixed before running are kept; the fourth was tested once, failed and was withdrawn). "
            "Inside a State recession period every month is at least red (deep red at grade 4.0 or more). Before July 1979 the State layer is version 1's (State payrolls "
            "and the insured unemployment rate). County periods are dated with the main OECD 5/5/15 windows only. A county month with one input missing uses the other alone: "
            "county jobs alone (the output dimension inside a period) when the unemployment rate is missing, the unemployment rate alone when county jobs are missing. "
            "<b>Known limits</b> (tests run once, reported, not tuned): " + '; '.join(t for t in [
                next((f"where the two State layers overlap (1979-1996) the pre-1979 method agrees with the State chronology v4 on {re.search(r'= ([0-9.]+)', x[2]).group(1)} of State-months "
                      f"({'at or above' if x[1] else 'below'} the 0.80 set in advance)" for x in J1.get('tests', []) if x[0] == 'P1'), None),
                (f"the majority of a State's counties agrees with the State's own period on {q1[2]['both'].get('agreement', float('nan')):.3f} of State-months with both county inputs "
                 f"({'at or above' if q1[0] else 'below'} the 0.75 set in advance)"
                 if q1[2].get('both') else None)] if t) + '.')] if V31 else []),
        f"<b>Recession bands</b> are read at each build from the live Recession Indicator's published chronology on the site's main branch ({LIVENOTE['text']}).",
        f"<b>Industry panels.</b> Payroll jobs by supersector, seasonally adjusted, current vintage: the nation from the BLS establishment survey (CES), the States from "
        f"BLS State payrolls. The colour is the 12-month percent change at the month shown, on the map's scale with fixed cut points: −3% red, −1% orange, 0 yellow, "
        f"+1% light green, +3% deep green (red deepens to deep red at −6%). The panel also shows the latest month held ({mlab(thru['ind_nat'])} for the nation, "
        f"{mlab(thru['ind_st'])} for the States; months marked preliminary by BLS: {', '.join(mlab(m) for m in prel) or 'none'}).",
        f"<b>As live as the data.</b> State colours: the State chronology v4 through {mlab(sh)}. County jobs through {mlab(info['lastQ'])}; after {mlab(info['lastQ'])} counties "
        f"are coloured from the rise in their unemployment rate alone, through {mlab(info['lastL'])}. County unemployment file: {_pg(LAUSNOTE['text'])}. No month is drawn beyond its data."])
    SHORT[0] = ''.join('<p>' + x + '</p>' for x in [
        "Red marks a State or county inside a recession or disturbance, and the deeper the red the more damage it has done (full red at the recession grade of 2.0). "
        "Orange marks a period with little damage so far, or activity slipping below its trend; yellow means no period is open and activity is near its trend; "
        "green means activity is running above its trend. From July 1979 the States follow the State chronology v4; before 1979 the same method runs on State payrolls "
        "and insured unemployment. "
        f"Latest month of each layer: States {mlab(sh)}; counties {mlab(info['lastQ'])} with jobs and unemployment, then {mlab(info['lastL'])} from unemployment alone; "
        f"payroll jobs by industry {mlab(thru['ind_nat'])} for the nation and {mlab(thru['ind_st'])} for the States. "
        "The line on the timeline is the States' mean damage grade weighted by payroll jobs (in a State view, its counties' mean weighted by labor force)."])
    TESTS2 = [['Q1', bool(q1[0]), q1[1]], ['Q2', bool(q2[0]), q2[1].split('\n')[0] + ': ' + '; '.join(l.strip() for l in q2[1].split('\n')[1:-2])], ['Q3', bool(rows_eq), q3_data + '; drawn strip checked in headless Chrome (tests file)'], ['Q4', bool(q4[0]), q4[1]]]
    size, sizes = step_page(J1, CSH, CM, PER, N, S, B, info, TESTS2, DESC2, gapm)
    BR = step_browser(B, J1, info) if not a.no_browser else None
    s22 = BR['strip_2002_12'] if BR else None
    clean = bool(s22) and all(s22[w]['d2_rects'] == len(d2s) and all(st_[0] != 'url(#hatch)' for st_ in s22[w]['d2_style']) and s22[w]['titles'] == 0 and not s22[w]['texts'] and s22[w]['tooltip_divs'] == 0
                              and not s22[w]['positioned_changed'] for w in ('over', 'away')) and not BR['map_hover_floating']['positioned_changed']
    q3_ok = rows_eq and BR is not None and BR['strip_nation']['n_bad'] == 0 and all(BR['click_' + s]['strip']['n_bad'] == 0 for s in ('MI', 'TX')) and clean
    q3_txt = "strip = the live chronology's recession rows (grey; 2024 row hatched) and every register disturbance row (dashed, class 1 and class 2), no register recession row; " + q3_data + (
        f"; strip at 2002-12, mouse over it / away: class-2 dashed disturbance bands {s22['over']['d2_rects']}/{s22['away']['d2_rects']} (style {s22['over']['d2_style']}), patterns {s22['over']['patterns']}, "
        f"<title> {s22['over']['titles']}, non-year text {len(s22['over']['texts'])}/{len(s22['away']['texts'])}, tooltip elements {s22['over']['tooltip_divs']}, "
        f"floating elements appeared {s22['over']['positioned_changed']}/{s22['away']['positioned_changed']}; map hover floating {BR['map_hover_floating']['positioned_changed']} -> {'clean' if clean else 'NOT clean'}" if s22 else '') + (
        f"; drawn strip in headless Chrome, nation view: months whose drawn bands differ from the register {BR['strip_nation']['n_bad']} of {BR['strip_nation']['months']}; "
        f"Michigan view {BR['click_MI']['strip']['n_bad']} of {BR['click_MI']['strip']['months']}; Texas view {BR['click_TX']['strip']['n_bad']} of {BR['click_TX']['strip']['months']}" if BR else '; browser check not run')
    TESTS2[2] = ['Q3', bool(q3_ok), q3_txt]
    size, sizes = step_page(J1, CSH, CM, PER, N, S, B, info, TESTS2, DESC2, gapm)
    DNL = depth_nation(J1)
    DR = {k: drill_summary(CM, PER, S, J1, *k.split('|')) for k in ['MI|2009-06', 'TX|2016-03']}
    H = [(f"STRESS MAP V3.1 TESTS (1052; PREREG-1052 v3 Amendment 1: C1, C3, C4 kept, C2 withdrawn, pre-1979 layer = v1's; the v2 test code and bars unchanged; P5 scored on colour). " if V31 else
          (f"STRESS MAP V3 TESTS (1052; PREREG-1052 v3: C1-C4; the v2 test code and bars unchanged, run once). " if V3 else "")) + f"LIVE CHRONOLOGY: {LIVENOTE['text']}. " + f"STRESS MAP V2 TESTS (1052; PREREG-1052 national stress map v2). Built {pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%dT%H:%M:%SZ')} by code/stress_map_v2_1052.py --all. No AI.",
         f"Summary: Q1 {'PASS' if q1[0] else 'FAIL'}, Q2 {'PASS' if q2[0] else 'FAIL'}, Q3 {'PASS' if q3_ok else 'FAIL'}, Q4 {'PASS' if q4[0] else 'FAIL'}; v1 tests rerun: "
         + ('identical to the previous run' if v1_same else 'DIFFER from the previous run (see below)'), '',
         "CHANGES 15 Nov 04:28-04:32 PT (Anthony): no text, tooltip, <title> or pop-up on the strip or the map (map hover info in the fixed side panel; the month's period in a fixed line under "
         "the slider); strip recessions now = the live Recession Indicator's chronology (bhs_state.json 'nber', 13 rows; the 2024-04..2024-08 row hatched as on the live page; register recession rows, incl. 2000-09..2003-04 and the open 2024-06, no longer drawn; State and county colours unchanged); disturbances = every register class-1 and class-2 row, dashed (2002-06..2003-04 now stands as a disturbance after the 2001 recession); Q3 checks exactly these rows as drawn; strip padded so no axis "
         "label is clipped; share lines one continuous path, joined across months not surveyed; Back button ('Back to the United States') above the county map, Escape too; counties extended to the "
         "latest LAUS month from unemployment alone after the last QCEW month (prereg Amendment 1), Q1 reported for both kinds of month.",
         f"COUNTY UNEMPLOYMENT FILE: {LAUSNOTE['text']}",
         f"NOT-SURVEYED MONTHS: {gapm}; nation line nulls {sum(1 for v in J1['red'] if v is None)}; State layer colours missing at those months: "
         + json.dumps({m: [st for st in J1['states'] if J1['states'][st]['c'][(int(m[:4]) * 12 + int(m[5:7]) - 1) - (int(J1['start'][:4]) * 12 + int(J1['start'][5:7]) - 1)] < 0] for m in gapm}),
         f"LINES (headless Chrome; M = path starts, must be 1): {json.dumps(BR['lines']) if BR else 'not run'}; joined months per State view: {json.dumps(JOINED)}",
         f"AXIS LABELS (clipped labels per view and width): {json.dumps({k: v['clipped'] for k, v in BR['axis'].items()}) if BR else 'not run'}; readout inside: {all(v['readout_inside'] for v in BR['axis'].values()) if BR else ''}",
         f"GAP MONTH VIEW: {json.dumps(BR.get('gap_month')) if BR else 'not run'}",
         f"BACK BUTTON (headless Chrome): {json.dumps(BR['back_button']) if BR else 'not run'}",
         'DEPTH LINE (nation, payroll-weighted mean State running grade) peak inside each live recession band: ' + '; '.join(
             f"{r['peak']}..{r['trough']} {max(DNL[i] for i in range(len(DNL)) if r['peak'] <= nat_months[i] <= r['trough']):.2f} ({nat_months[max((i for i in range(len(DNL)) if r['peak'] <= nat_months[i] <= r['trough']), key=lambda i: DNL[i])]})"
             for r in json.load(open(INPUTS['live_chronology']))['nber'] if r['peak'] >= nat_months[0]) + f"; series maximum {max(DNL):.2f} ({nat_months[int(np.argmax(DNL))]})",
         f"RENDERED TEXT CHECK (British spellings; PASS/FAIL/Q1-Q4/P1-P7; Method section opened): {json.dumps(BR['text_check']) if BR else 'not run'}",
         f"KNOB vs CURSOR LINE (centre x difference, px; must be within 1): max {max(abs(v) for v in BR['knob_align'].values()):.3f}; {json.dumps(BR['knob_align'])}" if BR else '',
         "CHANGE 15 Nov 04:55 PT (Anthony): the native range input is replaced by a slider drawn in the strip's own coordinates (same viewBox width, same month-to-x function, same 26-unit padding), with drag, click and arrow/Home/End/PageUp/PageDown keys.",
         "CHANGE 15 Nov 04:48 PT (Anthony): the line under the slider leads with the State's own status in the State view, and gives the national status with State counts in the nation view.",
         f"STATUS LINE (headless Chrome): {json.dumps(BR['status_line'], ensure_ascii=False) if BR else 'not run'}",
         (f"STATUS LINE, ALL STATES vs State chronology v4 files: {BR['status_all']['states_checked']} State-months checked (50 States x 2026-07, 2009-06), mismatches {len(BR['status_all']['mismatches'])} "
          f"{json.dumps(BR['status_all']['mismatches'][:10], ensure_ascii=False)}; nation counts {json.dumps(BR['status_all']['nation'], ensure_ascii=False)}" if BR else ''), '',
         f"Q1: {'PASS' if q1[0] else 'FAIL'}  {q1[1]}", f"Q2: {'PASS' if q2[0] else 'FAIL'}  {q2[1]}", f"Q3: {'PASS' if q3_ok else 'FAIL'}  {q3_txt}", f"Q4: {'PASS' if q4[0] else 'FAIL'}  {q4[1]}", '',
         'DATA THROUGH: ' + f"State layer {thru['state']} (State chronology v4); county jobs through {thru['qcew']}, after that counties coloured from the rise in their unemployment rate alone through {thru['laus']}; national industry {thru['ind_nat']} "
         f"(CES; preliminary months {', '.join(prel)}); State industry {thru['ind_st']}.",
         f"COUNTY COVERAGE: {cov['counties']} counties on the map (cb_2024, 50 States) x {cov['months']} months ({info['months'][0]}..{info['LASTC']}) = {cov['county_months']} county-months; grey share {cov['grey_share']}; "
         f"months grey in every county {cov['months_grey_everywhere']}; months grey in over half {cov['months_grey_over_half']}; full coverage {cov['full']}; partial {cov['partial']}; all grey {len(cov['allgrey'])}: {'; '.join(cov['allgrey'])}. LAUS rates of 0.0 entered as 0.1: {info['laus_zero']}. "
         f"QCEW county-months not disclosed (flag N or level 0): {info['qcew_suppressed']}. Data codes not on the 2024 map: {', '.join(info['data_not_on_map'])}.",
         'Partial counties:'] + ['  ' + x for x in cov['partial_list']] + ['',
         'INDUSTRY SERIES: national CES ' + ', '.join(f"{r.supersector} {r.series_id}" for r in N.drop_duplicates('code').itertuples()) + f"; range {N.month.min()}..{thru['ind_nat']}; file {INPUTS['ces_national']} (modified {time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(INPUTS['ces_national'])))}). "
         f"State SM series SMS<st>00000<ss>00000001 (seasonally adjusted), {S.month.min()}..{thru['ind_st']}, {S.series_id.nunique()} series; file {INPUTS['ces_state']} (modified {time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(INPUTS['ces_state'])))}).",
         '', 'DRILL-DOWN (script):'] + ['  ' + v for v in DR.values()] + ['', f"PAGE: {size} bytes; per-State county blobs (base64 gzip) total {sum(sizes.values())} bytes, largest {max(sizes, key=sizes.get)} {max(sizes.values())}.",
         'BROWSER (headless Chrome, own temporary profile): ' + (json.dumps(BR, indent=1, default=str) if BR else 'not run'), '', 'INPUTS READ:'] + [f"  {k}: {v}" for k, v in INPUTS.items()] + ['OUTPUTS: ' + '; '.join(OUTPUTS), '',
         f'================ v1 tests rerun (out/{STATE_TESTS}, written in this run by ' + ('code/stress_map_v3_1052.py: the v1 test code and bars unchanged, on the v3 State layer' if V3 else 'the unchanged v1 script') + ') ================', v1_after]
    open(os.path.join(OUT, 'STRESS-MAP-' + TAG.upper() + '-TESTS-1052.txt'), 'w').write('\n'.join(H) + '\n')
    json.dump(dict(q1=q1[2], q2=q2[0], q3=q3_ok, q4=q4[0], thru=thru, coverage=cov, browser=BR, drill=DR, page_bytes=size, blob_bytes=sizes, v1_same=v1_same), open(os.path.join(OUT, 'stress_map_' + TAG + '_tests_1052.json'), 'w'), indent=1, default=str)
    print('\n'.join(H[:12])); log('done')
if __name__ == '__main__': main()
