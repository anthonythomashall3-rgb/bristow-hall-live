#!/usr/bin/env python3
"""Deterministic FRED current-file collector for series that are never revised (market rates and yields, as posted
daily/weekly/monthly by the Federal Reserve Board's H.15 and Moody's via FRED). No key, no AI. Writes raw/fred/<ID>.csv
(bytes as served) and logs the URL and sha256 in raw/SOURCES.csv. Usage: python3 collect/fred_current.py ID [ID ...]"""
import csv, hashlib, os, subprocess, sys, time
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# rating-agency, index-provider and exchange series go to private/ (gitignored; never in the public repository)
THIRD_PARTY = {'BAA', 'AAA', 'DBAA', 'DAAA', 'VIXCLS', 'SP500', 'NASDAQCOM', 'DJIA', 'BAMLH0A0HYM2', 'BAMLC0A0CM'}


def fetch(sid):
    url = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s' % sid
    for k in range(6):
        r = subprocess.run(['curl', '--http1.1', '-sS', '-m', '120', '-A', 'curl/8', '-f', url], capture_output=True)
        if r.returncode == 0 and r.stdout.startswith(b'observation_date'): break
        time.sleep(2 ** (k + 1))
    else:
        raise SystemExit('%s: fetch failed: %s' % (sid, r.stderr[:200]))
    b = r.stdout; d = os.path.join(HERE, 'private' if sid in THIRD_PARTY else 'raw', 'fred'); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, '%s.csv' % sid); open(p, 'wb').write(b)
    m = os.path.join(HERE, 'raw', 'SOURCES.csv'); new = not os.path.exists(m)
    with open(m, 'a', newline='') as f:
        w = csv.writer(f)
        if new: w.writerow(['path', 'sha256', 'bytes', 'source', 'fetched_utc'])
        w.writerow([os.path.relpath(p, HERE), hashlib.sha256(b).hexdigest(), len(b), url, time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())])
    lines = b.decode().strip().split('\n')
    print('%s: %d rows %s .. %s' % (sid, len(lines) - 1, lines[1].split(',')[0], lines[-1].split(',')[0]))


if __name__ == '__main__':
    for s in sys.argv[1:]:
        fetch(s); time.sleep(1)
