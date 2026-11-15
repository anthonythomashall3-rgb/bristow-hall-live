"""EVERY LIVE TOOL'S INPUTS, AS /data/ ROWS (15 November 2026, collection 1052; Anthony 05:07 PT: "ALL OF OUR DATA IS CORRECT AND
OUR DATA PAGE IS CORRECT"). Called by bhs_site.py at every build. No row is typed here:
  disturbance : SERIES of s2/disturbance/disturbance_chronology.py (the list the live tool downloads), each one's newest observation
                read from the file the last run downloaded (out/fred_latest/<S>.csv), refreshed = out/chronology.json 'built';
                frequency measured from the file's own dates;
  stress-map, state-onset : s2/tool_inputs_mac.json, written on the Mac by s2/tool_inputs_mac.py from each tool's own
                code (stress map INPUTS, the 1032 chain's data paths, the 823 live run's feeds and doors).
The detector's rows stay where bhs_site.py makes them (the rule's feeds, the front page tiles, the backstop tier, the legs)."""
import os, ast, json, datetime as _dt
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = ['detector', 'disturbance', 'state-onset', 'stress-map']   # 15 Nov 2026 11:00 PT (Anthony: "remove all of the shadows from the data"): the shadow tool is not on the data page   # every live tool with inputs of its own (chronology, damage-index: stubs; margins: the detector's readings)
PAGE = {'detector': '/detector/', 'disturbance': '/disturbance/', 'state-onset': '/state-onset/', 'stress-map': '/stress-map/'}
def _row(tool, name, ids, source, url, cad, through, refreshed, note=None, value='', units=None, nxt='', frozen=False, values=None, vlist=None, period='', sched=None):
    return dict(kind='tool', tool=tool, cad=cad or '', name=name, ids=ids or '', url=url or '', source=source or '', value=value or '', values=values or [], units=units,
                through=str(through or ''), nxt=nxt or '', refreshed=str(refreshed or ''), legs=tool, note=note, srcs=([[source, url]] if url else None), frozen=frozen,
                vlist=vlist or [], period=period or '', sched=sched)
# NEXT PUBLISHED FOR A ROW THE TOOL REBUILDS BY HAND (15 Nov 2026, collection 1052; Anthony: the data page shows only dates): the publisher's
# next release of the series the row holds. Each row names its publisher's calendar (META in s2/tool_inputs_mac.py, 6th field); the days are
# FRED's release calendar for that release (ops/cache/fred_release_dates.json, refreshed at every update run by ops/calendar_build.py) and
# the publisher's own schedule page, read 15 Nov 2026 (listed below with its address); the first day after today is shown. A frozen history
# layer and a static boundary file have no next release: their Next published cell is a dash (the q41 gate allows it only there).
# 15 Nov 2026 12:34 PT (Anthony: every row the exact time, no gaps): no dash any more - s2/next_published.py gives every row its next time;
# a history layer follows the live series it continues in, a static file the next live-tools run that re-checks it. The days below are
# still the publishers' own schedule pages; census_cps drops 19 Nov 2026 (the October file was posted 12 Nov, so no new file that day).
CAL = {
    'bls_state': ([112], 'https://www.bls.gov/schedule/news_release/laus.htm', ['2026-11-20', '2026-12-18', '2027-01-26', '2027-03-15', '2027-03-26', '2027-04-20', '2027-05-21', '2027-06-22', '2027-07-20', '2027-08-20', '2027-09-21', '2027-10-22', '2027-11-19', '2027-12-17']),
    'bls_metro': ([], 'https://www.bls.gov/schedule/news_release/metro.htm', ['2026-12-02', '2026-12-30', '2027-02-03', '2027-03-19', '2027-04-07', '2027-04-28', '2027-06-02', '2027-06-30', '2027-07-28', '2027-09-01', '2027-09-29', '2027-11-03', '2027-12-01']),
    'bls_qcew': ([], 'https://www.bls.gov/schedule/news_release/cew.htm', ['2026-12-02', '2027-03-03', '2027-05-27', '2027-08-26', '2027-12-08']),
    'bls_cpi': ([10], 'https://www.bls.gov/schedule/news_release/cpi.htm', ['2026-12-10', '2027-01-13', '2027-02-11', '2027-03-10', '2027-04-13', '2027-05-12', '2027-06-10', '2027-07-14', '2027-08-11', '2027-09-14', '2027-10-14', '2027-11-10', '2027-12-10']),
    'bea_spi': ([], 'https://www.bea.gov/news/schedule', ['2026-12-23']),
    'census_bps': ([], 'https://www.census.gov/construction/bps/schedule.html', ['2026-11-25', '2026-12-23', '2027-01-27', '2027-02-24', '2027-03-23', '2027-04-23', '2027-05-25', '2027-06-24', '2027-07-26', '2027-08-24', '2027-09-24', '2027-10-26', '2027-11-24', '2027-12-22']),
    'census_cps': ([], 'https://www.census.gov/data/what-is-data-census-gov/upcoming-releases.html', ['2026-12-10', '2027-01-14']),
    'dol_claims': ([180], 'FRED release 180 (the Department posts weekly, Thursday 8:30 AM ET; it lists no days ahead)', []),
    # a register built from FRED series: the first of its inputs' next releases (G.17 for INDPRO, the Employment Situation, BEA's personal income and GDP)
    'inputs': ([13, 50, 54, 53, 282], 'https://www.federalreserve.gov/releases/g17/release_dates.htm', ['2026-11-17', '2026-12-16', '2027-01-15', '2027-02-17', '2027-03-15', '2027-04-15', '2027-05-17', '2027-06-16', '2027-07-16', '2027-08-17', '2027-09-16', '2027-10-18', '2027-11-17', '2027-12-16']),
}
def _cal_days():
    d = HERE
    for _ in range(6):
        p = os.path.join(d, 'ops', 'cache', 'fred_release_dates.json')
        if os.path.exists(p):
            try: return json.load(open(p))
            except Exception: return {}
        d = os.path.dirname(d)
    return {}
def next_release(key, today=None):
    if key not in CAL: return ''
    rids, _src, days = CAL[key]; C = _cal_days(); today = today or _dt.date.today().isoformat()
    ds = set(days)
    for rid in rids: ds |= set((C.get(str(rid)) or {}).get('dates') or [])
    fut = sorted(x for x in ds if x > today)
    return fut[0] if fut else ''
def _cad(dates):
    try:
        a, b = [_dt.date.fromisoformat(x[:10]) for x in dates[-2:]]; g = (b - a).days
        return 'daily' if g <= 3 else 'weekly' if g <= 8 else 'monthly' if g <= 31 else 'quarterly' if g <= 93 else 'annual'
    except Exception: return ''
def disturbance_rows():
    D = os.path.join(HERE, 'disturbance'); py = os.path.join(D, 'disturbance_chronology.py')
    ser = next(ast.literal_eval(n.value) for n in ast.parse(open(py).read()).body if isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'SERIES' for t in n.targets))
    try: built = json.load(open(os.path.join(D, 'out', 'chronology.json'))).get('built', '')
    except Exception: built = ''
    rows = []
    for s in ser:
        f = os.path.join(D, 'out', 'fred_latest', s + '.csv'); ds = []; vs = []
        try:
            for ln in open(f).read().strip().split('\n')[1:]:
                d, v = (ln.split(',') + [''])[:2]
                if v.strip() not in ('', '.'): ds.append(d.strip()); vs.append(v.strip())
        except Exception: pass
        rows.append(_row('disturbance', 'FRED series ' + s, s, 'FRED (fredgraph download, every run)', 'https://fred.stlouisfed.org/series/' + s, _cad(ds), ds[-1] if ds else 'MISSING', built or 'MISSING',
                         value=(vs[-1] if vs else 'MISSING'), units='FRED ' + s + ', as published', nxt='', sched=('cal', s)))
    return rows
def mac_rows():
    try: J = json.load(open(os.path.join(HERE, 'tool_inputs_mac.json')))
    except Exception as e: return [], 'tool_inputs_mac.json not read (%s)' % e
    rows = []
    for tool in ('state-onset', 'stress-map'):
        for r in (J.get('tools', {}).get(tool, {}).get('rows') or []):
            _rf = r.get('refresh') or ''; rel = r.get('release') or ''
            sched = ((rel,) if rel in ('static', 'derived_state', 'derived_detector') else ('inputs', CAL['inputs'][0]) if rel == 'inputs'
                     else ('pub', rel, (CAL.get(rel) or ([], '', []))[2]) if rel else None)
            h = r.get('held') if isinstance(r.get('held'), dict) else {}
            rows.append(_row(tool, r['name'], r['ids'], r['source'], r['url'], r['freq'], r['through'] or 'MISSING', r['refreshed'] or 'MISSING',
                             value=h.get('value') or ('' if (h.get('values') or h.get('vlist')) else 'MISSING'), values=h.get('values'), vlist=h.get('vlist'),
                             units=h.get('units'), period=h.get('period'), nxt='', sched=sched, frozen=('history layer' in _rf)))
    return rows, J.get('generated_at', '')
def all_rows():
    m, gen = mac_rows(); return disturbance_rows() + m, gen
