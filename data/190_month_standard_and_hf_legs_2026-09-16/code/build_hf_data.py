#!/usr/bin/env python3
"""Assemble the high-frequency transmission channels (daily / weekly, never or rarely revised) as two-column
CSVs for the leg screen. Sources already held in the Onset Detector Data folder; nothing fetched here.
  payments   DTSWITHHELD   withheld income+employment taxes deposited, daily 2005-10-03 -> (collection 183, spliced
                           across the Feb-2023 DTS format change)         + rolling sums S20, S65 (business days)
             DTSCUSTOMS    customs duties deposited, daily 2005-10-03 -> (three DTS category spellings spliced) + S20, S65
  physical   TSATHRU       TSA checkpoint throughput, daily 2019-01-01 ->        + S7, S28
             EIAWRPUPUS2   total petroleum products supplied, weekly 1990-11 ->  + 4-week mean M4
             EIAWGFUPUS2   finished motor gasoline supplied, weekly               + M4
             EIAWDIUPUS2   distillate supplied, weekly                            + M4
  plumbing   OFRFSI, OFRCREDIT, OFRFUNDING, OFRVOL, OFRSAFE, OFREQUITY   OFR financial stress index and subindexes, daily 2000 ->
  hiring     INDEEDSA, INDEEDNSA   Indeed aggregate US job postings index, daily 2020-02-01 ->
"""
import os, pandas as pd, numpy as np
ROOT = os.path.expanduser('~/Projects/Onset Detector Data')
if not os.path.isdir(ROOT): ROOT = os.path.expanduser('~/mnt/Onset Detector Data')
A = os.path.join(ROOT, '189_walk_from_1948_2026-09-16/out/alt')
OUT = os.path.join(ROOT, '190_month_standard_and_hf_legs_2026-09-16/data'); os.makedirs(OUT, exist_ok=True)
def w(name, s, note=''):
    s = s.dropna(); s = s[~s.index.duplicated(keep='last')].sort_index()
    pd.DataFrame({'date': s.index.strftime('%Y-%m-%d'), 'value': s.values}).to_csv(os.path.join(OUT, name + '.csv'), index=False)
    print('%-14s %s -> %s  n=%d  %s' % (name, s.index.min().date(), s.index.max().date(), len(s), note))
    return s
# payments
d = pd.read_csv(os.path.join(ROOT, '183_transmission_channels_2026-09-15/data/dts_withheld_daily.csv'))
s = pd.Series(pd.to_numeric(d.iloc[:, 1], errors='coerce').values, index=pd.to_datetime(d.iloc[:, 0]))
s = w('DTSWITHHELD', s, 'collection 183, $m')
w('DTSWITHHELD_S20', s.rolling(20).sum(), 'trailing 20 business days'); w('DTSWITHHELD_S65', s.rolling(65).sum(), 'trailing 65 business days')
r = pd.read_csv(os.path.join(A, 'dts_deposits_all.csv'))
cats = ['Customs and Certain Excise Taxes', 'DHS - Customs and Certain Excise Taxes', 'DHS - Customs Duties, Taxes, and Fees']
c = r[r.transaction_catg.isin(cats)].copy(); c['date'] = pd.to_datetime(c.record_date)
c = c.groupby('date').transaction_today_amt.sum().sort_index()
s = w('DTSCUSTOMS', c, 'three DTS spellings spliced; $m')
w('DTSCUSTOMS_S20', s.rolling(20).sum()); w('DTSCUSTOMS_S65', s.rolling(65).sum())
# physical
t = pd.read_csv(os.path.join(A, 'tsa_throughput.csv')); s = pd.Series(t.iloc[:, 1].values, index=pd.to_datetime(t.iloc[:, 0]))
s = w('TSATHRU', s, 'passengers/day'); w('TSATHRU_S7', s.rolling(7).sum()); w('TSATHRU_S28', s.rolling(28).sum())
for sid in ('WRPUPUS2', 'WGFUPUS2', 'WDIUPUS2', 'WCESTUS1', 'WGTSTUS1'):
    e = pd.read_csv(os.path.join(A, 'eia_%s.csv' % sid)); s = pd.Series(pd.to_numeric(e.value, errors='coerce').values, index=pd.to_datetime(e.date))
    s = w('EIA' + sid, s, 'weekly, kb/d');
    if sid in ('WRPUPUS2', 'WGFUPUS2', 'WDIUPUS2'): w('EIA%s_M4' % sid, s.rolling(4).mean())
# plumbing
o = pd.read_csv(os.path.join(A, 'ofr_fsi.csv')); o['Date'] = pd.to_datetime(o['Date'])
for col, name in [('OFR FSI', 'OFRFSI'), ('Credit', 'OFRCREDIT'), ('Funding', 'OFRFUNDING'), ('Volatility', 'OFRVOL'), ('Safe assets', 'OFRSAFE'), ('Equity valuation', 'OFREQUITY')]:
    w(name, pd.Series(pd.to_numeric(o[col], errors='coerce').values, index=o['Date']))
# hiring
i = pd.read_csv(os.path.join(A, 'indeed_job_postings_US.csv')); i = i[i.variable == 'total postings']; i['date'] = pd.to_datetime(i.date)
w('INDEEDSA', pd.Series(i.indeed_job_postings_index_SA.values, index=i.date)); w('INDEEDNSA', pd.Series(i.indeed_job_postings_index_NSA.values, index=i.date))
