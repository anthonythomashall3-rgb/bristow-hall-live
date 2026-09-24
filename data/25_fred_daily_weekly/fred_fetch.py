"""Fetch every observation of every series in a FRED tag index (3 September 2026; Anthony: "Fetch ALL
daily data!! And ALL weekly data!!!").

    python3 fred_fetch.py daily      -> lab/data/fred_daily/<ID>.csv  (+ _INDEX.csv, _MANIFEST.sha256, _fetch.log)
    python3 fred_fetch.py weekly     -> lab/data/fred_weekly/
    python3 fred_fetch.py biweekly   -> lab/data/fred_biweekly/

Order: series whose history begins on or before 1990 first (they can be read at the 1951, 1952 and 1967
disturbances and at most of the twelve), then the rest by FRED popularity.  Resumable: a series whose
file exists is skipped.  The key comes from lab/secrets/local.env and is never written anywhere.
FRED allows 120 requests a minute; this runs 110.  Transport is curl (python's own HTTP fails through
the proxy).  Each CSV: date,value with FRED's '.' as an empty cell; the current vintage as of the
fetch day (the `updated` column of the index is FRED's last-updated stamp for the series).
"""
import sys, os, json, time, hashlib, subprocess, threading, csv
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

FREQ = sys.argv[1]
ROOT = '/home/claude/lab/data'
OUT = f'{ROOT}/fred_{FREQ}'; os.makedirs(OUT, exist_ok=True)
RATE = int(sys.argv[2]) if len(sys.argv) > 2 else 110
KEY = None
for line in open('/home/claude/lab/secrets/local.env'):
    if line.startswith('FRED_API_KEY='): KEY = line.strip().split('=', 1)[1].strip().strip('"')
assert KEY, 'no key'
idx = pd.read_csv(f'{ROOT}/fred_{FREQ}_index.csv')
idx['s'] = pd.to_datetime(idx['start'], errors='coerce')
idx['early'] = idx['s'] <= pd.Timestamp('1990-12-31')
idx = idx.sort_values(['early', 'pop'], ascending=[False, False]).reset_index(drop=True)
todo = [r for r in idx.itertuples() if not os.path.exists(f'{OUT}/{r.id}.csv')]
log = open(f'{OUT}/_fetch.log', 'a')
print(f'{FREQ}: {len(idx)} series in the index, {len(todo)} to fetch', file=log, flush=True)

# token bucket: 110 requests a minute
lock = threading.Lock(); stamps = []
def wait_turn():
    while True:
        with lock:
            now = time.time()
            while stamps and now - stamps[0] > 60: stamps.pop(0)
            if len(stamps) < RATE:
                stamps.append(now); return
        time.sleep(0.25)

def fetch(sid):
    url = (f'https://api.stlouisfed.org/fred/series/observations?series_id={sid}&api_key={KEY}'
           f'&file_type=json&observation_start=1776-07-04&limit=100000')
    for attempt in range(4):
        wait_turn()
        r = subprocess.run(['curl', '-sS', '--max-time', '120', url], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.startswith('{'):
            j = json.loads(r.stdout)
            if 'observations' in j:
                obs = j['observations']
                if j.get('count', 0) > len(obs):    # paginate (a daily series can exceed 100000? no - but be safe)
                    off = len(obs)
                    while off < j['count']:
                        wait_turn()
                        r2 = subprocess.run(['curl', '-sS', '--max-time', '120', url + f'&offset={off}'], capture_output=True, text=True)
                        j2 = json.loads(r2.stdout); obs += j2['observations']; off += len(j2['observations'])
                        if not j2['observations']: break
                return obs, None
            return None, j.get('error_message', r.stdout[:200])
        time.sleep(5 * (attempt + 1))
    return None, (r.stderr or r.stdout)[:200]

def one(r):
    obs, err = fetch(r.id)
    path = f'{OUT}/{r.id}.csv'
    if obs is None:
        print(f'FAIL {r.id}: {err}', file=log, flush=True); return (r.id, None)
    with open(path, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['date', 'value'])
        for o in obs: w.writerow([o['date'], '' if o['value'] == '.' else o['value']])
    vals = [o for o in obs if o['value'] != '.']
    n = len(vals); first = vals[0]['date'] if vals else ''; last = vals[-1]['date'] if vals else ''
    return (r.id, (n, first, last))

done = 0; t0 = time.time()
with ThreadPoolExecutor(max_workers=6) as ex:
    for sid, res in ex.map(one, todo):
        done += 1
        if done % 100 == 0:
            print(f'{done}/{len(todo)} after {(time.time() - t0) / 60:.1f} min', file=log, flush=True)
print(f'fetched {done} in {(time.time() - t0) / 60:.1f} min', file=log, flush=True)

# index and manifest over everything present
rows = []; man = open(f'{OUT}/_MANIFEST.sha256', 'w')
for r in idx.itertuples():
    path = f'{OUT}/{r.id}.csv'
    if not os.path.exists(path): continue
    b = open(path, 'rb').read(); h = hashlib.sha256(b).hexdigest(); man.write(f'{h}  {r.id}.csv\n')
    s = pd.read_csv(path)
    v = s.dropna()
    rows.append(dict(id=r.id, title=r.title, freq=r.freq, units=r.units, sa=r.sa, pop=r.pop, fred_start=r.start, fred_end=r.end,
                     fred_updated=r.updated, nobs=len(v), first_obs=v['date'].iloc[0] if len(v) else '', last_obs=v['date'].iloc[-1] if len(v) else '',
                     sha256=h, fetched=time.strftime('%Y-%m-%d')))
man.close()
pd.DataFrame(rows).to_csv(f'{OUT}/_INDEX.csv', index=False)
print(f'index: {len(rows)} files', file=log, flush=True)
