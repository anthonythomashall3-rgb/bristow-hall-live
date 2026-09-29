"""Polite fetcher: saves every response body under raw/, appends a MANIFEST.csv row, keeps >=1.5 s between
requests to the same host (tracked across processes via a small state file).
Usage as a module: from fetch import get; path, status, body = get(url, name)
Usage CLI: python3 fetch.py URL NAME"""
import os, sys, time, json, hashlib, csv, subprocess, urllib.parse, datetime, fcntl
W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps'
RAW = f'{W}/raw'
MAN = f'{W}/MANIFEST.csv'
STATE = f'{W}/.host_times.json'
UA = 'curl/8.5.0 (research; weekly UI first prints)'
GAP = 1.5
GAPS = {'fraser.stlouisfed.org': 10.5}


def _wait(host):
    with open(STATE + '.lock', 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            st = json.load(open(STATE))
        except Exception:
            st = {}
        last = st.get(host, 0)
        now = time.time()
        gap = GAPS.get(host, GAP)
        if now - last < gap:
            time.sleep(gap - (now - last))
        st[host] = time.time()
        json.dump(st, open(STATE, 'w'))


def get(url, name, ua=UA, extra=None, force=False, gz=False):
    os.makedirs(RAW, exist_ok=True)
    path = f'{RAW}/{name}'
    if gz and os.path.exists(path + '.gz') and not force:
        import gzip
        return path + '.gz', 'cached', gzip.open(path + '.gz').read()
    if os.path.exists(path) and os.path.getsize(path) > 0 and not force:
        return path, 'cached', open(path, 'rb').read()
    host = urllib.parse.urlparse(url).netloc
    _wait(host)
    cmd = ['curl', '-sL', '--compressed', '--max-time', '60', '-A', ua, '-o', path, '-w', '%{http_code}', url]
    if extra:
        cmd[1:1] = extra
    try:
        status = subprocess.run(cmd, capture_output=True, text=True, timeout=90).stdout.strip()
    except Exception as e:
        status = f'ERR {e}'
    body = open(path, 'rb').read() if os.path.exists(path) else b''
    new = not os.path.exists(MAN)
    with open(MAN, 'a', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['raw_file', 'url', 'fetched_utc', 'http_status', 'bytes', 'sha256'])
        w.writerow([f'raw/{name}' + ('.gz' if gz and body else ''), url, datetime.datetime.utcnow().isoformat(timespec='seconds'), status, len(body),
                    hashlib.sha256(body).hexdigest()])
    if gz and body:
        import gzip
        with gzip.open(path + '.gz', 'wb') as g:
            g.write(body)
        os.remove(path)
        path = path + '.gz'
    return path, status, body


if __name__ == '__main__':
    p, s, b = get(sys.argv[1], sys.argv[2], force=len(sys.argv) > 3)
    print(s, len(b), p)
