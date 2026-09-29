#!/usr/bin/env python3
"""Tidy the smaller downloads into tidy/<source>/*.csv. Every value is parsed by code from a raw file
saved under raw/. Assumed availability dates ('asof_assumed') are documented rules, not observed
release days, and are marked as such.

  UMich Surveys of Consumers  raw/umich/sca_all_tables_{M,Q}.csv, tbmics.csv, tbqics.csv
  EIA Weekly Petroleum Status Report  raw/eia_wpsr/*.xls
  ALFRED keyless vintages     raw/alfred/*_realtime_periods.csv  -> first prints
  Philadelphia Fed MBOS       raw/philly_bos/bos_history.csv, bos_dif.csv
  BLS Employment Situation release dates (via RTDSM)  raw/rtdsm/files/pop/Release_-Dates-...xls
"""
import os, glob, calendar, datetime
import pandas as pd

W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/new_candidates'
R = os.path.join(W, 'raw'); T = os.path.join(W, 'tidy')

def eom(y, m):
    return datetime.date(y, m, calendar.monthrange(y, m)[1])

# ---------------- UMich ----------------
o = os.path.join(T, 'umich'); os.makedirs(o, exist_ok=True)
m = pd.read_csv(os.path.join(R, 'umich', 'sca_all_tables_M.csv'), skiprows=1)
m['date'] = pd.to_datetime(dict(year=m['yyyy'], month=m['Month'], day=1)).dt.date
m['asof_assumed'] = [eom(d.year, d.month) for d in m['date']]      # final release ~ last Friday of month
keep = ['date', 'asof_assumed'] + [c for c in m.columns if c.endswith('_all') and
        c.split('_')[0] in ('ics', 'icc', 'ice', 'umex', 'bus12', 'bus5', 'bexp', 'bago', 'news', 'pjob', 'pexp',
                            'pago', 'inex', 'dur', 'car', 'hom')]
m[keep].to_csv(os.path.join(o, 'umich_monthly_1978on_key.csv'), index=False)
m.drop(columns=['Month', 'yyyy']).to_csv(os.path.join(o, 'umich_monthly_1978on_all_tables.csv'), index=False)
q = pd.read_csv(os.path.join(R, 'umich', 'sca_all_tables_Q.csv'), skiprows=1)
q['date'] = pd.to_datetime(dict(year=q['yyyy'], month=3 * q['Quarter'] - 2, day=1)).dt.date
# quarterly surveys 1960-1977 were fielded irregularly within the quarter; assume available only one month
# after quarter end. From 1978 the quarterly figure is an average of monthly surveys.
q['asof_assumed'] = [eom(d.year + (d.month + 3 > 12), (d.month + 3 - 1) % 12 + 1) for d in q['date']]
q['survey_mode'] = ['quarterly_survey' if d.year < 1978 else 'avg_of_monthly' for d in q['date']]
q[['date', 'asof_assumed', 'survey_mode'] + [c for c in keep if c in q.columns and c not in ('date', 'asof_assumed')]] \
    .to_csv(os.path.join(o, 'umich_quarterly_1960on_key.csv'), index=False)
ics = pd.read_csv(os.path.join(R, 'umich', 'tbmics.csv'))
ics['date'] = pd.to_datetime(ics['Month'] + ' ' + ics['YYYY'].astype(str), format='%B %Y').dt.date
ics[['date', 'ICS_ALL']].to_csv(os.path.join(o, 'umich_ics_1952on_irregular.csv'), index=False)

# ---------------- EIA WPSR ----------------
o = os.path.join(T, 'eia_wpsr'); os.makedirs(o, exist_ok=True)
for f in sorted(glob.glob(os.path.join(R, 'eia_wpsr', '*.xls'))):
    sid = os.path.basename(f)[:-4]
    c = pd.read_excel(f, sheet_name='Data 1', header=None)
    name = str(c.iloc[2, 1])
    d = c.iloc[3:, :2]; d.columns = ['week_ending', 'value']
    d['week_ending'] = pd.to_datetime(d['week_ending']).dt.date
    d['value'] = pd.to_numeric(d['value'], errors='coerce')
    d = d.dropna()
    d['asof_assumed'] = [x + datetime.timedelta(days=5) for x in d['week_ending']]  # WPSR: Wednesday after Friday week end
    d.insert(0, 'series', sid); d.insert(1, 'name', name)
    d.to_csv(os.path.join(o, '%s_weekly.csv' % sid), index=False)

# ---------------- ALFRED first prints ----------------
o = os.path.join(T, 'alfred'); os.makedirs(o, exist_ok=True)
for f in sorted(glob.glob(os.path.join(R, 'alfred', '*_realtime_periods.csv'))):
    sid = os.path.basename(f).replace('_realtime_periods.csv', '')
    d = pd.read_csv(f)
    d.to_csv(os.path.join(o, '%s_realtime_periods.csv' % sid), index=False)
    v = d[pd.to_numeric(d['value'], errors='coerce').notna()].copy()
    v['value'] = pd.to_numeric(v['value'])
    v = v.sort_values(['date', 'realtime_start'])
    fp = v.groupby('date').first().reset_index()[['date', 'value', 'realtime_start']]
    fp.columns = ['date', 'first_value', 'first_published']
    lt = v.groupby('date').last().reset_index()[['date', 'value']].rename(columns={'value': 'latest_value'})
    fp = fp.merge(lt, on='date')
    # an observation counts as a genuine first print only if it was first published within 120 days of the
    # observation date; otherwise it entered ALFRED as back-filled history (first vintage, or history added later)
    lag = (pd.to_datetime(fp['first_published']) - pd.to_datetime(fp['date'])).dt.days
    fp['lag_days'] = lag
    fp['is_backfill'] = (lag > 120) | (fp['first_published'] == v['realtime_start'].min())
    fp.to_csv(os.path.join(o, '%s_firstprint.csv' % sid), index=False)

# ---------------- Philadelphia Fed MBOS ----------------
o = os.path.join(T, 'philly_bos'); os.makedirs(o, exist_ok=True)
for fn in ['bos_history.csv', 'bos_dif.csv']:
    d = pd.read_csv(os.path.join(R, 'philly_bos', fn))
    dt = pd.to_datetime(d['DATE'], format='%b-%y')
    dt = dt.where(dt.dt.year <= datetime.date.today().year, dt - pd.DateOffset(years=100))
    d.insert(0, 'date', dt.dt.date); d = d.drop(columns=['DATE'])
    d.to_csv(os.path.join(o, fn.replace('.csv', '_tidy.csv')), index=False)

# ---------------- BLS release dates (from RTDSM) ----------------
o = os.path.join(T, 'rtdsm'); os.makedirs(o, exist_ok=True)
f = glob.glob(os.path.join(R, 'rtdsm', 'files', '*', 'Release_-Dates-Employment_Situation-BLS.xls'))[0]
x = pd.read_excel(f, sheet_name=None, header=None)
for k, d in x.items():
    d.to_csv(os.path.join(o, 'bls_employment_situation_release_dates_%s.csv' % k.replace(' ', '_')), index=False, header=False)
print('ok')

# long form of the BLS release-date matrix: reference month -> Employment Situation release day
rows = []
for k, d in x.items():
    hdr = d.index[d.iloc[:, 0].astype(str).str.strip() == 'Year']
    if not len(hdr): continue
    for i in range(hdr[0] + 1, len(d)):
        y = pd.to_numeric(d.iloc[i, 0], errors='coerce')
        if pd.isna(y): continue
        for mth in range(1, 13):
            v = pd.to_datetime(d.iloc[i, mth], errors='coerce')
            if pd.notna(v): rows.append(dict(ref_month='%04d-%02d' % (int(y), mth), release_date=v.date()))
pd.DataFrame(rows).to_csv(os.path.join(o, 'bls_employment_situation_release_dates_long.csv'), index=False)
print('bls release dates', len(rows))

# ---------------- Livingston Survey ----------------
o = os.path.join(T, 'livingston'); os.makedirs(o, exist_ok=True)
rd = pd.read_excel(os.path.join(R, 'livingston', 'livingston-release-dates.xlsx'), sheet_name='Dates', header=None)
rd = rd.iloc[:, :3]; rd.columns = ['survey', 'release_exact', 'release_not_after']
rd['survey'] = pd.to_datetime(rd['survey'], errors='coerce')
rd = rd.dropna(subset=['survey'])
rd['survey'] = [d - pd.DateOffset(years=100) if d.year > datetime.date.today().year else d for d in rd['survey']]
for c in ['release_exact', 'release_not_after']:
    rd[c] = pd.to_datetime(rd[c], errors='coerce').dt.date
rd['survey'] = rd['survey'].dt.date
rd['release_asof'] = [a if pd.notna(a) else b for a, b in zip(rd['release_exact'], rd['release_not_after'])]
rd.to_csv(os.path.join(o, 'livingston_release_dates.csv'), index=False)
for fn in ['means.xlsx', 'medians.xlsx', 'MeanGrowthRate.xlsx', 'MedianGrowthRate.xlsx']:
    out = []
    for sh, d in pd.read_excel(os.path.join(R, 'livingston', fn), sheet_name=None).items():
        if 'Date' not in d.columns: continue
        d['Date'] = pd.to_datetime(d['Date']).dt.date
        mm = d.melt(id_vars=['Date'], var_name='field', value_name='value').dropna()
        mm.insert(1, 'variable', sh); out.append(mm)
    ll = pd.concat(out).rename(columns={'Date': 'survey'})
    ll = ll.merge(rd[['survey', 'release_asof']], on='survey', how='left')
    ll.to_csv(os.path.join(o, 'livingston_%s_long.csv' % fn.split('.')[0]), index=False)
print('livingston ok')

# ---------------- FRED never-revised Moody's yields ----------------
o = os.path.join(T, 'fred'); os.makedirs(o, exist_ok=True)
for s in ['BAA', 'AAA', 'DBAA', 'DAAA']:
    d = pd.read_csv(os.path.join(R, 'fred', s + '.csv'))
    d.columns = ['date', 'value']; d['value'] = pd.to_numeric(d['value'], errors='coerce')
    d.dropna().to_csv(os.path.join(o, s + '.csv'), index=False)
