#!/usr/bin/env python3
"""Turning the new raw files into series the rule and the audit can read.

18 September 2026. Forty jobs added this week write what the source publishes: a row per establishment, per county,
per retailer, per notice. Nothing downstream reads that shape. This reduces each of them to the two-column form the
warehouse uses everywhere else - a date and a value - and writes them into each job's derived/ folder, where the
quality gate and the rule's own loader look.

Each specification says which file, which column carries the date, which column carries the number, and how rows
sharing a date are combined: summed (claims in a week across counties), counted (layoff notices in a week), or taken
as they are (a national index). Nothing is interpolated and nothing is seasonally adjusted; a date with no rows is
simply absent. A file that is missing or whose columns have been renamed is skipped with a line in the log rather
than a fault, so a source changing its shape can never stop a cycle.
"""
import os, re, csv, sys, gzip, collections

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WH = os.path.join(HERE, 'warehouse')
LOG = [print]


def log(*a):
    try: LOG[0](*a)
    except Exception: print(*a)


# (job folder, file, out name, date spec, value column or None to count, how to combine)
#   date spec: a column name, or ('year+week', y, w), ('year+month', y, m), ('yyyymm', col)
SPECS = [
 ('state_business_formation', 'census_business_applications_state_weekly.csv',
  'business_applications_weekly_total', ('year+week', 'Year', 'Week'), 'BA_NSA', 'sum'),
 ('state_business_formation', 'census_business_applications_state_weekly.csv',
  'business_applications_weekly_high_propensity', ('year+week', 'Year', 'Week'), 'HBA_NSA', 'sum'),
 ('state_business_formation', 'census_business_applications_us_weekly.csv',
  'business_applications_us_weekly', ('year+week', 'Year', 'Week'), 'BA_NSA', 'sum'),
 ('state_business_formation', 'new_york_corporate_filings_daily.csv',
  'new_york_corporate_filings_per_day', 'filing_date', None, 'count'),

 ('state_warn', 'texas_warn_notices.csv', 'texas_warn_workers_by_notice_date', 'notice_date',
  'total_layoff_number', 'sum'),
 ('state_warn', 'texas_warn_notices.csv', 'texas_warn_notices_per_day', 'notice_date', None, 'count'),
 ('state_warn', 'colorado_warn_2026.csv', 'colorado_warn_workers_2026', 'WARN Date', 'Total Notified', 'sum'),

 ('state_spending_receipts', 'new_york_lottery_daily_retailer_sales.csv',
  'new_york_lottery_sales_per_day', 'bus_day',
  ['numbers_day', 'numbers_eve', 'win4_day', 'win4_eve', 't5_day', 't5_eve', 'pick10', 'lotto', 'mega',
   'powerball', 'quick_draw', 'c4l', 'm4l', 'doubleplay'], 'cols'),
 ('state_spending_receipts', 'texas_mixed_beverage_gross_receipts.csv',
  'texas_alcohol_receipts_monthly', 'obligation_end_date_yyyymmdd', 'total_receipts', 'sum'),

 ('state_claims_substate', 'missouri_initial_claims_by_county_weekly.csv',
  'missouri_initial_claims_weekly', 'weekending', 'claims', 'sum'),
 ('state_claims_substate', 'connecticut_initial_and_continued_claims_weekly.csv',
  'connecticut_initial_claims_weekly', 'date', 'initclaims_count_regular', 'sum'),
 ('state_claims_substate', 'connecticut_initial_and_continued_claims_weekly.csv',
  'connecticut_continued_claims_weekly', 'date', 'contclaims_count_regular', 'sum'),
 ('state_claims_substate', 'new_york_initial_claims_statewide_from_1971.csv',
  'new_york_initial_claims_monthly', None, None, 'auto'),

 ('state_safety_net', 'pennsylvania_snap_by_county_monthly.csv',
  'pennsylvania_snap_individuals_monthly', 'date', 'snap_individuals', 'sum'),
 ('state_safety_net', 'pennsylvania_snap_by_county_monthly.csv',
  'pennsylvania_snap_dollars_monthly', 'date', 'snap_dollars', 'sum'),

 ('state_programs', 'cms_medicaid_chip_monthly_by_state.csv',
  'medicaid_chip_enrollment_monthly', 'Reporting Period',
  'Total Medicaid and CHIP Enrollment', 'sum'),
 ('state_programs', 'cms_medicaid_chip_monthly_by_state.csv',
  'medicaid_eligible_at_application_monthly', 'Reporting Period',
  'Individuals Determined Eligible for Medicaid at Application', 'sum'),
 ('state_programs', 'cms_medicaid_chip_monthly_by_state.csv',
  'medicaid_new_applications_monthly', 'Reporting Period',
  'New Applications Submitted to Medicaid and CHIP Agencies', 'sum'),

 ('transit_activity', 'fta_monthly_ridership_by_agency.csv',
  'transit_unlinked_passenger_trips_monthly', 'date', 'upt', 'sum'),

 ('state_distress', 'connecticut_evictions_weekly_by_tract.csv',
  'connecticut_eviction_filings_weekly', 'week_date', 'filings_2020', 'sum'),
 ('state_distress', 'maryland_foreclosure_notices_by_county.csv',
  'maryland_foreclosure_notices_monthly', 'date', None, 'rowsum'),
 ('state_distress', 'texas_landlord_tenant_caseload.csv',
  'texas_eviction_cases_filed_monthly', 'date', 'new_cases_filed', 'sum'),

 ('labour_postings', 'indeed_postings_national_daily.csv',
  'indeed_job_postings_index_daily', 'date', 'indeed_job_postings_index_SA', 'first'),

 ('stress_daily', 'ofr_financial_stress_index_daily.csv', 'ofr_financial_stress_index', 'Date', 'OFR FSI', 'first'),
 ('stress_daily', 'ofr_financial_stress_index_daily.csv', 'ofr_stress_credit', 'Date', 'Credit', 'first'),
 ('stress_daily', 'ofr_financial_stress_index_daily.csv', 'ofr_stress_funding', 'Date', 'Funding', 'first'),

 ('text_attention', 'policy_uncertainty_daily.csv', 'policy_uncertainty_daily',
  ('ymd', 'year', 'month', 'day'), 'daily_policy_index', 'first'),

 ('state_labour_extra', 'colorado_state_jolts.csv', 'colorado_job_openings_monthly',
  ('year+month', 'year', 'month'), 'job_openings_adjusted', 'first'),
 ('state_labour_extra', 'colorado_state_jolts.csv', 'colorado_layoffs_and_discharges_monthly',
  ('year+month', 'year', 'month'), 'layoffs_and_discharges', 'first'),
 ('state_labour_extra', 'colorado_state_jolts.csv', 'colorado_quits_monthly',
  ('year+month', 'year', 'month'), 'quit_adjusted', 'first'),
]

ISO = re.compile(r'(\d{4})-(\d{2})-(\d{2})')
YMD8 = re.compile(r'^(\d{4})(\d{2})(\d{2})$')
MONTHS = 'january february march april may june july august september october november december'.split()


def norm_date(x):
    x = (x or '').strip().strip('"')
    if not x: return ''
    m = ISO.match(x)
    if m: return x[:10]
    m = YMD8.match(x)
    if m: return '%s-%s-%s' % m.groups()
    if len(x) == 7 and x[4] == '-': return x + '-01'
    if len(x) == 6 and x.isdigit() and '1900' < x[:4] < '2100': return '%s-%s-01' % (x[:4], x[4:])
    low = x.lower().replace(',', ' ')
    for i, mo in enumerate(MONTHS):                      # "September 2026" and "Sep 2026"
        if low.startswith(mo[:3]):
            y = re.search(r'(\d{4})', low)
            if y: return '%s-%02d-01' % (y.group(1), i + 1)
    if len(x) == 10 and x[2] in '/-' and x[5] in '/-':
        a, b, c = re.split(r'[/-]', x)
        return '%s-%s-%s' % (c, a.zfill(2), b.zfill(2))
    return ''


def week_date(year, week):
    """The Saturday ending the given week of the year, which is how Census dates its weekly file."""
    import datetime
    try:
        d = datetime.date(int(year), 1, 1) + datetime.timedelta(days=(int(week) - 1) * 7)
        return d.isoformat()
    except Exception:
        return ''


def opened(path):
    return gzip.open(path, 'rt', encoding='utf-8', errors='replace') if path.endswith('.gz') \
        else open(path, newline='', encoding='utf-8', errors='replace')


def number(x):
    x = (x or '').replace(',', '').replace('$', '').strip().strip('"')
    try: return float(x)
    except ValueError: return None


def derive_one(folder, fname, out, datespec, valcol, how):
    src = os.path.join(WH, folder, fname)
    if not os.path.exists(src):
        if os.path.exists(src + '.gz'):
            src = src + '.gz'          # large files are kept gzipped at rest since 18 Sep 2026
        else:
            return 'missing'
    acc = collections.OrderedDict()
    with opened(src) as f:
        rd = csv.DictReader(f)
        if rd.fieldnames is None: return 'unreadable'
        cols = {c.strip().strip('"'): c for c in rd.fieldnames}

        if datespec is None or how == 'auto':                 # a two-column file already: pass it through
            names = list(cols)
            dcol = next((c for c in names if re.search(r'(?i)date|week|month|period|year', c)), None)
            vcol = next((c for c in names if c != dcol and any(number(r) is not None for r in [''])), None)
            if dcol is None: return 'no date column'
            vcol = vcol or names[-1]
            for r in rd:
                d = norm_date(r.get(cols[dcol], ''))
                v = number(r.get(cols[vcol], ''))
                if d and v is not None: acc[d] = v
        else:
            if isinstance(datespec, tuple):
                kind = datespec[0]
                need = [c for c in datespec[1:] if c not in cols]
                if need: return 'missing column %s' % need[0]
            elif datespec not in cols:
                return 'missing column %s' % datespec
            if valcol is not None and how not in ('count', 'rowsum', 'cols') and valcol not in cols:
                return 'missing column %s' % valcol
            for r in rd:
                if isinstance(datespec, tuple):
                    if datespec[0] == 'year+week':
                        d = week_date(r.get(cols[datespec[1]], ''), r.get(cols[datespec[2]], ''))
                    elif datespec[0] == 'year+month':
                        y, m = r.get(cols[datespec[1]], ''), r.get(cols[datespec[2]], '')
                        d = '%s-%02d-01' % (y, int(m)) if y.isdigit() and str(m).isdigit() else ''
                    elif datespec[0] == 'ymd':
                        y, m, dd = (r.get(cols[c], '') for c in datespec[1:])
                        d = '%s-%02d-%02d' % (y, int(m or 0), int(dd or 0)) if y and m and dd else ''
                    else:
                        d = ''
                else:
                    d = norm_date(r.get(cols[datespec], ''))
                if not d: continue
                if how == 'count':
                    acc[d] = acc.get(d, 0) + 1
                elif how == 'cols':
                    s_ = sum(v for v in (number(r.get(cols[c], '')) for c in valcol if c in cols) if v is not None)
                    acc[d] = acc.get(d, 0) + s_
                elif how == 'rowsum':
                    s = sum(v for v in (number(x) for k, x in r.items() if k != cols[datespec]) if v is not None)
                    acc[d] = acc.get(d, 0) + s
                else:
                    v = number(r.get(cols[valcol], ''))
                    if v is None: continue
                    if how == 'sum': acc[d] = acc.get(d, 0) + v
                    elif how == 'first' and d not in acc: acc[d] = v
                    else: acc.setdefault(d, v)
    if not acc:
        return 'no rows'
    d = os.path.join(WH, folder, 'derived')
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, out + '.csv')
    with open(p + '.tmp', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['date', 'value'])
        for k in sorted(acc):
            v = acc[k]
            w.writerow([k, ('%d' % v) if float(v).is_integer() else ('%.6g' % v)])
    os.replace(p + '.tmp', p)
    return '%d observations' % len(acc)


def main():
    ok = 0
    for spec in SPECS:
        try:
            r = derive_one(*spec)
        except Exception as e:
            r = '%s %s' % (type(e).__name__, str(e)[:80])
        if r.endswith('observations'): ok += 1
        else: log('  derive_extra:', spec[2], '->', r)
    log('  derive_extra: %d of %d series written' % (ok, len(SPECS)))
    return ok


if __name__ == '__main__':
    main()
