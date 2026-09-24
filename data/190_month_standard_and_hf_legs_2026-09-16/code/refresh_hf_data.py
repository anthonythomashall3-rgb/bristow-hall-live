#!/usr/bin/env python3
"""Rebuild data/ (the high-frequency channels the v3.56 legs read) from the standing collector's warehouse (collection
191), so the legs read today's files each day. Same series, same derivations as build_hf_data.py; source paths moved
from the one-off 189 pulls to the warehouse the collector refreshes every six hours. Run daily from bhs_update.py."""
import os, sys, pandas as pd, numpy as np
ROOT = os.path.expanduser('~/Projects/Onset Detector Data')
if not os.path.isdir(ROOT): ROOT = os.path.expanduser('~/mnt/Onset Detector Data')
W = os.path.join(ROOT, '191_standing_collector_2026-09-16', 'warehouse')
OUT = os.path.join(ROOT, '190_month_standard_and_hf_legs_2026-09-16', 'data'); os.makedirs(OUT, exist_ok=True)
def rd(p, dcol=0, vcol=1):
    d = pd.read_csv(p); dt = pd.to_datetime(d.iloc[:, dcol], errors='coerce')
    return pd.Series(pd.to_numeric(d.iloc[:, vcol], errors='coerce').values, index=dt).dropna().sort_index()
LAST = {}
def w(name, s):
    s = s.dropna(); s = s[~s.index.duplicated(keep='last')]
    pd.DataFrame({'date': s.index.strftime('%Y-%m-%d'), 'value': s.values}).to_csv(os.path.join(OUT, name + '.csv'), index=False)
    print('%-16s -> %s n=%d' % (name, s.index.max().date(), len(s))); LAST[name] = s.index.max()
D = os.path.join(W, 'dts', 'derived')
s = rd(os.path.join(D, 'dts_withheld_taxes_daily.csv')); w('DTSWITHHELD', s); w('DTSWITHHELD_S20', s.rolling(20).sum()); w('DTSWITHHELD_S65', s.rolling(65).sum())
s = rd(os.path.join(D, 'dts_customs_duties_daily.csv')); w('DTSCUSTOMS', s); w('DTSCUSTOMS_S20', s.rolling(20).sum()); w('DTSCUSTOMS_S65', s.rolling(65).sum())
s = rd(os.path.join(D, 'dts_unemployment_insurance_benefits_daily.csv')); w('UIBENEFITS', s); w('UIBENEFITS_S20', s.rolling(20).sum()); w('UIBENEFITS_S65', s.rolling(65).sum())
s = rd(os.path.join(D, 'dts_corporate_income_taxes_daily.csv')); w('DTSCORP_S65', s.rolling(65).sum())
s = rd(os.path.join(W, 'eia', 'EIA930DEMAND_US48_daily.csv')); w('EIA930DEMAND', s); w('EIA930DEMAND_S7', s.rolling(7).sum()); w('EIA930DEMAND_S28', s.rolling(28).sum())
s = rd(os.path.join(W, 'tsa', 'tsa_throughput_daily.csv')); w('TSATHRU', s); w('TSATHRU_S7', s.rolling(7).sum()); w('TSATHRU_S28', s.rolling(28).sum())
for sid in ('WRPUPUS2', 'WGFUPUS2', 'WDIUPUS2', 'WCESTUS1', 'WGTSTUS1'):
    s = rd(os.path.join(W, 'eia', 'petroleum_sndw', sid + '.csv')); w('EIA' + sid, s)
    if sid in ('WRPUPUS2', 'WGFUPUS2', 'WDIUPUS2'): w('EIA%s_M4' % sid, s.rolling(4).mean())
o = pd.read_csv(os.path.join(W, 'ofr', 'ofr_fsi.csv')); o['Date'] = pd.to_datetime(o['Date'])
for col, name in [('OFR FSI', 'OFRFSI'), ('Credit', 'OFRCREDIT'), ('Funding', 'OFRFUNDING'), ('Volatility', 'OFRVOL'), ('Safe assets', 'OFRSAFE'), ('Equity valuation', 'OFREQUITY')]:
    w(name, pd.Series(pd.to_numeric(o[col], errors='coerce').values, index=o['Date']))
i = pd.read_csv(os.path.join(W, 'indeed', 'job_postings_tracker_US', 'US__aggregate_job_postings_US.csv')); i = i[i.variable == 'total postings']; i['date'] = pd.to_datetime(i.date)
w('INDEEDSA', pd.Series(i.indeed_job_postings_index_SA.values, index=i.date)); w('INDEEDNSA', pd.Series(i.indeed_job_postings_index_NSA.values, index=i.date))
w('PMMS30W', rd(os.path.join(W, 'freddiemac', 'derived', 'pmms30_weekly.csv')))
w('EPUDAILY', rd(os.path.join(W, 'policyuncertainty', 'derived', 'epu_us_daily.csv'))); w('GPRDAILY', rd(os.path.join(W, 'policyuncertainty', 'derived', 'gpr_daily.csv')))
w('SKEW', rd(os.path.join(W, 'cboe', 'derived', 'SKEW_daily.csv'))); w('VVIX', rd(os.path.join(W, 'cboe', 'derived', 'VVIX_daily.csv')))
# the summary line the live update reports (17 September 2026): every channel's age, and any that has gone stale
# (no datum in 14 days, when every source here publishes daily or weekly) named, so a dead collector shows in the log
_today = pd.Timestamp.today().normalize()
_age = {k: (_today - v).days for k, v in LAST.items()}
_stale = sorted(k for k, a in _age.items() if a > 14)
print('hf channels: %d rebuilt, newest %s, oldest %s (%d d)%s' % (len(LAST), max(LAST.values()).date(), min(LAST.values()).date(), max(_age.values()),
      ('; STALE >14 d: ' + ', '.join(_stale)) if _stale else '; none stale'))
