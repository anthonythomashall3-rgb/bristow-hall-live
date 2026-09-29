"""STATE INSURED RATES AS PRINTED, 2 MAY 2020 - 22 AUGUST 2026, DATED (29 September 2026, cloud session).

A defect in collection 45 (reported, not written: the handoff's rule): state_first_prints_clean.csv carries 17,066 rows from
322 page-8 releases of 2 May 2020 - 22 August 2026 with ic_week_ended and iu_week_ended BLANK. From May 2020 the Department's
page 8 prints its weeks without the year ("INITIAL CLAIMS FILED DURING WEEK ENDED MAY 11 ... INSURED UNEMPLOYMENT FOR WEEK
ENDED MAY 4"), and 45's parser required ", YYYY". Any loader that drops rows without a week (v3.76's s2/state_rates_as_printed.py
does) reads FRED's current file for these weeks instead of the prints - the whole 2024 episode.

This writes a dated copy of those rows: ic_week_ended = the release file's week (45's 'wk'), iu_week_ended = that week less
seven days - both CHECKED against the header of every one of the 321 pages, re-read from
https://oui.doleta.gov/unemploy/page8/<yyyy>/<mmddyy>.html (raw/ here), and every state's rate on the page checked against 45's.
0223.html (the 2023 archive's misnamed copy of 120223.html, identical in all 53 rows) is dropped. Weeks absent from the
Department's archive: 2022-12-24 and the shutdown weeks 2025-08-30, 2025-09-20 .. 2025-11-01 (404; dark in real time).

Run from the inbox folder: python3 code/state_page8_dated_2020_2026.py   (standard library; reads 45 read-only)
Out: state_page8_2020_2026/state_iur_asprinted_2020_2026_dated.csv, state_page8_2020_2026/verification.json
"""
import csv, datetime as dt, html, json, os, re, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, '..', '45_dol_first_prints_2026-09', 'state_first_prints_clean.csv')
RAW = os.path.join(HERE, 'state_page8_2020_2026', 'raw')
OUT = os.path.join(HERE, 'state_page8_2020_2026', 'state_iur_asprinted_2020_2026_dated.csv')
MON = {m: i for i, m in enumerate(['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'], 1)}

def page(year, f):
    t = open(os.path.join(RAW, '%s_%s' % (year, f)), encoding='latin-1').read()
    t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', t)))
    m1 = re.search(r'INITIAL CLAIMS FILED DURING WEEK ENDED ([A-Z]+)\.? (\d+)', t, re.I)
    m2 = re.search(r'INSURED UNEMPLOYMENT FOR WEEK ENDED ([A-Z]+)\.? (\d+)', t, re.I)
    rates = {st.rstrip('*'): n.split()[6] for st, n in re.findall(
        r'([A-Z][a-z]+(?: [A-Z][a-z]+)*(?: of Columbia)?\*?) ((?:-?[\d,]+(?:\.\d+)? ){11}-?[\d,]+(?:\.\d+)?)', t)}
    return (MON[m1.group(1)[:3].upper()], int(m1.group(2))), (MON[m2.group(1)[:3].upper()], int(m2.group(2))), rates

rows = [r for r in csv.DictReader(open(SRC)) if not r['iu_week_ended'].strip()]
out, checks = [], dict(pages=0, header_ok=0, rates_compared=0, rates_equal=0, dropped_duplicate=0, problems=[])
seen = {}
for r in rows:
    if not r['wk']:
        checks['dropped_duplicate'] += 1; continue
    wk = dt.date.fromisoformat(r['wk']); iu = wk - dt.timedelta(days=7)
    key = (r['release_file'], r['wk'])
    if key not in seen:
        (icm, icd), (ium, iud), rates = page(wk.year, r['release_file'])
        ok = (icm, icd) == (wk.month, wk.day) and (ium, iud) == (iu.month, iu.day)
        seen[key] = (ok, rates); checks['pages'] += 1; checks['header_ok'] += ok
        if not ok: checks['problems'].append([r['release_file'], 'header', [icm, icd, ium, iud]])
    ok, rates = seen[key]
    if not ok: continue
    v = rates.get(r['state'])
    if v is not None:
        checks['rates_compared'] += 1
        if abs(float(v) - float(r['iur'])) < 1e-9: checks['rates_equal'] += 1
        else: checks['problems'].append([r['release_file'], r['state'], v, r['iur']])
    out.append(dict(r, ic_week_ended=wk.isoformat(), iu_week_ended=iu.isoformat(), date_basis='release file week; checked against the page header'))
with open(OUT, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
json.dump(checks, open(os.path.join(HERE, 'state_page8_2020_2026', 'verification.json'), 'w'), indent=1)
print('%d rows dated (%s to %s insured weeks); pages %d, headers ok %d; rates equal %d of %d; duplicate rows dropped %d; problems %d'
      % (len(out), min(x['iu_week_ended'] for x in out), max(x['iu_week_ended'] for x in out), checks['pages'], checks['header_ok'],
         checks['rates_equal'], checks['rates_compared'], checks['dropped_duplicate'], len(checks['problems'])))
if checks['problems'] or checks['header_ok'] != checks['pages']: sys.exit(1)
