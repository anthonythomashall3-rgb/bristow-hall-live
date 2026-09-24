#!/usr/bin/env python3
"""Third-sweep patch for the standing collector (collection 191), 18 September 2026.

A third search, run after two others, for state data the warehouse still did not hold. Its largest single finding is
not a dataset but a door: api.us.socrata.com searches every Socrata portal in the United States at once, which is what
the collector's own discovery job now uses. Its largest datasets are the weekly business applications by state that
Census publishes as a plain keyless file, per-establishment alcohol receipts in Texas by county and month, daily
lottery sales by retailer in New York, weekly eviction filings by census tract in most states, and county-grain food
assistance in Pennsylvania.

Two warnings from the search are written into the code rather than into a note: a Socrata catalogue's updatedAt is
metadata churn and not data recency (Colorado's foreclosure files look fresh and end in 2016), so the discovery job
asks each dataset for the maximum of its own date column before believing it; and several hosts refuse a plain client
but answer a browser, which the fetch engine already handles.

Run on the Mac from 191/code:  python3 pending_patch_third_sweep_2026-09-18.py
"""
import json, os, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'sources.json')
STAMP = time.strftime('%Y-%m-%d_%H%M')
LIM = '?$limit=500000'


def F(out, url, **kw):
    d = {'url': url, 'out': out}
    d.update(kw)
    return d


JOBS = [
 {'name': 'state_business_formation', 'dir': 'state_business_formation', 'keep_vintages': True, 'fresh_hours': 12, 'parallel': 5,
  '_note': "Added 18 Sep 2026. Businesses being started and stopped, at the finest grain any government publishes. Census counts applications by state every week in a keyless file (the API now demands a key; this file does not). New York lists every corporate filing the day it is made, with the county; Colorado lists every entity with its formation date and every later transaction, so dissolutions can be counted as well as formations; Oregon, Connecticut and Delaware list registrations and licences; Texas and Pennsylvania list active permits, which is a count of establishments.",
  'files': [
   F('census_business_applications_state_weekly.csv', 'https://www.census.gov/econ/bfs/csv/bfs_state_apps_weekly_nsa.csv'),
   F('census_business_applications_region_weekly.csv', 'https://www.census.gov/econ/bfs/csv/bfs_region_apps_weekly_nsa.csv'),
   F('census_business_applications_us_weekly.csv', 'https://www.census.gov/econ/bfs/csv/bfs_us_apps_weekly_nsa.csv'),
   F('new_york_corporate_filings_daily.csv', 'https://data.ny.gov/resource/k4vb-judh.csv' + LIM),
   F('colorado_business_entities.csv', 'https://data.colorado.gov/resource/4ykn-tg5h.csv' + LIM, fresh_hours=40),
   F('colorado_business_entity_transactions.csv', 'https://data.colorado.gov/resource/casm-dbbj.csv' + LIM, fresh_hours=40),
   F('oregon_new_business_registrations.csv', 'https://data.oregon.gov/resource/esjy-u4fc.csv' + LIM),
   F('connecticut_business_registry.csv', 'https://data.ct.gov/resource/n7gp-d28j.csv' + LIM, fresh_hours=40),
   F('connecticut_business_filing_history.csv', 'https://data.ct.gov/resource/ah3s-bes7.csv' + LIM, fresh_hours=40),
   F('delaware_business_licences.csv', 'https://data.delaware.gov/resource/5zy2-grhr.csv' + LIM, fresh_hours=40),
   F('pennsylvania_sales_tax_licences_by_county.csv', 'https://data.pa.gov/resource/ugeq-ckxd.csv' + LIM, fresh_hours=40),
   F('texas_active_sales_tax_permits.csv', 'https://data.texas.gov/resource/jrea-zgmq.csv' + LIM, fresh_hours=40),
  ]},

 {'name': 'state_spending_receipts', 'dir': 'state_spending_receipts', 'keep_vintages': True, 'fresh_hours': 12, 'parallel': 5,
  '_note': "Added 18 Sep 2026. What people actually spend, collected by tax authorities rather than asked in a survey. Texas taxes every bar and restaurant's alcohol receipts and publishes them per establishment per month with the county, which is a discretionary-consumption series at sub-state grain. New York publishes lottery sales per retailer per day, which is the highest-frequency free spending proxy found anywhere in this search.",
  'files': [
   F('texas_mixed_beverage_gross_receipts.csv', 'https://data.texas.gov/resource/naix-2893.csv' + LIM),
   F('texas_mixed_beverage_sales_receipts.csv', 'https://data.texas.gov/resource/g5bj-yb6k.csv' + LIM),
   F('new_york_lottery_daily_retailer_sales.csv', 'https://data.ny.gov/resource/xyvi-fbb9.csv?$limit=1000000&$order=bus_day%20DESC'),
   F('texas_lottery_sales_by_month_and_retailer.csv', 'https://data.texas.gov/resource/beka-uwfq.csv' + LIM),
   F('texas_key_economic_indicators.csv', 'https://data.texas.gov/resource/karz-jr5v.csv' + LIM),
   F('texas_quarterly_sales_tax_history.csv', 'https://data.texas.gov/resource/7z4d-yf2c.csv' + LIM),
  ]},

 {'name': 'state_labour_extra', 'dir': 'state_labour_extra', 'keep_vintages': True, 'fresh_hours': 12, 'parallel': 5,
  '_note': "Added 18 Sep 2026. Claims cut by industry and by age in Missouri, and Colorado's own labour files, which are worth having for one reason beyond their content: the unemployment estimates carry preliminary and benchmark flags, so the state itself declares which numbers are not final. Colorado also publishes state-level job openings, hires, quits and layoffs back to December 2000.",
  'files': [
   F('missouri_claims_by_industry_monthly.csv', 'https://data.mo.gov/resource/cj66-t7xq.csv' + LIM),
   F('missouri_claims_by_age_monthly.csv', 'https://data.mo.gov/resource/5tqh-2x4m.csv' + LIM),
   F('colorado_state_jolts.csv', 'https://data.colorado.gov/resource/3p8a-wq25.csv' + LIM),
   F('colorado_employment_and_wages.csv', 'https://data.colorado.gov/resource/busm-qa5b.csv' + LIM),
   F('colorado_unemployment_estimates_substate.csv', 'https://data.colorado.gov/resource/4e3w-qire.csv' + LIM),
  ]},

 {'name': 'state_distress', 'dir': 'state_distress', 'keep_vintages': True, 'fresh_hours': 24, 'parallel': 4,
  '_note': "Added 18 Sep 2026. Households losing their homes, which no labour series records. The Eviction Lab file is weekly at census-tract level for most states and is still being updated despite a file name that says 2021; Connecticut publishes the same by tract; Maryland publishes foreclosure notices by county monthly and eviction cases one by one; Texas publishes landlord and tenant caseload by county and precinct.",
  'files': [
   F('eviction_lab_weekly_by_tract.csv.gz', 'https://eviction-lab-data-downloads.s3.amazonaws.com/ets/allstates_weekly_2020_2021.csv', stream=True, fresh_hours=100),
   F('eviction_lab_sites_weekly.csv', 'https://eviction-lab-data-downloads.s3.amazonaws.com/ets/all_sites_weekly_2020_2021.csv', fresh_hours=100),
   F('connecticut_evictions_weekly_by_tract.csv', 'https://data.ct.gov/resource/j5dt-tcp7.csv' + LIM),
   F('maryland_foreclosure_notices_by_county.csv', 'https://opendata.maryland.gov/resource/w3bc-8mnv.csv' + LIM),
   F('maryland_eviction_cases.csv', 'https://opendata.maryland.gov/resource/mvqb-b4hf.csv' + LIM),
   F('texas_landlord_tenant_caseload.csv', 'https://data.texas.gov/resource/8qme-eqs9.csv' + LIM),
   F('texas_landlord_tenant_caseload_2018_2022.csv', 'https://data.texas.gov/resource/t2fh-6f7n.csv' + LIM, fresh_hours=400),
   F('fulton_county_georgia_eviction_filings.csv', 'https://sharefulton.fultoncountyga.gov/resource/cbu2-qs5w.csv' + LIM),
  ]},

 {'name': 'state_safety_net', 'dir': 'state_safety_net', 'keep_vintages': True, 'fresh_hours': 40, 'parallel': 3,
  '_note': "Added 18 Sep 2026. Food assistance by county in Pennsylvania, individuals and dollars, monthly back to 2004, which is finer than the federal file; and Connecticut's monthly counts by programme.",
  'files': [
   F('pennsylvania_snap_by_county_monthly.csv', 'https://data.pa.gov/resource/kd9x-cq7y.csv' + LIM),
   F('connecticut_assistance_participation_monthly.csv', 'https://data.ct.gov/resource/chsv-phja.csv' + LIM),
  ]},

 {'name': 'state_indexes_extra', 'dir': 'state_indexes_extra', 'keep_vintages': True, 'fresh_hours': 40, 'parallel': 3,
  '_note': "Added 18 Sep 2026. Three state-level indexes the warehouse lacked: the Dallas Fed's Texas leading index, the New York Fed's household debt and delinquency by state, and economic policy uncertainty by state, monthly from 1985, which is the only state-level uncertainty measure that exists.",
  'files': [
   F('dallas_texas_leading_index.xlsx', 'https://www.dallasfed.org/~/media/documents/research/econdata/leadi.xlsx'),
   F('newyork_household_debt_by_state.xlsx', 'https://www.newyorkfed.org/medialibrary/Interactives/householdcredit/data/xls/area_report_by_year.xlsx'),
   F('state_economic_policy_uncertainty.xlsx', 'https://www.policyuncertainty.com/media/State_Policy_Uncertainty.xlsx'),
  ]},

 {'name': 'transit_activity', 'dir': 'transit_activity', 'keep_vintages': True, 'fresh_hours': 40, 'parallel': 3,
  '_note': "Added 18 Sep 2026. Public transport ridership by agency with the state attached, monthly: people going to work, counted at the turnstile. Reached through the transportation department's Socrata portal, because its own host refuses a plain client.",
  'files': [
   F('fta_monthly_ridership_by_agency.csv', 'https://data.transportation.gov/resource/8bui-9xvu.csv' + LIM),
   F('fta_monthly_modal_time_series.csv', 'https://data.transportation.gov/resource/5ti2-5uiv.csv' + LIM),
   F('bts_supply_chain_indicators.csv', 'https://data.bts.gov/resource/y5ut-ibwt.csv' + LIM),
   F('bts_monthly_transportation_statistics.csv', 'https://data.bts.gov/resource/crem-w557.csv' + LIM),
  ]},

 {'name': 'bankruptcy_district', 'dir': 'bankruptcy_district', 'keep_vintages': True, 'fresh_hours': 40, 'parallel': 2,
  '_note': "Added 18 Sep 2026. The federal courts publish bankruptcy filings by district only once a quarter. Individual bankruptcy courts publish their own monthly counts; Oregon's is a plain table by chapter, month and division and is the most readable of them. A crawl of the other ninety-three districts is a later job.",
  'files': [
   F('oregon_bankruptcy_monthly_by_chapter.html', 'https://ecf.orb.uscourts.gov/docs/extrpt/RPTbiyear.html', min_bytes=2000),
  ]},

 {'name': 'lehd_quarterly_workforce', 'dir': 'lehd_quarterly_workforce', 'keep_vintages': False, 'fresh_hours': 600, 'parallel': 2,
  '_note': "Added 18 Sep 2026. The Quarterly Workforce Indicators as flat files, which need no key where the Census API now does: hires, separations, turnover, job creation and destruction, and earnings, by county and industry, quarterly. The twelve largest states first; the rest follow when the disk allows. Heavily revised each vintage, which is itself the reason to date every copy.",
  'files': [F('qwi_%s_county.csv.gz' % s, 'https://lehd.ces.census.gov/data/qwi/latest_release/%s/qwi_%s_rh_f_gc_n3_op_u.csv.gz' % (s, s), stream=False)
            for s in ('ca', 'tx', 'fl', 'ny', 'pa', 'il', 'oh', 'ga', 'nc', 'mi', 'nj', 'va')]},
]


def main():
    j = json.load(open(SRC))
    names = [x['name'] for x in j['jobs']]
    added = []
    for job in JOBS:
        if job['name'] not in names:
            j['jobs'].append(job); added.append(job['name'])
    slow = set(j.get('slow_jobs', []))
    slow.update(['lehd_quarterly_workforce', 'state_distress'])
    j['slow_jobs'] = sorted(slow)
    shutil.copyfile(SRC, os.path.join(HERE, 'sources_pre_third_%s.json.bak' % STAMP))
    json.dump(j, open(SRC, 'w'), indent=1)
    print('jobs added:', added)
    print('registry now', len(j['jobs']), 'jobs |', sum(len(x.get('files', [])) for x in j['jobs']), 'files listed')


if __name__ == '__main__':
    main()
