#!/usr/bin/env python3
"""1150 (19 Nov 2026; no AI): QCEW county jobs by industry for the stress map's county panel, kept to the newest quarter BLS has published.
Held: 1032 data/qcew_industry_county/<YEAR>.csv.gz (header fips,own,ind,year,qtr,m1,m2,m3,disc): for every county of the 50 States and DC the
total (industry 10; ownership 0 all, 1 federal, 2 State, 3 local, 5 private) and the private supersectors (1011-1029, ownership 5), monthly
employment of each quarter with the BLS disclosure code (N = withheld). A year with no file is read whole from the BLS file
https://data.bls.gov/cew/data/files/<Y>/csv/<Y>_qtrly_by_industry.zip (only the 12 industry members are read, by byte range; four years at a
time); later quarters come from the BLS QCEW open-data API (https://data.bls.gov/cew/data/api/<Y>/<Q>/industry/<code>.csv), the same rows.
A 404 = not published yet. Add-only; a quarter is added whole (all 12 industry files read) or not at all.
Writes out/qcew_county_ind_refresh_1150.json."""
import os, sys, io, re, csv, gzip, json, time, datetime
C = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); ROOT = os.path.dirname(C)
QD = os.path.join(ROOT, '1032_state_recession_indicator_all_states_dc_2026-11-09', 'data', 'qcew_industry_county')
sys.path.insert(0, os.path.join(ROOT, '_shared')); import fastfetch
CODES = ['10', '1011', '1012', '1013', '1021', '1022', '1023', '1024', '1025', '1026', '1027', '1029']
HEAD = ['fips', 'own', 'ind', 'year', 'qtr', 'm1', 'm2', 'm3', 'disc']
def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
def keep(r, code):
    f = r['area_fips']
    if len(f) != 5 or not f.isdigit() or f.endswith('000') or f.endswith('999') or f[:2] > '56': return False
    a = r['agglvl_code']; return (code == '10' and a in ('70', '71')) or (code != '10' and a == '73' and r['own_code'] == '5')
def held(y):
    p = os.path.join(QD, f'{y}.csv.gz')
    if not os.path.exists(p): return []
    with gzip.open(p, 'rt', newline='') as f: return list(csv.reader(f))[1:]
def last_held():
    ys = sorted(int(m.group(1)) for f in os.listdir(QD) for m in [re.fullmatch(r'(\d{4})\.csv\.gz', f)] if m)
    for y in reversed(ys):
        h = held(y)
        if h: return y, max(int(r[4]) for r in h)
    raise SystemExit('no county industry file held')
def api_quarter(y, q):
    rows = []
    for c in CODES:
        u = f'https://data.bls.gov/cew/data/api/{y}/{q}/industry/{c}.csv'
        try: b = fastfetch.fetch_job(u, who='1052', fresh_days=0, timeout=180)
        except Exception as e:
            if c == '1029' and getattr(e, 'code', None) == 404: continue
            return None, ('not published (404)' if getattr(e, 'code', None) == 404 else f'{type(e).__name__} {e}'[:160])
        for r in csv.DictReader(io.StringIO(b.decode('latin-1'))):
            if keep(r, c): rows.append([r['area_fips'], r['own_code'], c, str(int(r['year'])), str(int(r['qtr'])), r['month1_emplvl'], r['month2_emplvl'], r['month3_emplvl'], r['disclosure_code'].strip()])
    return sorted(rows), 'ok'
def write_year(y, rows):
    p = os.path.join(QD, f'{y}.csv.gz')
    with gzip.GzipFile(p + '.tmp1150', 'wb', mtime=0) as g:
        w = io.TextIOWrapper(g, newline=''); cw = csv.writer(w); cw.writerow(HEAD); cw.writerows(sorted(rows)); w.flush()
    os.replace(p + '.tmp1150', p)
def zip_year(y):
    from remotezip import RemoteZip
    for k in range(3):
        try:
            z = RemoteZip(f'https://data.bls.gov/cew/data/files/{y}/csv/{y}_qtrly_by_industry.zip'); rows = []; got = set()
            for i in z.infolist():
                b = i.filename.split('/')[-1].split(' ')
                if len(b) < 2 or b[1] not in CODES: continue
                got.add(b[1])
                for r in csv.DictReader(io.TextIOWrapper(z.open(i), encoding='latin-1')):
                    if keep(r, b[1]): rows.append([r['area_fips'], r['own_code'], b[1], str(int(r['year'])), str(int(r['qtr'])), r['month1_emplvl'], r['month2_emplvl'], r['month3_emplvl'], r['disclosure_code'].strip()])
            if not set(CODES) - {'1029'} <= got or len(rows) < 100000: return y, f'incomplete ({len(got)} industries, {len(rows)} rows), not kept'
            write_year(y, rows); return y, f'{len(rows)} rows from the BLS file'
        except Exception as e:
            why = f'{type(e).__name__} {e}'[:160]; time.sleep(5)
    return y, why
def main():
    os.makedirs(QD, exist_ok=True); R = dict(run=time.strftime('%Y-%m-%dT%H:%M:%S%z'), added=[], changed=False, years_read=[])
    miss = [y for y in range(1990, datetime.date.today().year) if not os.path.exists(os.path.join(QD, f'{y}.csv.gz'))]
    if miss:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(4) as ex:
            for y, why in ex.map(zip_year, miss): log(y, why); R['years_read'].append(f'{y}: {why}'); R['changed'] = True
    y, q = last_held(); R['held_before'] = f'{y}Q{q}'
    today = datetime.date.today(); cy, cq = today.year, (today.month - 1) // 3 + 1
    while True:
        y, q = (y, q + 1) if q < 4 else (y + 1, 1)
        if (y, q) > (cy, cq): break
        n, why = api_quarter(y, q); log(f'{y}Q{q}', why)
        if n is None: R['next'] = f'{y}Q{q}: {why}'; break
        if len(n) < 40000: R['next'] = f'{y}Q{q}: only {len(n)} rows, not kept'; break
        write_year(y, [r for r in held(y) if int(r[4]) != q] + n); R['added'].append(f'{y}Q{q} ({len(n)} rows)'); R['changed'] = True
    R['held_after'] = '%dQ%d' % last_held()
    os.makedirs(os.path.join(C, 'out'), exist_ok=True); json.dump(R, open(os.path.join(C, 'out', 'qcew_county_ind_refresh_1150.json'), 'w'), indent=1); log(json.dumps(R)); return 0
if __name__ == '__main__': sys.exit(main())
