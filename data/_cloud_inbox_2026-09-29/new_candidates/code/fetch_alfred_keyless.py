#!/usr/bin/env python3
"""Full vintage history from ALFRED WITHOUT an API key.

The ALFRED 'Download Data' form (https://alfred.stlouisfed.org/series/downloaddata?seid=ID) lists every
vintage date as an <option>. POSTing the form back with all of them selected, file_type=1
('Observations by Real-Time Period') and file_format=csv returns a zip holding one CSV with
period_start_date, value, realtime_start_date, realtime_end_date -- the same content as the API's
realtime_start=1776-07-04&realtime_end=9999-12-31 pull, but keyless. >= 1.2 s between requests.
Usage: fetch_alfred_keyless.py ID [ID ...]
"""
import os, re, io, sys, csv, time, zipfile, urllib.request, urllib.parse

W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/new_candidates'
D = os.path.join(W, 'raw', 'alfred'); os.makedirs(D, exist_ok=True)
U = 'https://alfred.stlouisfed.org/series/downloaddata?seid=%s'
_last = [0.0]

def req(url, data=None):
    wait = 1.2 - (time.time() - _last[0])
    if wait > 0: time.sleep(wait)
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=300)
        return r.getcode(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, b''
    finally:
        _last[0] = time.time()

for sid in sys.argv[1:]:
    c, h = req(U % sid)
    t = h.decode('utf-8', 'replace')
    v = re.findall(r'<option value="(\d{4}-\d{2}-\d{2})"', t)
    s = re.search(r'id="form_obs_start_date"[^>]*value="([\d-]+)"', t)
    e = re.search(r'id="form_obs_end_date"[^>]*value="([\d-]+)"', t)
    if c != 200 or not v:
        print(sid, 'NO VINTAGES', c); continue
    form = [('form[units]', 'lin'), ('form[obs_start_date]', s.group(1)), ('form[obs_end_date]', e.group(1))]
    form += [('form[selected_vintage_dates][]', x) for x in v]
    form += [('form[entered_vintage_dates]', ''), ('form[file_type]', '1'), ('form[file_format]', 'csv'),
             ('form[download_data]', '')]
    c, b = req(U % sid, urllib.parse.urlencode(form).encode())
    if not b.startswith(b'PK'):
        print(sid, 'NOT A ZIP', c, b[:200]); continue
    open(os.path.join(D, sid + '_alfred.zip'), 'wb').write(b)
    z = zipfile.ZipFile(io.BytesIO(b))
    name = [n for n in z.namelist() if n.endswith('.csv')][0]
    raw = z.read(name).decode('utf-8', 'replace').splitlines()
    i = next(k for k, ln in enumerate(raw) if ln.startswith('period_start_date'))
    rows = list(csv.reader(raw[i:]))
    with open(os.path.join(D, sid + '_realtime_periods.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['date', 'value', 'realtime_start', 'realtime_end'])
        for r in rows[1:]:
            if len(r) >= 4: w.writerow(r[:4])
    print(sid, 'vintages', len(v), v[0], v[-1], 'rows', len(rows) - 1, flush=True)
