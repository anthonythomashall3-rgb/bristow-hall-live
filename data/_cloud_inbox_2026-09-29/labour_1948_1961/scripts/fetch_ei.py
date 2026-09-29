#!/usr/bin/env python3
"""Fetch CEA 'Economic Indicators' monthly issues from FRASER (plain urllib UA).

URL pattern (verified 2026-09-29):
  https://fraser.stlouisfed.org/files/docs/publications/ei/<YYYY>/<MM>-<YYYY>.pdf
Saves to raw/ei/ei_<YYYY>-<MM>.pdf and logs status to raw/ei/fetch_log.csv.
>=1.5 s between requests.
"""
import csv, os, sys, time, urllib.request, urllib.error

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(W, 'raw', 'ei')
os.makedirs(OUT, exist_ok=True)
LOG = os.path.join(OUT, 'fetch_log.csv')

def months(y0, m0, y1, m1):
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1

def main():
    y0, m0, y1, m1 = [int(x) for x in sys.argv[1:5]] if len(sys.argv) > 4 else (1948, 1, 1962, 3)
    new = not os.path.exists(LOG)
    with open(LOG, 'a', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['issue', 'url', 'status', 'bytes'])
        for y, m in months(y0, m0, y1, m1):
            fn = os.path.join(OUT, f'ei_{y}-{m:02d}.pdf')
            if os.path.exists(fn) and os.path.getsize(fn) > 10000:
                continue
            url = f'https://fraser.stlouisfed.org/files/docs/publications/ei/{y}/{m:02d}-{y}.pdf'
            try:
                with urllib.request.urlopen(url, timeout=120) as r:
                    data = r.read()
                    st = r.status
                if data[:4] == b'%PDF':
                    open(fn, 'wb').write(data)
                w.writerow([f'{y}-{m:02d}', url, st, len(data)])
            except urllib.error.HTTPError as e:
                w.writerow([f'{y}-{m:02d}', url, e.code, 0])
            except Exception as e:
                w.writerow([f'{y}-{m:02d}', url, 'ERR ' + repr(e)[:80], 0])
            f.flush()
            time.sleep(1.5)

if __name__ == '__main__':
    main()
