#!/usr/bin/env python3
"""More channels of state data (collection 191), 18 September 2026.

A sweep of the federal and quasi-federal channels the warehouse had never touched. Fifty-one addresses were tested and
their contents read. What is registered here is everything that answered, grouped by what it measures. Most of these
carry all fifty states in a single file, which is what the parity rule asks for.

The one worth naming first: the Social Security Administration publishes, monthly and in one file, the number of
people who applied for disability benefit in each state, with pending cases, determinations and allowance rates back
to October 2000. Applications for disability rise when work is scarce and are filed by people who have stopped
looking, which makes it one of the few counter-cyclical measures at state level that arrives within a month.

Beside it: federal employment by state and the hires and separations behind it; bank deposits by branch and county
and credit-union call reports; every mortgage application in the country with its state; the Census business-dynamics
file, which is firm entry and exit by state; poverty and median income; population; county permits monthly; state tax
collections quarterly; firearm background checks monthly, which is a well-known and unusually prompt state-level proxy
for household activity; assistance caseloads; farm income and the weekly crop report; rents, vacancy and time on
market; and migration between states.

Two access notes are written into the registry because they are the difference between a file and a refusal. The
Social Security host answers only to a complete browser identity, which the fetch engine's curl rung supplies. The
personnel office refuses its own archives unless the request names the page they are linked from.
"""
import json, os, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'sources.json')
STAMP = time.strftime('%Y-%m-%d_%H%M')
C2 = 'https://www2.census.gov/'
IRS = 'https://www.irs.gov/pub/irs-soi/'
HUD = 'https://www.huduser.gov/portal/'
AL = 'https://assets.ctfassets.net/jeox55pd4d8n/'
OPM_REF = {'Referer': 'https://www.opm.gov/data/datasets/'}


def F(out, url, **kw):
    d = {'url': url, 'out': out}; d.update(kw); return d


JOBS = [
 {'name': 'state_social_programs', 'dir': 'state_social_programs', 'keep_vintages': True, 'fresh_hours': 100,
  'parallel': 4,
  '_note': "Added 18 Sep 2026. People turning to the state when work fails, by state and month. Disability claims are "
           "the centre of it: the workload file carries applications, pending cases, determinations and allowance "
           "rates for every state monthly from October 2000, and applications rise when work is scarce. With them the "
           "supplemental income recipients and payments by state, and the assistance caseloads. The Social Security "
           "host answers only to a complete browser identity, which the fetch engine supplies through its curl rung.",
  'files': [
    F('ssa_disability_state_workload_monthly.csv', 'https://www.ssa.gov/disability/data/SSA-SA-MOWL.csv'),
    F('ssa_ssi_recipients_by_state.html', 'https://www.ssa.gov/policy/docs/statcomps/ssi_monthly/2026-07/table04.html'),
    F('ssa_ssi_payments_by_state.html', 'https://www.ssa.gov/policy/docs/statcomps/ssi_monthly/2026-07/table06.html'),
    F('ssa_ssi_by_state_and_county.xlsx',
      'https://www.ssa.gov/policy/docs/statcomps/ssi_sc/2024/ssi_sc24.xlsx', fresh_hours=800),
    F('ssa_oasdi_by_state_and_county.xlsx',
      'https://www.ssa.gov/policy/docs/statcomps/oasdi_sc/2024/oasdi_sc24.xlsx', fresh_hours=800),
    F('tanf_caseload_by_state_fy2025.xlsx',
      'https://acf.gov/sites/default/files/documents/ofa/fy2025-tanf-caseload.xlsx', fresh_hours=400),
    F('tanf_ssp_caseload_by_state_fy2025.xlsx',
      'https://acf.gov/sites/default/files/documents/ofa/fy2025-tanssp-caseload.xlsx', fresh_hours=400),
  ]},

 {'name': 'state_federal_employment', 'dir': 'state_federal_employment', 'keep_vintages': True, 'fresh_hours': 400,
  'parallel': 2,
  '_note': "Added 18 Sep 2026. Federal civilian employment by duty station, quarterly, with the hires and separations "
           "behind it. Federal employment moves against the cycle in some states and with policy in others, and it is "
           "a fifth of the payroll in several. The archives refuse a request that does not name the page they are "
           "linked from.",
  'files': [
    F('opm_fedscope_employment.zip',
      'https://www.opm.gov/data/datasets/Files/756/a1acc4f3-0c10-45e3-ac1f-0ee7f5769e1d.zip', headers=OPM_REF),
    F('opm_fedscope_accessions.zip',
      'https://www.opm.gov/data/datasets/Files/761/6124a377-5e92-43e7-ade2-3be674580bc7.zip', headers=OPM_REF),
    F('opm_fedscope_separations.zip',
      'https://www.opm.gov/data/datasets/Files/763/1e0ad2cd-40ee-4646-9daa-58b762bcddfb.zip', headers=OPM_REF),
  ]},

 {'name': 'state_banking_credit', 'dir': 'state_banking_credit', 'keep_vintages': True, 'fresh_hours': 200,
  'parallel': 4,
  '_note': "Added 18 Sep 2026. Where deposits sit and where credit is extended, by state. Branch-level deposits with "
           "the county attached; every credit union's call report; and every mortgage application in the country with "
           "its state, outcome and amount, which is the finest picture of household credit that exists free.",
  'files': [
    F('fdic_summary_of_deposits_2024.json',
      'https://api.fdic.gov/banks/sod?filters=YEAR:2024&fields=YEAR,STALPBR,CNTYNAMB,DEPSUMBR,NAMEFULL&limit=100000&format=json',
      fresh_hours=800),
    F('ncua_credit_union_call_reports.zip',
      'https://ncua.gov/files/publications/analysis/call-report-data-2026-06.zip', fresh_hours=800),
    F('hmda_aggregations_2024.json',
      'https://ffiec.cfpb.gov/v2/data-browser-api/view/aggregations?years=2024&actions_taken=1', fresh_hours=800),
  ]},

 {'name': 'state_census_bulk', 'dir': 'state_census_bulk', 'keep_vintages': True, 'fresh_hours': 400, 'parallel': 5,
  '_note': "Added 18 Sep 2026. The Census bulk files, which need no key where its interface now demands one. Firm "
           "entry and exit by state, which is the cleanest measure of business death there is; establishments and "
           "employment by state and county; poverty and median income; population; state tax collections quarterly "
           "and annually; and building permits by county every month.",
  'files': [
    F('census_business_dynamics_by_state.csv', C2 + 'programs-surveys/bds/tables/time-series/2023/bds2023_st.csv'),
    F('census_county_business_patterns_state.zip', C2 + 'programs-surveys/cbp/datasets/2023/cbp23st.zip'),
    F('census_county_business_patterns_county.zip', C2 + 'programs-surveys/cbp/datasets/2023/cbp23co.zip'),
    F('census_poverty_and_income_by_county.txt',
      C2 + 'programs-surveys/saipe/datasets/2024/2024-state-and-county/est24all.txt'),
    F('census_population_by_state.csv',
      C2 + 'programs-surveys/popest/datasets/2020-2024/state/totals/NST-EST2024-ALLDATA.csv'),
    F('census_population_by_county.csv',
      C2 + 'programs-surveys/popest/datasets/2020-2024/counties/totals/co-est2024-alldata.csv'),
    F('census_state_tax_collections_annual.xlsx',
      C2 + 'programs-surveys/stc/tables/2024/FY2024-STC-Detailed-Table-Transposed.xlsx'),
    F('census_state_and_local_finances.zip',
      C2 + 'programs-surveys/gov-finances/tables/2024/2024_Individual_Unit_Files.zip', fresh_hours=800),
  ]},

 {'name': 'state_households', 'dir': 'state_households', 'keep_vintages': True, 'fresh_hours': 200, 'parallel': 5,
  '_note': "Added 18 Sep 2026. How households are faring, by state: rents, vacancy and how long a home sits on the "
           "market monthly; homelessness counts and shelter beds annually; fair market rents by county; where people "
           "moved between states; income by postcode; and college enrolment, which rises when work is scarce.",
  'files': [
    F('apartment_list_rent_estimates.csv',
      AL + '7lvW7gaSwU8HQZurWlYEUY/ebb465ed74b4de28a0e90362552b26c1/Apartment_List_Rent_Estimates_2026_08.csv'),
    F('apartment_list_vacancy_index.csv',
      AL + '7J0sI14msoywiOM0Vg2Tm3/00b0d43a870663b7f31bc185f4b7c1b1/Apartment_List_Vacancy_Index_2026_08.csv'),
    F('apartment_list_time_on_market.csv',
      AL + '6vBOtfIZo5BhBvDpm8FEdm/8d48a03c0bdff40b9477a32a5cf3b4db/Apartment_List_Time_On_Market_2026_08.csv'),
    F('hud_homeless_point_in_time_by_state.xlsb',
      HUD + 'sites/default/files/xls/2007-2024-PIT-Counts-by-State.xlsb', fresh_hours=800),
    F('hud_shelter_beds_by_state.xlsx',
      HUD + 'sites/default/files/xls/2007-2024-HIC-Counts-by-State.xlsx', fresh_hours=800),
    F('hud_fair_market_rents_fy2027.xlsx', HUD + 'datasets/fmr/fmr2027/FY27_FMRs.xlsx', fresh_hours=800),
    F('irs_state_migration_outflow.csv', IRS + 'stateoutflow2122.csv', fresh_hours=800),
    F('irs_state_migration_inflow.csv', IRS + 'stateinflow2122.csv', fresh_hours=800),
    F('irs_income_by_zip_and_state.csv.gz', IRS + '22zpallagi.csv', stream=True, fresh_hours=800),
    F('ipeds_fall_enrollment_2023.zip', 'https://nces.ed.gov/ipeds/datacenter/data/EF2023A.zip', fresh_hours=800),
    F('ipeds_institution_directory_2024.zip', 'https://nces.ed.gov/ipeds/datacenter/data/HD2024.zip',
      fresh_hours=800),
  ]},

 {'name': 'state_activity_extra', 'dir': 'state_activity_extra', 'keep_vintages': True, 'fresh_hours': 40,
  'parallel': 4,
  '_note': "Added 18 Sep 2026. Four more state series with real cyclical content and short lags: firearm background "
           "checks monthly by state, which the literature treats as a prompt proxy for household activity and which "
           "arrives within a fortnight; motor-vehicle registrations by state; farm income by state; and the weekly "
           "crop report, which is a state-by-state field survey published the next day.",
  'files': [
    F('fbi_background_checks_by_state_month.pdf',
      'https://www.fbi.gov/file-repository/nics_firearm_checks_-_month_year_by_state.pdf'),
    F('fbi_background_checks_by_state_type.pdf',
      'https://www.fbi.gov/file-repository/nics_firearm_checks_-_month_year_by_state_type.pdf'),
    F('fhwa_vehicle_registrations_by_state.html',
      'https://www.fhwa.dot.gov/policyinformation/statistics/2023/mv1.cfm', fresh_hours=800),
    F('usda_farm_income_by_state.zip',
      'https://www.ers.usda.gov/media/29517/september-3-2026-release.zip', fresh_hours=400),
    F('usda_crop_progress_weekly.pdf',
      'https://release.nass.usda.gov/reports/prog3825.pdf', min_bytes=20000),
    F('cdc_drug_overdose_deaths_by_state.csv',
      'https://data.cdc.gov/resource/xkb8-kh2a.csv?$limit=200000'),
    F('cdc_provisional_births_deaths_by_state.csv',
      'https://data.cdc.gov/resource/hmz2-vwda.csv?$limit=200000'),
  ]},
]

DATED = [
 {'url': 'https://www2.census.gov/econ/bps/County/co%y%mc.txt',
  'out': 'census_permits_county_%Y-%m.txt', 'months': 60, 'min_bytes': 50000, 'mark_404_days': 7},
 {'url': 'https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_%Y_%-m.zip',
  'out': 'bts_flights_%Y-%m.zip', 'months': 18, 'min_bytes': 1000000, 'mark_404_days': 14},
]


def main():
    j = json.load(open(SRC))
    names = [x['name'] for x in j['jobs']]
    added = []
    for job in JOBS:
        if job['name'] not in names:
            j['jobs'].append(job); added.append(job['name'])
    dated = next((x for x in j['jobs'] if x['name'] == 'dated_backfill'), None) or \
        next((x for x in j['jobs'] if x['name'] == 'dated_files'), None)
    if dated is not None:
        have = {p['out'] for p in dated['patterns']}
        for p in DATED:
            if p['out'] not in have: dated['patterns'].append(p)
    slow = set(j.get('slow_jobs', []))
    slow.update(['state_census_bulk', 'state_households', 'state_banking_credit', 'state_federal_employment'])
    j['slow_jobs'] = sorted(slow)
    shutil.copyfile(SRC, os.path.join(HERE, 'sources_pre_channels_%s.json.bak' % STAMP))
    json.dump(j, open(SRC, 'w'), indent=1)
    print('jobs added:', added)
    print('registry:', len(j['jobs']), 'jobs |', sum(len(x.get('files', [])) for x in j['jobs']), 'files')


if __name__ == '__main__':
    main()
