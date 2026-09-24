#!/usr/bin/env python3
"""Alternative high-frequency channels not on FRED, fetched directly (no AI, no scraping service):
  indeed   -- Indeed Hiring Lab aggregate US job postings index, daily from February 2020 (GitHub raw CSV)
  ofr      -- OFR Financial Stress Index, daily from 2000 (CSV)
  dts      -- Daily Treasury Statement: withheld income and employment taxes deposited, daily from 2005
              (Treasury Fiscal Data API v1, paginated)
  ar539    -- DOL ETA-539 weekly state claims file (initial and continued claims by state)
  eia      -- EIA weekly petroleum: gasoline, distillate and total product supplied; crude stocks (API v2, key)
Resumable; each source is refreshed whole (small files). Output: /mnt/user-data/outputs/alt/
"""
import os, re, sys, json, csv, time, urllib.request, urllib.parse
OUT = '/mnt/user-data/outputs/alt'; os.makedirs(OUT, exist_ok=True)
ENV = '/mnt/user-data/uploads/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env'
txt = open(ENV).read()
def key(name):
    m = re.search(r'^%s=([^\r\n]+)' % name, txt, re.M)
    return m.group(1).strip().strip('"').strip("'") if m else ''
LOG = open(os.path.join(OUT, 'alt.log'), 'a')
def log(*a):
    s = time.strftime('%H:%M:%S ') + ' '.join(str(x) for x in a); LOG.write(s + '\n'); LOG.flush(); print(s, flush=True)
UA = {'User-Agent': 'Mozilla/5.0 (research collector; contact https://bhrrealtime.pages.dev)'}
def get(u, timeout=120):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()

def indeed():
    b = get('https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/master/US/aggregate_job_postings_US.csv')
    open(os.path.join(OUT, 'indeed_job_postings_US.csv'), 'wb').write(b); log('indeed', len(b), 'bytes')

def ofr():
    b = get('https://www.financialresearch.gov/financial-stress-index/data/fsi.csv')
    open(os.path.join(OUT, 'ofr_fsi.csv'), 'wb').write(b); log('ofr fsi', len(b), 'bytes')

def dts():
    base = 'https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash'
    rows = []; page = 1
    while True:
        u = base + '?' + urllib.parse.urlencode({'filter': 'transaction_type:eq:Deposits', 'fields': 'record_date,transaction_catg,transaction_today_amt,transaction_mtd_amt',
                                                 'page[size]': 10000, 'page[number]': page, 'sort': 'record_date'})
        d = json.loads(get(u, 180))
        rows += d.get('data', []); pages = d.get('meta', {}).get('total-pages', 1)
        if page % 10 == 0: log('dts page', page, 'of', pages, len(rows))
        if page >= pages: break
        page += 1
    with open(os.path.join(OUT, 'dts_deposits_all.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['record_date', 'transaction_catg', 'transaction_today_amt', 'transaction_mtd_amt'])
        for r in rows: w.writerow([r['record_date'], r['transaction_catg'], r['transaction_today_amt'], r['transaction_mtd_amt']])
    wh = [r for r in rows if 'Withheld' in (r['transaction_catg'] or '')]
    with open(os.path.join(OUT, 'dts_withheld_taxes.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['date', 'value', 'category'])
        for r in wh: w.writerow([r['record_date'], r['transaction_today_amt'], r['transaction_catg']])
    log('dts', len(rows), 'deposit rows;', len(wh), 'withheld rows', (wh[0]['record_date'] if wh else ''), '->', (wh[-1]['record_date'] if wh else ''))

def ar539():
    b = get('https://oui.doleta.gov/unemploy/csv/ar539.csv', 180)
    open(os.path.join(OUT, 'dol_ar539_state_weekly_claims.csv'), 'wb').write(b); log('ar539', len(b), 'bytes')

def eia():
    k = key('EIA_API_KEY')
    if not k: log('eia: no key'); return
    series = {'WGFUPUS2': 'finished motor gasoline product supplied', 'WDIUPUS2': 'distillate product supplied',
              'WRPUPUS2': 'total petroleum products supplied', 'WCESTUS1': 'crude stocks excl SPR', 'WGTSTUS1': 'gasoline stocks',
              'WCRFPUS2': 'crude oil production', 'WTTIMUS2': 'total imports'}
    for sid, name in series.items():
        try:
            data = []; off = 0
            while True:
                u = ('https://api.eia.gov/v2/petroleum/sum/sndw/data/?api_key=%s&frequency=weekly&data[0]=value&facets[series][]=%s'
                     '&sort[0][column]=period&sort[0][direction]=asc&length=5000&offset=%d' % (k, sid, off))
                d = json.loads(get(u, 120)); chunk = d.get('response', {}).get('data', []); data += chunk
                if len(chunk) < 5000: break
                off += 5000
            with open(os.path.join(OUT, 'eia_%s.csv' % sid), 'w', newline='') as f:
                w = csv.writer(f); w.writerow(['date', 'value'])
                for r in sorted(data, key=lambda r: r['period']): w.writerow([r['period'], r['value']])
            log('eia', sid, len(data), name)
        except Exception as e: log('eia', sid, 'ERR', type(e).__name__)
        time.sleep(1)

if __name__ == '__main__':
    for name in (sys.argv[1:] or ['indeed', 'ofr', 'ar539', 'eia', 'dts']):
        try: globals()[name]()
        except Exception as e: log(name, 'ERR', type(e).__name__, str(e)[:120])
    log('alt done')
