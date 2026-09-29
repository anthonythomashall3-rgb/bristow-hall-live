#!/usr/bin/env python3
"""Fetch monthly FRASER PDFs for a publication, trying several URL patterns.

usage: fetch_fraser_series.py <pub> <y0> <m0> <y1> <m1>
pubs:
  ee   Employment and Earnings (BLS)   raw/ee/ee_<YYYY>-<MM>.pdf
       patterns: employment/emp_<YYYY><MM>.pdf ; employment/1960s/empl_<MM><YYYY>.pdf
  mlr  Monthly Labor Review (BLS)      raw/mlr/mlr_<YYYY>-<MM>.pdf
       pattern: bls_mlr/bls_mlr_<YYYY><MM>.pdf
Plain urllib user agent; >=1.2 s between requests to fraser.stlouisfed.org.
FRASER answers 403 for a file that does not exist.
"""
import csv, os, sys, time, urllib.request, urllib.error

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://fraser.stlouisfed.org/files/docs/publications/'
PATTERNS = {
    'ee': ['employment/emp_{y}{m:02d}.pdf', 'employment/1960s/empl_{m:02d}{y}.pdf'],
    'mlr': ['bls_mlr/bls_mlr_{y}{m:02d}.pdf'],
    'frb': ['FRB/{d}s/frb_{m:02d}{y}.pdf'],
}

def months(y0, m0, y1, m1):
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1

def main():
    pub = sys.argv[1]
    y0, m0, y1, m1 = [int(x) for x in sys.argv[2:6]]
    out = os.path.join(W, 'raw', pub)
    os.makedirs(out, exist_ok=True)
    log = os.path.join(out, 'fetch_log.csv')
    new = not os.path.exists(log)
    with open(log, 'a', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['issue', 'url', 'status', 'bytes'])
        for y, m in months(y0, m0, y1, m1):
            fn = os.path.join(out, f'{pub}_{y}-{m:02d}.pdf')
            if os.path.exists(fn) and os.path.getsize(fn) > 10000:
                continue
            for pat in PATTERNS[pub]:
                url = BASE + pat.format(y=y, m=m, d=str(y)[:3] + '0')
                try:
                    with urllib.request.urlopen(url, timeout=180) as r:
                        data = r.read()
                        st = r.status
                    ok = data[:4] == b'%PDF'
                    if ok:
                        open(fn, 'wb').write(data)
                    w.writerow([f'{y}-{m:02d}', url, st, len(data)])
                except urllib.error.HTTPError as e:
                    ok = False
                    w.writerow([f'{y}-{m:02d}', url, e.code, 0])
                except Exception as e:
                    ok = False
                    w.writerow([f'{y}-{m:02d}', url, 'ERR ' + repr(e)[:80], 0])
                f.flush()
                time.sleep(1.2)
                if ok:
                    break

if __name__ == '__main__':
    main()
