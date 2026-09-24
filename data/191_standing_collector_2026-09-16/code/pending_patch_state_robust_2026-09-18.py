#!/usr/bin/env python3
"""State data brought up to the national object list, and the cycle made fast again (collection 191), 18 Sep 2026.

Anthony's standard: the tool should not be adapted to the state data we happen to hold; the state data should carry
every object the national rule reads. The coverage map showed which national objects had no state counterpart. This
registers what a search for each of them found.

Hours and earnings by state, which the rule's leg F reads nationally, exist in the Bureau's state and area files and
were simply never fetched. Credit conditions, which the rule reads nationally as the paper spread, have four free
state counterparts: bank call reports aggregated by state, mortgage delinquency by state monthly, and small-business
loan approvals by state. Manufacturing sentiment, which nationally is the purchasing managers' index, has exactly one
free state-level counterpart in the country - Creighton's nine-state survey - and it is never revised. Trade exposure
by state comes as two monthly workbooks. And the highest-frequency state signals found anywhere: petrol prices for all
fifty states daily, coal production by state weekly, Oklahoma's drilling permits daily, and the daily search-trend
feed for each state, which has no history endpoint and therefore only exists if we archive it ourselves from today.

Also in this patch: the hourly cycle had grown from twenty seconds to eleven minutes because the permit and revenue
backfills walk hundreds of dated addresses. Those move to their own lane.
"""
import json, os, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'sources.json')
STAMP = time.strftime('%Y-%m-%d_%H%M')
BLS = 'https://download.bls.gov/pub/time.series/sm/'
EIA = 'https://www.eia.gov/'
ST = ('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH '
      'OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY').split()


def F(out, url, **kw):
    d = {'url': url, 'out': out}; d.update(kw); return d


HOURS = {
 'name': 'state_hours_earnings', 'dir': 'state_hours_earnings', 'keep_vintages': True, 'fresh_hours': 100,
 'parallel': 3,
 '_note': "Added 18 Sep 2026. Average weekly hours and hourly and weekly earnings by state, which the national rule "
          "reads as factory hours and which the warehouse held only nationally. Manufacturing hours for all employees "
          "cover 46 states and for production workers all 52 state codes, monthly from 2007, not seasonally adjusted. "
          "The series identifier carries the state and the data type, so the whole panel is in these files: 02 hours, "
          "03 hourly earnings, 11 weekly earnings, 07 and 08 the production-worker forms.",
 'files': [
   F('sae_manufacturing_current.txt.gz', BLS + 'sm.data.63.Manufacturing.Current', stream=True),
   F('sae_all_current.txt.gz', BLS + 'sm.data.0.Current', stream=True),
   F('sae_series_dimension.txt.gz', BLS + 'sm.series', stream=True),
   F('sae_state_dimension.txt', BLS + 'sm.state', min_bytes=200),
   F('sae_data_type_dimension.txt', BLS + 'sm.data_type', min_bytes=100),
   F('sae_supersector_dimension.txt', BLS + 'sm.supersector', min_bytes=100),
 ]}

CREDIT = {
 'name': 'state_credit', 'dir': 'state_credit', 'keep_vintages': True, 'fresh_hours': 100, 'parallel': 4,
 '_note': "Added 18 Sep 2026. The state counterpart of the national rule's credit leg. Bank call reports summed by "
          "state give assets, loans, past-due and charge-offs; the consumer bureau publishes the share of mortgages "
          "thirty and ninety days late by state, monthly from 2008; the Small Business Administration publishes every "
          "approved loan with the borrower's state and the approval date, which is a monthly count of credit actually "
          "extended to small firms. The mortgage and loan files are restated with each vintage, which is why a dated "
          "copy is kept at every change.",
 'files': [
   F('fdic_bank_financials_latest.json',
     'https://api.fdic.gov/banks/financials?filters=REPDTE:20260630&fields=CERT,STALP,ASSET,DEP,LNLSNET,P3ASSET,P9ASSET,NAASSET,NTLNLSQ,NETINC&limit=10000&format=json'),
   F('fdic_state_summary.json',
     'https://api.fdic.gov/banks/summary?fields=YEAR,STNAME,ASSET,DEP,NETINC,LNLSNET&limit=10000&format=json'),
   F('cfpb_mortgages_30_89_days_late_by_state.csv',
     'https://files.consumerfinance.gov/data/mortgage-performance/downloads/StateMortgagesPercent-30-89DaysLate-thru-2025-12.csv'),
   F('cfpb_mortgages_90_plus_days_late_by_state.csv',
     'https://files.consumerfinance.gov/data/mortgage-performance/downloads/StateMortgagesPercent-90-plusDaysLate-thru-2025-12.csv'),
   F('sba_7a_loan_approvals.csv.gz',
     'https://data.sba.gov/sites/default/files/uploaded_resources/FOIA_7a_FY2020_Present_asof_260630.csv',
     stream=True, fresh_hours=400),
   F('sba_504_loan_approvals.csv.gz',
     'https://data.sba.gov/sites/default/files/uploaded_resources/FOIA_504_FY2010_Present_asof_260630.csv',
     stream=True, fresh_hours=400),
 ]}

ACTIVITY = {
 'name': 'state_activity_hf', 'dir': 'state_activity_hf', 'keep_vintages': True, 'fresh_hours': 8, 'parallel': 6,
 '_note': "Added 18 Sep 2026. The fastest state-level measures that exist free, all published once and not revised: "
          "petrol prices for every state daily, coal production by state weekly, the weekly price series the Energy "
          "Information Administration keeps for nine states, industrial gas deliveries by state, and Oklahoma's daily "
          "files of drilling permits and completions. Federal contract obligations by state are asked of the spending "
          "service directly.",
 'files': [
   F('aaa_state_gas_prices_daily.html', 'https://gasprices.aaa.com/state-gas-price-averages/'),
   F('eia_weekly_coal_production_by_state.xlsx', EIA + 'coal/production/weekly/xls/weekly_production.xlsx'),
   F('eia_drilling_productivity_report.xlsx', EIA + 'petroleum/drilling/xls/dpr-data.xlsx', fresh_hours=100),
   F('eia_industrial_gas_deliveries_by_state.xls',
     EIA + 'dnav/ng/xls/NG_CONS_SUM_A_EPG0_VIN_MMCF_M.xls', fresh_hours=100),
   F('oklahoma_intent_to_drill_daily.xlsx',
     'https://oklahoma.gov/content/dam/ok/en/occ/documents/og/ogdatafiles/ITD-wells-formations-daily.xlsx'),
   F('oklahoma_completions_daily.xlsx',
     'https://oklahoma.gov/content/dam/ok/en/occ/documents/og/ogdatafiles/completions-wells-formations-daily.xlsx'),
 ] + [F('eia_weekly_gasoline_%s.xls' % s.lower(),
        EIA + 'dnav/pet/hist_xls/EMM_EPM0_PTE_S%s_DPGw.xls' % s)
      for s in ('TX', 'CA', 'CO', 'FL', 'MA', 'MN', 'NY', 'OH', 'WA')]}

TRENDS = {
 'name': 'state_search_trends', 'dir': 'state_search_trends', 'keep_vintages': True, 'fresh_hours': 6, 'parallel': 8,
 '_note': "Added 18 Sep 2026. What each state is searching for, today. The feed is a snapshot with no history "
          "endpoint anywhere, so this series exists only from the day we begin keeping it - which is the argument for "
          "keeping it now rather than when it is wanted. A dated copy is kept at every change, so the archive builds "
          "itself.",
 'files': [F('google_trends_%s.xml' % s.lower(), 'https://trends.google.com/trending/rss?geo=US-%s' % s,
             min_bytes=200) for s in ST]}

SURVEYS = {
 'name': 'state_surveys', 'dir': 'state_surveys', 'keep_vintages': True, 'fresh_hours': 40, 'parallel': 3,
 '_note': "Added 18 Sep 2026. The only free state-level purchasing managers' survey in the country: Creighton's "
          "nine-state Mid-America index, with new orders, production, delivery lead time, inventories and employment "
          "for each of Arkansas, Iowa, Kansas, Minnesota, Missouri, Nebraska, North Dakota, Oklahoma and South "
          "Dakota, published on the first business day of the month and never revised; with it the ten-state rural "
          "bank survey, and the Atlanta Fed's firm cost expectations for its district.",
 'files': [
   F('atlanta_business_inflation_expectations.xlsx',
     'https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/research/inflationproject/bie/data/bie.xlsx'),
 ]}

TRADE_DATED = [
 {'url': 'https://www.census.gov/foreign-trade/statistics/state/origin_movement/exh2s_%y%m.xlsx',
  'out': 'census_state_exports_%Y-%m.xlsx', 'months': 90, 'min_bytes': 10000, 'mark_404_days': 7},
 {'url': 'https://www.census.gov/foreign-trade/statistics/state/destination_state/exh2as_%y%m.xlsx',
  'out': 'census_state_imports_%Y-%m.xlsx', 'months': 90, 'min_bytes': 10000, 'mark_404_days': 7},
 {'url': 'https://www.dmr.nd.gov/oilgas/stats/%Ymonthlystats.pdf',
  'out': 'north_dakota_oil_gas_%Y.pdf', 'quarters': 24, 'min_bytes': 10000, 'mark_404_days': 14},
]

PAGES = [
 {'page': 'https://www.creighton.edu/economicoutlook/midamericaneconomy',
  'pattern': 'href="([^"]*Mid-America-Business-Conditions[^"]*\\.pdf)"',
  'out_prefix': 'creighton_mid_america_pmi', 'take': 'all', 'fresh_hours': 40},
 {'page': 'https://www.creighton.edu/economicoutlook/ruralmainstreeteconomy',
  'pattern': 'href="([^"]*Rural-Mainstreet[^"]*\\.pdf)"',
  'out_prefix': 'creighton_rural_mainstreet', 'take': 'all', 'fresh_hours': 40},
 {'page': 'https://www.rrc.texas.gov/oil-and-gas/research-and-statistics/drilling-information/monthly-drilling-completion-and-plugging-summaries/',
  'pattern': 'href="([^"]*media/[^"]*\\.pdf)"', 'out_prefix': 'texas_drilling_summary', 'take': 'all',
  'fresh_hours': 100},
]


def main():
    j = json.load(open(SRC))
    names = [x['name'] for x in j['jobs']]
    added = []
    for job in (HOURS, CREDIT, ACTIVITY, TRENDS, SURVEYS):
        if job['name'] not in names:
            j['jobs'].append(job); added.append(job['name'])

    # --- the dated backfills move off the hourly lane -------------------------------------------------
    dated = next((x for x in j['jobs'] if x['name'] == 'dated_files'), None)
    back = next((x for x in j['jobs'] if x['name'] == 'dated_backfill'), None)
    if dated is not None and back is None:
        deep = [p for p in dated['patterns'] if int(p.get('months', 0)) > 24 or int(p.get('quarters', 0)) > 8]
        dated['patterns'] = [p for p in dated['patterns'] if p not in deep] + TRADE_DATED
        back = {'name': 'dated_backfill', 'func': 'job_dated_files', 'dir': 'dated_files',
                'patterns': deep,
                '_note': "Split out of dated_files on 18 Sep 2026. Walking four hundred dated addresses for the "
                         "permit and revenue histories had taken the hourly cycle from twenty seconds to eleven "
                         "minutes. The deep backfills run on the six-hour thread; the current months stay hourly. "
                         "Both mark an address that answers 404, so a month not yet published costs one request."}
        j['jobs'].append(back); added.append('dated_backfill')
    elif dated is not None:
        have = {p['out'] for p in dated['patterns']}
        for p in TRADE_DATED:
            if p['out'] not in have: dated['patterns'].append(p)

    dyn = next((x for x in j['jobs'] if x['name'] == 'dynamic_links'), None)
    if dyn is not None:
        seen = {p['out_prefix'] for p in dyn.get('pages', [])}
        for p in PAGES:
            if p['out_prefix'] not in seen: dyn['pages'].append(p)

    slow = set(j.get('slow_jobs', []))
    slow.update(['dated_backfill', 'state_credit', 'state_hours_earnings'])
    j['slow_jobs'] = sorted(slow)

    # --- speed ---------------------------------------------------------------------------------------
    j['cycle_workers'] = 8
    for x in j['jobs']:
        if x.get('files') and not x.get('pause_seconds') and not x.get('stop_after_throttles'):
            x['parallel'] = max(int(x.get('parallel', 1)), 8)
    j.setdefault('fast_jobs', [])
    for n in ('state_activity_hf', 'state_search_trends'):
        if n not in j['fast_jobs']: j['fast_jobs'].append(n)

    shutil.copyfile(SRC, os.path.join(HERE, 'sources_pre_robust_%s.json.bak' % STAMP))
    json.dump(j, open(SRC, 'w'), indent=1)
    print('jobs added:', added)
    print('registry:', len(j['jobs']), 'jobs |', sum(len(x.get('files', [])) for x in j['jobs']), 'files |',
          'hourly dated patterns', len(dated['patterns']) if dated else 0,
          '| backfill patterns', len(back['patterns']) if back else 0)
    print('cycle_workers', j['cycle_workers'], '| fast jobs', j['fast_jobs'])


if __name__ == '__main__':
    main()
