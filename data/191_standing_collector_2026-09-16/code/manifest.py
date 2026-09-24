#!/usr/bin/env python3
"""Writes ../MANIFEST.csv: path, sha256, bytes, rows, first_date, last_date, fetched_at for every file under ../warehouse.
Incremental: a cache (logs/manifest_cache.json) keyed by path+size+mtime avoids re-hashing unchanged files.
Run:  python3 manifest.py          (collector.py calls build() at the end of every cycle)"""
import os, re, csv, sys, json, gzip, time, hashlib

CODE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(CODE)
WH = os.path.join(ROOT, 'warehouse'); OUT = os.path.join(ROOT, 'MANIFEST.csv'); CACHE = os.path.join(ROOT, 'logs', 'manifest_cache.json')
DATE_RE = re.compile(r'^\d{4}-\d{2}(-\d{2})?')
US_RE = re.compile(r'^(\d{1,2})/(\d{1,2})/(\d{4})')
def iso(v):
    """ISO date (first 10 chars) from YYYY-MM[-DD]... or M/D/YYYY; None otherwise."""
    if DATE_RE.match(v): return v[:10]
    m = US_RE.match(v)
    if m: return '%s-%02d-%02d' % (m.group(3), int(m.group(1)), int(m.group(2)))
    return None
DATE_COLS = ('date', 'record_date', 'period', 'effectivedate', 'effective_date', 'auctiondate', 'operation_date', 'declarationdate', 'week_end', 'utc_hour_end', 'date_end', 'realtime_start')

def describe(path):
    """rows (data lines) and first/last date for csv / csv.gz; blanks otherwise."""
    rows = first = last = ''
    if not re.search(r'\.csv(\.gz)?$', path, re.I): return rows, first, last
    op = gzip.open if path.endswith('.gz') else open
    try:
        with op(path, 'rt', newline='', encoding='utf-8-sig', errors='replace') as f:
            rd = csv.reader(f); header = next(rd, None)
            if header is None: return 0, '', ''
            hl = [h.strip().lower() for h in header]
            di = 0
            for c in DATE_COLS:
                if c in hl: di = hl.index(c); break
            n = 0; lo = hi = None
            for r in rd:
                if not r: continue
                n += 1
                if di < len(r):
                    v = iso(r[di].strip())
                    if v:
                        if lo is None or v < lo: lo = v
                        if hi is None or v > hi: hi = v
            return n, lo or '', hi or ''
    except Exception:
        return '', '', ''

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    return h.hexdigest()

def build():
    cache = {}
    try: cache = json.load(open(CACHE))
    except Exception: pass
    new_cache = {}; rows = []
    for dp, dn, fn in os.walk(WH):
        dn.sort()
        for name in sorted(fn):
            if name.endswith(('.tmp', '.sha', '.parsed', '.DS_Store')): continue
            p = os.path.join(dp, name); rel = os.path.relpath(p, ROOT)
            try: st = os.stat(p)
            except OSError: continue
            ck = '%s|%d|%d' % (rel, st.st_size, int(st.st_mtime))
            if ck in cache: rec = cache[ck]
            else:
                n, lo, hi = describe(p)
                rec = {'sha256': sha256(p), 'bytes': st.st_size, 'rows': n, 'first_date': lo, 'last_date': hi, 'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(st.st_mtime))}
            new_cache[ck] = rec
            rows.append([rel, rec['sha256'], rec['bytes'], rec['rows'], rec['first_date'], rec['last_date'], rec['fetched_at']])
    tmp = OUT + '.tmp'
    with open(tmp, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['path', 'sha256', 'bytes', 'rows', 'first_date', 'last_date', 'fetched_at']); w.writerows(rows)
    os.replace(tmp, OUT)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(new_cache, open(CACHE, 'w'))
    return len(rows)

if __name__ == '__main__':
    t0 = time.time(); n = build()
    print('MANIFEST.csv: %d files, %.1fs' % (n, time.time() - t0))
