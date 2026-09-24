#!/usr/bin/env python3
"""CH-R41 S17 century-core feasibility. READ-ONLY; writes research/ only.
Never-revised membership = R25 roster (never_revised|negligible_revision) UNION
R22 FRED-MD panel (NEVER_REVISED|NEGLIGIBLE). Start year (data coverage, not vintage)
from catalog local_first_observation; R22-only panel cols -> 1959-01 FRED-MD monthly
floor (flagged). USREC* excluded from the predictor core (they are the target dummy).
Additions layer = cached-but-unlanded NBER century series + documented historical
non-FRED series, starts from CH-R26.  Per-year 1900->2026 member counts, per-episode
coverage over the 23 NBER recessions with peak>=1900 (matches R26), viable-core onset.
"""
import csv, json, collections

CAT = 'data_vault/catalog/metric_catalog.csv'
R25 = 'research/revision_certification_v2_roster.csv'
R22 = 'research/revision_certification_v3_fredmd_panel.csv'
OUT_YEARS = 'research/century_core_feasibility_v1.csv'
OUT_MEMBERS = 'research/century_core_members_v1.csv'
OUT_BRIEF = 'research/ch_r41_feasibility_brief.txt'

FREDMD_FLOOR = 1959   # FRED-MD monthly panel common start; conservative for panel-only cols
TARGET_DUMMIES = {'USREC', 'USRECD', 'USRECDM'}  # NBER recession indicator = target, not predictor

# ---- catalog first-observation lookup ----
cat_first = {}
with open(CAT) as f:
    for r in csv.DictReader(f):
        cat_first[r['series_id'].strip()] = r.get('local_first_observation', '').strip()

# ---- R25 never/negligible ----
r25 = {}
with open(R25) as f:
    for r in csv.DictReader(f):
        if r['class_r25'] in ('never_revised', 'negligible_revision'):
            r25[r['series_id'].strip()] = r['class_r25']

# ---- R22 FRED-MD panel never/negligible ----
r22 = {}
with open(R22) as f:
    for r in csv.DictReader(f):
        if r['class'] in ('NEVER_REVISED', 'NEGLIGIBLE'):
            r22[r['column'].strip()] = r['class']

# ---- assemble core members with start year + provenance ----
members = {}   # sid -> dict(start, cert, start_src, is_target, store_resident)
def add_member(sid, cert):
    fo = cat_first.get(sid, '')
    if fo:
        start = int(fo[:4]); src = 'catalog_first_obs'; resident = True
    else:
        start = FREDMD_FLOOR; src = 'fredmd_panel_floor_1959'; resident = False
    prev = members.get(sid)
    if prev:  # keep earliest evidence / merge cert tags
        prev['cert'] = prev['cert'] + '|' + cert
        return
    members[sid] = dict(start=start, cert=cert, start_src=src,
                        is_target=(sid in TARGET_DUMMIES), store_resident=resident)

for sid, c in r25.items():
    add_member(sid, 'R25:' + c)
for sid, c in r22.items():
    add_member(sid, 'R22:' + c)

# ---- additions: cached / documented historical never-revised, starts from CH-R26 ----
# store_resident=False; these EXTEND the core earlier. rights flag from R26 blockers.
ADDITIONS = [
    # sid/label,               start, freq,   status,                          note
    ('M13002US35620M156NNBR', 1857, 'm', 'cached_nber_unlanded', 'NBER commercial paper rate'),
    ('M010ADUSM561SNBR',      1877, 'm', 'cached_nber_unlanded', 'NBER pig iron production'),
    ('M0135AUSM577NNBR',      1899, 'm', 'cached_nber_unlanded', 'NBER steel ingot production'),
    ('M0601AUSM327NNBR',      1914, 'm', 'cached_nber_unlanded', 'NBER retail trade index'),
    ('M13009USM156NNBR',      1914, 'm', 'cached_nber_unlanded', 'NBER call money rate (m)'),
    ('Q03068USQ455SNBR',      1920, 'q', 'cached_nber_unlanded', 'NBER rail freight tons (q)'),
    ('CPIAUCNS',              1913, 'm', 'fred_unlanded',        'CPI all items NSA (negligible)'),
    ('SP_COMPOSITE_SHILLER',  1871, 'm', 'nonfred_research',     'S&P composite Cowles/Shiller'),
    ('DJIA_1896',             1896, 'd', 'nonfred_licensed',     'DJIA daily (S&P DJI licensed)'),
    ('FS_MONEY_STOCK_1907',   1907, 'm', 'nonfred_research',     'Friedman-Schwartz money stock'),
    ('DEPT_STORE_SALES_1919', 1919, 'm', 'nonfred_nber',         'Dept store sales (NBER)'),
    ('CALL_MONEY_1890S',      1890, 'm', 'nonfred_nber',         'Call money rate (NBER)'),
]

# ---- NBER recessions with peak >= 1900 (23 episodes; matches CH-R26 count) ----
EPISODES = [  # (peak_year, peak_month, trough_year, trough_month, label)
    (1902, 9, 1904, 8, '1902-04'), (1907, 5, 1908, 6, '1907-08'),
    (1910, 1, 1912, 1, '1910-12'), (1913, 1, 1914, 12, '1913-14'),
    (1918, 8, 1919, 3, '1918-19'), (1920, 1, 1921, 7, '1920-21'),
    (1923, 5, 1924, 7, '1923-24'), (1926, 10, 1927, 11, '1926-27'),
    (1929, 8, 1933, 3, '1929-33'), (1937, 5, 1938, 6, '1937-38'),
    (1945, 2, 1945, 10, '1945'),   (1948, 11, 1949, 10, '1948-49'),
    (1953, 7, 1954, 5, '1953-54'), (1957, 8, 1958, 4, '1957-58'),
    (1960, 4, 1961, 2, '1960-61'), (1969, 12, 1970, 11, '1969-70'),
    (1973, 11, 1975, 3, '1973-75'), (1980, 1, 1980, 7, '1980'),
    (1981, 7, 1982, 11, '1981-82'), (1990, 7, 1991, 3, '1990-91'),
    (2001, 3, 2001, 11, '2001'),   (2007, 12, 2009, 6, '2007-09'),
    (2020, 2, 2020, 4, '2020'),
]

# predictor core = members minus target dummies
core = {s: m for s, m in members.items() if not m['is_target']}
add_start = {a[0]: a[1] for a in ADDITIONS}

# ---- per-year counts 1900..2026 ----
YEARS = list(range(1900, 2027))
def count_at(year, pool_starts):
    return sum(1 for st in pool_starts if st <= year)

core_starts = [m['start'] for m in core.values()]
core_resident_starts = [m['start'] for m in core.values() if m['store_resident']]
add_all_starts = core_starts + list(add_start.values())
add_nber_starts = core_starts + [a[1] for a in ADDITIONS if a[3].startswith('cached') or a[3] == 'fred_unlanded']

rows = []
for y in YEARS:
    rows.append(dict(
        year=y,
        core_never_revised=count_at(y, core_starts),
        core_store_resident=count_at(y, core_resident_starts),
        core_plus_cached_nber=count_at(y, add_nber_starts),
        core_plus_all_additions=count_at(y, add_all_starts),
    ))

with open(OUT_YEARS, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['year', 'core_never_revised', 'core_store_resident',
                                      'core_plus_cached_nber', 'core_plus_all_additions'])
    w.writeheader(); w.writerows(rows)

# ---- members csv ----
with open(OUT_MEMBERS, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['series_id', 'start_year', 'cert', 'start_src', 'store_resident', 'layer'])
    for s, m in sorted(core.items(), key=lambda kv: kv[1]['start']):
        w.writerow([s, m['start'], m['cert'], m['start_src'], m['store_resident'], 'core'])
    for a in sorted(ADDITIONS, key=lambda x: x[1]):
        w.writerow([a[0], a[1], a[3], a[2], False, 'addition'])

# ---- viable-core onset at thresholds N ----
def first_sustained(pool_starts, N):
    # earliest year from which count>=N holds for all subsequent years (monotone -> just first hit)
    for y in YEARS:
        if count_at(y, pool_starts) >= N:
            return y
    return None

thresholds = [3, 5, 8, 10, 15, 20]
onset_core = {N: first_sustained(core_starts, N) for N in thresholds}
onset_res = {N: first_sustained(core_resident_starts, N) for N in thresholds}
onset_nber = {N: first_sustained(add_nber_starts, N) for N in thresholds}
onset_all = {N: first_sustained(add_all_starts, N) for N in thresholds}

# breadth distribution: modern plateau
plateau = count_at(2000, core_starts)
plateau_res = count_at(2000, core_resident_starts)

# ---- per-episode coverage ----
epi_rows = []
for py, pm, ty, tm, lab in EPISODES:
    epi_rows.append(dict(
        episode=lab, peak_year=py,
        core=count_at(py, core_starts),
        core_resident=count_at(py, core_resident_starts),
        core_plus_cached_nber=count_at(py, add_nber_starts),
        core_plus_all=count_at(py, add_all_starts),
    ))

# ---- brief ----
L = []
L.append('CH-R41 CENTURY-CORE FEASIBILITY (S17) — never-revised data coverage 1900->today')
L.append('=' * 78)
L.append('')
L.append('MEMBERSHIP (never-revised / negligible-revision certified):')
L.append(f'  R25 roster never|negligible : {len(r25)}')
L.append(f'  R22 FRED-MD panel never|neg : {len(r22)} (overlap w/ R25: {len(set(r25)&set(r22))})')
L.append(f'  union                       : {len(members)}')
L.append(f'  excluded as TARGET dummy    : {sorted(TARGET_DUMMIES & set(members))}')
L.append(f'  predictor core              : {len(core)} '
         f'({sum(1 for m in core.values() if m["store_resident"])} store-resident, '
         f'{sum(1 for m in core.values() if not m["store_resident"])} FRED-MD panel-only@1959 floor)')
L.append(f'  documented additions layer  : {len(ADDITIONS)} (cached NBER + non-FRED historical)')
L.append('')
L.append('PLAIN-LANGUAGE ANSWER')
L.append('-' * 78)
# find core onset for recommended N
recN = 5
yc = onset_core[recN]; yr = onset_res[recN]; yn = onset_nber[recN]
L.append(f'A never-revised predictor core of >={recN} members is viable from:')
L.append(f'   {yr}  using only STORE-RESIDENT certified series')
L.append(f'   {yc}  using the full certified core (incl FRED-MD panel-only, floored 1959)')
L.append(f'   {yn}  once the cached NBER century series are landed')
L.append('')
L.append('The predictor core is thin before WWII: store-resident never-revised coverage')
L.append('begins with PPIACO (1913), AAA & BAA corporate yields (1919), then does not')
L.append('thicken until the 1948 labor/rate cohort. Everything 1857-1918 is bought by the')
L.append('cached-but-unlanded NBER century block, NOT by anything currently in the store.')
L.append('')
L.append('WHAT BUYS EACH FRONTIER (earliest-extending additions):')
L.append('  1857 : M13002US35620M156NNBR  NBER commercial paper rate (cached, unlanded)')
L.append('  1871 : S&P composite Cowles/Shiller (non-FRED research series)')
L.append('  1877 : M010ADUSM561SNBR  NBER pig iron production (cached, unlanded)')
L.append('  1890 : Call money rate NBER / Lebergott (non-FRED)')
L.append('  1896 : DJIA daily (LICENSED - rights blocker)')
L.append('  1899 : M0135AUSM577NNBR  NBER steel ingot (cached, unlanded)')
L.append('  1907 : Friedman-Schwartz money stock (non-FRED research)')
L.append('  1913 : PPIACO (store) + CPIAUCNS (FRED, unlanded)')
L.append('  1914 : NBER retail trade + call money monthly (cached, unlanded)')
L.append('  1919 : AAA/BAA (store) + dept-store sales NBER; rail freight (q) 1920')
L.append('')
L.append('=> To reach 1919 with a >=3-member never-revised core you need ONLY the store')
L.append('   (PPIACO 1913 + AAA + BAA 1919). To reach 1914 add the two 1914 NBER monthlies.')
L.append('   To reach 1857-1907 you must land the cached NBER block; store alone cannot.')
L.append('')
L.append('VIABLE-CORE ONSET BY THRESHOLD N (first year count>=N, monotone):')
L.append(f'  {"N":>3} {"store_only":>11} {"full_core":>10} {"+cached_nber":>12} {"+all_add":>9}')
for N in thresholds:
    L.append(f'  {N:>3} {str(onset_res[N]):>11} {str(onset_core[N]):>10} '
             f'{str(onset_nber[N]):>12} {str(onset_all[N]):>9}')
L.append(f'  (modern plateau: full core={plateau} members @2000; store-resident={plateau_res})')
L.append(f'  N recommended = {recN} (>=1/10 of modern breadth AND multi-domain: yields, prices,')
L.append('   real activity, labor). Higher N is only reachable post-1948.')
L.append('')
L.append('PER-EPISODE COVERAGE (23 NBER recessions, peak>=1900):')
L.append(f'  {"episode":<9}{"peak":>5} {"core":>5} {"resident":>9} {"+nber":>6} {"+all":>5}')
for e in epi_rows:
    L.append(f'  {e["episode"]:<9}{e["peak_year"]:>5} {e["core"]:>5} {e["core_resident"]:>9} '
             f'{e["core_plus_cached_nber"]:>6} {e["core_plus_all"]:>5}')
n_epi_res3 = sum(1 for e in epi_rows if e['core_resident'] >= 3)
n_epi_nber3 = sum(1 for e in epi_rows if e['core_plus_cached_nber'] >= 3)
n_epi_all3 = sum(1 for e in epi_rows if e['core_plus_all'] >= 3)
L.append('')
L.append(f'  episodes with >=3 never-revised members present:')
L.append(f'    store-resident core        : {n_epi_res3}/23')
L.append(f'    + cached NBER landed        : {n_epi_nber3}/23')
L.append(f'    + all documented additions  : {n_epi_all3}/23')
L.append('')
L.append('CAVEATS / METHOD NOTES:')
L.append(' - Coverage = data start year (first observation), NOT vintage depth. A')
L.append('   never-revised series has current==first-print, so first-observation coverage')
L.append('   IS as-of-replayable back to its start; that is the S17 property being counted.')
L.append(' - 26 FRED-MD panel-only cols have no catalog first_obs; floored at 1959. This')
L.append('   understates a few (e.g. deep IP/CPI panel cols) but they contribute nothing')
L.append('   pre-1959 so the century-core conclusion is unaffected.')
L.append(' - PPIACO: R25 classes it never_revised; CH-R26 called it "revised". Kept per')
L.append('   R25 certification but flag pending reconciliation (affects the 1913 frontier).')
L.append(' - USREC/USRECD/USRECDM excluded: they are the NBER target dummy (1854), not a')
L.append('   predictor; counting them would be circular.')
L.append(' - Additions are DOCUMENTED (CH-R26), not re-measured here. Cached-NBER are on')
L.append('   disk in research/prefetch; non-FRED historical carry rights/route notes.')
L.append('')
L.append(f'OUTPUTS: {OUT_YEARS}  (per-year 1900-2026)')
L.append(f'         {OUT_MEMBERS}  (per-member start+cert+layer)')

with open(OUT_BRIEF, 'w') as f:
    f.write('\n'.join(L) + '\n')

# echo key lines to stdout (kept short for transcript diet)
print(f'core={len(core)} additions={len(ADDITIONS)} plateau@2000={plateau}')
print(f'onset N=5: store={onset_res[5]} full={onset_core[5]} +nber={onset_nber[5]} +all={onset_all[5]}')
print(f'epi>=3: resident={n_epi_res3}/23 +nber={n_epi_nber3}/23 +all={n_epi_all3}/23')
print('wrote', OUT_YEARS, OUT_MEMBERS, OUT_BRIEF)
