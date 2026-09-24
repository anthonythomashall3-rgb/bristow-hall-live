#!/usr/bin/env python3
"""Daily withheld income and employment taxes, both legs, spliced on their handoff.

WHY THIS SERIES. It is employment multiplied by wages, collected by the Internal Revenue Service
every business day from every employer with a payroll. Not a survey: no sample, no response rate, no
birth-death model, no seasonal adjustment and NO REVISION -- the number is the money that actually
arrived. Published the next business day, so a one-day lag against the household survey's forty.

And it is CAUSE-AGNOSTIC, which is why it belongs in a rule that must work for recession types that
have not happened yet. It does not care WHY people stopped being paid. A cyber shock, a climate
shock, an AI displacement -- none has an instrument in this programme, and all of them must show up
here, because all of them end with somebody not being paid.

TWO LEGS, because the Daily Treasury Statement changed format in February 2023:
  leg 1  table `federal_tax_deposits`, `tax_deposit_type` = 'Withheld Income and Employment Taxes',
         to 2023-02-13.
  leg 2  table `deposits_withdrawals_operating_cash`, `transaction_catg` =
         'Taxes - Withheld Individual/FICA', from the changeover to today.
The gap between them is recorded rather than papered over; if they do not overlap, the splice is a
join at a format change, which is a documented fact about the publication, not a measurement.
"""
import csv, json, os, time, urllib.parse, urllib.request
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, 'data'); os.makedirs(DATA, exist_ok=True)
ROOT = 'https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/'

def pull(table, fields, filt, page):
    q = {'fields': fields, 'filter': filt, 'page[size]': '10000',
         'page[number]': str(page), 'sort': 'record_date'}
    url = ROOT + table + '?' + urllib.parse.urlencode(q, quote_via=urllib.parse.quote, safe=':,')
    with urllib.request.urlopen(url, timeout=180) as r:
        return json.loads(r.read())

def harvest(table, fields, filt, dcol, vcol, label):
    rows, page = [], 1
    while True:
        j = pull(table, fields, filt, page)
        d = j.get('data', [])
        rows += d
        tp = int(j.get('meta', {}).get('total-pages', 1) or 1)
        print('  %-34s page %d/%d  +%d  total %d' % (label, page, tp, len(d), len(rows)), flush=True)
        if page >= tp or not d: break
        page += 1; time.sleep(0.25)
    return [(r[dcol], r[vcol]) for r in rows]

legs = []
legs.append(harvest('federal_tax_deposits',
                    'record_date,tax_deposit_type,tax_deposit_today_amt',
                    'tax_deposit_type:eq:Withheld Income and Employment Taxes',
                    'record_date', 'tax_deposit_today_amt', 'leg1 federal_tax_deposits'))
legs.append(harvest('deposits_withdrawals_operating_cash',
                    'record_date,transaction_catg,transaction_today_amt',
                    'transaction_catg:eq:Taxes - Withheld Individual/FICA',
                    'record_date', 'transaction_today_amt', 'leg2 operating_cash'))

for i, L in enumerate(legs, 1):
    if L: print('leg%d n=%d  %s .. %s' % (i, len(L), min(x[0] for x in L), max(x[0] for x in L)))
    else: print('leg%d EMPTY' % i)

merged = {}
for L in legs:
    for d, v in L:
        merged[d] = v
out = os.path.join(DATA, 'dts_withheld_daily.csv')
with open(out, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['date', 'withheld_musd'])
    for d in sorted(merged): w.writerow([d, merged[d]])
print('\nSPLICED daily withheld: n=%d  %s .. %s' % (len(merged), min(merged), max(merged)))
if legs[0] and legs[1]:
    o = set(x[0] for x in legs[0]) & set(x[0] for x in legs[1])
    print('overlap days between the two legs: %d' % len(o))
    print('leg1 ends %s | leg2 starts %s' % (max(x[0] for x in legs[0]), min(x[0] for x in legs[1])))
