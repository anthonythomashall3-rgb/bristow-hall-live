#!/usr/bin/env python3
"""Deterministic ALFRED vintage collector (no API key, no AI). Standard library + pandas.

For a FRED/ALFRED series id it
  1. reads the list of every vintage date from ALFRED's own download page (https://alfred.stlouisfed.org/series/downloaddata?seid=ID),
  2. downloads the series as it stood on each vintage date, in batches, from
     https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=ID,ID,...&vintage_date=d1,d2,...
  3. writes raw/<ID>/batch_<k>.csv (the bytes as served), panel/vintages/<ID>_vintages.csv (long: obs, vintage, value)
     and panel/vintages/<ID>_firstprint.csv (obs, first_release, first_print), and appends every file's sha256 to MANIFEST.csv.
A value's first print is the value in the first vintage in which the observation is present; its first_release is that
vintage date (ALFRED's vintage date = the day the data were published). Re-running is safe: batches already on disk are reused.
Usage: python3 collect/alfred_vintages.py ID [ID ...]
"""
import csv, hashlib, io, os, re, sys, time, urllib.request
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = 'curl/8'   # ALFRED (through this proxy) closes the connection for browser-like and custom agents; a plain client works
BATCH = 12   # ALFRED's graph CSV returns at most 12 series per request (checked 5 Oct 2026: 25 asked, 12 served)


def get(url, tries=6):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception as e:
            if k == tries - 1: raise
            time.sleep(2 ** (k + 1))


def sha(b): return hashlib.sha256(b).hexdigest()


def manifest(path, b, source):
    """the source ledger: one row per file written (url or derivation, sha256, time); MANIFEST.csv is rebuilt from disk by
    collect/manifest.py, which joins these rows"""
    m = os.path.join(HERE, 'raw', 'SOURCES.csv'); new = not os.path.exists(m)
    with open(m, 'a', newline='') as f:
        w = csv.writer(f)
        if new: w.writerow(['path', 'sha256', 'bytes', 'source', 'fetched_utc'])
        w.writerow([os.path.relpath(path, HERE), sha(b), len(b), source, time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())])


def vintage_dates(sid):
    b = get('https://alfred.stlouisfed.org/series/downloaddata?seid=%s' % sid)
    v = sorted(set(re.findall(rb'<option value="(\d{4}-\d{2}-\d{2})"', b)))
    return [x.decode() for x in v]


def collect(sid, offline=False):
    """offline: rebuild the tables from raw/alfred/<ID>/ (unpacked from raw/alfred_packed/<ID>.tar.gz) with no network"""
    rawd = os.path.join(HERE, 'raw', 'alfred', sid); os.makedirs(rawd, exist_ok=True)
    outd = os.path.join(HERE, 'panel', 'vintages'); os.makedirs(outd, exist_ok=True)
    vf = os.path.join(rawd, 'vintage_dates.txt')
    if offline:
        vds = open(vf).read().split()
    else:
        vds = vintage_dates(sid)
        open(vf, 'w').write('\n'.join(vds) + '\n')
    if not vds: raise SystemExit('%s: no vintage dates found' % sid)
    frames = []
    for k in range(0, len(vds), BATCH):
        chunk = vds[k:k + BATCH]
        p = os.path.join(rawd, 'batch_%s_%s.csv' % (chunk[0], chunk[-1]))
        if os.path.exists(p) and os.path.getsize(p) > 0:
            b = open(p, 'rb').read()
        else:
            url = ('https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=%s&vintage_date=%s'
                   % (','.join([sid] * len(chunk)), ','.join(chunk)))
            b = get(url); open(p, 'wb').write(b); manifest(p, b, url); time.sleep(1.0)
        d = pd.read_csv(io.BytesIO(b), na_values=['.', ''])
        d = d.rename(columns={d.columns[0]: 'obs'})
        cols = [c for c in d.columns if c != 'obs']
        # column names are ID_YYYYMMDD; check they are exactly the vintages asked for
        got = [c.rsplit('_', 1)[1] for c in cols]
        want = [x.replace('-', '') for x in chunk]
        if got != want:
            os.remove(p)   # never keep a short batch
            raise SystemExit('%s: batch columns %s do not match vintages %s' % (sid, got[:3], want[:3]))
        long = d.melt(id_vars='obs', var_name='col', value_name='value').dropna(subset=['value'])
        long['vintage'] = pd.to_datetime(long['col'].str.rsplit('_', n=1).str[1], format='%Y%m%d')
        frames.append(long[['obs', 'vintage', 'value']])
    V = pd.concat(frames)
    V['obs'] = pd.to_datetime(V['obs'])
    V = V.sort_values(['obs', 'vintage']).drop_duplicates(['obs', 'vintage'])
    vp = os.path.join(outd, '%s_vintages.csv' % sid)
    V.to_csv(vp, index=False, date_format='%Y-%m-%d'); manifest(vp, open(vp, 'rb').read(), 'derived from raw/alfred/%s' % sid)
    F = V.groupby('obs').first().reset_index().rename(columns={'vintage': 'first_release', 'value': 'first_print'})
    fp = os.path.join(outd, '%s_firstprint.csv' % sid)
    F.to_csv(fp, index=False, date_format='%Y-%m-%d'); manifest(fp, open(fp, 'rb').read(), 'derived from raw/alfred/%s' % sid)
    print('%s: %d vintages %s..%s; %d obs %s..%s; first prints from %s' % (
        sid, len(vds), vds[0], vds[-1], V['obs'].nunique(), V['obs'].min().date(), V['obs'].max().date(),
        F['first_release'].min().date()))


if __name__ == '__main__':
    off = '--offline' in sys.argv
    for s in [a for a in sys.argv[1:] if not a.startswith('--')]: collect(s, offline=off)
