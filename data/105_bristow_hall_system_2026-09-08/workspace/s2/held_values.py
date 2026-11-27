"""WHERE IT STANDS = THE VALUES WE HOLD (15 November 2026, collection 1052; Anthony 12:36 PT: 'Where it stands' must show "THE EXACT
VALUE OF THE DATA THAT WE ARE HOLDING", never a count of files or calls). Called by s2/tool_inputs_mac.py for each input row at
every run (on GitHub by live-tools.yml, on the Mac by hand); reads the very file the tool reads and returns its latest value(s):
  one series            -> its latest value;
  several named series  -> each with its FRED ID;
  a 50-State family     -> each State's latest value (a compact list in the cell);
  a county file         -> the U.S. figure computed from it (labor-force-weighted unemployment rate, total labor force);
  a derived layer       -> its latest reading; a boundary file -> '2024 boundaries'.
Returns dict(value=str, values=[[id, value, units]], vlist=[[label, value]], units=str, period='YYYY-MM[-DD]') or None. No AI, nothing typed."""
import os, re, csv, gzip, glob, json
ST = ('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD '
      'TN TX UT VT VA WA WV WI WY').split()
FIPS = dict(zip('01 02 04 05 06 08 09 10 11 12 13 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 44 45 46 47 48 49 50 51 53 54 55 56'.split(),
                'AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split()))
NAME = {'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
        'District of Columbia': 'DC', 'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
        'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
        'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
        'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
        'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
        'Wisconsin': 'WI', 'Wyoming': 'WY'}
CES = [('PAYEMS', 'CES0000000001'), ('USMINE', 'CES1000000001'), ('USCONS', 'CES2000000001'), ('MANEMP', 'CES3000000001'), ('USTPU', 'CES4000000001'),
       ('USINFO', 'CES5000000001'), ('USFIRE', 'CES5500000001'), ('USPBS', 'CES6000000001'), ('USEHS', 'CES6500000001'), ('USLAH', 'CES7000000001'),
       ('USSERV', 'CES8000000001'), ('USGOVT', 'CES9000000001')]
MON = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def num(v, d=None):
    """the held number as written, with thousands separators; d decimals only where the file's own digits are re-expressed"""
    s = str(v).strip().strip('"')
    try: f = float(s)
    except Exception: return s
    if d is None:
        ip, _, fp = s.partition('.')
        neg = ip.startswith('-'); ip = ip.lstrip('-')
        return ('-' if neg else '') + '{:,}'.format(int(ip or '0')) + ('.' + fp if fp else '')
    return '{:,.{d}f}'.format(f, d=d)


def per(p):
    """'2026-09' / '2026-09-01' -> 'Sep 2026'; a full date that is not the 1st -> 'Nov 7, 2026'"""
    p = str(p or '')
    m = re.match(r'^(\d{4})-(\d{2})(?:-(\d{2}))?', p)
    if not m: return p
    y, mo, d = m.groups()
    if d and d != '01': return '%s %d, %s' % (MON[int(mo) - 1], int(d), y)
    return '%s %s' % (MON[int(mo) - 1], y)


def _fam(items, units):
    """[(ST, value, period)] -> one result; a State whose period differs from the family's newest carries its own"""
    items = [x for x in items if x[1] not in (None, '')]
    if not items: return None
    top = max(x[2] for x in items)
    vl = [[s + ('' if p == top else ' (' + per(p) + ')'), v] for s, v, p in sorted(items, key=lambda x: (ST.index(x[0]) if x[0] in ST else 99, x[0]))]
    return dict(vlist=vl, units=units, period=top)


def _last_nonempty(f):
    with (gzip.open(f, 'rt') if f.endswith('.gz') else open(f, newline='')) as h:
        R = list(csv.reader(h))
    hdr, rows = R[0], [r for r in R[1:] if r]
    return hdr, rows


def state_dir(fs, suffix, units, d=None):
    out = []
    for f in fs:
        b = os.path.basename(f).split('.')[0]
        if not b.endswith(suffix): continue
        st = b[:-len(suffix)]
        hdr, rows = _last_nonempty(f)
        rows = [r for r in rows if len(r) > 1 and r[1].strip() not in ('', '.')]
        if rows: out.append((st, num(rows[-1][1], d), rows[-1][0][:7]))
    return _fam(out, units)


def wide_states(f, units, d=None, datecol=0, only=None):
    hdr, rows = _last_nonempty(f)
    out = []
    for j, c in enumerate(hdr):
        st = c.split(' |')[0].strip()
        if st not in ST or (only and not c.endswith(only)): continue
        for r in reversed(rows):
            if j < len(r) and r[j].strip() not in ('', '.'):
                out.append((st, num(r[j], d), r[datecol][:10] if len(r[datecol]) > 7 and r[datecol][8:10] != '01' else r[datecol][:7])); break
    return _fam(out, units)


def eta(f, cols, units):
    best = {}
    with open(f, newline='') as h:
        for r in csv.DictReader(h):
            st = r['st']
            if st in ST and (st not in best or r['rptdate'] > best[st]['rptdate']) and all((r.get(c) or '').strip() != '' for c in cols): best[st] = r
    out = [(st, '; '.join(num(r[c]) for c in cols), r['rptdate']) for st, r in best.items()]
    return _fam(out, units)


def county_us(pairs, units_note):
    """pairs: {month: [sum(ur*lf), sum(lf), n]} -> the newest month's labor-force-weighted rate and total labor force"""
    m = max(pairs); a, b, n = pairs[m]
    return dict(values=[['U.S., from the county file', '%.1f%%' % (a / b), 'unemployment rate, labor-force-weighted over %s counties, not seasonally adjusted' % format(n, ',')],
                        ['U.S., from the county file', format(int(round(b)), ','), 'labor force, persons (sum of the counties)']],
                units=units_note, period=m)


def laus_flat(f):
    U, L = {}, {}
    with gzip.open(f, 'rt', errors='replace') as h:
        next(h)
        for ln in h:
            if not ln.startswith('LAUCN'): continue
            x = ln.split('\t'); sid = x[0].strip(); per_ = x[2].strip()
            if not re.match(r'M(0[1-9]|1[0-2])$', per_) or sid[5:7] in ('72', '78'): continue
            k = (sid[5:10], '%s-%s' % (x[1].strip(), per_[1:])); mc = sid[-2:]
            try: v = float(x[3])
            except Exception: continue
            if mc == '03': U[k] = v
            elif mc == '06': L[k] = v
    acc = {}
    for k, u in U.items():
        if k in L: a = acc.setdefault(k[1], [0.0, 0.0, 0]); a[0] += u * L[k]; a[1] += L[k]; a[2] += 1
    return county_us(acc, 'BLS LAUS county flat file')


def laus_held(f):
    acc = {}
    with gzip.open(f, 'rt') as h:
        for r in csv.DictReader(h):
            if r['fips5'][:2] in ('72', '78'): continue
            try: u, l = float(r['ur']), float(r['lf'])
            except Exception: continue
            a = acc.setdefault(r['month'], [0.0, 0.0, 0]); a[0] += u * l; a[1] += l; a[2] += 1
    return county_us(acc, 'BLS LAUS county, held base file')


def qcew_county(fs):
    f = sorted(fs)[-1]; acc = {}
    with open(f) as h:
        for ln in h:
            x = ln.rstrip('\n').split(',')
            try:
                if x[0][:2] in ('72', '78'): continue
                k = '%s-%02d' % (x[3], 3 * (int(x[4]) - 1) + int(x[5])); v = float(x[6] or 0)
            except Exception: continue
            a = acc.setdefault(k, [0.0, 0]); a[0] += v; a[1] += 1 if v > 0 else 0
    ks = [k for k in acc if acc[k][1] > 0]; m = max(ks)
    return dict(values=[['U.S., from the county file', format(int(acc[m][0]), ','), 'covered employment, persons (sum of %s county rows, not seasonally adjusted)' % format(acc[m][1], ',')]],
                units='', period=m)


def bls_flat_series(f, want):
    """{series_id: (period, value)} newest monthly value of each wanted series in a BLS flat file"""
    best = {}
    with gzip.open(f, 'rt', errors='replace') as h:
        next(h)
        for ln in h:
            sid = ln[:ln.find('\t')].strip() if '\t' in ln else ''
            if sid not in want: continue
            x = ln.split('\t'); p = x[2].strip()
            if not re.match(r'M(0[1-9]|1[0-2])$', p): continue
            k = '%s-%s' % (x[1].strip(), p[1:])
            if sid not in best or k > best[sid][0]: best[sid] = (k, x[3].strip())
    return best


def _grade1198(d, recession=False):
    """1198: the published grade of a damage (s2/one_scale.py grade: a recession on the log scale from 1.00, anything else below the line);
    the damage itself if that file cannot be read"""
    try:
        import importlib.util as _iu
        _sp = _iu.spec_from_file_location('one_scale', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'one_scale.py')); _m = _iu.module_from_spec(_sp); _sp.loader.exec_module(_m)
        return _m.grade(float(d), recession)
    except Exception:
        return d


def chron_v4(f):
    """the State chronology v4 in its latest month (the month of the damage line it is built with, as the stress map reads it)"""
    D = json.load(open(os.path.join(os.path.dirname(f), 'damage_line_v4_a198_1032.json'))); M = D['through']
    rec, dis = [], []
    with open(f, newline='') as h:
        for r in csv.DictReader(h):
            if r['peak'] <= M and (r['open'] == 'True' or (r['trough'] or '9999') >= M):
                (rec if r['status'] == 'recession' else dis if r['status'] == 'disturbance' else []).append(r['st'])
    return dict(values=[['States in recession', str(len(rec)), ', '.join(sorted(rec)) or 'none'],
                        ['States in disturbance', str(len(dis)), ', '.join(sorted(dis)) or 'none']], units='', period=M)


def qcew_county_ind(fs):
    """1164: the county-by-industry file (newest year, gz): the U.S. sums of the county totals, all ownerships (0) and private (5), industry 10, newest month"""
    acc = {}
    with gzip.open(sorted(fs)[-1], 'rt', newline='') as h:
        for r in csv.DictReader(h):
            if r['fips'][:2] in ('72', '78') or r['ind'] != '10' or r['own'] not in ('0', '5'): continue
            for i in (1, 2, 3):
                try: v = float(r['m%d' % i] or 0)
                except ValueError: continue
                a = acc.setdefault('%s-%02d' % (r['year'], 3 * (int(r['qtr']) - 1) + i), {'0': [0.0, 0], '5': [0.0, 0]})[r['own']]; a[0] += v; a[1] += 1 if v > 0 else 0
    m = max(k for k in acc if acc[k]['0'][1] > 0)
    return dict(values=[['U.S., all jobs, from the county file', format(int(acc[m]['0'][0]), ','), 'covered employment, persons (sum of %s county rows, not seasonally adjusted)' % format(acc[m]['0'][1], ',')],
                        ['U.S., private jobs, from the county file', format(int(acc[m]['5'][0]), ','), 'covered employment, persons (sum of %s county rows, not seasonally adjusted)' % format(acc[m]['5'][1], ',')]],
                units='', period=m)
def held(path, fs):
    """the value(s) held in the file(s) behind one data-page row, or None when no reader applies"""
    b = path
    if not fs: return None
    f = fs[-1]
    if 'state_shapes_cb2024' in b or b.endswith('.zip'): return dict(value='2024 boundaries', units='')
    if b.endswith('coincident-revised.xls'):
        import pandas as pd
        X = pd.read_excel(fs[0], sheet_name='Indexes'); X = X[X.iloc[:, 0].notna()]
        p = str(pd.to_datetime(X.iloc[-1, 0]).date())[:7]
        return _fam([(c, num('%.2f' % X[c].dropna().iloc[-1]), str(pd.to_datetime(X.loc[X[c].notna()].iloc[-1, 0]).date())[:7]) for c in X.columns if c in ST],
                    'index, 2007=100, seasonally adjusted (to two decimals)')
    if b.endswith('spi_state_monthly_benchmarked_1167.csv'):   # 1167j (27 Nov 2026): the State production index, each State's newest month
        import pandas as pd
        X = pd.read_csv(fs[0])
        return _fam([(c, num('%.1f' % X[c].dropna().iloc[-1]), str(X.loc[X[c].notna(), X.columns[0]].iloc[-1])[:7]) for c in X.columns if c in ST],
                    'index, 2017 = 100 (to one decimal)')
    if 'fred_state_ur' in b: return state_dir(fs, 'UR', 'percent, seasonally adjusted')
    if 'fred_state_payrolls' in b: return state_dir(fs, 'NA', 'thousands of persons, seasonally adjusted')
    if 'state_nan' in b: return state_dir(fs, 'NAN', 'thousands of persons, not seasonally adjusted')
    if b.rstrip('/').endswith('fred_nsa'):
        a = state_dir(fs, 'NAN', ''); u = state_dir(fs, 'URN', '')
        ud = {x[0].split(' ')[0]: x[1] for x in u['vlist']}
        return dict(vlist=[[s, v + '; ' + ud.get(s.split(' ')[0], '') + '%'] for s, v in a['vlist']], period=max(a['period'], u['period']),
                    units='payrolls, thousands of persons; unemployment rate, percent; not seasonally adjusted')
    if 'FH_state_claims' in b: return wide_states(f, 'natural log of the month\'s initial claims, not seasonally adjusted (as held)', d=3, only='| initial claims')   # 1167: three decimals (the data page showed 9.56317796268366)
    if b.endswith('ar539.csv'): return eta(f, ['c3', 'c8'], 'initial claims (c3); continued weeks claimed (c8); not seasonally adjusted, week ending')
    if b.endswith('ar5159.csv'): return eta(f, ['c1'], 'State UI initial claims (c1), not seasonally adjusted, month')
    if 'state_ic_weekly' in b: return wide_states(f, 'initial claims, not seasonally adjusted, week ending', d=0)
    if 'state_iur_monthly' in b: return wide_states(f, 'percent, insured unemployment rate, monthly average', d=2)
    if 'SQINC4' in b:
        with open(f, newline='', encoding='latin1') as h: R = list(csv.reader(h))
        hdr = R[0]; q = [i for i, c in enumerate(hdr) if re.match(r'^\d{4}:Q[1-4]$', c)]
        got = {}; desc = {}
        for r in R[1:]:
            lc = r[4].strip() if len(r) > 4 else ''
            if len(r) > q[-1] and lc in ('10', '50') and r[1].strip().rstrip(' *') in NAME:
                j = max(i for i in q if r[i].strip() not in ('', '(NA)'))
                got.setdefault(NAME[r[1].strip().rstrip(' *')], {})[lc] = (num(r[j]), '%s-%02d' % (hdr[j][:4], 3 * int(hdr[j][-1])))
            if len(r) > 7 and lc in ('10', '50') and r[0].strip().strip('"') == '00000': desc[lc] = r[6].strip() + (' (' + r[7].strip() + ')' if '(' not in r[6] else '')
        out = [(s_, v.get('10', ('', ''))[0] + '; ' + v.get('50', ('', ''))[0], max(x[1] for x in v.values())) for s_, v in got.items()]
        return _fam(out, 'line 10: %s; line 50: %s; quarter' % (desc.get('10', ''), desc.get('50', '')))
    if 'bps_state' in b:
        with open(f, newline='') as h: rows = list(csv.DictReader(h))
        m = max(r['month'] for r in rows)
        return _fam([(r['st'], num(r['units'], 0), m) for r in rows if r['month'] == m and r['st'] in ST], 'housing units authorized, total, not seasonally adjusted')
    if 'cps_state' in b:
        f = sorted(fs)[-1]
        with open(f, newline='') as h: rows = list(csv.DictReader(h))
        m = max(r['month'] for r in rows)
        return _fam([(FIPS['%02d' % int(r['fips'])], '%.1f%%' % (100 * float(r['unemp']) / (float(r['emp']) + float(r['unemp']))), m) for r in rows
                     if r['month'] == m and '%02d' % int(r['fips']) in FIPS], 'unemployment rate from the tallies: unemployed / (employed + unemployed), weighted, not seasonally adjusted')
    if b.endswith('CPIAUCSL.csv'):
        hdr, rows = _last_nonempty(f)
        return dict(values=[['CPIAUCSL', num(rows[-1][1]), 'index 1982-1984=100, seasonally adjusted']], units='', period=rows[-1][0][:7])
    if 'qcew_release_dates' in b:
        hdr, rows = _last_nonempty(f); r = max(rows, key=lambda r: r[2])
        return dict(value='%s Q%s released %s' % (r[0], r[1], per(r[2])), units='', period=r[2])
    if 'qcew_state_total' in b:
        with open(f, newline='') as h: rows = [r for r in csv.DictReader(h) if r['system'] == 'naics' and r['emplvl']]
        m = max(r['month'] for r in rows)
        return _fam([(r['st'], num(float(r['emplvl']), 0), m) for r in rows if r['month'] == m and r['st'] in ST], 'covered employment, persons, not seasonally adjusted')
    if 'qcew_industry_county' in b: return qcew_county_ind(fs)
    if 'county_tot' in b: return qcew_county(fs)
    if 'state_industry_releases' in b:
        with open(f, newline='') as h: rows = [r for r in csv.DictReader(h) if r['group'] in ('Total(1)', 'g0')]
        m = max(r['ref_month'] for r in rows); last = {}
        for r in rows:
            if r['ref_month'] == m and r['st'] in ST: last[r['st']] = r
        return _fam([(s, num(r['m0']), m) for s, r in last.items()], 'total nonfarm, thousands of persons, seasonally adjusted, as first published')
    if 'state_payroll_releases' in b:
        with open(f, newline='') as h: rows = list(csv.DictReader(h))
        last = {}
        for r in rows:
            s = NAME.get(r['state'])
            if s and (s not in last or r['ref_month'] > last[s]['ref_month']): last[s] = r
        return _fam([(s, num(r['m0']), r['ref_month']) for s, r in last.items()], 'total nonfarm, thousands of persons, as first published')
    if b.endswith('laus_county.txt.gz'): return laus_flat(f)
    if 'county_ur_lf' in b: return laus_held(f)
    if b.endswith('ces_all.txt.gz'):
        B = bls_flat_series(f, {s for _, s in CES}); p = max(v[0] for v in B.values())
        return dict(values=[[i, num(B[s][1]) + ('' if B[s][0] == p else ' (' + per(B[s][0]) + ')'), 'thousands of persons, seasonally adjusted'] for i, s in CES if s in B], units='', period=p)
    if b.endswith('state_metro_payrolls_all.txt.gz'):
        want = {'SMS%s000000000000001' % k: v for k, v in FIPS.items()}
        B = bls_flat_series(f, set(want))
        return _fam([(want[s], num(v[1]), v[0]) for s, v in B.items()], 'total nonfarm, thousands of persons, seasonally adjusted')
    if 'BH-STATE-CHRONOLOGY-V4' in b: return chron_v4(f)
    if 'damage_line_v4' in b:
        D = json.load(open(f)); M = D['through']; out = []; rec = set()
        for cf in glob.glob(os.path.join(os.path.dirname(f), 'BH-STATE-CHRONOLOGY-V4*.csv')):   # 1198: the States in a recession that month (the chronology beside the line), as chron_v4 reads them
            with open(cf, newline='') as h:
                for r in csv.DictReader(h):
                    if r['status'] == 'recession' and r['peak'] <= M and (r['open'] == 'True' or (r['trough'] or '9999') >= M): rec.add(r['st'])
        for s, v in (D.get('states') or {}).items():
            ln = [x for x in (v.get('line') or []) if x[1] is not None]
            if ln: out.append((s, num(_grade1198(ln[-1][1], s in rec)), ln[-1][0]))   # 1198: shown as the published grade, as the State page and the stress map show it
        return _fam(out, 'damage grade v4 (1.00 = recession), latest month')
    if 'out_v3_2_damage_cut/chronology.csv' in b:
        # 1198: the row shown is the LIVE register's (s2/disturbance/out/chronology.csv, rebuilt on every run), not the Mac's copy of
        # register v3.2, which still held 2024 as a recession; the Mac's file is read only if the live one is missing
        lf = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'disturbance', 'out', 'chronology.csv')
        with open(lf if os.path.exists(lf) else f, newline='') as h: rows = list(csv.DictReader(h))
        r = max(rows, key=lambda r: r['peak']); r['status'] = 'disturbance' if r['status'].startswith('disturbance') else r['status']
        txt = '%s from the %s peak%s: %s, grade %s%s' % ('Open' if r['open'] == 'True' else 'Closed', per(r['peak']), '' if r['open'] == 'True' else ' to the %s trough' % per(r['trough']),
                                                     r['status'], ('%.2f' % float(r['grade'])) if r.get('grade') not in (None, '') else '', ', provisional' if r['provisional'] == 'True' else '')
        return dict(value=txt, units='the register\'s latest dated row', period=r.get('payroll_latest_month') or r.get('graded_to') or r['peak'])
    if 'bhs_state' in os.path.basename(b):
        S = json.load(open(f)); sd = S.get('standing') or {}
        txt = '%s since %s' % (str(sd.get('state', '')).capitalize(), per(sd.get('since'))) if sd else ''
        return dict(value=txt, units='the detector\'s standing (closed: no recession open; open: a recession called)', period=str(S.get('built_at', ''))[:10])
    return None
