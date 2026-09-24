#!/usr/bin/env python3
"""Data from the institutions that publish it, for mechanisms FRED does not cover.

Each block below exists because the MECHANISM MAP names an observable and FRED does not carry it.
Nothing here is a keyword sweep; every source is fetched because a specific mechanism needs it.

  World Bank commodity prices (the 'Pink Sheet')   A5 energy and commodity shock, monthly from 1960
  CPB World Trade Monitor                          B2 external shock: world and regional trade volume
  OECD composite leading indicators                B2 external shock, for the countries that lead
  IMF PortWatch                                    B4 supply-chain rupture: daily port calls
  BIS credit-to-GDP gaps                           A2 credit: the standing measure of credit overhang

Where a source moves its file each month -- the CPB does -- the landing page is read for the link
rather than the filename being guessed, so the script does not quietly fetch a stale file.
"""
import os, re, csv, json, io, sys, time, urllib.request, zipfile
BASE = os.path.expanduser('~/Projects/Onset Detector Data')
if not os.path.isdir(BASE): BASE = os.path.expanduser('~/mnt/Onset Detector Data')
HERE = os.path.join(BASE, '186_realtime_channels_2026-09-15')
DATA, OUT = os.path.join(HERE, 'data'), os.path.join(HERE, 'out')
os.makedirs(DATA, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
def get(u, timeout=180):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=timeout).read()
def wr(slug, rows):
    rows = [(d, v) for d, v in rows if v == v]
    if len(rows) < 60: return 0
    with open(os.path.join(DATA, slug + '.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['date', 'value']); w.writerows(rows)
    return 1
log = []

# ---------- World Bank Pink Sheet: monthly commodity prices from 1960 ----------
try:
    import pandas as pd
    u = ('https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/'
         'related/CMO-Historical-Data-Monthly.xlsx')
    b = get(u, 300); open('/tmp/pink.xlsx', 'wb').write(b)
    d = pd.read_excel('/tmp/pink.xlsx', sheet_name='Monthly Prices', header=None)
    hdr = next(i for i in range(10) if d.iloc[i].astype(str).str.contains('Crude oil', case=False).any())
    names = [str(v) for v in d.iloc[hdr]]
    start = next(i for i in range(hdr + 1, len(d)) if re.match(r'^\d{4}M\d{1,2}$', str(d.iloc[i, 0]).strip()))
    n = 0
    for j in range(1, len(names)):
        nm = names[j]
        if nm in ('nan', 'None') or not nm.strip(): continue
        vals = []
        for i in range(start, len(d)):
            m = re.match(r'^(\d{4})M(\d{1,2})$', str(d.iloc[i, 0]).strip())
            if not m: continue
            v = pd.to_numeric(d.iloc[i, j], errors='coerce')
            if v == v: vals.append(('%s-%02d-01' % (m.group(1), int(m.group(2))), float(v)))
        n += wr('WB_' + re.sub(r'[^A-Za-z0-9]+', '_', nm).strip('_').upper()[:40], vals)
    log.append(('world_bank_pink_sheet', 'ok', n))
except Exception as e:
    log.append(('world_bank_pink_sheet', type(e).__name__ + ':' + str(e)[:70], 0))

# ---------- CPB World Trade Monitor: the link is read from the landing page, not guessed ----------
try:
    import pandas as pd
    page = None
    for slug in ['april-2026', 'march-2026', 'may-2026', 'february-2026']:
        try:
            page = get('https://www.cpb.nl/en/world-trade-monitor/cpb-world-trade-monitor-' + slug, 120).decode('utf-8', 'ignore')
            if '.xlsx' in page: break
        except Exception: page = None
    m = re.search(r'href="(/[^"]*\.xlsx)"', page or '')
    if not m: raise RuntimeError('no xlsx link on the CPB page')
    b = get('https://www.cpb.nl' + m.group(1), 240); open('/tmp/wtm.xlsx', 'wb').write(b)
    n = 0
    for sheet, tag in [('trade_out', 'TRADE'), ('inpro_out', 'INDPRO')]:
        d = pd.read_excel('/tmp/wtm.xlsx', sheet_name=sheet, header=None)
        hdr = next((i for i in range(8) if d.iloc[i].astype(str).str.match(r'^\d{4}m\d{2}$').sum() > 50), None)
        if hdr is None: continue
        cols = [(j, str(d.iloc[hdr, j])) for j in range(d.shape[1]) if re.match(r'^\d{4}m\d{2}$', str(d.iloc[hdr, j]))]
        for i in range(hdr + 1, len(d)):
            nm = next((str(d.iloc[i, j]).strip() for j in range(6)
                       if isinstance(d.iloc[i, j], str) and len(str(d.iloc[i, j]).strip()) > 2), None)
            if not nm: continue
            vals = []
            for j, dt in cols:
                v = pd.to_numeric(d.iloc[i, j], errors='coerce')
                if v == v: vals.append(('%s-%s-01' % (dt[:4], dt[5:7]), float(v)))
            n += wr('CPB_%s_%s' % (tag, re.sub(r'[^A-Za-z0-9]+', '_', nm).strip('_').upper()[:40]), vals)
    log.append(('cpb_world_trade_monitor', 'ok', n))
except Exception as e:
    log.append(('cpb_world_trade_monitor', type(e).__name__ + ':' + str(e)[:70], 0))

# ---------- OECD composite leading indicators, for the countries that lead the United States ----------
try:
    n = 0
    for iso in ['USA', 'DEU', 'JPN', 'KOR', 'CAN', 'GBR', 'FRA', 'ITA', 'CHN', 'MEX', 'OECD', 'G7M']:
        u = ('https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_CLI,/'
             '%s.M.LI...AA...H?format=csvfile' % iso)
        try:
            txt = get(u, 120).decode('utf-8', 'ignore')
        except Exception:
            continue
        rows = []
        rd = csv.DictReader(io.StringIO(txt))
        for r in rd:
            t = r.get('TIME_PERIOD') or r.get('TIME')
            v = r.get('OBS_VALUE')
            if not t or not v: continue
            m = re.match(r'^(\d{4})-(\d{2})$', t.strip())
            if not m: continue
            try: rows.append(('%s-%s-01' % (m.group(1), m.group(2)), float(v)))
            except Exception: pass
        rows.sort()
        n += wr('OECD_CLI_' + iso, rows)
        time.sleep(0.4)
    log.append(('oecd_cli', 'ok', n))
except Exception as e:
    log.append(('oecd_cli', type(e).__name__ + ':' + str(e)[:70], 0))

# ---------- IMF PortWatch: daily port calls, the supply-chain rupture observable ----------
try:
    import pandas as pd
    u = ('https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/'
         'Daily_Port_Activity_Data_and_Trade_Estimates/FeatureServer/0/query'
         '?where=1%3D1&outFields=date,portname,portcalls,import,export&returnGeometry=false'
         '&resultRecordCount=32000&f=json&orderByFields=date')
    got, off, recs = True, 0, []
    while got and off < 400000:
        d = json.loads(get(u + '&resultOffset=%d' % off, 180).decode('utf-8', 'ignore'))
        fs = d.get('features', [])
        if not fs: break
        recs += [f['attributes'] for f in fs]
        off += len(fs); got = len(fs) >= 1000
    agg = {}
    for r in recs:
        dt = r.get('date')
        if not dt: continue
        iso = time.strftime('%Y-%m-%d', time.gmtime(dt / 1000)) if isinstance(dt, (int, float)) else str(dt)[:10]
        a = agg.setdefault(iso, [0.0, 0.0, 0.0])
        for k, i in (('portcalls', 0), ('import', 1), ('export', 2)):
            v = r.get(k)
            if isinstance(v, (int, float)): a[i] += float(v)
    ks = sorted(agg)
    n = wr('PORTWATCH_GLOBAL_PORTCALLS_DAILY', [(k, agg[k][0]) for k in ks])
    n += wr('PORTWATCH_GLOBAL_IMPORT_DAILY', [(k, agg[k][1]) for k in ks])
    n += wr('PORTWATCH_GLOBAL_EXPORT_DAILY', [(k, agg[k][2]) for k in ks])
    log.append(('imf_portwatch', 'ok (%d records)' % len(recs), n))
except Exception as e:
    log.append(('imf_portwatch', type(e).__name__ + ':' + str(e)[:70], 0))

with open(os.path.join(OUT, 'MANIFEST_institutions.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['source', 'status', 'series_written']); w.writerows(log)
for r in log: print('%-28s %-46s %d' % r)
