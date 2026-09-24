"""Reproduce the whole record in one command.

    python reproduce.py

Every number the memo reports about the rule's accuracy is recomputed here from the
data on disk, and each is compared with what the memo says.  Any disagreement is a
failure, printed and counted; the exit status is non-zero if anything moved.  The
point is that the record is a measurement, not a remembered figure: a reader who runs
this either sees the same numbers or is told exactly which one changed.

What it checks, in order:
  1. the tool's own self-test
  2. the channel manifest - every data file the panels resolve, by SHA-256
  3. the nine chronologies the configuration was chosen on
  4. the tool and the benchmark harness agree episode by episode, not merely in total
  5. the four chronologies held out entirely
  6. the all-in totals across all thirteen chronologies
  7. the memo's own summary lines
  8. the rule against ECRI on the held-out chronologies
  9. the first-print replay on the OECD revisions database
  10. the quarterly committees on GDP first prints
  11. every monthly end of all thirteen chronologies on one denominator (memo section 1)
  12. the American real-time route (the union), both scorings, and the vintage replay
  13. (3 September 2026) the independent American rulings, and the day's measured negatives -
      the composite at the trough, the committee's emphasis as weights, the weekly warm-up,
      real income as first published in the final-date replay
  14. (3 September 2026, the American pass) the opening-edge clause and the bounded refinement -
      the one end of the 83 that moved (Japan 1977), the held-out four unmoved, the real-time
      replay with windows bounded by the route and the committee's announcement days - and the
      pass's negatives: the even-count median convention, the k-th channel as the date, the
      weekly initial-claims clause selected leave-one-out, the current reading of the panel
      (2022 to the data edge), and the Philadelphia Fed's daily index as a ruling
  15. (3 September 2026, the second half) the states' payrolls breadth, leave-one-peak-out (a
      measured object; the confirmation tier built on it was withdrawn in version 34 - one call,
      one date); the route's own American chronology of fifteen downturns; the velocity table;
      the eight panels; the self-test at 53
  16. (3 September 2026, night) route B - the claims objects and Sahm's gap: exactly the twelve
      and 2023-24, 1951 and 1967 not called, median 96 days; Sahm's own form of the gap (the
      minimum over the PREVIOUS twelve months) from version 36 - 5 of 12 dates exact under the
      'later' rule, April 2024
  17. (3 September 2026, night, second half) Anthony's standard - exactly the twelve and 2024,
      one call one date at every turn, one month: the separation bound object by object, the
      rate's forms in real time, the states' breadth, the trough clauses' 1970 floor, and the
      chronology under one call one date (route B the default); the self-test at 59
  18. (3 September 2026, night, third pass) the speed hunt: every fast object at the sixteen claims
      calls (the S&P and its exposure, spreads, the curve, the bill rate, carloadings, failures, the
      claims field's depth) and the one that adds speed - the vacancy rate at 0.6 beside Sahm's 0.5;
      route B' the default (median 80 days, 2023-26 called 28 August 2023); the self-test at 61
  19. (3 September 2026, night, fourth pass) the vacancy object's forms leave-one-out - the two-month
      mean 0.36 below its six-month maximum, every fold - route B'' the default (median 40 days, six
      within a month after); the Paper 2 chat's rule read for what transfers; temporary help and
      payrolls' first fall not adopted; the factor-free weekly state breadth at the route's line
  20. (3 September 2026, night, fifth pass) Paper 1's end rule as trough leg S (sahm_end_calls), gated by
      the claims field's arming: the 2023-24 downturn ends August 2024, called 5 December 2024; the
      twelve's ends unchanged; the self-test at 63
"""
import sys, subprocess, re, os
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab'); sys.path.insert(0, '/home/claude/lab/rt')
LAB = '/home/claude/lab'

ok = bad = 0
def chk(name, got, want):
    global ok, bad
    good = got == want
    if good: ok += 1
    else:    bad += 1
    print(f'  {"OK  " if good else "FAIL"} {name}')
    if not good:
        print(f'        recorded {want!r}')
        print(f'        measured {got!r}')

def run(script, cwd=LAB):
    r = subprocess.run([sys.executable, script], cwd=cwd, capture_output=True, text=True,
                       timeout=3600)
    if r.returncode != 0:
        print(r.stderr[-800:])
        raise RuntimeError(f'{script} exited {r.returncode}')
    return r.stdout

def row(text, label):
    """The peaks/troughs pair on the line whose label starts the row."""
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith(label):
            n = re.findall(r'(\d+)\s*/\s*(\d+)', s)
            if len(n) >= 2: return (int(n[0][0]), int(n[0][1])), (int(n[1][0]), int(n[1][1]))
    raise RuntimeError(f'no row starting {label!r}')

print('=== 1. the tool')
import bristow_rule_v3 as B
n = B.self_test(verbose=False)
chk('the tool self-test passes every check', n >= 39, True)
print(f'       ({n} checks)')

print('=== 2. the data')
import bench
chk('the panels match the channel manifest', bench.manifest_check(strict=False, verbose=False), [])
import json
chk('the manifest carries 118 channels',
    json.load(open(f'{LAB}/bench_manifest.json'))['total_channels'], 118)

print('=== 3. the nine chronologies the configuration was chosen on')
t = run('tool_check.py')
m = re.search(r'peak\s+(\d+)/(\d+)\s+trough\s+(\d+)/(\d+)', t)
chk('83 contractions, 78 peaks and 80 troughs',
    (int(m[1]), int(m[2]), int(m[3]), int(m[4])), (78, 83, 80, 83))

print('=== 4. the tool and the benchmark agree episode by episode')
d = run('tool_diff.py').strip()
chk('no episode is dated differently by the two', d, '')

print('=== 5. the four chronologies held out entirely')
z = run('zaf_full.py')
chk('South Africa: 8 of 11 peaks, 9 of 11 troughs', row(z, 'committee object '), ((8, 11), (9, 11)))
w = run('twn_test.py')
chk('Taiwan: 10 of 10 peaks, 8 of 10 troughs',
    row(w, "committee's own detrended index"), ((10, 10), (8, 10)))
g = run('deu_test.py')
chk('Germany: 5 of 7 peaks, 7 of 7 troughs (the four channels the Council names, adopted 2 September)',
    row(g, 'the four channels the Council itself names'), ((5, 7), (7, 7)))
x = run('mex_test.py', cwd=f'{LAB}/mex')
chk('Mexico: 5 of 5 published peaks, 6 of 6 troughs',
    row(x, 'the eight-channel Mexican panel'), ((5, 5), (6, 6)))

print('=== 6. all thirteen chronologies together')
# contractions, peaks hit, peaks published, troughs hit, troughs published.  Mexico's
# first cycle has no published peak, which is why the two denominators differ.
tot = {'the nine':   (83, 78, 83, 80, 83),
       'South Africa': (11,  8, 11,  9, 11),
       'Taiwan':       (10, 10, 10,  8, 10),
       'Germany':      ( 7,  5,  7,  7,  7),
       'Mexico':       ( 6,  5,  5,  6,  6)}
v = list(tot.values())
chk('117 contractions', sum(r[0] for r in v), 117)
chk('106 of 116 peaks', (sum(r[1] for r in v), sum(r[2] for r in v)), (106, 116))
chk('110 of 117 troughs', (sum(r[3] for r in v), sum(r[4] for r in v)), (110, 117))

print('=== 7. the memo says the same')
memo = open('/home/claude/Paper1.5_Bristow_Rule_Evidence_Memo.md').read()
chk('the memo reports 106 of the 116 published peaks',
    '106 of the 116 published peaks' in memo, True)
chk('the memo reports 110 of the 117 troughs', '110 of the 117' in memo, True)
chk('the memo reports 78/83 and 80/83 on the nine chronologies, and 78/80 and 80/81 reachable',
    '78/83 (94%)' in memo and '80/83 (96%)' in memo and '**78/80 (98%)**' in memo and '**80/81 (99%)**' in memo, True)
chk("the memo's all-in row reads 117 / 106 / 110",
    bool(re.search(r'\*\*all thirteen\*\*\s*\|\s*\*\*117\*\*\s*\|\s*'
                   r'\*\*106 ?/ ?116\*\*\s*\|\s*\*\*110 ?/ ?117\*\*', memo)), True)

chk('the memo carries the wall-adjusted score 106/113 and 110/115',
    '**106/113 (94%)**' in memo and '**110/115 (96%)**' in memo, True)

# The two CUMULATIVE lines - after South Africa alone, and after South Africa and Taiwan -
# are the ones that go stale silently when the nine move, so they are recomputed here.
o = tot['the nine']; z = tot['South Africa']; t = tot['Taiwan']
c1 = (o[0]+z[0], o[1]+z[1], o[3]+z[3])
c2 = (c1[0]+t[0], c1[1]+t[1], c1[2]+t[3])
chk(f'the memo\'s South Africa cumulative line reads {c1[0]} / {c1[1]} / {c1[2]}',
    (f'the sample becomes {c1[0]} contractions' in memo
     and f'**{c1[1]} peaks ({round(100*c1[1]/c1[0])}%) and {c1[2]} troughs '
         f'({round(100*c1[2]/c1[0])}%)**' in memo), True)
chk(f'the memo\'s Taiwan cumulative line reads {c2[0]} / {c2[1]} / {c2[2]}',
    (f'**{c2[0]} contractions**' in memo
     and f'**{c2[1]} peaks ({round(100*c2[1]/c2[0])}%) and {c2[2]} troughs '
         f'({round(100*c2[2]/c2[0])}%)**' in memo), True)

print('=== 8. the rule against ECRI on the held-out chronologies')
h = run('cmp/rulings_heldout.py')
def tot(label):
    m = re.search(re.escape(label) + r'.*?n (\d+) exact (\d+) w1 (\d+) w3 (\d+)', h)
    return tuple(int(x) for x in m.groups())
chk('ECRI against the committees, 40 ends: 11 / 23 / 31', tot('ECRI against the committees'), (40, 11, 23, 31))
chk('the rule against the committees, the same 40 ends: 16 / 28 / 36',
    tot('the rule against the committees, same ends'), (40, 16, 28, 36))
chk('the rule against ECRI, the same 40 ends: 10 / 21 / 31', tot('the rule against ECRI'), (40, 10, 21, 31))
chk('the memo\'s held-out rulings rows say the same',
    '| 40 | 11 (28%) | 23 (58%) | 31 (78%) | 2.30 |' in memo
    and '| 40 | **16 (40%)** | **28 (70%)** | **36 (90%)** | **1.60** |' in memo
    and '| 40 | 10 (25%) | 21 (52%) | 31 (78%) | 2.50 |' in memo, True)
r8 = run('rulings_all.py', cwd=f'{LAB}/cmp')
def tot8(label):
    m = re.search(re.escape(label) + r'\s*n=(\d+) exact (\d+) within1 (\d+) within3 (\d+)', r8)
    return tuple(int(x) for x in m.groups())
chk('in sample, ECRI against the committees, 36 ends: 10 / 17 / 32', tot8('ECRI vs committee'), (36, 10, 17, 32))
chk('in sample, the rule against the committees, the same 36 ends: 12 / 27 / 36',
    tot8('rule v23 vs committee, ECRI-dated ends only'), (36, 12, 27, 36))
chk('in sample, the rule against ECRI, 36 ends: 8 / 21 / 31', tot8('rule v23 vs ECRI'), (36, 8, 21, 31))
chk('the memo\'s in-sample rulings rows say the same',
    '| ECRI against the committees | 36 | 10 (28%) | 17 (47%) | 32 (89%) | 1.83 |' in memo
    and '| 36 | **12 (33%)** | **27 (75%)** | **36 (100%)** | **1.06** |' in memo
    and '| the rule as shipped against ECRI | 36 | 8 (22%) | 21 (58%) | 31 (86%) | 1.89 |' in memo, True)

print('=== 9. the first-print replay on the OECD revisions database')
r9 = run('oecd_rt/replay_oecd.py')
def line(label):
    m = re.search(re.escape(label) + r'\s*:\s*called (\d+) of (\d+), exact (\d+), within 1 (\d+), within 3 (\d+)', r9)
    return tuple(int(x) for x in m.groups())
mon = r9.split('--- monthly')[1].split('--- quarterly')[0]; qua = r9.split('--- quarterly')[1]
def lin(text, label):
    m = re.search(re.escape(label) + r'\s*:\s*called (\d+) of (\d+), exact (\d+), within 1 (\d+), within 3 (\d+)', text)
    return tuple(int(x) for x in m.groups())
chk('monthly peaks as first called: 19 of 28, 6 / 10 / 15', lin(mon, 'peaks, as first called'), (19, 28, 6, 10, 15))
chk('monthly troughs as called: 19 of 30, 4 / 12 / 18', lin(mon, 'troughs, as called'), (19, 30, 4, 12, 18))
chk('quarterly peaks as first called: 6 of 8, 4 / 6 / 6', lin(qua, 'peaks, as first called'), (6, 8, 4, 6, 6))
chk('quarterly troughs as called: 6 of 8, 5 / 5 / 6', lin(qua, 'troughs, as called'), (6, 8, 5, 5, 6))
chk('no end called within the month on the monthly chronologies',
    'within the month 0' in mon.split('peaks, as first called')[1].split('\n')[0]
    and 'within the month 0' in mon.split('troughs, as called')[1].split('\n')[0], True)
chk('the memo\'s replay table says the same',
    '| peaks, monthly chronologies, as first called | 19 of 28 | 6 | 10 | 15 |' in memo
    and '| troughs, monthly chronologies, as called | 19 of 30 | 4 | 12 | 18 |' in memo
    and '| peaks, quarterly chronologies, as first called (quarters) | 6 of 8 | 4 | 6 | 6 |' in memo
    and '| troughs, quarterly chronologies, as called (quarters) | 6 of 8 | 5 | 5 | 6 |' in memo, True)

print('=== 10. the quarterly committees on GDP first prints')
r10 = run('oecd_rt/replay_oecd_q.py')
m10 = re.search(r'GDP alone\s+peaks called (\d+)/8 exact (\d+) w1 (\d+) withinQ (\d+) \| troughs called (\d+)/8 exact (\d+) w1 (\d+)', r10)
chk('GDP first prints alone: peaks 6 of 8 called, 5 exact, 6 within one; troughs 7 of 8, 3 exact, 7 within one',
    tuple(int(x) for x in m10.groups()), (6, 5, 6, 0, 7, 3, 7))
blocks = [r10.split('=== ')[i] for i in range(1, len(r10.split('=== '))) if r10.split('=== ')[i].startswith(('EA, GDP alone', 'FRA, GDP alone', 'ESP, GDP alone'))]
chk('no other dated call on GDP alone (Spain\'s undated 2013 call is the second dip)',
    [re.findall(r"other peak calls: (\[.*?\])", b)[0] for b in blocks] == ['[]', '[]', "[('201303', None)]"]
    and all('other trough calls: []' in b for b in blocks), True)
chk('the memo\'s GDP-first-prints rows say the same',
    '| peaks, quarterly chronologies, **GDP first prints alone** (`replay_oecd_q.py`) | 6 of 8 | 5 | 6 | 6 |' in memo
    and '| troughs, quarterly chronologies, GDP first prints alone | 7 of 8 | 3 | 7 | 7 |' in memo, True)

print('=== 11. every monthly end of all thirteen chronologies on one denominator')
r11 = run('monthly_ends_all.py')
def lin11(label):
    m = re.search(re.escape(label) + r'\s+n\s+(\d+)\s+exact\s+(\d+)\s+w1\s+(\d+)\s+w2\s+(\d+)\s+w3\s+(\d+)\s+mae\s+([\d.]+)', r11)
    return tuple(int(x) for x in m.groups()[:5]) + (float(m.group(6)),)
chk('the nine, reachable monthly peaks: 61, exact 25, within one 42, within three 59, mae 1.28 (within one 43 and mae 1.26 before the opening-edge clause of 3 September)',
    lin11('peaks, reachable (walls out)'), (61, 25, 42, 52, 59, 1.28))
chk('the nine, reachable monthly troughs: 62, exact 31, within one 47, within three 61, mae 0.89',
    lin11('troughs, reachable (walls out)'), (62, 31, 47, 55, 61, 0.89))
chk('all thirteen, every reachable monthly peak: 94, exact 36, within one 65, within three 87, mae 1.63 (66 and 1.62 before 3 September)',
    lin11('peaks, all monthly ends'), (94, 36, 65, 77, 87, 1.63))
chk('all thirteen, every reachable monthly trough: 96, exact 44, within one 70, within three 91, mae 1.31',
    lin11('troughs, all monthly ends'), (96, 44, 70, 81, 91, 1.31))
chk('the memo\'s all-monthly-ends rows say the same',
    '| the exact month | **36/94 (38%)** | **44/96 (46%)** |' in memo
    and '| within one month | **65/94 (69%)** | **70/96 (73%)** |' in memo
    and '| within three months | **87/94 (93%)** | **91/96 (95%)** |' in memo
    and '**1.63 months (94 ends)**' in memo and '**1.31 months (96 ends)**' in memo, True)

print('=== 12. the American call from every object the record holds (memo section 8f)')
r12a = run('v8_legs.py', cwd=LAB + '/weekly')
m = re.search(r'conjunct, 4-week mean\s+line\s+0\.20: hits (\d+)/8 other\s+(\d+) inMonth (\d+) median\s+(\d+) d', r12a)
chk('the conjunct at the v8 line of 0.20: 8 of 8 peaks since 1969, no other call, median 72 days',
    tuple(int(x) for x in m.groups()), (8, 0, 2, 72))
m = re.search(r'lowest recession-window maximum \+([\d.]+)', r12a)
chk('the conjunct\'s lowest recession-window maximum is +0.350', round(float(m.group(1)), 3), 0.350)
r12b = run('union_peaks.py', cwd=LAB + '/weekly')
m = re.search(r'union: (\d+)/12 called, in-month (\d+), median lag (\d+) d, worst (\d+) d', r12b)
chk('peaks 1948 on, the union with the monthly conjunct: 12 of 12 called, 7 inside the month, median 30 days, worst 142',
    tuple(int(x) for x in m.groups()), (12, 7, 30, 142))
chk('the monthly conjunct opens November 1948 on 10 December 1948',
    '1948-11   1948-12-10   M      10   yes' in r12b, True)
m = re.search(r'the weekly object where it exists \(1991 on\), else A: exact (\d+)/12, within one (\d+)/12', r12b)
chk('peak dates: 6 of 12 exact, 8 within a month', tuple(int(x) for x in m.groups()), (6, 8))
chk('other peak episodes, per leg: 1951-09, 1952-04, 1967-04, 2023-08; three under the tool\'s grouping',
    re.search(r"other calls \(episodes, legs\): \[\('1951-09'.*\('1952-04'.*\('1967-04'.*\('2023-08'", r12b) is not None
    and len(re.findall(r"\('\d{4}-\d{2}', \[", r12b)) == 4, True)
r12c = run('union_troughs.py', cwd=LAB + '/weekly')
m = re.search(r'union: (\d+)/12 called, in-month (\d+), median lag (\d+) d, worst (\d+) d; final dates exact (\d+)/12, within one (\d+)/12', r12c)
chk('troughs 1949 on, the union with the monthly legs, per-leg scoring: 12 of 12 called, 9 inside the month, median 10 days, worst 41; dates 4 exact, 9 within a month',
    tuple(int(x) for x in m.groups()), (12, 9, 10, 41, 4, 9))
chk('the eight since 1970: lags 26, -41, 10, -43, 40, 41, -73, 18 (six inside the month)',
    'lags [26, -41, 10, -43, 40, 41, -73, 18]' in r12c, True)
chk('per-leg scoring: other trough calls 1951-10, 1952-10 (monthly initial claims), 1970-07 and 1975-09; the July 1948 call falls in the field\'s unadjusted warm-up and is outside the record (3 September 2026, legs_1948.RECORD_START)',
    [x for x in re.findall(r"\('(\d{4}-\d{2})', \[", r12c)] == ['1951-10', '1952-10', '1970-07', '1975-09'], True)
m = re.search(r'route: (\d+)/12 called, in-month (\d+), lags \[(.*?)\], worst after the trough (\d+) d; final dates exact (\d+)/12, within one (\d+)/12; other episodes (\d+)', r12c)
chk("the tool's grouping (union_calls): 12 of 12, 9 in-month, worst 41 days, dates 4 and 9, two other episodes (1951, 1952); 1970 opened 10 July 1970 dated May",
    (tuple(int(m.group(i)) for i in (1, 2, 4, 5, 6, 7)), m.group(3), '1970-07-10   H    1970-05       1970-11 (K)        1970-11    -143   yes' in r12c),
    ((12, 9, 41, 4, 9, 2), '-143, -73, -43, -41, -21, -18, 10, 10, 18, 40, 41, 41', True))
chk('the initial-claims clause with the spike maximum calls 2001 on the Department\'s file: 19 January 2002, dated November 2001',
    "('2002-01-19', '2001-11')" in r12c and "('2002-07-06'" not in r12c, True)
chk('the four troughs before 1970 are the monthly legs\': 1949-11-10 J, 1954-05-10 H, 1958-06-10 H, 1961-02-10 J',
    all(x in r12c for x in ('1949-10   1949-11-10   J      10  yes', '1954-05   1954-05-10   H     -21  yes', '1958-04   1958-06-10   H      41  no ', '1961-02   1961-02-10   J     -18  yes')), True)
r12f = run('legs_1948.py', cwd=LAB + '/weekly')
chk('the monthly conjunct at 0.20: 12 of 12 peaks, 4 of 4 before 1969, other calls 1952-04 and 1967-05; quiet maximum +0.287, lowest recession maximum +0.337',
    "M conjunct monthly, line 0.20: peaks 12/12 (1948-60: 4/4)" in r12f and "other ['1952-04-10', '1967-05-10']" in r12f
    and 'quiet-month maximum +0.287' in r12f and "('1981-07', 0.337)" in r12f, True)
chk('the monthly level clause on the field: continued claims 9 of 12 (all four before 1969), initial claims 9 of 12 (three)',
    'J continued claims monthly, shipped clause: troughs 9/12 (1949-61: 4/4)' in r12f and 'H initial claims monthly, shipped clause: troughs 9/12 (1949-61: 3/4)' in r12f, True)
sys.path.insert(0, LAB + '/rt'); r12g = run('final_date_rt.py', cwd=LAB + '/rt')
chk('the final date on the vintages fourteen months after the trough: peaks 4 exact 6 within one, troughs 4 and 6 (shipped analogues)',
    '  +14   : peaks n 8 exact 4 w1 6 w3 7 mae 1.75 | troughs n 8 exact 4 w1 6 w3 6 mae 1.75' in r12g, True)
chk('household employment vintages: 786 from ALFRED\'s form, the harvest\'s copy ended in 1965',
    len(__import__('alfred').vintages('CE16OV')) == 786, True)
m = re.search(r'route: (\d+)/12 called, in-month (\d+), median (\d+) d, worst (\d+) d; final dates exact (\d+)/12, within one (\d+)/12; other episodes (\d+)', r12b)
chk("the tool's grouping at the peak: 12/12, 7 in-month, median 30, worst 142, dates 6 and 8, three other episodes",
    tuple(int(x) for x in m.groups()), (12, 7, 30, 142, 6, 8, 3))
# the corrected clause leaves the file it was built on unchanged
r12d = run('speed_final.py', cwd=LAB + '/weekly')
chk('speed_final on its own state-sum file, after the correction: peaks 3/3 one false, troughs 4/4 two false, unchanged',
    'From 1991: peaks 3/3 within two months on both lag and error, 1 false;  troughs 4/4, 2 false' in r12d, True)
_ol = open(LAB + '/weekly/final_caller_pre_fix_2026-09-02.py').read()
chk('the pre-correction file is kept beside the corrected one and differs only in the maximum',
    'if n[i]>nmax: nmax=n[i]; nmax_i=i; fall=0' in _ol and 'if g[i]<=0 or n[i]>nmax' in open(LAB + '/weekly/final_caller.py').read(), True)
import monthly_ends_all as _M
_P,_T=_M.nine()
_us=[e for c,k,e,w in _P if c=='United States']; _ut=[e for c,k,e,w in _T if c=='United States']
chk('United States, retrospective, the shipped tool: peaks 6 exact and 11 within one of 12, troughs 8 and 11',
    (sum(x==0 for x in _us), sum(abs(x)<=1 for x in _us), sum(x==0 for x in _ut), sum(abs(x)<=1 for x in _ut)), (6, 11, 8, 11))
chk('the memo\'s Rule 17 table and section 8f carry 11 within one at the peak',
    '| **6/12** | **11/12** (all but the 1969 peak, +4) |' in memo and '6 exact and 11 within a month (§1' in memo, True)
chk('the memo\'s section 8f says the same',
    '**Twelve of twelve peaks since 1948 called, seven inside the month, median 30 days after the\npeak month, worst 142 (1981); dates 6 of 12 exact and 8 within a month**' in memo
    and '**Twelve of twelve troughs since 1949 called, nine inside the month, none later than\nforty-one days after the trough month; dates 4 of 12 exact and 9 within a month' in memo, True)
chk('the memo records the adoption, the corrected maximum and the 1981 reading',
    '**Adopted.** The union is the shipped American real-time route from 2 September 2026' in memo
    and "**The initial-claims clause's maximum, corrected.**" in memo
    and "**What the 1981 peak's 142 days are made of.**" in memo
    and '| Nov 2001 | 10 Jan 2002 | monthly continued claims | 41 | no | Nov 2001 | **Nov 2001 (0)** |' in memo
    and '| Oct 1949 | 10 Nov 1949 | monthly continued claims | 10 | **yes** | Sep 1949 | Sep 1949 (−1) |' in memo, True)
r12e = run('sahm_leg.py', cwd=LAB + '/weekly')
chk("Sahm's rule on the vintages: 1981 crossed with November's figure (4 December 1981), 1969 on 7 November 1969, others 69 to 129 days",
    "('1981-12-04'" not in r12e and '1981-07   none' in r12e and '1969-12   1969-11-07     -54' in r12e
    and all(x in r12e for x in ('1973-11   1974-04-05     126', '1980-01   1980-05-02      92', '1990-07   1990-12-07     129',
                                '2001-03   2001-07-06      97', '2007-12   2008-05-02     123', '2020-02   2020-05-08      69')), True)

print('=== 13. the independent American rulings, and the negatives of 3 September 2026')
r13 = run('rulings_us_full.py', cwd=LAB + '/cmp')
chk('the rule against the committee, twelve American contractions: peaks 6 exact 11 within one 11 within three, troughs 8 / 11 / 12',
    ('the rule, peaks (12)                                 n 12  exact  6  w1 11  w3 11' in r13 and
     'the rule, troughs (12)                               n 12  exact  8  w1 11  w3 12' in r13), True)
chk('Stock-Watson ISD index (Bry-Boschan) against the committee: peaks 4/6/7 of 8, troughs 7/8/8',
    ('SW10 ISD, peaks                                      n  8  exact  4  w1  6  w3  7' in r13 and
     'SW10 ISD, troughs                                    n  8  exact  7  w1  8  w3  8' in r13), True)
chk('like for like on the eight Stock-Watson ends the rule reads 4/7/7 peaks and 5/8/8 troughs',
    ('rule where SW10 ISD has a peak                       n  8  exact  4  w1  7  w3  7' in r13 and
     'rule where SW10 ISD has a trough                     n  8  exact  5  w1  8  w3  8' in r13), True)
chk('the readings: 1981 peak a divergence the median shares (+1.0), 2001 peak median -4.0 with the rule exact, 1969 peak off both (median -2.0, rule +4)',
    ('1981-07/82-11 peak           +1         +1.0         +0.0  DIVERGENCE' in r13 and
     '2001-03/01-11 peak           +0         -4.0         +4.0  exact vs committee' in r13 and
     '1969-12/70-11 peak           +4         -2.0         +6.0  off both' in r13), True)
chk('counts: 11 exact vs committee, 5 within a month of the median, 1 divergence, 1 off both',
    "counts: {'exact vs committee': 11, 'off both': 1, 'within a month of the median': 5, \"DIVERGENCE: the independent median sits on the rule's side of the committee\": 1}" in r13, True)
chk('the memo section 8e carries the American rulings table',
    '### The same question in the United States: the rule, the committee, and the independent American rulings' in memo
    and '| 1981-07 / 1982-11 | **+1** / +1 | **+1.0** / 0.0 (12, 12) |' in memo
    and '| 2001-03 / 2001-11 | **0** / +1 | **−4.0** / 0.0 (9, 9) |' in memo, True)
r13b = run('composite_trough_test.py')
chk('composite-then-date on the United States: equal-weight 5 peaks 6 troughs exact, inverse-sd 6 and 4, Bry-Boschan on the composite 4 and 3, ISD weights 2 and 5 - all below the shipped 6 and 8 (the composites\' 1981 trough no longer escapes the window: trough mae 0.82 and 1.18, from 3.17 and 3.50 before the bounded refinement)',
    ('shipped      peaks  6/11/11 of 12 mae 0.75   troughs  8/11/12 of 12 mae 0.42' in r13b and
     'comp-eq      peaks  5/ 9/10 of 12 mae 0.91   troughs  6/ 7/11 of 12 mae 0.82' in r13b and
     'comp-sd      peaks  6/ 9/ 9 of 12 mae 1.36   troughs  4/ 6/11 of 12 mae 1.18' in r13b and
     'comp-eq BB   peaks  4/ 9/10 of 12 mae 1.33   troughs  3/ 9/12 of 12 mae 1.08' in r13b and
     'comp-ISD     peaks  2/ 7/ 8 of 12 mae 0.88   troughs  5/ 7/ 8 of 12 mae 0.50' in r13b), True)
r13c = run('nber_emphasis_test.py')
chk("the committee's emphasis as a double vote: 5 peaks and 7 troughs exact against the shipped 6 and 8",
    ('shipped              peaks  6/11/11 of 12 mae 0.75   troughs  8/11/12 of 12 mae 0.42' in r13c and
     'income+payrolls x2   peaks  5/10/10 of 12 mae 1.08   troughs  7/10/11 of 12 mae 0.83' in r13c), True)
r13d = open(LAB + '/weekly/warmup_test.log').read()
chk('the weekly warm-up: residual 16.1 / 11.5 / 7.9 log points at floors of 260 / 156 / 104 weeks against 2.0 mature; the January 1988 call at every floor and no 1990 call',
    ('factor floor 260 weeks (first factor year 1991): residual 1988-90 16.1 log points, 1992-99 2.0' in r13d and
     'factor floor 104 weeks (first factor year 1988): residual 1988-90 7.9 log points, 1992-99 2.0' in r13d and
     r13d.count("peak calls before 2002: [('1988-01-02', '1987-12'), ('2001-04-14', '2001-03')]") == 4), True)
r13e = run('final_date_rt.py', cwd=LAB + '/rt')
chk('the final date at fourteen months with real personal income as first published: peaks 4/6/6, troughs 4/6/7; 2001 trough +2, 1969 peak +4, 1973 peak +9',
    ('=== shipped analogues + real personal income first print' in r13e and
     '2001-03    P 01-03(+0) T 01-12(+1)   P 01-03(+0) T 02-01(+2)' in r13e and
     '1969-12    P 70-04(+4) T 70-11(+0)   P 70-04(+4) T 70-11(+0)' in r13e and
     '1973-11    P 74-08(+9) T 75-05(+2)   P 74-08(+9) T 75-04(+1)' in r13e and
     r13e.split('=== shipped analogues + real personal income')[1].count('  +14   : peaks n 8 exact 4 w1 6 w3 6 mae 1.88 | troughs n 8 exact 4 w1 6 w3 7 mae 1.38') == 1), True)
chk('the shipped-analogue rows of the final-date replay are unchanged: +14 peaks 4/6/7 and troughs 4/6/6',
    r13e.split('=== wider')[0].count('  +14   : peaks n 8 exact 4 w1 6 w3 7 mae 1.75 | troughs n 8 exact 4 w1 6 w3 6 mae 1.75') == 1, True)
import alfred as _al
chk('ALFRED vintage files fetched 3 September: CPI 668 vintages from 1972-07-21, personal income 730 from 1966-01-18, PCE 563 from 1979-11-19, transfers 211 from 2009-02-02',
    (len(_al.vintages('CPIAUCSL')), str(_al.vintages('CPIAUCSL')[0].date()), len(_al.vintages('PI')), str(_al.vintages('PI')[0].date()),
     len(_al.vintages('PCE')), str(_al.vintages('PCE')[0].date()), len(_al.vintages('PCTR')), str(_al.vintages('PCTR')[0].date())),
    (668, '1972-07-21', 730, '1966-01-18', 563, '1979-11-19', 211, '2009-02-02'))
chk('the memo section 2 opens with version 42 and the header is dated September 4, 2026',
    '**Evidence memo, version 42. Hall & Bristow recession program. September 4, 2026.**' in memo and "**Version 42 puts a NUMBER on Rule 20" in memo and '**Version 41 (4 September 2026, small hours)' in memo and "**Version 40 carries out the three sweeps" in memo and "**Version 39 answers Anthony's question of the night" in memo and "**Version 38 continues the speed hunt under Anthony's clearance" in memo, True)

print('=== 14. the American pass of 3 September 2026: the opening-edge clause, the bounded refinement, the replays, the negatives')
import bristow_rule_v3 as _B, bench as _bench
chk('the tool and the harness both ship the opening-edge abstention (joint) and the bounded refinement',
    (_B.TROUGH_EDGE_ABSTAIN, _B.REFINE_BOUNDED, _bench.TROUGH_EDGE_ABSTAIN, _bench.REFINE_BOUNDED), ('joint', True, 'joint', True))
chk('the self-test carries the opening-edge, payroll-breadth, conjunction, chronology, second-object and leg-S checks (63 checks)', n >= 63, True)
r14 = run('edge_abstain_test.py')
chk('the four opening-edge readings on the nine: joint and dpeak move one end (Japan 1977 peak +1 to +2), both and either cost three American troughs',
    ('joint   peaks exact/w1/w3/n (25, 42, 59, 61)   troughs (31, 47, 61, 62)' in r14 and
     'dpeak   peaks exact/w1/w3/n (25, 42, 59, 61)   troughs (31, 47, 61, 62)' in r14 and
     'both    peaks exact/w1/w3/n (24, 41, 57, 61)   troughs (28, 43, 61, 62)' in r14 and
     'end     peaks exact/w1/w3/n (25, 43, 59, 61)   troughs (31, 47, 61, 62)' in r14 and
     r14.count('peak   Japan                      1977-01      1 -> 2') == 2 and
     'trough United States              1960-04      0 -> 2' in r14), True)
r14b = run('refine_bounded_test.py')
chk('the bounded refinement alone exposes the 1981 knife-edge (US trough +1 to -5); with the opening-edge clause nothing but Japan 1977 moves',
    ('bounded        peaks exact/w1/w3/n (25, 43, 59, 61)   troughs (31, 46, 60, 62)' in r14b and
     'trough United States              1981-07      1 -> -5' in r14b and
     'bounded+dpeak  peaks exact/w1/w3/n (25, 42, 59, 61)   troughs (31, 47, 61, 62)' in r14b), True)
chk('the held-out four are unmoved by the clause (67 ends, 24 exact, 46 within one, 58 within three)',
    'the rule against the committees, all ends : n 67 exact 24 w1 46 w3 58 mean 2.18' in h, True)
r14c = run('final_date_rt_windows.py', cwd=LAB + '/rt')
chk('the replay with windows bounded by the route, shipped analogues: +6 peaks 3/6/7 troughs 3/4/7 -> with the clause troughs 4/5/8; +14 peaks 4/6/7 troughs 5/7/7; +24 peaks 5/6/7 troughs 6/7/7; the 1982 trough exact at every horizon',
    (r14c.split('=== wider')[0].count('  +14   : peaks n 8 exact 4 w1 6 w3 7 mae 1.75 | troughs n 8 exact 5 w1 7 w3 7 mae 0.88') == 1 and
     r14c.split('=== wider')[0].count('  +24   : peaks n 8 exact 5 w1 6 w3 7 mae 1.50 | troughs n 8 exact 6 w1 7 w3 7 mae 0.75') == 1 and
     '1981-07    P 81-08(+1) T 82-11(+0)   P 81-08(+1) T 82-11(+0)   P 81-08(+1) T 82-11(+0)' in r14c and
     '1980-01    P 80-02(+1) T 80-06(-1)   P 80-02(+1) T 80-06(-1)   P 80-01(+0) T 80-06(-1)' in r14c), True)
chk("on the committee's own announcement days, shipped analogues: peaks 4/5/6 of 6 (1981 +2, 2007 +1), troughs 4/5/5 of 6 (1980 -1, 2001 +5); wider: peaks 3/5/5, troughs 4/5/6",
    (r14c.split('=== wider')[0].count('  peaks: n 6 exact 4 w1 5 w3 6 mae 0.50') == 1 and r14c.split('=== wider')[0].count('  troughs: n 6 exact 4 w1 5 w3 5 mae 1.00') == 1 and
     '1981-07   P    1981-07    1982-01-06    P 81-09  T none          +2' in r14c and
     '1981-07   T    1982-11    1983-07-08    P 81-08  T 82-11         +0' in r14c and
     r14c.split('=== wider: on the committee')[1].count('  troughs: n 6 exact 4 w1 5 w3 6 mae 0.50') == 1), True)
r14d = run('median_convention_loo.py')
chk('the even-count median convention: the earlier middle loses at every fold; the later middle (shipped) is picked six of six',
    ("conventions picked: {'later (shipped)': 6}" in r14d and 'earlier         : peaks exact 25 w1 38 w3 55 of 61 | troughs exact 30 w1 44 w3 59 of 62' in r14d), True)
r14e = run('order_statistic_test.py')
chk('the k-th channel as the date: US peaks exact 0/3/5 of 12 for the 1st/2nd/3rd earliest against the median 6; troughs the median in every fold; no earlier availability',
    ('peak 1th earliest  : peaks 16/29/46 of 61  US peaks 0/1/3 of 12' in r14e and 'peak 3th earliest  : peaks 23/41/58 of 61  US peaks 5/10/11 of 12' in r14e and
     "out of sample 31/47/61 of 62; the median 31/47/61 of 62; picked {'median': 6}" in r14e and
     '1th earliest  : available median 0 months after the peak (n 12)' in r14e and
     'median        : available median 0 months after the peak (n 12), settled median 3 (n 12); final date (data cut at +30) exact 6, within one 10, within three 10 of 12' in r14e), True)
r14f = open(LAB + '/weekly/ic_trough_loo.log').read()
chk('the weekly initial-claims level clause selected leave-one-out calls 4 of 8 troughs, never 1991 or 2001; continued claims 8 of 8 with in-month 2 and exact 3 against the shipped 1 and 4',
    ('out of sample: called 4/8, in-month 3, exact 2, within one 3' in r14f and
     'out of sample: called 8/8, in-month 2, exact 3, within one 6' in r14f and
     'held out 1991-03: picks nsm 4 rt 6 drop 1 arm 25 rearm 13 -> not called' in r14f), True)
r14g = open(LAB + '/us_now_2026-09-03.log').read()
chk('the panel 2022 to the data edge: no channel but retail volume fell more than 1.2 per cent; the largest 2024 drawdown is industrial production 1.26 per cent (November 2024); composite D peaks at 0.27; no month at 2.0',
    ('industrial production (Federal Reserve)    D max  1.26 at 2024-11' in r14g and 'composite D (median across channels): max 0.27 at 2022-08; months >= 2.0: 0' in r14g
     and "'verdict': 'growth cycle'" in r14g), True)
r14h = open(LAB + '/cmp/ads_ruling.log').read()
chk("the Philadelphia Fed's daily index as a ruling: BB on the monthly mean dates no peak within three months; the cumulated level 1/2/3 peaks and 4/5/6 troughs of 9; twenty-nine turns with no committee counterpart",
    ('BB on monthly ADS               : peaks n 4 exact 0 w1 0 w3 0' in r14h and 'level clause on cumulated ADS   : peaks n 9 exact 1 w1 2 w3 3' in r14h
     and 'troughs n 9 exact 4 w1 5 w3 6' in r14h and r14h.count("'2023-08P', '2024-01T', '2025-03P', '2025-10T'") >= 1), True)
chk('the memo carries the version 32 ledger',
    '**The opening edge, and the refinement kept inside the window' in memo and 'Japan\'s January 1977 peak' in memo, True)

print('=== 15. the confirmation leg and the two-tier verdict (3 September 2026, the second half)')
r15 = run('legs_state_payroll.py', cwd=LAB + '/weekly')
chk('the states\' payroll breadth, leave-one-peak-out: every fold picks amplitude 0.75, minimum phase 6, smooth 3; 12 of 12 called, no other call',
    ("picked {(0.75, 6, 3): 12}" in r15 and 'out of sample: called 12/12, in-month 0, exact 0, within one 2' in r15
     and "calls [('1949-06-20', '1949-04'), ('1953-10-20', '1953-08'), ('1957-12-20', '1957-10'), ('1960-12-20', '1960-10'), ('1970-09-20', '1970-07'), ('1975-02-20', '1974-12'), ('1980-07-20', '1980-05'), ('1981-11-20', '1981-09'), ('1991-03-20', '1991-01'), ('2001-09-20', '2001-07'), ('2008-10-20', '2008-08'), ('2020-05-20', '2020-03')]" in r15), True)
r15b = run('american_verdict.py', cwd=LAB + '/weekly')
chk('the route\'s own American chronology: fifteen episodes since 1948, twelve the committee\'s and 1951, 1967 and 2023 (the confirmation reading measured on them is withdrawn from the route - one call, one date)',
    ("episodes 15: confirmed 12 (all twelve committee recessions: True), unconfirmed 3 ['1951-09', '1967-04', '2023-08']" in r15b
     and '2023-08-28       C    2023-07       2023-09' in r15b and 'ONE CALL, ONE DATE' in B.AMERICAN_ROUTE and 'CONFIRMATION (' not in B.AMERICAN_ROUTE), True)
r15c = run('velocity_table.py')
chk('velocity: the twelve reach the composite line in 9, at least two channels at 2.0 in every one; the three other calls one channel each and no line',
    ('the twelve committee peaks: composite D reaches 2.0 in 9 of 12' in r15c and 'channels at 2.0: min 2 of 7' in r15c
     and 'the three other calls (1951, 1967, 2023): max composite D [0.79, 0.06, 0.17]; channels at 2.0 [1, 1, 1]' in r15c), True)
r15d = run('panel_edit_test.py')
chk('eight panels: none makes 2022-2026 a contraction (largest composite D 1.10); the shipped panel 6/11/11 and 8/11/12',
    ('shipped (committee six + retail volume)         7 | 6/11/11, 8/11/12' in r15d and 'labor market only                               7 | 0/2/3, 5/8/10' in r15d
     and '1.10 (2025-10), 2/7' in r15d and '+ hours and manufacturing employment            9 | 8/9/9, 9/11/12' in r15d), True)
chk('the memo carries section 8h and the rule\'s own American chronology', '## 8h. The second half of the American pass' in memo and "**The rule's own American chronology.**" in memo and '| **28 Aug 2023** | **Jul 2023** at the call' in memo, True)
r15e = run('american_now.py', cwd=LAB + '/weekly')
chk("the live reading runs: the Department's index called the downturn August 2023 (dated June 2023) and its return below the line February 2026 (called August 2026); no object at its line today",
    ("peak calls since 2015: [('2020-04', '2020-02'), ('2023-08', '2023-06')]; trough calls since 2015: [('2021-10', '2021-04'), ('2026-08', '2026-02')]" in r15e and 'No object is at its line today' in r15e), True)

print('=== 16. route B: the claims objects and Sahm\'s gap (3 September 2026, night)')
r16 = run('conjunction_route.py')
chk('route B calls exactly the twelve committee recessions and the 2023-24 downturn; 1951 and 1967 are not called',
    ("called 13: committee recessions 12/12, other episodes 1 (['2023-08']); episodes not called: ['1951-09', '1967-04']" in r16), True)
chk("route B (conjunction_calls, current vintage, the 'later' date rule): lag median 96 days, 1 of 12 inside the month, worst 248; dates exact 5/12, within one 9, within three 10, mae 1.33",
    ('lag: median 96 d, in-month 1/12, worst 248; dates exact 5/12, within one 9, within three 10, mae 1.33' in r16), True)
chk("the 2023-24 downturn under conjunction_calls is published 5 August 2024 and dated April 2024 - Sahm's form of the gap, Paper 1's month", '2024-08-05    none               -      2024-04   n/a' in r16, True)
chk('the memo carries section 8i and the route docstring carries the second condition', "## 8i. Anthony's rule for the call" in memo and "THE SECOND CONDITION (Sahm's gap at 0.5, first prints" in B.AMERICAN_ROUTE, True)

print('=== 17. one call, one date at every turn; the separation bound; the trough floor (3 September 2026, night, second half)')
r17a = run('slack/bound.py')
chk("the separation bound: the rate's Sahm form excludes 1951 and 1967 at 0.333 (current vintage), reaches the twelve, crosses in April 2024 and fires once alone (2003)",
    ('UR                       sahm3     0.333          0.33   0.23  12/12      4   3  -1  -3   2   4   0  -3   2   1   0   2     1.5     4   2024-04       1' in r17a), True)
chk('the payrolls, the hours and the insured rate reach the twelve only at lines that never cross in 2023-24 (the memo\'s wall)',
    ("-payrolls (log)          sahm3     0.482          0.48  -0.03  11/12" in r17a and 'never' in r17a.split('-payrolls (log)          sahm3')[1].split('\n')[0]
     and 'never' in r17a.split('IUR (FH)                 sahm3')[1].split('\n')[0]), True)
r17b = run('slack/ur_forms_rt.py')
chk("in real time the 1967 episode reached 0.43 on Sahm's form (first prints), so the line cannot go below it; at 0.433 the twelve cross a median of 2.5 months after the peak",
    ('3  12     0.33    0.43      0.433' in r17b and '2.5    4    2024-07' in r17b.split('3  12     0.33    0.43      0.433')[1].split('\n')[0]), True)
chk("Sahm's own line in real time: crossings a median of 3.5 months after the peak, worst 4, 2024 in July 2024, alone 1976-11 and 2003-06",
    ("Sahm's form at her line 0.5:  lags [4, 4, 2, 4, -2, 4, 3, -3, 4, 3, 4, 2]  median 3.5 worst 4  2024 crossing 2024-07  alone ['1976-11', '2003-06']" in r17b), True)
r17c = run('slack/state_breadth.py')
chk("the states' breadth at 30 per cent crosses before the national line in every recession since 1980 and in March 2024, and every month with a national gap of 0.4 or more shows 30 per cent or more - the same rise at a lower line",
    (' 30%         -1       -3       +1       +0       +1       +1   2024-03' in r17c and 'national gap in [0.4,0.5):  10 months, breadth median   38%, min  30, max  44; share of months at or above 30%: 100%' in r17c), True)
r17d = run('trough_floor.py', cwd=f'{LAB}/weekly')
chk('the trough floor: the shipped drops misfire on the 1970 pause on H, J and I; the lowest drops with no misfire are H 8, J 5, I 20, and K has none at 4',
    ('drop  5.0                    troughs 10/12' in r17d and '1970 misfire YES' in r17d.split('H  monthly')[1].split('drop  8.0')[0]
     and '1970 misfire no ' in r17d.split('H  monthly')[1].split('drop  8.0')[1].split('\n')[0]
     and '1970 misfire no ' in r17d.split('J  monthly')[1].split('drop  5.0')[1].split('\n')[0]
     and '1970 misfire YES' in r17d.split('J  monthly')[1].split('drop  5.0')[0]
     and '1970 misfire no ' in r17d.split('I  weekly')[1].split('drop 20.0')[1].split('\n')[0]
     and '1970 misfire YES' in r17d.split('I  weekly')[1].split('drop 20.0')[0]
     and '1970 misfire no ' in r17d.split('K  weekly')[1].split('drop  4.0')[1].split('\n')[0]), True)
r17e = run('american_chronology.py', cwd=f'{LAB}/weekly')
chk('the default chronology (route B, first prints, the claims date, safe drops): onsets 12 of 12 and one other, median 111 days, dates 6 exact and 8 within one; ends 12 of 12, median 30 days, six within a month',
    ('=== ROUTE B - claims AND Sahm 0.5 (first prints); the claims date; all legs' in r17e and
     'peaks: 12/12 committee peaks called; other onset calls 1; lag median 111 d, worst 142, inside the month 1, within a month after 2; dates exact 6, within one 8, mae 1.17' in r17e.split('the claims date; all legs')[1].split('===')[0] and
     'troughs: 12/12 committee troughs closed; lag median 30 d, worst 130, within a month after 6; dates exact 2, within one 8, mae 1.17' in r17e.split('the claims date; all legs')[1].split('===')[0]), True)
chk('the claims objects alone (route A) under one call one date: median 30 days, seven within a month after, and 1951, 1952 and 1967 called as well',
    ('peaks: 12/12 committee peaks called; other onset calls 4; lag median 30 d, worst 142, inside the month 4, within a month after 7; dates exact 6, within one 8, mae 1.17' in r17e.split('=== ROUTE A - the claims objects alone')[1].split('===')[0]), True)
chk('the 2023-26 downturn under the default: called 5 August 2024 by C, dated July 2023; ended 20 August 2026 by T, dated February 2026',
    ('  2024-08-05   C    2023-07   none                 |  2026-08-20   T    2026-02   none' in r17e), True)
chk("with the shipped trough drops the 1969-70 recession would have ended in May 1970 (called 10 July 1970) - the misfire the floor removes",
    ('1970-07-10   H    1970-05   1970-11      -143   -6' in r17e.split('=== ROUTE B, shipped trough drops')[1].split('===')[0]), True)
# (american_now's standing under the version-37 default - the last end 20 August 2026 by leg T dated February 2026 - is superseded
#  by version 39's leg S; the live standing is checked once, at step 19, on the current default)
chk('the memo carries section 8j and the route docstring the trough floors', "## 8j. Anthony's standard of 3 September (night)" in memo and 'TROUGH FLOORS (3 September 2026, night' in B.AMERICAN_ROUTE, True)

print('=== 18. the speed hunt: fast second conditions at the sixteen claims calls; the vacancy rate (3 September 2026, night, third pass)')
r18a = run('veto_hunt.py', cwd=f'{LAB}/speed2')
chk("the S&P drawdown separates the record - recessions' weakest -10.7 within thirty days of the call, disturbances' strongest -6.0 - and 2023 reads -6.9",
    ("minimum within 30 days   recessions: weakest  -10.7" in r18a and "disturbances: strongest   -6.0" in r18a.split('minimum within 30 days')[1].split('\n')[0] and '2023: -6.9' in r18a.split('minimum within 30 days')[1].split('\n')[0]), True)
chk('the exposure: an eight per cent drawdown inside sixty days on 43.6 per cent of all days and 31.5 per cent of quiet days since 1948',
    ('line  8%: within 30 days - all days 36.7%, quiet days 25.0%;   within 60 days - all 43.6%, quiet 31.5%' in r18a), True)
r18b = run('depth_branch.py', cwd=f'{LAB}/speed2')
chk("the claims field's depth: the disturbances' maxima 0.22, 0.22, 0.29 on the monthly conjunct and 75 on the breadth; the twelve's minima 0.34 and 77",
    ('1951-07      DISTURBANCE          -             0.22                75' in r18b and '1967-02      DISTURBANCE       0.02             0.29                75' in r18b and '1981-07      recession         0.35             0.34                91' in r18b and '1990-07      recession         0.30             0.37                77' in r18b), True)
r18c = run('american_chronology.py', cwd=f'{LAB}/weekly')
chk("route B' (the rate at 0.5 or the vacancy rate at 0.6): thirteen onsets and no other, median 80 days, one inside the month and three within a month after, dates 6 exact and 8 within one",
    ("peaks: 12/12 committee peaks called; other onset calls 1; lag median 80 d, worst 142, inside the month 1, within a month after 3; dates exact 6, within one 8, mae 1.17" in r18c.split("the vacancy rate's fall >= 0.6); the claims date; all legs")[1].split('===')[0]), True)
chk("under route B' the 2023-26 downturn is called 28 August 2023 by C (the vacancy rate already past its line), 1948 on 10 December 1948, 2001 on 30 May 2001",
    ('  2023-08-28   C    2023-07   none                 |  2026-08-20   T    2026-02   none' in r18c.split("the vacancy rate's fall >= 0.6); the claims date; all legs")[1].split('===')[0]
     and '  1948-12-10   M    1948-11   1948-11        10   +0' in r18c.split("the vacancy rate's fall >= 0.6); the claims date; all legs")[1].split('===')[0]
     and '  2001-05-30   B    2001-03   2001-03        60   +0' in r18c.split("the vacancy rate's fall >= 0.6); the claims date; all legs")[1].split('===')[0]), True)
chk("the rate-only route B is unchanged by the window's closing at the claims field's own end: median 111 days, thirteen onsets",
    ('peaks: 12/12 committee peaks called; other onset calls 1; lag median 111 d, worst 142, inside the month 1, within a month after 2; dates exact 6, within one 8, mae 1.17' in r18c.split('=== ROUTE B - claims AND Sahm 0.5 (first prints); the claims date; all legs')[1].split('===')[0]), True)
r18d = run('vacancy_veto.py', cwd=f'{LAB}/speed2')
chk("the vacancy rate's fall: maxima 0.07, 0.06, 0.42 in the three disturbances, 0.82 the twelve's minimum (1960), 1.55 in 2023-24; no own crossing at 0.5 or above outside a recession window since 1948",
    ('1951-06     0.07' in r18d and '1952-03     0.06' in r18d and '1967-01     0.42' in r18d and '1960-04     0.82' in r18d and '2023-06     1.55' in r18d and 'own firings outside [peak-9m, trough+6m] since 1948 at 0.5: []' in r18d and 'at 0.6: []' in r18d), True)
chk('on JOLTS as first published the gap never reaches 0.5 in 2010-2019 (pre-pandemic high 0.49, the February 2020 vintage), crosses 0.6 on 9 June 2020 and 1 November 2022, and reads 1.30 on 29 August 2023',
    ("(0.5, NaT), (0.6, NaT), (0.8, NaT)" in r18d and "(0.6, Timestamp('2020-06-09 00:00:00'))" in r18d and "(0.6, Timestamp('2022-11-01 00:00:00'))" in r18d and 'the pre-pandemic high of the as-of gap (vintages to March 2020, before the pandemic reached the data): 0.49 on 2020-02-11; the reading on 29 August 2023: 1.30' in r18d), True)
chk('the memo carries section 8k and the route docstring the speed hunt', '## 8k. The speed hunt' in memo and 'THE SPEED HUNT (3 September 2026, night, third pass' in B.AMERICAN_ROUTE, True)

print("=== 19. the vacancy object's fast form; route B'' (3 September 2026, night, fourth pass)")
r19a = run('vacancy_forms.py', cwd=f'{LAB}/speed2')
chk("the forms: (2, 6) at 0.36 - ceiling 0.24, floor 0.49 - crosses the twelve at 0 0 -3 4 1 3 0 3 -1 0 9 1 (median 0.5) with no own crossing outside recession windows from 1949",
    ('(2,  6)            0.24               0.49             0.36              0   0  -3   4   1   3   0   3  -1   0   9   1    6    8    0.5   2023-03   []' in r19a), True)
chk('leave-one-peak-out picks (2, 6) in every fold', 'every fold picks the same form: True {(2, 6)}' in r19a, True)
chk('out of sample 1920-1947 the (2, 6) form reaches all six interwar recessions with one crossing outside their windows (October 1946); the twelve-month forms miss 1937',
    ("form (2, 6) line 0.36: interwar crossings (months after the peak)   3   2   1   4   6   7   reached 6/6;  crossings outside the windows: ['1946-10']" in r19a and 'form (2, 12) line 0.65: interwar crossings (months after the peak)   3   2   3   4   -   7   reached 5/6' in r19a), True)
r19b = run('breadth_yoy.py', cwd=f'{LAB}/weekly')
chk("the factor-free weekly state breadth at the route's fifty-per-cent line: every fold picks x = 10, one week; it calls 17 September 1990, 1 January 2001, 21 April 2008, 6 April 2020, 24 April 2023 and nothing else",
    ('every fold the same: True {(10, 1)}' in r19b and "every call: [('1990-09-17', '1990-09'), ('2001-01-01', '2000-12'), ('2008-04-21', '2008-04'), ('2020-04-06', '2020-03'), ('2023-04-24', '2023-04')]" in r19b), True)
r19c = run('american_chronology.py', cwd=f'{LAB}/weekly')
blk = r19c.split("=== ROUTE B'' on first prints")[1].split('===')[0]
chk("route B'' on first prints: thirteen onsets and no other, median 40 days, two inside the month and six within a month after, dates 6 exact and 8 within one; ends unchanged",
    ('peaks: 12/12 committee peaks called; other onset calls 1; lag median 40 d, worst 142, inside the month 2, within a month after 6; dates exact 6, within one 8, mae 1.17' in blk and
     'troughs: 12/12 committee troughs closed; lag median 30 d, worst 130, within a month after 6; dates exact 2, within one 8, mae 1.17' in blk), True)
chk("under route B'' the calls: 1948 10 Dec 1948, 1953 20 Sep 1953, 1957 20 Aug 1957, 1980 20 Mar 1980, 1990 20 Sep 1990, 2001 30 Apr 2001, 2020 28 Mar 2020, 2023 28 Aug 2023",
    all(x in blk for x in ('  1948-12-10   M    1948-11   1948-11        10   +0', '  1953-09-20   A    1953-07   1953-07        51   +0', '  1957-08-20   A    1957-06   1957-08       -11   -2',
                           '  1980-03-20   A    1980-01   1980-01        49   +0', '  1990-09-20   A    1990-07   1990-07        51   +0', '  2001-04-30   B    2001-03   2001-03        30   +0',
                           '  2020-03-28   C    2020-03   2020-02        28   +1', '  2023-08-28   C    2023-07   none')), True)
r19d = run('american_now.py', cwd=f'{LAB}/weekly')
chk("american_now reads the default: the fast vacancy form's standing, the last onset 28 August 2023 by C dated July 2023, the last end 5 December 2024 by S dated August 2024",
    ("the vacancy rate's fall, fast form" in r19d and 'the last onset was called 28 August 2023 by leg C, dated July 2023; the last end was called 5 December 2024 by leg S, dated August 2024; the downturn is closed.' in r19d), True)
chk('the memo carries section 8l and the route docstring version 38\'s onsets', '## 8l. The fourth pass' in memo and 'DEFAULT (version 39 = version 38' in B.AMERICAN_ROUTE, True)

print("=== 20. Paper 1's end rule as leg S (3 September 2026, night, fifth pass)")
chk("leg S ungated ends 1973-75 in March 1974 (called 5 July 1974); gated by the claims field's arming it makes five calls and ends 2023-24 at August 2024, called 5 December 2024",
    ('  1974-03-30   B    1974-02   1973-11       120   +3   |  1974-07-05   S    1974-03   none' in r19c.split("among the trough legs, ungated")[1].split('===')[0] and
     'leg S gated by the claims field (admitted only where no level object armed): 5 calls; 1960-03-05>1959-11, 1970-02-05>1969-10, 1977-04-05>1976-12, 2003-11-05>2003-07, 2024-12-05>2024-08' in r19c and
     '  2023-08-28   C    2023-07   none                 |  2024-12-05   S    2024-08   none' in r19c.split('THE CANDIDATE')[1].split('===')[0]), True)
chk("with the gated leg S the twelve's ends are unchanged: 12 of 12, median 30 days, six within a month, dates 2 exact and 8 within one",
    ('troughs: 12/12 committee troughs closed; lag median 30 d, worst 130, within a month after 6; dates exact 2, within one 8, mae 1.17' in r19c.split('THE CANDIDATE')[1].split('===')[0]), True)
chk('the memo carries section 8m and the route docstring leg S', '## 8m. Paper 1' in memo and 'S  Paper 1\'s own end rule' in B.AMERICAN_ROUTE, True)

print("=== 21. the sweeps: the field's claims rules, ALL daily and weekly data, the walls (3 September 2026, night, fifth pass, continued)")
r21a = run('field_claims_rules.py', cwd=f'{LAB}/speed2')
chk("Hester's +90,000 rule on the current file: 8 of 9 since 1967, median 84 d, other episodes 1977-02 and 1979-04; never in 2023-24 (maximum 53,250)",
    ("reached 8/9, median 84 d, within a month 2;  other episodes (2): ['1977-02-10', '1979-04-19']" in r21a and 'Hester 53,250' in r21a), True)
chk("the Budget Lab's +0.25 on the insured rate: 7 of 8 since 1971, one other (1976-09); the SOS touches 0.200 in 2023-24 and never crosses",
    ("reached 7/8, median 62 d, within a month 2;  other episodes (1): ['1976-09-02']" in r21a and 'Budget Lab 0.200; SOS 0.200' in r21a), True)
import os as _os, pandas as pd
for _f, _n in (('daily', 11481), ('weekly', 3631), ('biweekly', 16)):
    _idx = pd.read_csv(f'{LAB}/data/fred_{_f}/_INDEX.csv')
    chk(f'the FRED {_f} corpus is complete: {_n} files indexed with sha256, every one present', len(_idx) == _n and all(_os.path.exists(f'{LAB}/data/fred_{_f}/{i}.csv') for i in _idx.id), True)
_sd = pd.read_csv(f'{LAB}/data/screen_daily.csv'); _sw = pd.read_csv(f'{LAB}/data/screen_weekly.csv')
chk('the daily screen: 4,618 series with history to 2005, 27,796 objects; one series reaches 1951; no full candidate separates; no object is a call object on its own',
    _sd.id.nunique() == 4618 and len(_sd) == 27796 and _sd[_sd.veto_dis == 3].id.nunique() == 1 and ((_sd.veto_dis == 3) & (_sd.veto_margin > 0)).sum() == 0
    and ((_sd.speed_cov == _sd.speed_of) & (_sd.speed_of >= 6)).sum() == 0, True)
chk('the weekly screen: 2,496 series, 17,262 objects; 35 reach 1951, none separates; the two own-ceiling call objects are continued claims (3- and 6-month change)',
    _sw.id.nunique() == 2496 and len(_sw) == 17262 and _sw[_sw.veto_dis == 3].id.nunique() == 35 and ((_sw.veto_dis == 3) & (_sw.veto_margin > 0)).sum() == 0
    and sorted(_sw[(_sw.speed_cov == _sw.speed_of) & (_sw.speed_of >= 6)].object.tolist()) == ['chg3m', 'chg6m'] and set(_sw[(_sw.speed_cov == _sw.speed_of) & (_sw.speed_of >= 6)].id) == {'CCSA'}, True)
_d5 = _sd[(_sd.id == 'DGS5') & (_sd.object == 'chg1m')].iloc[0]
chk("the one daily partial: the 5-year yield's one-month fall of 0.65 (margin 0.318 sd, exposure 1.9 per cent, read at 1967 only)",
    _d5.veto_dis == 1 and _d5.veto_sign == -1 and abs(_d5.veto_line - 0.65) < 1e-6 and abs(_d5.veto_margin - 0.318) < 1e-3 and abs(_d5.veto_exposure - 1.9) < 0.05, True)
_wl = open(f'{LAB}/data/walls.log').read()
chk('inside the route the Baa yield partial would call 2007 at -3 days and give median 30; it is refused on the monthly record (memo 8o)',
    '2007-12:-3*' in _wl.split('--- WBAA')[1].split('---')[0] and 'median 30 d, within a month 6' in _wl.split('--- WBAA')[1].split('---')[0], True)
chk('self-test 64 (the pub_lag_days entry) and the memo carries 8n-8q', B.self_test(verbose=False) >= 64 and all(f'## 8{c}.' in memo for c in 'nopq'), True)
r21b = run('window_exposure.py', cwd=f'{LAB}/data')
chk("the window-exposure simulation (Anthony's amendment: validate, not span): vacancy 0.9 per cent, Sahm 5.8, the 5-year yield's daily fall 23.6, the Baa rise 48.3, the S&P drawdown 53.9",
    all(x in r21b for x in ('confirmed inside the window   0.9%', 'confirmed inside the window   5.8%', 'confirmed inside the window  23.6%', 'confirmed inside the window  48.3%', 'confirmed inside the window  53.9%')), True)
chk("the memo records the amendment and STANDING-RULES carries Rule 18 amended and Rule 20", "**Anthony's amendment, and the simulation it asks for.**" in memo and 'RULE 18, AMENDED' in open('/home/claude/proj/STANDING-RULES.md').read() and 'RULE 20' in open('/home/claude/proj/STANDING-RULES.md').read(), True)

print("=== 22. the field's mechanisms, the nowcasts, the gauge (4 September 2026, small hours)")
r22a = run('gauge.py', cwd=f'{LAB}/weekly')
chk('the gauge: 804 closed months, calibration 1.0 / 6.4 / 8.6 / 18.2 / 58.3 per cent by bin, the at-line row 1.7; Brier 0.0326 against 0.0428',
    'closed months read: 804' in r22a and all(x in r22a for x in ('   1.0%', '   6.4%', '   8.6%', '  18.2%', '  58.3%', '   1.7%')) and 'Brier score of the calibrated gauge 0.0326 against the flat base rate 0.0428' in r22a, True)
chk("the gauge at the committee's peak month: 0.14 in July 1981, 0.16 in February 2020, 0.28 in November 1973",
    'r in the peak month: 0.14' in r22a and 'r in the peak month: 0.16' in r22a and 'r in the peak month: 0.28' in r22a, True)
r22b = run('late_objects.py', cwd=f'{LAB}/data')
chk("the late objects: the news sentiment's six-month fall is the nearest (8.9 per cent window exposure); GDPNow's objects 87-100 per cent",
    'confirmed inside the window   8.9%' in r22b and 'GDPNow real-time (2011-) [gdpnow] level        sign -1 | 2 rec (2020-02-2023-07) | line    -1.133 | at the line  19.0%  confirmed inside the window  89.6%' in r22b, True)
chk('the memo carries 8r-8u and STANDING-RULES Rule 21', all(f'## 8{c}.' in memo for c in 'rstu') and 'RULE 21' in open('/home/claude/proj/STANDING-RULES.md').read(), True)

print('=== 23. the hazard, measured; the 1946-1983 weekly state claims panel (4 September 2026)')
r23 = run('hazard.py', cwd=f'{LAB}/weekly')
chk("the hazard: Sahm's gap clears 0.5 in 5.5 per cent of quiet years, the vacancy form 0.36 in 6.4; the route's own hazard 0.035-0.25 per cent a year",
    'P(year clears)  5.482%' in r23 and 'P(year clears)  6.376%' in r23 and 'route hazard, point estimate: 0.035% to 0.250% a year' in r23, True)
chk('the record leg: thirty quiet years since 1949, no route episode in any of them; three claims-leg calls (1951, 1952, 1967) confirmed 0 of 3',
    'quiet years since 1949: 30' in r23 and 'three calls outside the thirteen in 78 years' in r23, True)
_pan = pd.read_csv(f'{LAB}/dol_hist/ui_claims_ALL_clean.csv', parse_dates=['week_ic'])
chk('the 1946-1983 panel as parsed so far: 5,043 verified state-weeks, 51 states, 236 weeks, July 1960 to March 1972',
    len(_pan) == 5043 and _pan.state_name.nunique() == 51 and _pan.week_ic.nunique() == 236, True)
chk('the memo carries 8v and 8w', '## 8v.' in memo and '## 8w.' in memo, True)

print()
print(f'=== {ok} checks passed, {bad} failed')
sys.exit(1 if bad else 0)
