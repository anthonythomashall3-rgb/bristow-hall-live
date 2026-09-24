#!/usr/bin/env python3
"""Industry data, nationally and crossed with state (collection 191), 18 September 2026.

A recession does not arrive everywhere at once; it arrives in an industry, in a state, and spreads. The warehouse
could see states and it could see the nation, but it could barely see industries, and it could not see the two
crossed. Fifty addresses were tested for this and read.

The unlock is the Quarterly Workforce Indicators. They are the only free source giving quarterly flows by state and
six-digit industry - not levels but flows: firm job gains, firm job losses, hires, separations, turnover and
earnings, through the fourth quarter of 2025. Firm job losses by state and industry is closer to what this rule wants
than any employment level, and nothing else publishes it.

Beside it, three doors that need no key where the usual ones now demand one. The Census bulk endpoint serves
manufacturers' orders, the services survey, the quarterly financial report and construction spending as whole files.
The employment and wages census publishes one file per area and one per industry, and a slice interface that returns
monthly employment for any county and any six-digit industry. And the Securities and Exchange Commission publishes,
every quarter, the numeric facts of every filing with the filer's industry code and its state of business, which is
company-level activity by industry and state that no statistical agency produces.

With them: producer prices by industry and by commodity, import and export prices, industry productivity, capacity
utilisation for thirty-nine industries and the motor-vehicle assembly series, the establishment census by state and
county and six-digit industry, firm-size detail, non-employer businesses, the weekly rail file, which reports grain
cars loaded by state and carloads in twenty-two commodity categories two days behind, and job postings by sector
daily.
"""
import json, os, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'sources.json')
STAMP = time.strftime('%Y-%m-%d_%H%M')
EC = 'https://www.census.gov/econ_getzippedfile/?programCode='
C2 = 'https://www2.census.gov/'
BLS = 'https://download.bls.gov/pub/time.series/'
FRB = 'https://www.federalreserve.gov/releases/g17/'
UA = {'User-Agent': 'Bristow-Hall recession research (+https://bhrrealtime.pages.dev)'}
HL = 'https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/master/US/'


def F(out, url, **kw):
    d = {'url': url, 'out': out}; d.update(kw); return d


CENSUS = {
 'name': 'industry_census_bulk', 'dir': 'industry_census_bulk', 'keep_vintages': True, 'fresh_hours': 40,
 'parallel': 5,
 '_note': "Added 18 Sep 2026. The Census bulk endpoint, which serves a whole programme as one file and asks for no "
          "key where the interface now demands one. Manufacturers' shipments, inventories and orders across eighty-"
          "seven categories, with new orders and unfilled orders separated - unfilled orders being the clearest "
          "forward-looking series in the manufacturing data. The advance durables file two weeks earlier. The "
          "quarterly services survey down to six-digit industry. The quarterly financial report, which is profits, "
          "sales and balance sheets by manufacturing industry. Construction spending by type, including the "
          "manufacturing category that has moved so much lately. And the inventory-to-sales ratios.",
 'files': [
   F('census_m3_manufacturers_orders.zip', EC + 'M3'),
   F('census_m3_advance_durables.zip', EC + 'M3ADV'),
   F('census_quarterly_services_survey.zip', EC + 'QSS'),
   F('census_quarterly_financial_report.zip', EC + 'QFR'),
   F('census_construction_spending.zip', EC + 'VIP'),
   F('census_inventories_and_sales.zip', EC + 'MTIS'),
   F('census_construction_private_detail.xls', 'https://www.census.gov/construction/c30/xls/privsa.xls'),
   F('census_services_current_tables.xlsx', 'https://www.census.gov/services/qss/qss-current.xlsx'),
 ]}

STATEIND = {
 'name': 'state_by_industry', 'dir': 'state_by_industry', 'keep_vintages': True, 'fresh_hours': 400, 'parallel': 3,
 '_note': "Added 18 Sep 2026, and the scarcest thing in the warehouse: measures that are state AND industry at once. "
          "The workforce indicators give quarterly flows by state and six-digit industry - firm job gains, firm job "
          "losses, hires, separations, turnover, earnings - which is what a rule about job destruction actually "
          "wants. The employment and wages census gives one file per area and one per industry, quarterly, to six "
          "digits. The establishment census gives counts and payroll by state, county and six-digit industry. Firm "
          "size detail says whether small firms or large ones are shedding. Non-employer businesses count the "
          "self-employed, who vanish from payroll measures entirely.",
 'files': [
   F('qcew_2025_by_area.zip', 'https://data.bls.gov/cew/data/files/2025/csv/2025_qtrly_by_area.zip',
     headers=UA, fresh_hours=800),
   F('qcew_2025_by_industry.zip', 'https://data.bls.gov/cew/data/files/2025/csv/2025_qtrly_by_industry.zip',
     headers=UA, fresh_hours=800),
   F('susb_state_by_6digit_naics_by_firm_size.txt.gz',
     C2 + 'programs-surveys/susb/tables/2022/us_state_6digitnaics_2022.txt', stream=True, fresh_hours=800),
   F('susb_county_by_3digit_naics.xlsx',
     C2 + 'programs-surveys/susb/tables/2022/county_3digitnaics_2022.xlsx', fresh_hours=800),
   F('nonemployer_statistics_state_by_naics.zip',
     C2 + 'programs-surveys/nonemployer-statistics/datasets/2022/historical-datasets/nonemp22st.zip',
     fresh_hours=800),
   F('economic_census_2022_basic.zip',
     C2 + 'programs-surveys/economic-census/data/2022/sector00/EC2200BASIC.zip', fresh_hours=2000),
   F('aies_manufacturing_2024.zip', C2 + 'programs-surveys/aies/data/2024/AIES31BASIC01.zip', fresh_hours=800),
   F('aies_all_sectors_2024.zip', C2 + 'programs-surveys/aies/data/2024/AIES00BASIC.zip', fresh_hours=800),
 ] + [F('qwi_%s_state_by_6digit_naics.csv.gz' % s,
        'https://lehd.ces.census.gov/data/qwi/latest_release/%s/qwi_%s_sa_f_gs_n6_op_u.csv.gz' % (s, s),
        fresh_hours=2000)
      for s in ('ca', 'tx', 'fl', 'ny', 'pa', 'il', 'oh', 'ga', 'nc', 'mi', 'nj', 'va', 'wa', 'az', 'ma', 'tn',
                'in', 'mo', 'md', 'wi', 'co', 'mn', 'sc', 'al', 'la')]}

PRICES = {
 'name': 'industry_prices_productivity', 'dir': 'industry_prices_productivity', 'keep_vintages': True,
 'fresh_hours': 100, 'parallel': 3,
 '_note': "Added 18 Sep 2026. What industries charge and what it costs them to produce. Producer prices by industry "
          "to six-digit detail and by commodity back to 1967; import and export prices across sixteen hundred "
          "series; and productivity and unit labour cost by industry. Prices turn before volumes in several "
          "industries, and unit labour cost is the margin squeeze that precedes a layoff.",
 'files': [
   F('ppi_by_industry.txt.gz', BLS + 'pc/pc.data.0.Current', stream=True, headers=UA),
   F('ppi_industry_codes.txt', BLS + 'pc/pc.industry', headers=UA, min_bytes=1000),
   F('ppi_by_commodity.txt.gz', BLS + 'wp/wp.data.1.AllCommodities', stream=True, headers=UA),
   F('import_export_prices.txt.gz', BLS + 'ei/ei.data.0.Current', stream=True, headers=UA),
   F('import_export_price_series.txt.gz', BLS + 'ei/ei.series', stream=True, headers=UA),
   F('industry_productivity.txt.gz', BLS + 'ip/ip.data.1.AllData', stream=True, headers=UA),
   F('sae_industry_codes.txt', BLS + 'sm/sm.industry', headers=UA, min_bytes=1000),
 ]}

CAPACITY = {
 'name': 'industry_capacity', 'dir': 'industry_capacity', 'keep_vintages': True, 'fresh_hours': 100, 'parallel': 3,
 '_note': "Added 18 Sep 2026. Capacity utilisation for thirty-nine industries as a flat file, and the whole "
          "production release as one package: two and a half thousand series, including a hundred and seventy-one "
          "utilisation series and the twelve motor-vehicle assembly series, which are a weekly-to-monthly physical "
          "count of cars and trucks actually built and which fall early and hard.",
 'files': [
   F('capacity_utilisation_by_industry.txt', FRB + 'ipdisk/utl_sa.txt', min_bytes=10000),
   F('capacity_level_by_industry.txt', FRB + 'ipdisk/cap_sa.txt', min_bytes=10000),
   F('industrial_production_by_industry.txt', FRB + 'ipdisk/ip_sa.txt', min_bytes=100000),
   F('g17_full_release.zip', FRB + 'data/FRB_g17_xml.zip'),
 ]}

FILERS = {
 'name': 'industry_company_filings', 'dir': 'industry_company_filings', 'keep_vintages': False, 'fresh_hours': 400,
 'parallel': 2,
 '_note': "Added 18 Sep 2026. Every quarter the Securities and Exchange Commission publishes the numeric facts of "
          "every filing, with the filer's industry code and its state of business address. That is company-level "
          "revenue, income and balance sheet by industry and by state, at a grain no statistical agency produces, "
          "about a month after the quarter closes. The rule cannot read it directly, but a measure of how many firms "
          "in an industry and a state reported falling revenue is buildable from it and from nothing else free.",
 'files': [
   F('sec_financial_statements_2026q2.zip',
     'https://www.sec.gov/files/dera/data/financial-statement-data-sets/2026q2.zip', headers=UA, fresh_hours=2000),
   F('sec_financial_statements_2026q1.zip',
     'https://www.sec.gov/files/dera/data/financial-statement-data-sets/2026q1.zip', headers=UA, fresh_hours=2000),
   F('sec_financial_statements_2025q4.zip',
     'https://www.sec.gov/files/dera/data/financial-statement-data-sets/2025q4.zip', headers=UA, fresh_hours=2000),
   F('sec_company_tickers.json', 'https://www.sec.gov/files/company_tickers.json', headers=UA),
 ]}

HF = {
 'name': 'industry_high_frequency', 'dir': 'industry_high_frequency', 'keep_vintages': True, 'fresh_hours': 12,
 'parallel': 4,
 '_note': "Added 18 Sep 2026. Industry activity faster than a month. The rail file reports carloads in twenty-two "
          "commodity categories and grain cars loaded BY STATE, weekly and two days behind, which is the only weekly "
          "state-and-industry physical measure found anywhere. Job postings by sector daily. And the keyless series "
          "endpoint for the industrial production and orders series that have no flat file of their own.",
 'files': [
   F('indeed_postings_by_sector_daily.csv', HL + 'job_postings_by_sector_US.csv'),
   F('indeed_sector_dictionary.csv',
     'https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/master/sector-job-title-examples.csv',
     fresh_hours=800, min_bytes=200),
   F('bts_transportation_services_index.csv', 'https://data.bts.gov/resource/bw6n-ddqk.csv?$limit=50000'),
 ] + [F('fred_%s.csv' % s.lower(), 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s' % s, min_bytes=200)
      for s in ('IPG331S', 'IPG3311A2S', 'IPG334S', 'IPG3254S', 'IPG321S', 'IPG327S', 'CAPUTLG3361T3S',
                'MVATOTASSS', 'RAILFRTCARLOADSD11', 'RAILFRTINTERMODALD11', 'TRUCKD11', 'AMTMNO', 'AMTMUO',
                'ACOGNO', 'DGORDER', 'NEWORDER', 'MNFCTRIRSA')]}

PAGES = [
 {'page': 'https://www.stb.gov/reports-data/rail-service-data/',
  'pattern': 'href="([^"]*EP724%20Consolidated%20Data[^"]*\\.xlsx)"',
  'out_prefix': 'stb_rail_by_commodity_and_state', 'take': 'first', 'fresh_hours': 40},
]


def main():
    j = json.load(open(SRC))
    names = [x['name'] for x in j['jobs']]
    added = []
    for job in (CENSUS, STATEIND, PRICES, CAPACITY, FILERS, HF):
        if job['name'] not in names:
            j['jobs'].append(job); added.append(job['name'])
    dyn = next((x for x in j['jobs'] if x['name'] == 'dynamic_links'), None)
    if dyn is not None:
        seen = {p['out_prefix'] for p in dyn.get('pages', [])}
        for p in PAGES:
            if p['out_prefix'] not in seen: dyn['pages'].append(p)
    slow = set(j.get('slow_jobs', []))
    slow.update(['state_by_industry', 'industry_company_filings', 'industry_prices_productivity'])
    j['slow_jobs'] = sorted(slow)
    fast = j.setdefault('fast_jobs', [])
    if 'industry_high_frequency' not in fast: fast.append('industry_high_frequency')
    shutil.copyfile(SRC, os.path.join(HERE, 'sources_pre_industry_%s.json.bak' % STAMP))
    json.dump(j, open(SRC, 'w'), indent=1)
    print('jobs added:', added)
    print('registry:', len(j['jobs']), 'jobs |', sum(len(x.get('files', [])) for x in j['jobs']), 'files')


if __name__ == '__main__':
    main()
