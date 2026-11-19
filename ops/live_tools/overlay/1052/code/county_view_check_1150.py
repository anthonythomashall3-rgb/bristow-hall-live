#!/usr/bin/env python3
"""1150 (no AI): the county view of the stress map read in a browser and compared with the files. usage: county_view_check_1150.py <1052 collection> <out json>
Serves web/stress-map over http (the page fetches cf/ and ci/), then for a fixed list of (State, county, month): opens the State, reads the State
factor panel, clicks the county shape, reads the title, the back button, the status line, the factor panel and the industry table, and compares every
number with out/stress_map_v3_1_county_month.csv.gz, out/stress_map_v3_1_state_month.csv and 1032 data/qcew_industry_county. Then Back twice."""
import os, sys, json, gzip, csv, threading, http.server, functools, re
import pandas as pd
from playwright.sync_api import sync_playwright
C = sys.argv[1]; OUTJ = sys.argv[2]; WEB = os.path.join(C, 'web', 'stress-map'); QD = os.path.join(os.path.dirname(C), '1032_state_recession_indicator_all_states_dc_2026-11-09', 'data', 'qcew_industry_county')
CASES = [('AL', '01001', '2009-06'), ('TX', '48201', '2020-04'), ('CA', '06037', '1993-06'), ('MI', '26163', '2009-06'), ('HI', '15009', '2026-03'), ('ND', '38105', '2016-03'), ('NY', '36061', '2001-12'), ('LA', '22071', '2005-10'), ('AK', '02020', '2024-01'), ('CT', None, '2025-06')]
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k): pass
h = functools.partial(Q, directory=WEB)
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), h); threading.Thread(target=srv.serve_forever, daemon=True).start(); URL = 'http://127.0.0.1:%d/index.html' % srv.server_address[1]
CM = pd.read_csv(os.path.join(C, 'out/stress_map_v3_1_county_month.csv.gz'), dtype={'fips': str, 'month': str}).set_index(['fips', 'month'])
SM = pd.read_csv(os.path.join(C, 'out/stress_map_v3_1_state_month.csv'), dtype={'month': str}).set_index(['st', 'month'])
def prev12(m): return '%d-%s' % (int(m[:4]) - 1, m[5:])
def qc(fips, month):
    y, mo = int(month[:4]), int(month[5:]); q = (mo - 1) // 3 + 1; k = (mo - 1) % 3; o = {}
    with gzip.open(os.path.join(QD, '%d.csv.gz' % y), 'rt') as f:
        for r in csv.reader(f):
            if r[0] == fips and r[4] == str(q):
                key = ('10' if r[1] == '0' else 'gov' if r[1] in '123' else None) if r[2] == '10' else r[2]
                if key is None: continue
                v = None if r[8] == 'N' else int(r[5 + k])
                if key == 'gov': o[key] = None if (o.get(key, 0) is None or v is None) else o.get(key, 0) + v
                else: o[key] = v
    return o
def num(s): s = s.replace(',', '').replace('−', '-').replace('%', '').replace(' points', '').replace('+', ''); return None if s in ('–', '') else float(s)
R = dict(cases=[], fail=[])
with sync_playwright() as p:
    br = p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True); pg = br.new_page(viewport={'width': 1400, 'height': 1000}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.goto(URL); pg.wait_for_function('()=>window.__SM&&window.__SM.ready')
    for st, f, mo in CASES:
        c = dict(st=st, fips=f, month=mo); pg.evaluate(f"()=>window.__SM.openState('{st}')"); pg.wait_for_function(f"()=>window.__SM.view().st==='{st}'"); pg.evaluate(f"()=>window.__SM.setMonth('{mo}')")
        pg.wait_for_function("()=>document.querySelectorAll('#fact tr').length>0", timeout=15000)
        sf = pg.evaluate("()=>Array.from(document.querySelectorAll('#fact tr')).map(r=>Array.from(r.children).map(x=>x.textContent))"); c['state_factors'] = sf
        want_u = SM.labour_input.get((st, mo)); want_p = SM.deviation_pp.get((st, mo))
        if want_u == want_u and want_u is not None and abs(num(sf[0][1]) - round(float(want_u), 1)) > 0.051: R['fail'].append(f'{st} {mo} State unemployment {sf[0][1]} vs {want_u}')
        if want_p == want_p and want_p is not None and abs(num(sf[2][1]) - float(want_p)) > 0.0051: R['fail'].append(f'{st} {mo} State index against trend {sf[2][1]} vs {want_p}')
        if f is None: f = pg.evaluate("()=>document.querySelector('#layer path').dataset.id"); c['fips'] = f
        pg.click(f'#layer path[data-id="{f}"]', force=True); pg.wait_for_function(f"()=>window.__SM.county()==='{f}'")
        pg.wait_for_function("()=>/Jobs by industry/.test(document.getElementById('indh').textContent)&&document.querySelectorAll('#indtab tr').length>0", timeout=15000)
        c['title'] = pg.inner_text('#vtitle'); c['back'] = pg.inner_text('#back'); c['status'] = pg.inner_text('#stline'); c['indh'] = pg.inner_text('#indh')
        cf = pg.evaluate("()=>Array.from(document.querySelectorAll('#fact tr')).map(r=>Array.from(r.children).map(x=>x.textContent))"); c['county_factors'] = cf
        it = pg.evaluate("()=>Array.from(document.querySelectorAll('#indtab tr')).map(r=>Array.from(r.children).map(x=>x.textContent))"); c['industry_rows'] = len(it) - 1; c['industry_table'] = it
        row = CM.loc[(f, mo)] if (f, mo) in CM.index else None
        if row is not None:
            for lab, col, k, tol in (('Unemployment rate', 'laus_ur', 0, 0.051), ('Labor force', 'laus_lf', 2, 0.51), ('Jobs', 'qcew_employment', 3, 0.51), ('Jobs against trend', 'deviation_pp', 5, 0.0051)):
                w = row[col]; g = num(cf[k][1])
                if (w != w) != (g is None) or (g is not None and abs(g - float(w)) > tol): R['fail'].append(f'{f} {mo} {lab}: page {cf[k][1]} file {w}')
        if len(it) > 1 and len(it[1]) == 4:
            src = qc(f, mo); names = pg.evaluate("()=>null"); got = {r[0]: r[2] for r in it[1:]}; c['industry_source'] = src
            nm = {'10': 'Total, all covered jobs', 'gov': 'Government', '1012': 'Construction', '1013': 'Manufacturing', '1026': 'Leisure and hospitality'}
            for k, n_ in nm.items():
                w = src.get(k); g = num(got.get(n_, '–'))
                if (w is None) != (g is None) or (g is not None and g != w): R['fail'].append(f'{f} {mo} industry {n_}: page {got.get(n_)} file {w}')
        pg.click('#back'); pg.wait_for_function("()=>window.__SM.county()===null"); c['after_back_1'] = dict(title=pg.inner_text('#vtitle'), mode=pg.evaluate("()=>window.__SM.view().mode"), indh=pg.inner_text('#indh'))
        if not c['after_back_1']['title'].endswith(': counties') or c['after_back_1']['mode'] != 'state': R['fail'].append(f'{st}: Back from the county did not return to the State')
        pg.click('#back'); pg.wait_for_function("()=>window.__SM.view().mode==='nation'"); R['cases'].append(c)
    R['console_errors'] = errs
    if errs: R['fail'].append('page errors: %d' % len(errs))
    br.close()
R['ok'] = not R['fail']; json.dump(R, open(OUTJ, 'w'), indent=1, default=str); print('county view check:', 'ok' if R['ok'] else 'FAILED', len(R['cases']), 'cases', R['fail'][:8]); sys.exit(0 if R['ok'] else 1)
