#!/usr/bin/env python3
"""The standing collector. Runs unattended in the container and never idles while there is a job left.

Jobs, in order:
  1. catalog   -- every FRED series tagged nation+usa at daily, weekly, biweekly, monthly and quarterly
                  frequency (about 77,000), metadata saved as JSON so the tool's future screens can
                  enumerate candidates without asking FRED again.
  2. observe   -- the observations of every catalogued series not already held in the channel
                  collection (/mnt/user-data/outputs/us), written gzipped to us_bulk/.
  3. vintages  -- the complete vintage record (every observation with its realtime_start and
                  realtime_end) for every series the walks and screens use as a leg, proposer or
                  confirmer, written gzipped to vint/. This is what a real-time claim rests on.

Resumable: a job skips whatever is already on disk. Twelve keys, each throttled below its own limit.
"""
import os, re, csv, sys, json, time, gzip, threading, queue, urllib.request, urllib.error, urllib.parse

ENV = '/mnt/user-data/uploads/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env'
txt = open(ENV).read()
KEY = re.search(r'^FRED_API_KEY=([^\r\n]+)', txt, re.M).group(1).strip().strip('"').strip("'")
P = re.search(r'^FRED_API_KEY_POOL=([^\r\n]+)', txt, re.M)
KEYS = list(dict.fromkeys([KEY] + ([k.strip() for k in P.group(1).strip().strip('"').strip("'").split(',') if k.strip()] if P else [])))
ROOT = '/mnt/user-data/outputs'
BULK = os.path.join(ROOT, 'us_bulk'); VINT = os.path.join(ROOT, 'vint'); CAT = os.path.join(ROOT, 'catalog')
for d in (BULK, VINT, CAT): os.makedirs(d, exist_ok=True)
HELD = [os.path.join(ROOT, 'us'), os.path.join(ROOT, 'us_nber')]
LOG = open(os.path.join(ROOT, 'collector.log'), 'a')
def log(*a):
    s = time.strftime('%H:%M:%S ') + ' '.join(str(x) for x in a)
    LOG.write(s + '\n'); LOG.flush(); print(s, flush=True)

_last = {k: 0.0 for k in KEYS}; _lk = threading.Lock()
def get(path, key, **kw):
    kw.update(api_key=key, file_type='json')
    u = 'https://api.stlouisfed.org/fred/' + path + '?' + urllib.parse.urlencode(kw)
    for attempt in range(5):
        with _lk:
            wait = 0.7 - (time.time() - _last[key])
            if wait > 0: time.sleep(wait)
            _last[key] = time.time()
        try:
            with urllib.request.urlopen(u, timeout=180) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 400: return {'error': 400}
            if e.code == 429: time.sleep(20 + 20 * attempt); continue
            time.sleep(3 + 5 * attempt)
        except Exception:
            time.sleep(3 + 5 * attempt)
    return None

# ---------------------------------------------------------------- 1. catalog
def job_catalog():
    out = {}
    for freq in ['daily', 'weekly', 'biweekly', 'monthly', 'quarterly']:
        fn = os.path.join(CAT, 'fred_nation_usa_%s.json' % freq)
        if os.path.exists(fn):
            out[freq] = json.load(open(fn)); log('catalog', freq, 'held', len(out[freq])); continue
        rows, off, k = [], 0, 0
        while True:
            d = get('tags/series', KEYS[k % len(KEYS)], tag_names='nation;usa;' + freq, limit=1000, offset=off, order_by='series_id')
            k += 1
            if not d or 'seriess' not in d: log('catalog', freq, 'failed at offset', off); break
            rows += d['seriess']; off += 1000
            if off >= d.get('count', 0): break
        json.dump(rows, open(fn, 'w'))
        out[freq] = rows; log('catalog', freq, len(rows))
    return out

# ---------------------------------------------------------------- 2. observations
def _held(sid):
    return any(os.path.exists(os.path.join(h, sid + '.csv')) for h in HELD) or os.path.exists(os.path.join(BULK, sid + '.csv.gz'))

def job_observe(cat):
    ids = []
    for freq in ['daily', 'weekly', 'biweekly', 'monthly', 'quarterly']:
        ids += [r['id'] for r in cat.get(freq, [])]
    ids = [s for s in dict.fromkeys(ids) if not _held(s)]
    log('observe: to fetch', len(ids))
    q = queue.Queue()
    for s in ids: q.put(s)
    done = [0]; t0 = time.time()
    def worker(key):
        while True:
            try: sid = q.get_nowait()
            except queue.Empty: return
            d = get('series/observations', key, series_id=sid)
            if d and 'observations' in d:
                obs = [o for o in d['observations'] if o.get('value') not in (None, '.', '')]
                tmp = os.path.join(BULK, '.' + sid + '.tmp')
                with gzip.open(tmp, 'wt', newline='') as f:
                    w = csv.writer(f); w.writerow(['date', 'value'])
                    for o in obs: w.writerow([o['date'], o['value']])
                os.replace(tmp, os.path.join(BULK, sid + '.csv.gz'))
            with _lk:
                done[0] += 1
                if done[0] % 500 == 0: log('observe %d/%d, %.1f min' % (done[0], len(ids), (time.time() - t0) / 60))
    th = [threading.Thread(target=worker, args=(k,), daemon=True) for k in KEYS]
    for t in th: t.start()
    for t in th: t.join()
    log('observe done', done[0])

# ---------------------------------------------------------------- 3. vintages
def leg_series():
    ids = set()
    for fn in ['/home/claude/ws/walk90.py', '/home/claude/w/late_screen.py', '/home/claude/w/screen_1969.py', '/home/claude/w/channel_fdr.py']:
        if not os.path.exists(fn): continue
        for m in re.findall(r"'([A-Z][A-Z0-9_]{2,}[0-9A-Z])'", open(fn).read()):
            if os.path.exists(os.path.join(ROOT, 'us', m + '.csv')): ids.add(m)
    extra = open('/home/claude/w/leg_series.txt').read().split() if os.path.exists('/home/claude/w/leg_series.txt') else []
    return sorted(ids | set(extra))

def job_vintages():
    ids = [s for s in leg_series() if not os.path.exists(os.path.join(VINT, s + '.csv.gz'))]
    log('vintages: to fetch', len(ids))
    q = queue.Queue()
    for s in ids: q.put(s)
    def worker(key):
        while True:
            try: sid = q.get_nowait()
            except queue.Empty: return
            vd = get('series/vintagedates', key, series_id=sid, limit=10000)
            if not vd or 'vintage_dates' not in vd: log('vintages', sid, 'no vintage dates'); continue
            vdates = vd['vintage_dates']
            rows, off = [], 0
            while True:
                d = get('series/observations', key, series_id=sid, realtime_start='1776-07-04', realtime_end='9999-12-31',
                        output_type=1, limit=100000, offset=off)
                if not d or 'observations' not in d: rows = None; break
                rows += d['observations']; off += 100000
                if off >= d.get('count', 0): break
            if rows is None: log('vintages', sid, 'failed'); continue
            tmp = os.path.join(VINT, '.' + sid + '.tmp')
            with gzip.open(tmp, 'wt', newline='') as f:
                w = csv.writer(f); w.writerow(['realtime_start', 'realtime_end', 'date', 'value'])
                for o in rows: w.writerow([o['realtime_start'], o['realtime_end'], o['date'], o['value']])
            os.replace(tmp, os.path.join(VINT, sid + '.csv.gz'))
            json.dump(vdates, open(os.path.join(VINT, sid + '.vintagedates.json'), 'w'))
            log('vintages', sid, len(vdates), 'vintages', len(rows), 'rows')
    th = [threading.Thread(target=worker, args=(k,), daemon=True) for k in KEYS[:6]]
    for t in th: t.start()
    for t in th: t.join()
    log('vintages done')

# ---------------------------------------------------------------- 4. peers (countries similar to the USA with complete data)
PEERS = {'gb': 'united kingdom', 'de': 'germany', 'jp': 'japan', 'au': 'australia', 'fr': 'france', 'ca': 'canada'}
def job_peers():
    for cc, tag in PEERS.items():
        dest = os.path.join(ROOT, 'peer_' + cc); os.makedirs(dest, exist_ok=True)
        cat = []
        for freq in ['daily', 'weekly', 'monthly', 'quarterly']:
            fn = os.path.join(CAT, 'fred_%s_%s.json' % (cc, freq))
            if os.path.exists(fn): rows = json.load(open(fn))
            else:
                rows, off, k = [], 0, 0
                while True:
                    d = get('tags/series', KEYS[k % len(KEYS)], tag_names=tag + ';' + freq, limit=1000, offset=off, order_by='series_id')
                    k += 1
                    if not d or 'seriess' not in d: log('peers catalog', cc, freq, 'failed at', off); break
                    rows += d['seriess']; off += 1000
                    if off >= d.get('count', 0): break
                json.dump(rows, open(fn, 'w'))
            log('peers catalog', cc, freq, len(rows)); cat += rows
        ids = [r['id'] for r in cat if not os.path.exists(os.path.join(dest, r['id'] + '.csv.gz'))]
        ids = list(dict.fromkeys(ids)); log('peers observe', cc, 'to fetch', len(ids))
        q = queue.Queue()
        for s in ids: q.put(s)
        done = [0]
        def worker(key):
            while True:
                try: sid = q.get_nowait()
                except queue.Empty: return
                d = get('series/observations', key, series_id=sid)
                if d and 'observations' in d:
                    obs = [o for o in d['observations'] if o.get('value') not in (None, '.', '')]
                    tmp = os.path.join(dest, '.' + sid + '.tmp')
                    with gzip.open(tmp, 'wt', newline='') as f:
                        w = csv.writer(f); w.writerow(['date', 'value'])
                        for o in obs: w.writerow([o['date'], o['value']])
                    os.replace(tmp, os.path.join(dest, sid + '.csv.gz'))
                with _lk:
                    done[0] += 1
                    if done[0] % 500 == 0: log('peers observe %s %d/%d' % (cc, done[0], len(ids)))
        th = [threading.Thread(target=worker, args=(k,), daemon=True) for k in KEYS]
        for t in th: t.start()
        for t in th: t.join()
        log('peers done', cc, done[0])

if __name__ == '__main__':
    jobs = sys.argv[1:] or ['catalog', 'observe', 'vintages']
    cat = None
    for j in jobs:
        if j == 'catalog': cat = job_catalog()
        elif j == 'observe':
            if cat is None: cat = job_catalog()
            job_observe(cat)
        elif j == 'vintages': job_vintages()
        elif j == 'peers': job_peers()
    log('all jobs done')
