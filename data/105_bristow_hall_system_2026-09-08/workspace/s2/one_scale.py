#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ONE SCALE (collection 1140, 16 Nov 2026). Anthony: "recessions and disturbances are on the same scale ... recessions should start
when it crosses the threshold of 3 on the real time bristow hall rule recession indicator".

The scale runs from 0 to 10 with the recession line at 3.00:
  the real-time indicator   outside a recession 3 x the share of conditions met, at most 2.99; inside one 3 + 0.7 x the damage
                            grade: 3.00 on the call day, 10 at the damage of 1929-33 (bhs_build.py writes it)
  a disturbance             1.5 x its damage (damage below 2.00, so the grade is below 3.00)
  a recession               3 + 0.7 x its damage (damage 2.00 or more, so 4.40 to 10)
grade(d) is that map for a damage d on the tools' own 0-10 damage arithmetic (s2/damage_dimensions.py), read at the two decimals
the tools publish, rounded half up. No date, call or class moves: the damage arithmetic and the cut at damage 2.00 (register
v3.2, State chronology v4, stress map v3.1) are read unchanged.
A month inside a period (a State's or county's running damage) is placed by what the tool itself says of that month: a month of a
State recession period reads 3 + 0.7 x its damage so far, 3.00 with none yet, as the national line reads 3.00 on the call day (on
the stress map that is every red cell: the State layer colors every month of a recession period at least red, the county layer
colors a month red once its damage reaches 2.00); every other month reads 1.5 x its damage. So a red cell always reads 3.00 or
more and an orange one always less.

This file also places on the scale the two pages that code outside this repository builds, after the runner's site steps have
written them (run_cloud.sh and ops/live_tools/publish_pages.py call it):
  /state-onset/   the line, the table and the page's words      (s2/state_onset/page.html, collection 1032)
  /stress-map/    the numbers the panels print, the legend and the page's words   (s2/stress_map/page.html, collection 1052)
      python3 s2/one_scale.py pages     convert both published pages in place; a page already converted is left alone
      python3 s2/one_scale.py check     exit 1 unless both published pages are on the scale
A page that cannot be converted (its words or data changed) is never published half converted: the last converted page (the
one committed) is put back, the error is printed, an alert goes to the phone once a day, and the run goes on. No AI."""
import os, re, sys, json, subprocess, traceback, datetime
from decimal import Decimal, ROUND_HALF_UP

LINE = 3.0          # the recession line
CUT = 2.0           # the damage at which a contraction is a recession (register v3.2; State chronology v4)
MARK = 'one-scale-1140'
H = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(H, '..'))
SITE = os.path.abspath(os.path.join(WS, '..', 'site', 'public'))
PAGES = {'state': os.path.join(SITE, 'state-onset', 'index.html'), 'stress': os.path.join(SITE, 'stress-map', 'index.html')}


def grade(d):
    """a damage grade (0 to 10) on the one scale: 1.5 x d below damage 2.00, 3 + 0.7 x d from it; two decimals, half up"""
    if d is None: return None
    d2 = Decimal(str(d)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if d2 < 0: d2 = Decimal(0)
    g = Decimal('1.5') * d2 if d2 < 2 else Decimal(3) + Decimal('0.7') * d2
    return float(g.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def grade100(gi, red=None):
    """the same map in whole hundredths (the stress map stores damage x 100): the arithmetic the page's own script uses.
    red=True: a month the tool holds at recession grade (3 + 0.7 x damage whatever the damage so far); red=False: 1.5 x damage"""
    if gi is None: return None
    gi = max(0, int(gi))
    if red is None: red = gi >= 200
    return 300 + (7 * gi + 5) // 10 if red else (3 * gi + 1) // 2


def recession_grade(d):
    """3 + 0.7 x damage for a month or period the tool classes as a recession, whatever its damage so far"""
    return grade100(int(Decimal(str(d)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) * 100), True) / 100


def index_quiet(share):
    """the real-time indicator outside a recession: 3 x the share of conditions met, at most 2.99"""
    return min(2.99, 3.0 * max(0.0, float(share)))


def index_recession(damage):
    """the real-time indicator inside a recession: 3 + 0.7 x the damage grade so far (3.00 on the call day)"""
    return 3.0 + 0.7 * max(0.0, float(damage))


class Miss(Exception):
    pass


def _swap(t, pairs, what):
    """exact replacements, each found exactly n times, or Miss"""
    for old, new, n in pairs:
        c = t.count(old)
        if c != n: raise Miss('%s: %r found %d time(s), expected %d' % (what, old[:90], c, n))
        t = t.replace(old, new)
    return t


# ---------------------------------------------------------------- /state-onset/
STATE_TEXT = [
    ('<div class="lab">Units:</div>Damage grade,<br>0 to 10</div>', '<div class="lab">Units:</div>Grade, 0 to 10,<br>3.00 = recession</div>', 1),
    ('<b>Units:</b> Damage grade, 0 to 10: labor and output, Great Depression = 10', '<b>Units:</b> Grade, 0 to 10: 3.00 = recession, Great Depression = 10', 1),
    ('Shaded: recessions (damage grade 2.0 or more). Lined: disturbances (below 2.0).', 'Shaded: recessions (grade 3.00 or more). Lined: disturbances (below 3.00).', 1),
    ('Damage grade: the mean of the national labor and output scores (Great Depression = 10).',
     'Grade: 1.5 &times; damage for a disturbance, 3 + 0.7 &times; damage for a recession. Damage: the mean of the national labor and output scores (Great Depression = 10).', 1),
    ('<th>Damage, 0 to 10</th>', '<th>Grade, 0 to 10</th>', 1),
    ('<p>Units: Damage grade, 0 to 10</p>', '<p>Units: Grade, 0 to 10, 3.00 = recession</p>', 1),
    ("units:'Damage grade, 0 to 10'", "units:'Grade, 0 to 10, 3.00 = recession'", 1),
    # the peak label of each run: runs above damage 1.00 before, the same runs now (1.5 x 1.00)
    ('const v=k<N?SER.values[k]:null; if(v!==null&&v!==undefined&&v>1){', 'const v=k<N?SER.values[k]:null; if(v!==null&&v!==undefined&&v>1.5){', 1),
]


def convert_state(t):
    """the published State page on the one scale: every period's grade (1.5 x damage for a disturbance, 3 + 0.7 x damage for a recession), every State's line (a month of a recession period 3 + 0.7 x its damage so far, any other month 1.5 x), and the words"""
    if MARK in t: return t, dict(already=True)
    m = re.search(r'const ALL = (\{.*?\});\n', t, re.S)
    if not m: raise Miss('state page: no data (const ALL)')
    A = json.loads(m.group(1)); rows = pts = 0
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
                if (r['damage'] >= LINE) != (r.get('cls') == 'recession'): raise Miss('state page: %s %s is a %s with damage %s' % (st, r.get('peak'), r.get('cls'), r['damage_points']))
        S['scale'] = MARK
    t = t[:m.start(1)] + json.dumps(A, separators=(',', ':'), ensure_ascii=False) + t[m.end(1):]
    t = _swap(t, STATE_TEXT, 'state page')
    return t, dict(states=len(A), periods=rows, points=pts)


# ---------------------------------------------------------------- /stress-map/
G1_JS = ("// one scale (collection 1140): a damage grade in hundredths on the recession scale (half up). red = the cell is at recession grade (its color band is red or deep red,\n"
         "// or the period is a recession): 3 + 0.7 x the damage, 3.00 with none yet; otherwise 1.5 x the damage. A red cell reads 3.00 or more, an orange one less.\n"
         "function G1(gi,red){if(gi==null||isNaN(gi))return null;gi=Math.max(0,Math.round(gi));return (red?300+Math.floor((7*gi+5)/10):Math.floor((3*gi+1)/2))/100;}\n"
         "function RD(b){return b==='r'||b==='D';}\n")
STRESS_JS = [
    ('function abs_(s){', G1_JS + 'function abs_(s){', 1),
    ("'<br>Running damage grade <b>'+f2(c.g[i]/100)+'</b>'+(pr?(pr[1]==='open'?'':' (grade at the trough '+f2(pr[3])+')'):'')",
     "'<br>Running grade <b>'+f2(G1(c.g[i],RD(c.b[i])))+'</b>'+(pr?(pr[1]==='open'?'':' (grade at the trough '+f2(G1(pr[3]*100,pr[2]==='recession'))+')'):'')", 1),
    ("'Labor damage grade <b>'+f2(D.v[f][i]/100)+'</b> (rise of", "'Labor grade <b>'+f2(G1(D.v[f][i],RD(D.b[f][i])))+'</b> (rise of", 1),
    ('(labor damage grade under 0.05)', '(labor grade under 0.08)', 1),
    ("'<br>Running damage grade <b>'+f2(D.v[f][i]/100)+'</b>'+(pr&&pr[1]!=='open'?' (grade at the trough '+f2(pr[3])+')':'')",
     "'<br>Running grade <b>'+f2(G1(D.v[f][i],RD(D.b[f][i])))+'</b>'+(pr&&pr[1]!=='open'?' (grade at the trough '+f2(G1(pr[3]*100,pr[2]==='recession'))+')':'')", 1),
    ("running grade '+f2(c.g[ni]/100)", "running grade '+f2(G1(c.g[ni],RD(c.b[ni])))", 2),
    ("labor grade '+f2(c.g[ni]/100)", "labor grade '+f2(G1(c.g[ni],RD(c.b[ni])))", 1),
    ("[-4,'grade 4.0'],[-3,'2.0 (recession bar)'],[-2,'1.0'],[-1,'0.05 ", "[-4,'grade 5.8'],[-3,'3.0 (recession bar)'],[-2,'1.5'],[-1,'0.08 ", 1),
    ("'Mean damage grade of the States, weighted by State payroll jobs':'Mean damage grade of the State\\'s counties, weighted by county labor force'",
     "'Mean damage of the States, weighted by State payroll jobs':'Mean damage of the State\\'s counties, weighted by county labor force'", 1),
    ("'2.0 = recession damage</span>'", "'recession line (damage 2.0, grade 3.0)</span>'", 1),
    ("'Deep red: grade 4.0 or more'", "'Deep red: grade 5.8 or more'", 1),
    ("'Red: grade 2.0 to 4.0'", "'Red: grade 3.0 to 5.8'", 1),
    ("'Orange: period under 2.0, or index below trend'", "'Orange: period under 3.0, or index below trend'", 1),
]
STRESS_DESC = [   # (where, old, new)
    ('desc', "the color is the period's running damage grade, the same grade the national register and the State chronology use (labor and output dimensions, the Great Depression at 10): orange while the grade is small, full red at 2.0 (the recession bar), deep red at 4.0 and above.",
     "the color is the period's running grade, the same grade the national register and the State chronology use (labor and output dimensions, the Great Depression at 10; below the recession bar the grade is 1.5 times the damage, from the bar 3 plus 0.7 times the damage): orange while the grade is small, full red at 3.0 (the recession bar), deep red at 5.8 and above."),
    ('desc', 'The cut points (grade 0.05, 1.0, 2.0, 4.0; deviation', 'The cut points (grade 0.08, 1.5, 3.0, 5.8, that is damage 0.05, 1.0, 2.0, 4.0; deviation'),
    ('desc', 'a window must fall at least 1.0 point, grade 2.0 or more is a recession.', 'a window must fall at least 1.0 point, grade 3.0 or more (damage 2.0 or more) is a recession.'),
    ('v2.desc', 'on the same color scale (yellow when under 0.05)', 'on the same color scale (yellow when under 0.08)'),
    ('v2.desc', 'every month is at least red (deep red at grade 4.0 or more)', 'every month is at least red (deep red at grade 5.8 or more)'),
    ('v2.short', '(full red at the recession grade of 2.0)', '(full red at the recession grade of 3.0)'),
    ('v2.short', "The line on the timeline is the States' mean damage grade weighted by payroll jobs", "The line on the timeline is the States' mean damage weighted by payroll jobs"),
]


def convert_stress(t):
    """the published stress map on the one scale: the panels print grade (the page's own data stay damage x 100, read through G1 with
    the cell's own color band), the legend, the bands' words and the method text"""
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
        if not os.path.exists(p): print('one scale: %s page not there (%s); nothing to do' % (k, p)); continue
        t = open(p, encoding='utf-8').read()
        try:
            new, rep = CONV[k](t)
            if rep.get('already'): print('one scale: %s page already on the scale' % k); continue
            open(p, 'w', encoding='utf-8').write(new)
            if k == 'state':     # the card picture beside the page, drawn from the page as published
                try:
                    sys.path.insert(0, os.path.join(H, 'state_onset')); import state_onset_site as _s
                    open(os.path.join(os.path.dirname(p), 'thumb.svg'), 'w', encoding='utf-8').write(_s.thumb(new))
                except Exception: traceback.print_exc()
            print('one scale: %s page converted (recession line %.2f): %s' % (k, LINE, json.dumps(rep)))
        except Exception as e:
            traceback.print_exc(); last = _git_last(p)
            if last and MARK in last:
                open(p, 'w', encoding='utf-8').write(last)
                print('one scale: %s page NOT converted (%s); the last converted page is put back' % (k, e))
            else:
                print('one scale: %s page NOT converted (%s) and no converted page is committed; the page stands on the old scale' % (k, e))
            bad.append('%s: %s' % (k, e))
    if bad: _alert('The State page or the stress map could not be placed on the one scale (recession line 3.00): ' + ' | '.join(bad) + '. The last converted page is shown. Fix s2/one_scale.py.')
    return bad


def check():
    out = {}
    for k, p in PAGES.items():
        t = open(p, encoding='utf-8').read() if os.path.exists(p) else ''
        out[k] = bool(t) and MARK in t and (('3.00 = recession' in t) if k == 'state' else ("'3.0 (recession bar)'" in t and 'function G1(' in t))
    print('one scale check:', json.dumps(out)); return all(out.values())


if __name__ == '__main__':
    a = sys.argv[1] if len(sys.argv) > 1 else 'pages'
    if a == 'check': sys.exit(0 if check() else 1)
    try:
        pages()
    except Exception:
        traceback.print_exc(); print('one scale: the step failed; the pages stand as written')
    sys.exit(0)
