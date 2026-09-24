#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""THE YEARLY DRIFT REPORT (ops/; 23 September 2026, collection 356; risks register R4 - "a yearly drift report (each object's level
and variance against its own history) ... Test: the drift report produced from the cache alone").

What the tool's objects measure can drift while nothing breaks: unemployment insurance can cover fewer of the unemployed (gig work,
shrinking eligibility), claims can answer less to job losses, the states' survey-based rates can grow noisier as response falls.
The recession-type atlas (collection 351) found the tool leans on claims; the second-opener drill (350) registered a switch should the
states' first prints grow noisy. This report measures each, year by year, against its own history, and raises a flag when a
registered line is crossed. It never changes the rule: a flag is a CHECK line in the run's message for Anthony.

Measures, by calendar year:
  coverage        continued claims (CCSA) / the number of unemployed (UNEMPLOY x 1000): the share of the unemployed the claims
                  objects can see
  claims_per_loser initial claims (ICSA, weekly mean) / job losers (LNS13023621 x 1000): how strongly the claims flow answers job loss
  insured_ratio   the insured unemployment rate (IURSA) / the unemployment rate (UNRATE)
  state_noise     the median state's first-print noise, sd of the second difference / sqrt(6) and the robust MAD x 1.4826 / sqrt(6),
                  over the 36 months to December (to the latest month for the current year), from the tool's own
                  cache/state_ur_firstprints.csv (collection 350's measure)
Flags (registered before this report first ran):
  E31B_NOISE      state_noise on the robust scale >= 0.30 in the latest window: 350's registered switch (the national
                  confirmation G1 at 0.30 in place of bare E31b) is due for Anthony's decision
  COVERAGE_LOW    coverage in the latest complete year below every earlier complete year since 1967
  CLAIMS_FLOW_LOW claims_per_loser in the latest complete year below every earlier complete year
FRED series are fetched with the key the workflow writes (or FRED_API_KEY in the environment) at most once a week and kept in
ops/cache/drift/; without a key or a network the cache alone is used. Writes ops/out/drift_report.json and a copy beside the site's
release calendar (<site_public>/ops/drift_report.json). Never raises: a failure is written into the report.

    python3 ops/drift_report.py          (from the repository root)
    python3 ops/drift_report.py --cache  use the cache alone (the R4 test)
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

OPS = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(OPS)
TOOL = {'workspace': 'data/105_bristow_hall_system_2026-09-08/workspace', 'site_public': 'data/105_bristow_hall_system_2026-09-08/site/public'}
try:
    TOOL.update({k: v for k, v in json.load(open(os.path.join(OPS, 'tool.json'))).items() if k in TOOL})
except Exception:
    pass
CACHE = os.path.join(OPS, 'cache', 'drift'); os.makedirs(CACHE, exist_ok=True)
SERIES = {'CCSA': 'continued claims', 'ICSA': 'initial claims', 'UNEMPLOY': 'unemployed', 'LNS13023621': 'job losers',
          'IURSA': 'insured unemployment rate', 'UNRATE': 'unemployment rate'}
CACHE_ONLY = '--cache' in sys.argv
NOISE_LINE = 0.30


def fred_key():
    k = os.environ.get('FRED_API_KEY', '').strip()
    for env in (os.path.join(ROOT, 'data', 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env'),      # the runner
                os.path.expanduser('~/Projects/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env')):  # the Mac
        if k:
            break
        try:
            for line in open(env):
                if line.startswith('FRED_API_KEY='):
                    k = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return k


def series(sid, notes):
    path = os.path.join(CACHE, sid + '.csv'); fresh = False
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < 7 * 86400:
        fresh = True
    if not fresh and not CACHE_ONLY and fred_key():
        try:
            url = 'https://api.stlouisfed.org/fred/series/observations?' + urllib.parse.urlencode(
                {'series_id': sid, 'file_type': 'json', 'api_key': fred_key(), 'observation_start': '1967-01-01'})
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'bhr-drift'}), timeout=60) as r:
                obs = json.load(r).get('observations', [])
            rows = [(o['date'], float(o['value'])) for o in obs if o.get('value') not in (None, '', '.')]
            if rows:
                tmp = path + '.tmp'; pd.DataFrame(rows, columns=['date', 'value']).to_csv(tmp, index=False); os.replace(tmp, path)
        except Exception as e:
            notes.append('%s not fetched (%s); the cache is used' % (sid, type(e).__name__))
    if not os.path.exists(path):
        notes.append('%s: no cache and no fetch' % sid); return None
    s = pd.read_csv(path, parse_dates=['date']).set_index('date')['value'].astype(float)
    return s.sort_index()


def yearly(s):
    y = s.groupby(s.index.year).mean(); n = s.groupby(s.index.year).size()
    return y, n


def main():
    notes = []; out = {'written': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%MZ'), 'measures': {}, 'flags': [], 'notes': notes}
    S = {k: series(k, notes) for k in SERIES}
    today = dt.date.today(); cy = today.year
    def ratio(a, b, scale):
        if S.get(a) is None or S.get(b) is None:
            return None
        ya, na = yearly(S[a]); yb, nb = yearly(S[b]); r = (ya / (yb * scale)).dropna()
        return r
    table = {'coverage': ratio('CCSA', 'UNEMPLOY', 1000.0), 'claims_per_loser': ratio('ICSA', 'LNS13023621', 1000.0),
             'insured_ratio': ratio('IURSA', 'UNRATE', 1.0)}
    for name, r in table.items():
        if r is None or not len(r):
            continue
        complete = r[r.index < cy]
        last = int(complete.index.max()) if len(complete) else None
        m = {'by_year': {int(k): round(float(v), 4) for k, v in r.items()}, 'latest_complete_year': last}
        if last is not None and len(complete) > 5:
            prior = complete[complete.index < last]
            m.update(latest=round(float(complete[last]), 4), prior_min=round(float(prior.min()), 4), prior_min_year=int(prior.idxmin()),
                     percentile=round(float((prior < complete[last]).mean() * 100), 1))
        out['measures'][name] = m
    # the states' first-print noise (collection 350's measure), from the tool's own cache
    try:
        P = pd.read_csv(os.path.join(ROOT, TOOL['workspace'], 'cache', 'state_ur_firstprints.csv'), parse_dates=['date'])
        X = P.pivot_table(index='date', columns='state', values='value', aggfunc='first').sort_index()
        D2 = X.diff().diff()
        sd = D2.rolling(36, min_periods=24).std() / np.sqrt(6)
        mad = D2.rolling(36, min_periods=24).apply(lambda v: np.nanmedian(np.abs(v - np.nanmedian(v))), raw=True) * 1.4826 / np.sqrt(6)
        by = {}
        for y in sorted(set(X.index.year)):
            ms = [t for t in X.index if t.year == y]
            t = max(ms)
            if y < cy and t.month != 12:
                continue
            by[int(y)] = {'month': t.strftime('%Y-%m'), 'sd': round(float(sd.loc[t].median()), 4), 'mad': round(float(mad.loc[t].median()), 4)}
        out['measures']['state_noise'] = {'by_year': by, 'latest': by[max(by)] if by else None, 'line': NOISE_LINE}
    except Exception as e:
        notes.append('state noise not computed (%s: %s)' % (type(e).__name__, str(e)[:80]))
    # the flags
    sn = (out['measures'].get('state_noise') or {}).get('latest') or {}
    if sn and sn.get('mad') is not None and sn['mad'] >= NOISE_LINE:
        out['flags'].append('E31B_NOISE: the states\' first-print noise is %.3f on the robust scale (line %.2f) - 350\'s registered '
                            'switch (the national confirmation G1 at 0.30 on the state breadth) is due for a decision' % (sn['mad'], NOISE_LINE))
    for name, code, what in (('coverage', 'COVERAGE_LOW', 'continued claims cover a smaller share of the unemployed'),
                             ('claims_per_loser', 'CLAIMS_FLOW_LOW', 'initial claims answer job losses less')):
        m = out['measures'].get(name) or {}
        if m.get('latest') is not None and m.get('prior_min') is not None and m['latest'] < m['prior_min']:
            out['flags'].append('%s: %s in %d (%.3f) than in any earlier year (lowest before: %.3f in %d) - the claims branches see '
                                'less of a downturn (collection 351)' % (code, what, m['latest_complete_year'], m['latest'], m['prior_min'], m['prior_min_year']))
    bits = []
    for name, label in (('coverage', 'claims coverage'), ('claims_per_loser', 'claims per job loser'), ('insured_ratio', 'insured/total rate')):
        m = out['measures'].get(name) or {}
        if m.get('latest') is not None:
            bits.append('%s %.3f in %d (%.0f per cent of the years since 1967 were lower; lowest %.3f in %d)' % (
                label, m['latest'], m['latest_complete_year'], m['percentile'], m['prior_min'], m['prior_min_year']))
    if sn:
        bits.append('state first-print noise %.3f (robust; line %.2f; sd scale %.3f, %s)' % (sn['mad'], NOISE_LINE, sn['sd'], sn['month']))
    out['summary'] = '; '.join(bits) if bits else 'no measure could be computed'
    out['year'] = cy
    os.makedirs(os.path.join(OPS, 'out'), exist_ok=True)
    json.dump(out, open(os.path.join(OPS, 'out', 'drift_report.json'), 'w'), indent=1)
    site = os.path.join(ROOT, TOOL['site_public'], 'ops')
    try:
        os.makedirs(site, exist_ok=True); json.dump(out, open(os.path.join(site, 'drift_report.json'), 'w'), indent=1)
    except Exception as e:
        notes.append('site copy not written (%s)' % type(e).__name__)
    print('drift report:', out['summary'])
    for f in out['flags']:
        print('FLAG', f)
    for n in notes:
        print('note:', n)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:                      # never fails the run
        print('drift report failed: %s: %s' % (type(e).__name__, e))
        try:
            os.makedirs(os.path.join(OPS, 'out'), exist_ok=True)
            json.dump({'failed': '%s: %s' % (type(e).__name__, str(e)[:200]), 'flags': []}, open(os.path.join(OPS, 'out', 'drift_report.json'), 'w'))
        except Exception:
            pass
    sys.exit(0)
