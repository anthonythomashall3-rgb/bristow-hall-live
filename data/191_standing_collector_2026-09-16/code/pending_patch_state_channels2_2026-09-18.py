#!/usr/bin/env python3
"""A second sweep of state channels (collection 191), 18 September 2026.

The find that matters most: the Boston Fed publishes a weekly index of economic conditions for every one of the fifty
states, six days behind, back to April 1987. Nothing else in this programme is weekly, state-level and forty years
long at the same time. It belongs at the front of any state test, and the warehouse did not have it.

Beside it, in order of what a detector would want: the daily index of job postings by state (our earlier address
pointed at the wrong repository and never answered - corrected here); monthly retail sales by state and by trade
category, which is the state counterpart of the national retail report; the operating authorities the federal motor
carrier administration grants and revokes each day, with the carrier register to attach a state to each, which is
business formation and failure in the one industry that turns first; consumer complaints by state, daily; federal
obligations by state, monthly; small-business lending by project state, monthly and only two and a half weeks behind;
student-loan balances and marketplace enrolment by state; entrepreneurship indicators; and alcohol permits, which are
a licence count for an industry that opens and closes with the cycle.
"""
import json, os, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'sources.json')
STAMP = time.strftime('%Y-%m-%d_%H%M')
DT = 'https://data.transportation.gov/resource/'
SBA = 'https://sba-llms-prd-public.sbalenderportal.com/'


def F(out, url, **kw):
    d = {'url': url, 'out': out}; d.update(kw); return d


WEEKLY = {
 'name': 'state_weekly_conditions', 'dir': 'state_weekly_conditions', 'keep_vintages': True, 'fresh_hours': 12,
 'parallel': 4,
 '_note': "Added 18 Sep 2026, and the most valuable state object found in any sweep. The Boston Fed's weekly index of "
          "economic conditions covers all fifty states with a six-day lag and runs back to April 1987, which means a "
          "state-level test can be run weekly over four decades rather than monthly over two. The normalised file is "
          "kept beside the raw one. With it the daily index of job postings by state: the address used earlier "
          "pointed at the wrong repository and never answered, which is why postings had been missing from the state "
          "panel.",
 'files': [
   F('boston_fed_weekly_state_conditions.csv',
     'https://www.bostonfed.org/api/azurecontainer/download/weekly-state-summaries/data/SWEP.csv'),
   F('boston_fed_weekly_state_conditions_normalized.csv',
     'https://www.bostonfed.org/api/azurecontainer/download/weekly-state-summaries/data/SWEP_normalized.csv'),
   F('indeed_job_postings_by_state_daily.csv',
     'https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/master/US/state_job_postings_us.csv'),
   F('indeed_job_postings_national_daily.csv',
     'https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/master/US/aggregate_job_postings_US.csv'),
 ]}

RETAIL = {
 'name': 'state_retail_and_spending', 'dir': 'state_retail_and_spending', 'keep_vintages': True, 'fresh_hours': 40,
 'parallel': 4,
 '_note': "Added 18 Sep 2026. Monthly retail sales by state and by trade category, the state counterpart of the "
          "national retail report, with its standard errors and its coverage file; and consumer complaints by state, "
          "which arrive within days and rise when households are under strain.",
 'files': [
   F('census_monthly_state_retail_sales.csv',
     'https://www.census.gov/retail/mrts/www/statedata/state_retail_yy.csv'),
   F('census_monthly_state_retail_sales_errors.csv',
     'https://www.census.gov/retail/mrts/www/statedata/state_retail_se.csv'),
   F('census_monthly_state_retail_coverage.csv',
     'https://www.census.gov/retail/mrts/www/statedata/state_retail_coverage.csv'),
   F('cfpb_consumer_complaints.csv.zip', 'https://files.consumerfinance.gov/ccdb/complaints.csv.zip',
     fresh_hours=160),
   F('cfpb_auto_loan_originations_by_state.json',
     'https://files.consumerfinance.gov/data/consumer-credit-trends/auto-loans/map_data_AUT.json'),
   F('cfpb_mortgage_originations_by_state.json',
     'https://files.consumerfinance.gov/data/consumer-credit-trends/mortgages/map_data_MTG.json'),
   F('cfpb_credit_card_originations_by_state.json',
     'https://files.consumerfinance.gov/data/consumer-credit-trends/credit-cards/map_data_CRC.json'),
 ]}

CARRIER = {
 'name': 'state_carrier_activity', 'dir': 'state_carrier_activity', 'keep_vintages': True, 'fresh_hours': 24,
 'parallel': 5,
 '_note': "Added 18 Sep 2026. Trucking turns before almost anything else, and the federal motor carrier "
          "administration publishes its register daily: which operating authorities were granted and which revoked, "
          "which carriers were put out of service, and the carrier file that attaches a state to each docket. Together "
          "they are daily business formation and failure in the industry that moves first. Never revised; the record "
          "is the record.",
 'files': [
   F('fmcsa_authority_history.csv', DT + 'yu5v-wbh6.csv?$limit=500000&$order=status_change_date%20DESC'),
   F('fmcsa_revocations.csv', DT + 'sa6p-acbp.csv?$limit=300000'),
   F('fmcsa_out_of_service.csv', DT + 'p2mt-9ige.csv?$limit=300000'),
   F('fmcsa_carrier_state_crosswalk.csv',
     DT + '6eyk-hxee.csv?$select=bus_state_code,count(*)&$group=bus_state_code'),
   F('fmcsa_carrier_census.csv.gz', DT + 'az4n-8mr2.csv?$limit=2000000', stream=True, fresh_hours=400),
   F('fmcsa_crashes.csv', DT + 'aayw-vxb3.csv?$limit=500000&$order=report_date%20DESC'),
 ]}

FEDERAL = {
 'name': 'state_federal_flows', 'dir': 'state_federal_flows', 'keep_vintages': True, 'fresh_hours': 100,
 'parallel': 4,
 '_note': "Added 18 Sep 2026. Money the federal government puts into each state, and the loans it guarantees there. "
          "Contract obligations by place of performance for any window; small-business lending by project state, "
          "monthly and only two and a half weeks behind, which is the promptest credit series with a state dimension "
          "found anywhere; flood claims and policies by state; marketplace enrolment; and student-loan balances and "
          "borrower counts by state.",
 'files': [
   F('usaspending_by_state_recipient.json', 'https://api.usaspending.gov/api/v2/recipient/state/'),
   F('sba_monthly_lender_activity.xlsx', SBA + 'SBA-Monthly-Lender7AActivity.xlsx'),
   F('sba_monthly_cdc_activity.xlsx', SBA + 'SBA-Monthly-CDCActivity.xlsx'),
   F('sba_monthly_combined_activity.xlsx', SBA + 'SBA-Monthly-MonthlyYearlyActivity7a504.xlsx'),
   F('sba_state_small_business_statistics.xlsx',
     'https://data.sba.gov/sites/default/files/distribution/SBA-ADVO-CKAN-009/state_statistics_rankings_2025.xlsx',
     fresh_hours=800),
   F('fema_nfip_policies_by_state.json',
     'https://www.fema.gov/api/open/v3/NfipPolicies?$select=propertyState,policyEffectiveDate,policyCount'
     '&$top=100000', fresh_hours=400),
   F('cms_marketplace_enrolment_by_state.csv',
     'https://data.cms.gov/data-api/v1/dataset/1829fdb3-a6f9-4036-856a-3af1f7828c8c/data?size=50000&format=csv'),
   F('student_loan_portfolio_by_state.xls',
     'https://studentaid.gov/sites/default/files/fsawg/datacenter/library/DLPortfolio-by-Location.xls',
     fresh_hours=400),
 ]}

FIRMS = {
 'name': 'state_firm_formation', 'dir': 'state_firm_formation', 'keep_vintages': True, 'fresh_hours': 400,
 'parallel': 3,
 '_note': "Added 18 Sep 2026. Who is starting businesses in each state and who is being licensed to trade. The "
          "entrepreneurship indicators by state, and the alcohol permits issued since the last publication, which is "
          "a licence count for an industry that opens and closes with the cycle. With them the household debt and "
          "delinquency figures by state and the college enrolment appendix, which rises when work is scarce.",
 'files': [
   F('kauffman_early_stage_entrepreneurship.zip',
     'https://indicators.kauffman.org/wp-content/uploads/sites/13/2026/05/'
     'KauffmanEarlyStageEntrepreneurship_May2026.zip'),
   F('kauffman_new_employer_businesses.zip',
     'https://indicators.kauffman.org/wp-content/uploads/sites/13/2026/05/'
     'KauffmanNewEmployerBusinesses_May2026.zip'),
   F('ttb_alcohol_permits_issued.csv',
     'https://www.ttb.gov/system/files/2025-04/FRL_Basic_Permits_Issued_Since_the_Last_Publication.csv'),
   F('newyork_household_debt_by_state.xlsx',
     'https://www.newyorkfed.org/medialibrary/interactives/householdcredit/data/xls/area_report_by_year.xlsx'),
   F('student_clearinghouse_enrollment_by_state.xlsx',
     'https://nscresearchcenter.org/wp-content/uploads/CTEESpring2025-DataAppendix.xlsx', fresh_hours=800),
 ]}


def main():
    j = json.load(open(SRC))
    names = [x['name'] for x in j['jobs']]
    added = []
    for job in (WEEKLY, RETAIL, CARRIER, FEDERAL, FIRMS):
        if job['name'] not in names:
            j['jobs'].append(job); added.append(job['name'])
    # the weekly index and postings belong on the fast lane; the heavy registers on the slow one
    fast = j.setdefault('fast_jobs', [])
    if 'state_weekly_conditions' not in fast: fast.append('state_weekly_conditions')
    slow = set(j.get('slow_jobs', []))
    slow.update(['state_carrier_activity', 'state_firm_formation'])
    j['slow_jobs'] = sorted(slow)
    shutil.copyfile(SRC, os.path.join(HERE, 'sources_pre_channels2_%s.json.bak' % STAMP))
    json.dump(j, open(SRC, 'w'), indent=1)
    print('jobs added:', added)
    print('registry:', len(j['jobs']), 'jobs |', sum(len(x.get('files', [])) for x in j['jobs']), 'files')


if __name__ == '__main__':
    main()
