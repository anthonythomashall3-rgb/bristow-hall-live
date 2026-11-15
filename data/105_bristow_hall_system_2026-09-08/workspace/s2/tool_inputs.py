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
def _row(tool, name, ids, source, url, cad, through, refreshed, note=None, value='', units=None, nxt=''):
    return dict(kind='tool', tool=tool, cad=cad or '', name=name, ids=ids or '', url=url or '', source=source or '', value=value or '', values=[], units=units,
                through=str(through or ''), nxt=nxt or '', refreshed=str(refreshed or ''), legs=tool, note=note, srcs=([[source, url]] if url else None))
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
                         value=(vs[-1] if vs else 'MISSING'), units='FRED ' + s + ', as published', nxt='each cloud run'))
    return rows
def mac_rows():
    try: J = json.load(open(os.path.join(HERE, 'tool_inputs_mac.json')))
    except Exception as e: return [], 'tool_inputs_mac.json not read (%s)' % e
    rows = []
    for tool in ('state-onset', 'stress-map'):
        for r in (J.get('tools', {}).get(tool, {}).get('rows') or []):
            rows.append(_row(tool, r['name'], r['ids'], r['source'], r['url'], r['freq'], r['through'] or 'MISSING', r['refreshed'] or 'MISSING', value=r.get('held') or '-', nxt=r.get('refresh') or '-'))
    return rows, J.get('generated_at', '')
def all_rows():
    m, gen = mac_rows(); return disturbance_rows() + m, gen
