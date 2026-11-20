#!/usr/bin/env python3
"""THE STATE PAYROLLS BY INDUSTRY, AS FIRST PRINTED (speed program 1052, step 5; 16 November 2026). No AI.

The State industry first-print file the live tools hold stops in 2023-11, and no public vintage source of the BLS State payrolls by
supersector exists for the runner. From now on, each BLS State Employment and Unemployment release is recorded on its release day:
at the release slot (run_slots.json wait group bls_state, update.yml), every seasonally adjusted State payroll series by supersector
(SMS<state>00000<supersector>00000001, 50 States and DC, 12 supersectors) is read from the BLS API v2 and its newest month - the
first print - is appended to data/state_industry_first_prints/sm_first_prints.csv (add-only: a series-month already there is never
rewritten; the previous month's revision printed the same day is recorded too, as revised_1, since the release revises it).
    python3 ops/speed/state_first_prints.py [--force]      (--force: record even when today is not a State release day)"""
import os, sys, csv, json, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'data', '105_bristow_hall_system_2026-09-08', 'workspace', 's2'))
import publisher_first as pf
OUT = os.path.join(ROOT, 'data', 'state_industry_first_prints', 'sm_first_prints.csv')
FIPS = ['01', '02', '04', '05', '06', '08', '09', '10', '11', '12', '13', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26',
        '27', '28', '29', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '40', '41', '42', '44', '45', '46', '47', '48', '49', '50',
        '51', '53', '54', '55', '56']
SUPER = ['00000000', '05000000', '10000000', '15000000', '20000000', '30000000', '40000000', '50000000', '55000000', '60000000',
         '65000000', '70000000', '80000000', '90000000']
COLS = ['release_date', 'series_id', 'month', 'value', 'kind', 'captured_utc']


def main():
    today = pf._today_et().isoformat()
    if '--force' not in sys.argv and today not in pf.release_days('bls_state'):
        print('State first prints: %s is not a State release day; nothing recorded' % today); return
    ids = ['SMS%s00000%s01' % (f, s) for f in FIPS for s in SUPER]
    have = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT)): have.add((r['series_id'], r['month'], r['kind']))
    import pandas as pd
    t0 = pf._today_et(); want = (pd.Timestamp(t0.year, t0.month, 1) - pd.DateOffset(months=1))   # the month this release first prints
    # 20 Nov 2026 (the BLS key's 500 a day are shared by every job): a series whose first print of this month is already recorded is not
    # asked again (the file is add-only: nothing of it could change), and before the 714 series are asked, ONE latest=true request per
    # 50 States' total payrolls (2 requests) asks whether the release is out at all; a run before 10:00 ET used to ask all 15 requests
    todo = [i for i in ids if (i, str(want)[:7], 'first_print') not in have]
    if not todo:
        print('State first prints: all %d series already recorded for %s; nothing asked' % (len(ids), str(want)[:7])); return
    tot = ['SMS%s00000%s01' % (f, SUPER[0]) for f in FIPS]   # each State's total payrolls, the same id as in `ids`
    nw = {}
    for i in range(0, len(tot), 50): nw.update(pf.bls_newest(tot[i:i + 50]))
    if not nw:
        print('State first prints: no source answered for the States\' total payrolls (the BLS API, its fallbacks); nothing asked, nothing recorded - the next run asks again'); return
    if not any(v >= want for v in nw.values()):
        print('State first prints: the release of %s is not out yet (newest total payrolls %s in %d States); nothing asked, nothing recorded' % (
            str(want)[:7], max((str(v)[:7] for v in nw.values()), default='-'), len(nw))); return
    key = pf.bls_key(); y = datetime.date.today().year; got = {}
    unanswered = 0
    for i in range(0, len(todo), 50):
        try: got.update(pf._bls(todo[i:i + 50], y - 1, y, key))
        except RuntimeError as e:      # no source answered this block (the key refused or guarded; FRED carries only the totals): next run
            unanswered += len(todo[i:i + 50]); print('State first prints: %d series not answered (%s); the next run asks again' % (len(todo[i:i + 50]), str(e)[:160]))
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    rows = []
    late = 0
    for sid, obs in sorted(got.items()):
        ms = sorted(obs)
        if not ms: continue
        if ms[-1] < want: late += 1; continue          # the release is not out yet for this series (a run before 10:00): nothing recorded
        for m, kind in ((ms[-1], 'first_print'), (ms[-2] if len(ms) > 1 else None, 'revised_1')):
            if m is None: continue
            k = (sid, str(m)[:7], kind)
            if k in have: continue
            rows.append(dict(release_date=today, series_id=sid, month=str(m)[:7], value=obs[m], kind=kind, captured_utc=now))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    new = not os.path.exists(OUT)
    with open(OUT, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if new: w.writeheader()
        w.writerows(rows)
    newest = max((r['month'] for r in rows if r['kind'] == 'first_print'), default='-')
    print('State first prints: %d series read (%d already recorded, %d not answered), %d rows recorded (first prints of %s) in %s; %d series not yet at %s' % (len(got), len(ids) - len(todo), unanswered, len(rows), newest, os.path.relpath(OUT, ROOT), late, str(want)[:7]))


if __name__ == '__main__':
    main()
