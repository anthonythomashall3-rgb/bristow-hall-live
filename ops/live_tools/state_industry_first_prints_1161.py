#!/usr/bin/env python3
"""LIVE TOOLS (collection 1161, 21 Nov 2026; no AI): keep "State payrolls by industry, as first published" current.

1032 data/state_industry_releases_1994_2026_a168.csv (published, ref_month, st, group, m1, m0: the State Employment and Unemployment
release's table of payrolls by State and industry, seasonally adjusted, thousands; m0 = the month as first published, m1 = the month
before as revised in the same release) was built once from the release texts and never refreshed, so the day after each State release
the source gate found it a month behind and held every full build (21 Nov 2026: September shown, October published 20 Nov).

The same figures are already held: bls_api_1052.py keeps state_metro_payrolls_all.txt.gz (SMS{fips}00000{ss}00000001, the BLS's own
series) current in every run. Until the next State release the newest month there IS the first print, and the month before is the
revision printed with it. Proven on the day this was written: for all 459 State-groups the August 2026 figure in that file equals m1 of
the September release in the csv; construction is supersector 20, or 15 (mining, logging and construction) where the BLS publishes no 20
(Delaware, District of Columbia, Hawaii), as in the release's own table.

Each run: if every one of the 459 series holds a month M newer than the csv's newest ref_month, and M is the newest month the flat file
holds for all of them (so nothing has been revised yet), append the 459 rows of M. published = the day the month is first seen here, in
New York time (the live tools run on the release day), or KNOWN[M] for a month added late. Add-only: no held row is changed.
Writes $LT_OUT/state_industry_first_prints_1161.json. Exit 0 always (a refresh never stops the run); --check exits 1 if the csv is behind."""
import os, sys, csv, gzip, json, datetime as dt
ROOT = os.path.expanduser('~/Projects/Onset Detector Data')
FLAT = os.path.join(ROOT, '191_standing_collector_2026-09-16/warehouse/bls_flat_files/state_metro_payrolls_all.txt.gz')
CSV = os.path.join(ROOT, '1032_state_recession_indicator_all_states_dc_2026-11-09/data/state_industry_releases_1994_2026_a168.csv')
OUTD = os.environ.get('LT_OUT') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
FIPS = dict(AL='01', AK='02', AZ='04', AR='05', CA='06', CO='08', CT='09', DE='10', DC='11', FL='12', GA='13', HI='15', ID='16', IL='17', IN='18', IA='19', KS='20',
            KY='21', LA='22', ME='23', MD='24', MA='25', MI='26', MN='27', MS='28', MO='29', MT='30', NE='31', NV='32', NH='33', NJ='34', NM='35', NY='36', NC='37',
            ND='38', OH='39', OK='40', OR='41', PA='42', RI='44', SC='45', SD='46', TN='47', TX='48', UT='49', VT='50', VA='51', WA='53', WV='54', WI='55', WY='56')
GROUPS = [('Total(1)', ['00']), ('Construction', ['20', '15']), ('Manufacturing', ['30']), ('Trade, transportation, and utilities', ['40']), ('Financial activities', ['55']),
          ('Professional and business services', ['60']), ('Education and health services', ['65']), ('Leisure and hospitality', ['70']), ('Government', ['90'])]
KNOWN = {'2026-10': '2026-11-20'}   # FRED release 112 (State Employment and Unemployment): the day the source gate itself names


def flat():
    V = {}
    with gzip.open(FLAT, 'rt', encoding='latin-1') as f:
        next(f, None)
        for line in f:
            q = line.rstrip('\n').split('\t')
            if len(q) < 4 or not q[2].strip().startswith('M') or q[2].strip() == 'M13': continue
            try: V.setdefault(q[0].strip(), {})['%s-%s' % (q[1].strip(), q[2].strip()[1:])] = float(q[3])
            except ValueError: pass
    return V


def prev(m):
    y, mo = int(m[:4]), int(m[5:]); return '%04d-%02d' % ((y, mo - 1) if mo > 1 else (y - 1, 12))


def main():
    res = dict(csv_newest=None, flat_newest=None, appended=0, note='')
    with open(CSV, newline='') as h: rows = list(csv.DictReader(h))
    res['csv_newest'] = held = max(r['ref_month'] for r in rows)
    V = flat(); S = {}
    for st, fp in FIPS.items():
        for g, codes in GROUPS:
            sid = next((s for s in ('SMS%s00000%s00000001' % (fp, c) for c in codes) if s in V), None)
            if sid is None: res['note'] = 'no series for %s %s: nothing appended' % (st, g); return res
            S[(st, g)] = V[sid]
    newest = {max(v) for v in S.values()}
    res['flat_newest'] = sorted(newest)[-1]
    if len(newest) != 1: res['note'] = 'the %d series do not end in one month (%s): nothing appended' % (len(S), ', '.join(sorted(newest))); return res
    M = newest.pop()
    if M <= held: res['note'] = 'current'; return res
    if any(prev(M) not in v for v in S.values()): res['note'] = 'a series lacks %s: nothing appended' % prev(M); return res
    pub = KNOWN.get(M)
    if pub is None:
        try:
            from zoneinfo import ZoneInfo
            pub = dt.datetime.now(ZoneInfo('America/New_York')).date().isoformat()
        except Exception: pub = dt.datetime.now(dt.timezone.utc).date().isoformat()
    add = [dict(published=pub, ref_month=M, st=st, group=g, m1=repr(S[(st, g)][prev(M)]), m0=repr(S[(st, g)][M])) for st in FIPS for g, _ in GROUPS]
    tmp = CSV + '.tmp1161'
    with open(CSV, newline='') as h, open(tmp, 'w', newline='') as o:
        data = h.read(); o.write(data if data.endswith('\n') else data + '\n')
        w = csv.DictWriter(o, fieldnames=['published', 'ref_month', 'st', 'group', 'm1', 'm0'], lineterminator='\n'); w.writerows(add)
    os.replace(tmp, CSV)
    res.update(appended=len(add), published=pub, month=M)
    if prev(M) != held: res['note'] = 'months between %s and %s were never taken as first published' % (held, M)
    return res


if __name__ == '__main__':
    try: r = main()
    except Exception as e: r = dict(error='%s: %s' % (type(e).__name__, e), appended=0, note='failed: the held file is kept')
    print('state industry first prints:', json.dumps(r))
    try:
        os.makedirs(OUTD, exist_ok=True); json.dump(r, open(os.path.join(OUTD, 'state_industry_first_prints_1161.json'), 'w'))
    except Exception: pass
    if '--check' in sys.argv and (r.get('error') or (r.get('flat_newest') and r.get('csv_newest') and r['flat_newest'] > r['csv_newest'] and not r.get('appended'))): sys.exit(1)
    sys.exit(0)
