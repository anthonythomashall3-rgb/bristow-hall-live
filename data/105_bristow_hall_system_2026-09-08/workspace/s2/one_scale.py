#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RELABEL (collection 1197, 27 Nov 2026; Anthony: "can we switch the recession line to 1.00", "relabel the scale", option "Halve every
grade"): every PUBLISHED grade is the damage x 0.5, so the recession line reads 1.00 and 1929-33 reads 5.00. Nothing is re-dated or
re-classed: the damage itself (0 to 10, the cut at 2.00) is computed exactly as before inside the register, the State chronology and
the stress map; only the numbers and words the pages and the state publish are halved here. A grade below the line never rounds up to
it (at most 0.99). What follows is the 1167 text, with its numbers as they stood on the damage scale.

ONE NUMBER (collection 1167, 24 Nov 2026; replaces the one scale of collection 1140). Anthony: "what if we had recessions and
disturbances graded the same way", "Why dont we move the recession line to 2.00 then?", "Adopt".

The grade IS the damage: one number, 0 to 10, the damage of 1929-33 = 10 (s2/damage_dimensions.py). Every contraction is graded by
the same rule (on the fall of activity itself, or on its fall against trend where activity fell less than 1 percent; the register,
s2/disturbance/disturbance_chronology.py). A contraction that grades 2.00 or more is a recession; below 2.00 a disturbance.
  the real-time indicator   outside a recession 2 x the share of conditions met, at most 1.99; inside one the grade so far, never
                            below 2.00 (2.00 on the call day); each recession's grade is the register's (python3 s2/one_scale.py indicator)
  a disturbance, a recession, a State's or a county's period: its damage grade, unchanged (a month inside a recession period reads at
                            least 2.00, as the national line does from the call day)
grade(d) is the damage read at two decimals, rounded half up.
This file also writes the indicator's recession grades from the register and places on the scale the two pages that code outside this
repository builds (run_cloud.sh and ops/live_tools/publish_pages.py call it):
      python3 s2/one_scale.py indicator   the indicator's state: each recession's grade and the line inside it from the register
      python3 s2/one_scale.py pages       the State page and the stress map; a page already converted is left alone
      python3 s2/one_scale.py check       exit 1 unless both published pages are on the scale
A page that cannot be converted is never published half converted: the last converted page (the one committed) is put back, the error
is printed, an alert goes to the phone once a day, and the run goes on. No AI."""
import os, re, sys, json, subprocess, traceback, datetime
from decimal import Decimal, ROUND_HALF_UP

K = 0.5             # 1197: a published grade is the damage x K
DLINE = 2.0         # the recession line on the damage scale (1167), unchanged: the class cut everywhere inside
LINE = 1.0          # 1197: the recession line as published (DLINE x K)
CUT = 2.0
MARK = 'one-number-1197'
OLD_MARKS = ('one-number-1167',)
H = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(H, '..'))
SITE = os.path.abspath(os.path.join(WS, '..', 'site', 'public'))
STATE = os.path.abspath(os.path.join(WS, '..', 'site', 'bhs_state.json'))
REG = os.path.join(H, 'disturbance', 'out', 'chronology.json')
PAGES = {'state': os.path.join(SITE, 'state-onset', 'index.html'), 'stress': os.path.join(SITE, 'stress-map', 'index.html')}


def _q(d):
    return Decimal(str(d)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def grade(d):
    """1197: the published grade, the damage (0 to 10) x 0.5 at two decimals, half up (0 to 5; the line at 1.00). A damage below the
    line (2.00 at two decimals) never reads the line: at most 0.99."""
    if d is None: return None
    d2 = max(_q(d), Decimal(0))
    g = (d2 * Decimal(str(K))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if d2 < Decimal(str(DLINE)): g = min(g, Decimal('0.99'))
    return float(g)


def grade100(gi, red=None):
    """the same in whole hundredths (the stress map stores damage x 100). red=True: a month the tool holds at recession grade
    (at least 2.00, whatever its damage so far); otherwise the damage"""
    if gi is None: return None
    gi = max(0, int(gi))
    return max(200, gi) if red else gi          # still on the damage scale (the stress map's own unit); the page halves it in G1


def recession_grade(d):
    """a month or period the tool classes as a recession: its published grade so far, never below the line (1.00)"""
    return max(LINE, float((max(_q(d), Decimal(0)) * Decimal(str(K))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)))


def index_quiet(share):
    """the real-time indicator outside a recession: the share of conditions met, at most 0.99 (1197; was 2 x the share, at most 1.99)"""
    return min(LINE - 0.01, 2.0 * K * max(0.0, float(share)))


def index_recession(damage):
    """the real-time indicator inside a recession: the published grade so far (damage x 0.5), never below 1.00 (1.00 on the call day)"""
    return max(LINE, K * float(damage))


class Miss(Exception):
    pass


def _swap(t, pairs, what):
    """exact replacements, each found exactly n times (n may be a tuple of the counts allowed), or Miss"""
    for old, new, n in pairs:
        c = t.count(old)
        if c not in (n if isinstance(n, tuple) else (n,)): raise Miss('%s: %r found %d time(s), expected %s' % (what, old[:90], c, n))
        t = t.replace(old, new)
    return t


# ---------------------------------------------------------------- /state-onset/
STATE_TEXT = [   # the State page as its builder (collection 1032) writes it is already in damage grade with the cut at 2.0; 1167 names the line
    ('<div class="lab">Units:</div>Damage grade,<br>0 to 10</div>', '<div class="lab">Units:</div>Damage grade, 0 to 5,<br>1.00 = recession</div>', 1),
    ('<b>Units:</b> Damage grade, 0 to 10: labor and output, Great Depression = 10', '<b>Units:</b> Damage grade, 0 to 5: 1.00 = recession, Great Depression = 5', 1),
    ('Shaded: recessions (damage grade 2.0 or more). Lined: disturbances (below 2.0).', 'Shaded: recessions (damage grade 1.00 or more). Lined: disturbances (below 1.00).', 1),
    ('<th>Damage, 0 to 10</th>', '<th>Damage grade, 0 to 5</th>', 1),
    ('<p>Units: Damage grade, 0 to 10</p>', '<p>Units: Damage grade, 0 to 5, 1.00 = recession</p>', 1),
    ("units:'Damage grade, 0 to 10'", "units:'Damage grade, 0 to 5, 1.00 = recession'", 1),
    ("['Units','Index, 1.00 = recession, 0\\u201310 damage']", "['Units','Damage grade, 0 to 5, 1.00 = recession']", (0, 1)),
    # 1197: the two places the page still said the Depression is 10 and drew its axis to 10
    ('scores (Great Depression = 10). Index through', 'scores (Great Depression = 5). Index through', 1),
    ('{lo:0,hi:10,step:2}', '{lo:0,hi:5,step:1}', 1),
]


def v4_basis():
    """1167k: what each State period was graded on, from the State chronology itself (1032 out/BH-STATE-CHRONOLOGY-V4-1032.csv, a198:
    'activity' where the State index fell 1.0 percent or more, otherwise 'trend'): {(State, peak): graded_on}; {} where it is not here"""
    import glob, csv
    out = {}
    for f in glob.glob(os.path.expanduser('~/Projects/Onset Detector Data/1032_*/out/BH-STATE-CHRONOLOGY-V4-1032.csv')):
        try:
            for r in csv.DictReader(open(f, newline='')):
                if r.get('graded_on'): out[(r['st'], r['peak'])] = r['graded_on']
        except Exception: pass
    return out


def published_trend_basis():
    """1197: where the State chronology file is not on the disk (a site run without the live tools' state), the periods the page ALREADY
    PUBLISHED as disturbances at damage 2.00 or more - each was accepted, against the chronology's own 'graded_on', by the run that
    converted that page - are taken as graded on trend: {(State, peak)}. Read from the page as last committed, on this scale or the last."""
    out = set(); last = _git_last(PAGES['state'])
    if not last or not any(k in last for k in (MARK,) + OLD_MARKS): return out
    try:
        A = json.loads(re.search(r'const ALL = (\{.*?\});\n', last, re.S).group(1))
        for st, S in A.items():
            for r in S.get('nber') or []:
                if r.get('cls') == 'disturbance' and r.get('damage_points') is not None and r['damage_points'] >= DLINE:
                    out.add((st, r.get('slow') or r.get('peak'))); out.add((st, r.get('peak')))
    except Exception: traceback.print_exc()
    return out


def convert_state(t):
    """the published State page on one number: every period's grade is its damage; every State's line is its damage so far, a month of a
    recession period never below 2.00, and the words"""
    if MARK in t: return t, dict(already=True)
    m = re.search(r'const ALL = (\{.*?\});\n', t, re.S)
    if not m: raise Miss('state page: no data (const ALL)')
    A = json.loads(m.group(1)); rows = pts = 0
    BASIS = v4_basis(); SEEN = published_trend_basis() if not BASIS else set()
    if len(A) < 50: raise Miss('state page: %d States in the data' % len(A))
    for st, S in A.items():
        ser = S['series']; per = S.get('nber') or []; mk = [str(d)[:7] for d in ser['dates']]
        rec = [any(r.get('cls') == 'recession' and r['peak'] <= m <= ('9999-99' if r.get('open') else r['trough']) for r in per) for m in mk]   # the month lies in a recession period
        for k in ('values', 'reading'):
            if isinstance(ser.get(k), list) and len(ser[k]) == len(mk):
                ser[k] = [None if v is None else (0.0 if v <= 0 else (recession_grade(v) if rec[i] else grade(v))) for i, v in enumerate(ser[k])]; pts += len(mk) if k == 'values' else 0
        for r in per:
            if r.get('damage') is not None:
                r['damage_points'] = r['damage']; r['damage'] = recession_grade(r['damage']) if r.get('cls') == 'recession' else grade(r['damage']); rows += 1
                # 1167k (27 Nov 2026): the 1167 class rule, as the national register and q41 have it: a recession grades 2.00 or more on a fall of
                # activity; a disturbance grades below 2.00 or was not graded on a fall of activity (graded on its fall against trend: a198
                # graded_on 'trend'). AL 1990-01 (State index fall 0.32%, graded on trend, 3.00) stopped every State page from 26 Nov.
                if (r['damage'] >= LINE) != (r.get('cls') == 'recession') and not (r.get('cls') == 'disturbance' and ((r.get('graded_on') or BASIS.get((st, r.get('slow') or r.get('peak')))) == 'trend' or (st, r.get('slow') or r.get('peak')) in SEEN)):   # 'slow': the chronology's own peak (state_page_1032 moves 'peak' to the line's first month)
                    raise Miss('state page: %s %s is a %s with damage %s' % (st, r.get('peak'), r.get('cls'), r['damage_points']))
        S['scale'] = MARK
    t = t[:m.start(1)] + json.dumps(A, separators=(',', ':'), ensure_ascii=False) + t[m.end(1):]
    t = _swap(t, STATE_TEXT, 'state page')
    return t, dict(states=len(A), periods=rows, points=pts)


# ---------------------------------------------------------------- /stress-map/
G1_JS = ("// one number (1167), relabeled (1197): the page holds damage in hundredths (0 to 1000); the grade shown is damage x 0.5. red = the cell is at\n"
         "// recession grade (its color band is red or deep red, or the period is a recession): never below 1.00. A cell below the line reads at most 0.99.\n"
         "function G1(gi,red){if(gi==null||isNaN(gi))return null;gi=Math.max(0,Math.round(gi));var g=Math.round((red?Math.max(200,gi):gi)/2+1e-9)/100;return (!red&&gi<200)?Math.min(0.99,g):g;}\n"
         "function GH(x){if(x==null||isNaN(x))return null;var g=Math.round(x*50+1e-9)/100;return x<2?Math.min(0.99,g):g;}\n"
         "function RD(b){return b==='r'||b==='D';}\n")
STRESS_JS = [
    ('function abs_(s){', G1_JS + 'function abs_(s){', 1),
    ("'<br>Running damage grade <b>'+f2(c.g[i]/100)+'</b>'", "'<br>Running damage grade <b>'+f2(G1(c.g[i],RD(c.b[i])))+'</b>'", 1),
    ("'Labor damage grade <b>'+f2(D.v[f][i]/100)+'</b> (rise of", "'Labor damage grade <b>'+f2(G1(D.v[f][i],RD(D.b[f][i])))+'</b> (rise of", 1),
    ("'<br>Running damage grade <b>'+f2(D.v[f][i]/100)+'</b>'", "'<br>Running damage grade <b>'+f2(G1(D.v[f][i],RD(D.b[f][i])))+'</b>'", 1),
    ("running grade '+f2(c.g[ni]/100)", "running grade '+f2(G1(c.g[ni],RD(c.b[ni])))", 2),
    ("labor grade '+f2(c.g[ni]/100)", "labor grade '+f2(G1(c.g[ni],RD(c.b[ni])))", 1),
    # 1197: every other grade and cut the page prints, halved
    ("(grade at the trough '+f2(pr[3])+')'", "(grade at the trough '+f2(GH(pr[3]))+')'", 2),
    ("G1(g,RD(b)):g/100;}", "G1(g,RD(b)):g/200;}", 1),
    ("(labor damage grade under 0.05)", "(labor damage grade under 0.03)", 1),
    ("[[-4,'grade 4.0'],[-3,'2.0 (recession bar)'],[-2,'1.0'],[-1,'0.05 · −1 SD']", "[[-4,'grade 2.00'],[-3,'1.00 (recession line)'],[-2,'0.50'],[-1,'0.03 · −1 SD']", 1),
    ("'Deep red: grade 4.0 or more'", "'Deep red: grade 2.00 or more'", 1),
    ("'Red: grade 2.0 to 4.0'", "'Red: grade 1.00 to 2.00'", 1),
    ("'Orange: period under 2.0, or index below trend'", "'Orange: period under 1.00, or index below trend'", 1),
    ("'2.0 = recession damage</span>'", "'1.00 = recession</span>'", 1),
]
STRESS_DESC = [   # (where, old, new), 1197: the page's method text, written on the damage scale with the bar at 2.0, on the published scale
    ('desc', 'the Great Depression at 10): orange while the grade is small, full red at 2.0 (the recession bar), deep red at 4.0 and above', 'the Great Depression at 5): orange while the grade is small, full red at 1.00 (the recession line), deep red at 2.00 and above'),
    ('desc', 'The cut points (grade 0.05, 1.0, 2.0, 4.0;', 'The cut points (grade 0.03, 0.50, 1.00, 2.00;'),
    ('desc', 'a window must fall at least 1.0 point, grade 2.0 or more is a recession', 'a window must fall at least 1.0 point, grade 1.00 or more is a recession'),
    ('v2.desc', '(yellow when under 0.05)', '(yellow when under 0.03)'),
    ('v2.desc', '(deep red at grade 4.0 or more)', '(deep red at grade 2.00 or more)'),
    ('v2.short', '(full red at the recession grade of 2.0)', '(full red at the recession grade of 1.00)'),
]


def convert_stress(t):
    """the published stress map on one number: the panels print the damage grade (the page's own data, damage x 100, read through G1
    with the cell's own color band: a red cell never below 2.00)"""
    if MARK in t: return t, dict(already=True)
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', t, re.S)
    if not m: raise Miss('stress map: no data on the page')
    raw = m.group(1); J = json.loads(raw); V = J.get('v2') or {}
    for where, old, new in STRESS_DESC:
        o = J if where == 'desc' else V; k = where.split('.')[-1]
        if o.get(k, '').count(old) != 1: raise Miss('stress map %s: %r found %d time(s), expected 1' % (where, old[:80], o.get(k, '').count(old)))
        o[k] = o[k].replace(old, new)
    nb = 0
    for b in V.get('bands') or []:
        if len(b) > 4 and b[3] is not None:
            g = grade(b[3]); b[4], k = re.subn(r'grade \d+(?:\.\d+)?$', 'grade %.2f' % g, b[4])
            if k != 1: raise Miss('stress map: band text %r carries no grade' % b[4][:80])
            if g >= LINE: raise Miss('stress map: a disturbance band grades %.2f' % g)
            b.append(b[3]); b[3] = g; nb += 1          # the damage it was read from is kept as a last element
    if not nb: raise Miss('stress map: no disturbance band with a grade')
    J['scale'] = MARK
    for asc in (False, True):   # write the data as the builder wrote it (raw UTF-8 or escaped), so only what changed changes
        if json.dumps(json.loads(raw), separators=(',', ':'), ensure_ascii=asc).replace('</', '<\\/') == raw: break
    else: asc = False
    t = t[:m.start(1)] + json.dumps(J, separators=(',', ':'), ensure_ascii=asc).replace('</', '<\\/') + t[m.end(1):]
    t = _swap(t, STRESS_JS, 'stress map')
    return t, dict(bands=nb, states=len(J.get('states') or {}))


CONV = {'state': convert_state, 'stress': convert_stress}


def _git_last(path):
    """the page as last committed (a converted page after the first good run), or None"""
    try:
        top = subprocess.run(['git', '-C', os.path.dirname(path), 'rev-parse', '--show-toplevel'], capture_output=True, text=True, timeout=30).stdout.strip()
        if not top: return None
        r = subprocess.run(['git', '-C', top, 'show', 'HEAD:' + os.path.relpath(path, top)], capture_output=True, timeout=120)
        return r.stdout.decode('utf-8') if r.returncode == 0 and r.stdout else None
    except Exception:
        return None


def _alert(msg):
    """the phone, once a day while it lasts (the path the rule's own calls use)"""
    try:
        mark = os.path.join(WS, 'cache', 'one_scale_alert_on'); today = datetime.date.today().isoformat()
        if os.path.exists(mark) and open(mark).read().strip() == today: return
        os.makedirs(os.path.dirname(mark), exist_ok=True); open(mark, 'w').write(today)
        subprocess.run(['bash', os.path.join(WS, 's2', 'alert.sh'), 'ONE SCALE: A PAGE WAS NOT CONVERTED', msg[:900]], timeout=90)
    except Exception:
        traceback.print_exc()


def pages(which=('state', 'stress')):
    bad = []
    for k in which:
        p = PAGES[k]
        if not os.path.exists(p): print('one number: %s page not there (%s); nothing to do' % (k, p)); continue
        t = open(p, encoding='utf-8').read()
        try:
            new, rep = CONV[k](t)
            if rep.get('already'): print('one number: %s page already on the scale' % k); continue
            open(p, 'w', encoding='utf-8').write(new)
            if k == 'state':     # the card picture beside the page, drawn from the page as published
                try:
                    sys.path.insert(0, os.path.join(H, 'state_onset')); import state_onset_site as _s
                    open(os.path.join(os.path.dirname(p), 'thumb.svg'), 'w', encoding='utf-8').write(_s.thumb(new))
                except Exception: traceback.print_exc()
            print('one number: %s page converted (recession line %.2f): %s' % (k, LINE, json.dumps(rep)))
        except Exception as e:
            traceback.print_exc(); last = _git_last(p)
            if last and MARK in last:
                open(p, 'w', encoding='utf-8').write(last)
                print('one scale: %s page NOT converted (%s); the last converted page is put back' % (k, e))
            else:
                print('one scale: %s page NOT converted (%s) and no converted page is committed; the page stands on the old scale' % (k, e))
            bad.append('%s: %s' % (k, e))
    if bad: _alert('The State page or the stress map could not be placed on one number (recession line 1.00): ' + ' | '.join(bad) + '. The last converted page is shown. Fix s2/one_scale.py.')
    return bad


def check():
    out = {}
    for k, p in PAGES.items():
        t = open(p, encoding='utf-8').read() if os.path.exists(p) else ''
        out[k] = bool(t) and MARK in t and (('1.00 = recession' in t) if k == 'state' else ('function GH(' in t))
    print('one number check:', json.dumps(out)); return all(out.values())


def _months(a, b):
    return (int(b[:4]) - int(a[:4])) * 12 + int(b[5:7]) - int(a[5:7])


def indicator(state_path=STATE, reg_path=REG, extra=()):
    """1167: the indicator's state on one number. Each recession's grade is the register's grade of the recession window it overlaps (the
    same grade in Papers 2 and 3 and on every page); the line on a day of a recession is the register's grade so far that month, never below
    2.00 (2.00 on the call day); outside a recession bhs_build.py already wrote 2 x the share of conditions met. Writes the state in place
    (and each path in extra)."""
    S = json.load(open(state_path)); R = json.load(open(reg_path))
    recs = [e for e in R['episodes'] if e['status'] == 'recession' and e.get('damage_path')]
    # 1167 class rule: a call can fall on a window the register classes a disturbance (activity did not fall 1 percent: 2024-26). Such a
    # call takes that window's grade and its class; the line inside the call reads 2.00 (the call), never a recession grade it does not have.
    allw = [e for e in R['episodes'] if e['status'] in ('recession', 'disturbance_class1', 'disturbance_class2')]
    today = S.get('built_at', datetime.date.today().isoformat())[:7]
    def match(a, b, pool=None):
        best, bo = None, -1
        for e in (recs if pool is None else pool):
            p, t = e['peak'], (e['trough'] or '9999-12'); lo, hi = max(p, a), min(t, b)
            if lo <= hi and _months(lo, hi) > bo: best, bo = e, _months(lo, hi)
        return best
    ep_paths = []
    for e in S['episodes']:
        a = (e.get('open_month') or e.get('open_pub', '')[:7]); b = (e.get('close_month') or (e.get('close_pub') or '')[:7] or today)
        # chronology v4 (25 Nov 2026): a call may fall on a slowdown under way that is not yet a disturbance ('open_unsettled'); it takes that
        # window's grade so far and the status 'unsettled' until the window settles
        m = match(a, b) or match(a, b, allw) or match(a, b, [x for x in R['episodes'] if x['status'] == 'open_unsettled'])
        if m is None: raise Miss('indicator: the call opened %s overlaps no window of the register' % a)
        e['grade'] = grade(m['damage']); e['register_window'] = [m['peak'], m['trough']]; e['graded_on'] = m.get('graded_on')
        e['register_status'] = 'recession' if m['status'] == 'recession' else ('unsettled' if m['status'] == 'open_unsettled' else 'disturbance')
        ep_paths.append(((e.get('open_pub') or a)[:10], (e.get('close_pub') or '9999-12-31')[:10], m))
    def at(day):
        for a, b, m in ep_paths:
            if a <= day <= b:
                path = m.get('damage_path') or {}; mo = day[:7]; ks = sorted(path)
                if not ks: return LINE
                if mo in path: return index_recession(path[mo])
                return index_recession(path[ks[-1]] if mo > ks[-1] else 0.0)
        return LINE
    for key in ('series', 'series_monthly'):
        ser = S.get(key) or {}
        if not ser.get('values'): continue
        ser['values'] = [round(at(str(d)[:10]), 3) if p == 'open' else v for d, v, p in zip(ser['dates'], ser['values'], ser['phase'])]
        bad = [d for d, v, p in zip(ser['dates'], ser['values'], ser['phase']) if v is not None and ((p == 'open' and v < LINE) or (p == '' and v >= LINE))]
        if bad: raise Miss('indicator: %s reads off the line on %d days, first %s' % (key, len(bad), bad[0]))
    S['scale'] = dict(name='one number', line=LINE, collection='1197_relabel_line_1_2026-11-27',
                      indicator='outside a recession the share of conditions met (series.reading), at most 0.99; inside one the register grade so far, never below 1.00 (1.00 on the call day)',
                      grade='the damage x 0.5, 0 to 5 (1929-33 = 5); every contraction by one rule; 1.00 or more is a recession (damage 2.00 or more)', damage_per_grade=1.0 / K, relabel='1197, 27 Nov 2026')
    for p in (state_path,) + tuple(extra):
        json.dump(S, open(p, 'w'), allow_nan=False)
    print('one number: indicator state written (%d recessions from the register)' % len(ep_paths))


if __name__ == '__main__':
    a = sys.argv[1] if len(sys.argv) > 1 else 'pages'
    if a == 'check': sys.exit(0 if check() else 1)
    if a == 'indicator':
        try:
            indicator(extra=tuple(p for p in (os.path.join(WS, 'out', 'bhs_state.json'),) if os.path.exists(p)))
        except Exception as e:
            traceback.print_exc(); print('one number: indicator NOT placed (%s); the state stands as bhs_build.py wrote it' % e)
            _alert('The indicator could not be placed on one number: %s' % e)
        sys.exit(0)
    try:
        pages()
    except Exception:
        traceback.print_exc(); print('one scale: the step failed; the pages stand as written')
    sys.exit(0)
