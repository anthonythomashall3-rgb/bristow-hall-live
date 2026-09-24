#!/usr/bin/env python3
"""The Canadian counterparts of the surviving American family — which the collection did not hold.

WHY THIS FETCH EXISTS. The Canadian transfer test was run against the 97 Canadian bank, credit and
money series already collected, and it failed: the true C.D. Howe chronology drew 403 admissible
configurations against 996 to 1,726 for wrongly dated ones, and the third-best channel was CANNED AND
OTHER PRESERVED FISH. But the American family that survives is central bank LENDING and bank CASH
ASSETS -- Federal Reserve primary and secondary credit, total borrowings from the Fed, commercial bank
cash assets -- and the Canadian collection held none of those. It held government debt issuance and
consumer credit aggregates. The test was run on the wrong series, and a negative from it says nothing
about the mechanism.

Statistics Canada has the counterparts and they reach further back than the American ones:
  10-10-0108  Bank of Canada, assets and liabilities, month-end          1935-01 ->  (cf. TOTRA)
  10-10-0107  Bank of Canada, assets and liabilities, average of Wednesdays 1953-01 ->
  10-10-0109  Chartered banks, assets and liabilities, month-end          1946-01 ->  (cf. H.8)
  10-10-0090  Chartered banks, Canadian cash reserves and liquid assets   1946-01 ->  (cf. CASACBW)
  10-10-0078  Chartered banks, assets and liabilities, Wednesdays         1976-01 ->
  10-10-0116  Chartered bank assets, liabilities and monetary aggregates  1953-01 ->
  10-10-0112  Currency outside banks and chartered bank deposits          1926-01 ->
  10-10-0084  Currency outside banks and chartered bank deposits, Wednesdays 1968-01 ->
"""
import os, io, csv, sys, json, time, zipfile, urllib.request, collections

def get(url, tries=6, timeout=900):
    """Statistics Canada's WDS endpoint returns 503 intermittently under any sustained use -- the same
    request that failed eight times in a row succeeded on the next attempt from a different process.
    Retry with backoff, and fall back to the direct archive URL, whose pattern the WDS response itself
    reveals: https://www150.statcan.gc.ca/n1/tbl/csv/{productId}-eng.zip"""
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r: return r.read()
        except Exception as e:
            last = e; time.sleep(3 + 5 * i)
    raise last

CUBES = ['10100108', '10100107', '10100109', '10100090', '10100078', '10100116', '10100112', '10100084']
DEST = sys.argv[1] if len(sys.argv) > 1 else '/mnt/user-data/outputs/ca_boc'
os.makedirs(DEST, exist_ok=True)

def slug(s):
    out = ''.join(ch if ch.isalnum() else '_' for ch in (s or '').upper())
    while '__' in out: out = out.replace('__', '_')
    return out.strip('_')[:56]

man = []
for pid in CUBES:
    try:
        try:
            d = json.loads(get('https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/%s/en' % pid, tries=4, timeout=180))
            url = d['object'] if d.get('status') == 'SUCCESS' else None
        except Exception:
            url = None
        if not url: url = 'https://www150.statcan.gc.ca/n1/tbl/csv/%s-eng.zip' % pid
        blob = get(url)
        z = zipfile.ZipFile(io.BytesIO(blob))
        name = [n for n in z.namelist() if n.endswith('.csv') and 'MetaData' not in n][0]
        txt = z.read(name).decode('utf-8-sig', 'replace')
        rd = csv.DictReader(io.StringIO(txt))
        cols = rd.fieldnames
        dimcols = [c for c in cols if c not in
                   ('REF_DATE', 'GEO', 'DGUID', 'UOM', 'UOM_ID', 'SCALAR_FACTOR', 'SCALAR_ID', 'VECTOR',
                    'COORDINATE', 'VALUE', 'STATUS', 'SYMBOL', 'TERMINATED', 'DECIMALS')]
        series = collections.defaultdict(list)
        for row in rd:
            if row.get('GEO') not in (None, '', 'Canada'): continue
            v = row.get('VALUE')
            if v in (None, ''): continue
            key = ' '.join(row.get(c, '') or '' for c in dimcols).strip()
            try: series[key].append((row['REF_DATE'], float(v)))
            except ValueError: continue
        n = 0
        for key, pts in series.items():
            if len(pts) < 60: continue
            pts.sort()
            fn = 'CA%s_%s.csv' % (pid, slug(key))
            with open(os.path.join(DEST, fn), 'w', newline='') as f:
                w = csv.writer(f); w.writerow(['date', 'value'])
                for dte, val in pts:
                    w.writerow([dte if len(dte) > 7 else dte + '-01', val])
            man.append((pid, fn, key[:90], pts[0][0], pts[-1][0], len(pts))); n += 1
        print('%s: %d series written (of %d raw)' % (pid, n, len(series)), flush=True)
    except Exception as e:
        print('%s: ERROR %s %s' % (pid, type(e).__name__, e), flush=True)
with open(os.path.join(DEST, 'MANIFEST_ca_boc.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['productId', 'file', 'label', 'start', 'end', 'n'])
    for r in man: w.writerow(r)
print('\ntotal series: %d' % len(man))
