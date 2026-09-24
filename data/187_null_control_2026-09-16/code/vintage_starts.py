#!/usr/bin/env python3
"""Where does each candidate's real-time record actually begin? Asked of ALFRED, one request each.

The three legs with no usable vintage history need substitutes, and a substitute is only worth
considering if its OWN vintages reach back past the calls it would have to make. `series/vintagedates`
with sort_order=asc and limit=1 answers that in one request per series, so a long candidate list costs
little. A series with no vintages at all answers 400 and is reported as such rather than skipped
silently.
"""
import os, re, sys, json, time, urllib.request, urllib.parse, concurrent.futures as cf
ENV = '/mnt/user-data/uploads/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env'
txt = open(ENV).read()
KEY = re.search(r'^FRED_API_KEY=([^\r\n]+)', txt, re.M).group(1).strip().strip('"').strip("'")
P = re.search(r'^FRED_API_KEY_POOL=([^\r\n]+)', txt, re.M)
KEYS = list(dict.fromkeys([KEY] + ([k.strip() for k in P.group(1).strip().strip('"').strip("'").split(',') if k.strip()] if P else [])))

CAND = sys.argv[1:] or """
PERMIT PERMITNSA PERMIT1 PERMIT1NSA AUTHNOTT AUTHNOTTSA HOUST HOUSTNSA HOUST1F COMPUTSA UNDCONTSA
DRSFRMACBS DRSFRMACBN DRALACBS DRCLACBS DRBLACBS DRCCLACBS DRSREACBS CORSFRMACBS CORALACBS
TDSP FODSP MDSP DRTSCILM DRTSCIS STDSL
BBKMCOIX BBKMLEIX BBKMGDP CFNAI CFNAIDIFF CFNAIMA3 USPHCI USSLIND STLENI NFCI ANFCI
INDPRO PAYEMS UNRATE ICSA CCSA AWHMAN MANEMP NEWORDER M1SL BORROW WBUSAPPWNSAUS
UMCSENT T10Y3M BAA10Y DGS10 GS10 TB3MS RSAFS TOTALSA HSN1F MSACSR
""".split()

def one(sid):
    for k in KEYS[:3]:
        u = ('https://api.stlouisfed.org/fred/series/vintagedates?series_id=%s&api_key=%s&file_type=json'
             '&sort_order=asc&limit=1' % (sid, k))
        try:
            with urllib.request.urlopen(u, timeout=60) as r: d = json.load(r)
            return sid, d.get('count', 0), (d.get('vintage_dates') or ['-'])[0]
        except urllib.error.HTTPError as e:
            if e.code == 400: return sid, 0, 'none'
            time.sleep(1)
        except Exception:
            time.sleep(1)
    return sid, -1, 'error'

if __name__ == '__main__':
    rows = []
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for sid, n, first in ex.map(one, CAND): rows.append((sid, n, first))
    for sid, n, first in sorted(rows, key=lambda r: (r[2] == 'none', r[2])):
        print('%-14s %6s  %s' % (sid, n, first))
