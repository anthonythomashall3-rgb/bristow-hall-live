#!/usr/bin/env python3
"""The quality gate for the standing collector (collection 191), added 18 September 2026.

Until now nothing checked that a collected file was still USABLE. The dangerous failure is silent: a source keeps
answering 200 while its content freezes, or starts returning an error page, and the collector logs a success every
cycle. Anthony's standing rule is that every dataset carries its true first and last observation, its count and its
share of repeated values; this recomputes those from the files themselves and says which ones have stopped being
data.

What it reads: every two-column derived series (date,value) under warehouse/<source>/derived/, and every raw file
for the shape checks. Nothing is changed or deleted; it only reports.

What it writes:
  logs/AUDIT.csv    one row per series: source, series, n_obs, first, last, days_stale, pct_repeated, verdict
  logs/AUDIT.txt    the short version: what is wrong, worst first, with the counts
  logs/AUDIT_flags.csv   only the rows that are not 'ok', for the collector to notify on

The verdicts, in the order they are tested:
  empty          the file has no observations at all
  not_data       the file begins with HTML or an error payload (a "soft 404": 200 with a page instead of a table)
  stalled        the newest observation is older than the series' own typical gap times stale_factor, plus a grace
                 period; a weekly series silently frozen for two months is the case this is built to catch
  frozen         the last quarter of the observations carry a single repeated value
  flat           more than 98 per cent of all values are repeats of the previous one (a forward-filled series
                 masquerading as a high-frequency one, the BIS trap in the collection rule)
  short          fewer than min_obs observations
  ok             none of the above

Run:  python3 audit_warehouse.py            audit everything
      python3 audit_warehouse.py fred_bulk  audit one source folder
It is also registered as the job `audit`, which the collector runs on its slow lane.
"""
import re, os, sys, csv, gzip, glob, json, time, statistics
from datetime import date, datetime, timedelta

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
WH = os.path.join(ROOT, 'warehouse')
LOGS = os.path.join(ROOT, 'logs')
MIN_OBS = 8
STALE_FACTOR = 4.0          # newest observation older than this many typical gaps counts as stalled
STALE_GRACE_DAYS = 21       # ... plus this, so a monthly series is never called stale for a late release
HTML_HEADS = (b'<!DOCTYPE', b'<html', b'<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE', b'{"error', b'<HTML')


DATE_HEADS = ('month_date_yyyymm', 'date_name', 'time', 'yr', 'begin date', 'obligation_end_date_yyyymmdd',
              'date', 'time_period', 'record_date', 'observation_date', 'mapdate', 'week', 'month', 'period',
              'time', 'realtime_start', 'valid_from', 'ref_date', 'datetime', 'file_date', 'week_ended')


MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
MONTHNUM = {m: i + 1 for i, m in enumerate(MONTHS)}
NAMED = re.compile(r'(?i)^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?[ ,]+((?:19|20)\d{2})$')
YEARCOLON = re.compile(r'(?i)^((?:19|20)\d{2})[:/ ]+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*$')
MONYY = re.compile(r'(?i)^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[-/ ](\d{2})$')
ISOWEEK = re.compile(r'^((?:19|20)\d{2})-W(\d{1,2})$')
YMTAG = re.compile(r'(?i)^((?:19|20)\d{2})[MQ](\d{1,2})$')


def _is_date(x):
    x = (x or '').strip().strip('"')
    if len(x) >= 10 and x[4] == '-' and x[7] == '-' and x[:4].isdigit():
        return True                                   # 2026-09-05 and 2026-09-05T00:00:00.000, which every open-data
                                                      # portal serves and which the reader had been calling not a date
    if len(x) == 10 and x[4] in '-/' and x[7] in '-/':
        return True
    if len(x) == 10 and x[2] in '/.' and x[5] in '/.' and x[6:].isdigit():
        return True                                   # 01/02/1990 and 02.01.1990: the CBOE and several European files
    if len(x) == 8 and x.isdigit():
        return True
    if len(x) == 7 and x[4] == '-' and x[:4].isdigit():
        return True                                   # 2026-09 and 2026-M09 after normalising
    if len(x) == 8 and x[4] == '-' and x[5] in 'MQ':
        return True
    if len(x) == 6 and x.isdigit() and '1900' < x[:4] < '2100' and '01' <= x[4:] <= '12':
        return True                                   # 202608, the listing files
    if NAMED.match(x) or YEARCOLON.match(x) or ISOWEEK.match(x) or YMTAG.match(x) or MONYY.match(x):
        return True                                   # January 1986 | 2026:August | 1998-W53 | 2013M11
    return False


def _norm_date(x):
    x = (x or '').strip().strip('"')
    m = NAMED.match(x)
    if m: return '%s-%02d-01' % (m.group(2), MONTHNUM[m.group(1).lower()[:3]])
    m = MONYY.match(x)
    if m:
        yy = int(m.group(2)); y = 1900 + yy if yy > 40 else 2000 + yy
        return '%d-%02d-01' % (y, MONTHNUM[m.group(1).lower()[:3]])
    m = YEARCOLON.match(x)
    if m: return '%s-%02d-01' % (m.group(1), MONTHNUM[m.group(2).lower()[:3]])
    m = YMTAG.match(x)
    if m:
        n = int(m.group(2))
        return '%s-%02d-01' % (m.group(1), min(12, n * 3 if x[4].upper() == 'Q' else n))
    m = ISOWEEK.match(x)
    if m:
        try:
            import datetime
            return (datetime.date.fromisocalendar(int(m.group(1)), min(52, int(m.group(2))), 6)).isoformat()
        except Exception:
            return '%s-01-01' % m.group(1)
    if len(x) == 6 and x.isdigit() and '1900' < x[:4] < '2100':
        return '%s-%s-01' % (x[:4], x[4:])
    if len(x) > 10 and x[4] == '-' and x[7] == '-' and x[:4].isdigit():
        return x[:10]
    if len(x) == 10 and x[2] in '/.' and x[5] in '/.' and x[6:].isdigit():
        a, b, y = x[:2], x[3:5], x[6:]
        return '%s-%s-%s' % (y, a, b) if x[2] == '/' else '%s-%s-%s' % (y, b, a)
    if len(x) == 8 and x.isdigit():
        return '%s-%s-%s' % (x[:4], x[4:6], x[6:])
    if len(x) == 8 and x[4] == '-' and x[5] in 'MQ':
        return '%s-%02d-01' % (x[:4], int(x[6:]) * (3 if x[5] == 'Q' else 1))
    if len(x) == 7:
        return x + '-01'
    return x[:10].replace('/', '-')


def read_pairs(path, sniff_rows=400):
    """(date, value) pairs from a series file.

    A two-column date,value CSV is read directly. A WIDE table - the raw files, which are most of the warehouse - is
    read by finding its date column (by header name, else by which column parses as dates in most of a sample) and
    taking the row count and the span from it. Without this every wide table was reported 'empty', which is a false
    alarm, and a gate that cries wolf is worse than no gate (found and fixed the hour it was written, 18 Sep 2026).
    Returns [] only when the file really carries no dated rows."""
    op = gzip.open if path.endswith('.gz') else open
    try:
        with op(path, 'rt', encoding='utf-8', errors='replace', newline='') as f:
            first = f.readline()
            if not first:
                return []
            # the Bundesbank and several European services serve semicolons; a reader that assumes commas called
            # six real files empty (fixed 18 Sep 2026)
            delim = ';' if first.count(';') > first.count(',') else ('\t' if first.count('\t') > first.count(',') else ',')
            f.seek(0)
            rd = csv.reader(f, delimiter=delim)
            try:
                head = next(rd)
            except StopIteration:
                return []
            # Some files open with a title and a note before the header (the disaster file has two such lines).
            # The header is the first line that has at least three fields; up to eight lines are passed over.
            tries = 0
            while len(head) < 3 and tries < 8:
                try: head = next(rd)
                except StopIteration: return []
                tries += 1
            if len(head) == 2:
                out = []
                for p in rd:
                    if len(p) == 2 and p[0] and p[1]:
                        out.append((_norm_date(p[0]), p[1]))
                return out
            # A table with a year column and twelve month columns (the Census business-formation files and several
            # others) carries no date column at all; every month cell is an observation (18 Sep 2026).
            # A table whose DATES ARE ITS COLUMN HEADERS (the house-price and listing files): each dated column is an
            # observation, and the row count is not what matters (18 Sep 2026).
            dcols = [(i, h.strip().strip('"')) for i, h in enumerate(head) if _is_date(h.strip().strip('"'))]
            if len(dcols) >= 6:
                out = []
                for p in rd:
                    for i, h in dcols:
                        if i < len(p) and p[i].strip():
                            out.append((_norm_date(h), p[i]))
                    if len(out) > 400000: break
                return out
            # A table dated by a YEAR column plus a period column (year+week for the business-application files,
            # year+quarter for the workforce indicators and the covered-employment census). No date column exists in
            # any of them and every one was being called empty (18 Sep 2026).
            full = [h.strip().strip('"').lower() for h in head]
            qcols = [(i, k + 1) for k, q in enumerate(('q1', 'q2', 'q3', 'q4')) for i, h in enumerate(full) if h == q]
            if 'year' in full and len(qcols) >= 3:
                yi = full.index('year'); out = []
                for p in rd:
                    if yi >= len(p) or not p[yi].strip()[:4].isdigit(): continue
                    y = p[yi].strip()[:4]
                    for ci, qn in qcols:
                        if ci < len(p) and p[ci].strip():
                            out.append(('%s-%02d-01' % (y, qn * 3), p[ci]))
                if out: return out
            di_ = next((i for i, h in enumerate(full) if h == 'day'), None)
            mi_ = next((i for i, h in enumerate(full) if h == 'month'), None)
            yi_ = next((i for i, h in enumerate(full) if h in ('year', 'yr', 'yyyy', 'calendar_year')), None)
            if None not in (di_, mi_, yi_):
                out = []
                for p in rd:
                    if max(di_, mi_, yi_) >= len(p): continue
                    d_, m_, y_ = p[di_].strip(), p[mi_].strip(), p[yi_].strip()[:4]
                    if not (d_.isdigit() and m_.isdigit() and y_.isdigit()): continue
                    vi = next((k for k in range(len(p) - 1, -1, -1)
                               if k not in (di_, mi_, yi_) and p[k].strip()), None)
                    if vi is None: continue
                    out.append(('%s-%02d-%02d' % (y_, int(m_), int(d_)), p[vi]))
                if out: return out
            mi = next((i for i, h in enumerate(full) if h in ('month', 'month_name', 'monthname')), None)
            yi2 = next((i for i, h in enumerate(full) if h in ('year', 'yr', 'yyyy', 'calendar_year')), None)
            if mi is not None and yi2 is not None:
                out = []
                for p in rd:
                    if mi >= len(p) or yi2 >= len(p): continue
                    mo = p[mi].strip().strip('"').lower()[:3]; y = p[yi2].strip()[:4]
                    if mo not in MONTHNUM or not y.isdigit(): continue
                    vi = next((k for k in range(len(p) - 1, -1, -1) if k not in (mi, yi2) and p[k].strip()), None)
                    if vi is None: continue
                    out.append(('%s-%02d-01' % (y, MONTHNUM[mo]), p[vi]))
                if out: return out
            if 'year' in full:
                yi = full.index('year')
                for pname, mult in (('week', 7), ('quarter', 91), ('qtr', 91), ('month', 30), ('period', 30)):
                    if pname in full:
                        pi = full.index(pname); out = []
                        for p in rd:
                            if yi >= len(p) or pi >= len(p): continue
                            y, n = p[yi].strip()[:4], re.sub(r'[^0-9]', '', p[pi])[:2]
                            if not (y.isdigit() and n.isdigit()): continue
                            vi = next((k for k in range(len(p) - 1, -1, -1) if k not in (yi, pi)), pi)
                            doy = min(365, max(1, (int(n) - 1) * mult + 1))
                            out.append(('%s-%02d-%02d' % (y, min(12, (doy // 31) + 1), min(28, (doy % 31) + 1)),
                                        p[vi] if vi < len(p) else ''))
                            if len(out) > 400000: break
                        if out: return out
            low = [h.strip().strip('"').lower()[:3] for h in head]
            if 'yea' in low and sum(1 for m in MONTHS if m in low) >= 6:
                yi = low.index('yea'); mi = [(low.index(m), k + 1) for k, m in enumerate(MONTHS) if m in low]
                out = []
                for p in rd:
                    if yi >= len(p) or not p[yi].strip()[:4].isdigit(): continue
                    y = p[yi].strip()[:4]
                    for ci, mn in mi:
                        if ci < len(p) and p[ci].strip():
                            out.append(('%s-%02d-01' % (y, mn), p[ci]))
                return out
            sample = []
            for i, p in enumerate(rd):
                if i >= sniff_rows: break
                if p: sample.append(p)
            if not sample:
                return []
            di = None
            named = [i for i, h in enumerate(head) if h.strip().strip('"').lower() in DATE_HEADS]
            best_named, best_hits = None, 0
            for i in named:                       # a file with both a 'year' and a 'date' column: take the one that
                n = sum(1 for p in sample if i < len(p) and _is_date(p[i]))   # actually carries dates (18 Sep 2026)
                if n > best_hits: best_named, best_hits = i, n
            if best_named is not None and best_hits >= 0.6 * len(sample): di = best_named
            if di is None:
                best, score = None, 0
                for i in range(min(len(head), 12)):
                    n = sum(1 for p in sample if i < len(p) and _is_date(p[i]))
                    if n > score: best, score = i, n
                if score >= 0.6 * len(sample): di = best
            if di is None:
                return []
            vi = next((i for i in range(len(head) - 1, -1, -1) if i != di), di)
            out = [(_norm_date(p[di]), (p[vi] if vi < len(p) else '')) for p in sample if di < len(p) and _is_date(p[di])]
            for p in rd:
                if di < len(p) and _is_date(p[di]):
                    out.append((_norm_date(p[di]), p[vi] if vi < len(p) else ''))
            return out
    except (OSError, csv.Error):
        return []


def looks_like_page(path):
    try:
        op = gzip.open if path.endswith('.gz') else open
        with op(path, 'rb') as f:
            head = f.read(200).lstrip()
        return any(head.startswith(h) for h in HTML_HEADS)
    except OSError:
        return False


def days_between(a, b):
    try:
        return (date.fromisoformat(b) - date.fromisoformat(a)).days
    except ValueError:
        return None


def typical_gap(dates):
    """The median gap in days between consecutive observations, from the last hundred."""
    ds = [d for d in dates[-101:] if len(d) == 10]
    gaps = [g for g in (days_between(ds[i], ds[i + 1]) for i in range(len(ds) - 1)) if g and g > 0]
    return statistics.median(gaps) if gaps else None


def audit_series(path, today):
    rel = os.path.relpath(path, WH)
    source = rel.split(os.sep)[0]
    name = os.path.basename(path).replace('.csv.gz', '').replace('.csv', '')
    row = {'source': source, 'series': name, 'file': rel, 'n_obs': 0, 'first': '', 'last': '',
           'days_stale': '', 'typical_gap_days': '', 'pct_repeated': '', 'n_cols': 0, 'verdict': 'ok', 'note': ''}
    try:
        op = gzip.open if path.endswith('.gz') else open
        with op(path, 'rt', encoding='utf-8', errors='replace', newline='') as f:
            h = f.readline()
            row['n_cols'] = 1 + max(h.count(','), h.count(';'), h.count('\t'))
    except Exception:
        pass
    if looks_like_page(path):
        row['verdict'] = 'not_data'; row['note'] = 'the file begins with a web page, not data'
        return row
    pairs = read_pairs(path)
    if not pairs:
        row['verdict'] = 'empty'; row['note'] = 'no observations'
        return row
    pairs.sort()
    dates = [d for d, v in pairs]; vals = [v for d, v in pairs]
    row['n_obs'] = len(pairs); row['first'] = dates[0]; row['last'] = dates[-1]
    rep = sum(1 for i in range(1, len(vals)) if vals[i] == vals[i - 1])
    row['pct_repeated'] = round(100.0 * rep / max(1, len(vals) - 1), 1)
    gap = typical_gap(dates)
    if gap: row['typical_gap_days'] = int(gap)
    stale = days_between(dates[-1], today)
    if stale is not None: row['days_stale'] = stale
    tail = vals[max(0, int(len(vals) * 0.75)):]
    if len(pairs) < MIN_OBS:
        row['verdict'] = 'short'; row['note'] = 'fewer than %d observations' % MIN_OBS
    elif gap and stale is not None and stale > gap * STALE_FACTOR + STALE_GRACE_DAYS:
        row['verdict'] = 'stalled'
        row['note'] = 'newest observation %s is %d days old; this series normally moves every %d days' % (dates[-1], stale, gap)
    elif len(tail) >= 8 and len(set(tail)) == 1:
        row['verdict'] = 'frozen'; row['note'] = 'the last quarter of the series is one repeated value (%s)' % tail[0][:20]
    elif row['pct_repeated'] > 98.0 and len(pairs) > 50 and row['n_cols'] == 2:
        row['verdict'] = 'flat'; row['note'] = 'nearly every value repeats the one before: a lower-frequency series carried forward'
    return row


def main():
    only = sys.argv[1:] or None
    today = date.today().isoformat()
    paths = []
    for d in sorted(os.listdir(WH)) if os.path.isdir(WH) else []:
        if only and d not in only: continue
        base = os.path.join(WH, d)
        if not os.path.isdir(base): continue
        paths += sorted(glob.glob(os.path.join(base, 'derived', '*.csv'))
                        + glob.glob(os.path.join(base, 'derived', '*.csv.gz'))
                        + glob.glob(os.path.join(base, '*.csv'))
                        + glob.glob(os.path.join(base, '*.csv.gz')))
    paths = [p for p in paths if os.sep + 'vintages' + os.sep not in p]
    rows = []
    t0 = time.time()
    for p in paths:
        try:
            rows.append(audit_series(p, today))
        except Exception as e:
            rows.append({'source': os.path.relpath(p, WH).split(os.sep)[0], 'series': os.path.basename(p), 'file': os.path.relpath(p, WH),
                         'n_obs': 0, 'first': '', 'last': '', 'days_stale': '', 'typical_gap_days': '', 'pct_repeated': '', 'n_cols': 0,
                         'verdict': 'unreadable', 'note': type(e).__name__ + ' ' + str(e)[:80]})
    cols = ['source', 'series', 'file', 'n_obs', 'first', 'last', 'days_stale', 'typical_gap_days', 'pct_repeated', 'n_cols', 'verdict', 'note']
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, 'AUDIT.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    bad = [r for r in rows if r['verdict'] != 'ok']
    bad.sort(key=lambda r: (r['verdict'], -(r['days_stale'] if isinstance(r['days_stale'], int) else 0)))
    with open(os.path.join(LOGS, 'AUDIT_flags.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(bad)
    counts = {}
    for r in rows: counts[r['verdict']] = counts.get(r['verdict'], 0) + 1
    L = ['Warehouse audit - %s' % datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
         '%d series read in %.0f s from %d source folders' % (len(rows), time.time() - t0, len({r['source'] for r in rows})),
         '', 'verdicts: ' + ', '.join('%s %d' % (k, v) for k, v in sorted(counts.items(), key=lambda x: -x[1])), '']
    if bad:
        L.append('WHAT IS WRONG (worst first; the full list is AUDIT_flags.csv)')
        for r in bad[:60]:
            L.append('  %-9s %-22s %-34s %s' % (r['verdict'], r['source'][:22], r['series'][:34], r['note'][:80]))
        if len(bad) > 60: L.append('  ... and %d more' % (len(bad) - 60))
    else:
        L.append('Nothing is wrong: every series carries observations, moves on its own schedule and is not a page.')
    open(os.path.join(LOGS, 'AUDIT.txt'), 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L[:12]))
    return len(bad)


if __name__ == '__main__':
    main()
