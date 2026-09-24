# -*- coding: utf-8 -*-
"""L3 - WHAT HAPPENS WHEN THE COMMITTEE DATES A RECESSION (plan Step 5, L3 and L6; 23 September 2026, collection 335).

The committee watch (s2/chronology_watch.py, L2) writes chronology/lesson_pending.json when the NBER's pages carry a dating the
file chronology/announcements.json lacks. Nothing moves by itself: Anthony confirms, and this script does the rest in order.

    python3 s2/relearn.py status                       what is pending, what the file holds, whether the walk's knowledge agrees
    python3 s2/relearn.py confirm                      write the pending entry into the file (backup kept), clear the flag, open the ledger entry
    python3 s2/relearn.py rewalk [--run]               the exact commands that re-run the labour walk from the first cut after the announcement,
                                                       the union and the port; --run runs the walk in the lab sandbox and compares the chosen
                                                       lines cut by cut with the shipped ones (cache/<memo>_chosen_1948.pkl)
    python3 s2/relearn.py replay <memo>                the L3 test: the walk re-run on the file as it stands must choose the shipped lines at
                                                       every cut (the 2020 announcements re-derive the 2021 and 2022 cuts)

What may move and what may not (the learning protocol, plan item 19): a lesson moves the lines only through the causal walk at the
cuts after the announcement day; the lines chosen at earlier cuts are frozen by construction; the record before the announcement is
never rewritten; the windows, the objective, the two-family admission rule, the tie-break, the no-false-stop constraint and the
first-print discipline never move. The tool's own calls are never a lesson.

The ledger (L6): chronology/lessons.jsonl, one line per lesson - who dated it, when, what the walk chose after it and what changed.
"""
import os, sys, json, shutil, datetime, subprocess
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(HERE, 'chronology', 'announcements.json'); P = os.path.join(HERE, 'chronology', 'lesson_pending.json'); LEDGER = os.path.join(HERE, 'chronology', 'lessons.jsonl')
def _od():
    for r in (os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')):
        if os.path.isdir(r): return r
    return None
SB = os.path.join(_od() or '', '276_core_v6_lab_speed_1960_tiers_2026-09-20', 'sandbox')
KNOW = os.path.join(_od() or '', '303_the_four_round4_official_recognition_2026-09-22', 'code', 'e20_knowledge.py')
SHIPPED_MEMO = 'e29'   # the labour walk the shipped diary w7w5 rests on (collections 304, 309, 310)
# the walk's switches, exactly as 310/code/run_e29.sh set them for e29 (E28, E29, E20 knowledge dates, event cuts, the start rule, pre-1970 troughs, E19a/b, E21 close, E22)
WALK_ENV = dict(BHS_WRAP='walk_fast_e29.py', BHS_E28='1', BHS_E29='1', BHS_E='off', BHS_TIE='thin', BHS_E20='1', BHS_EVENTS='1', BHS_START='1', BHS_PRE70='1', BHS_E19A='1', BHS_E19B='1', BHS_E21='close', BHS_E22='1')

def load(): return json.load(open(F))
def status():
    a = load(); pend = json.load(open(P)) if os.path.exists(P) else None
    print('announcements.json: %d recessions, updated %s' % (len(a.get('recessions', [])), a.get('updated')))
    last = a['recessions'][-1]; print('  last entry:', json.dumps(last)[:200])
    print('pending:', json.dumps(pend)[:300] if pend else 'nothing')
    r = subprocess.run([sys.executable, '-c', "import importlib.util,sys;s=importlib.util.spec_from_file_location('k',%r);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);print('knowledge agrees with the file:',getattr(m,'_FILE_AGREES',None))" % KNOW], capture_output=True, text=True)
    print((r.stdout or r.stderr).strip()[-400:])

def confirm():
    if not os.path.exists(P): print('nothing is pending'); return 1
    pend = json.load(open(P)); a = load()
    shutil.copy2(F, F + '.bak_' + datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ'))
    added = []
    for e in pend.get('pending', []):
        kind, month, ann = e.get('kind'), e.get('month'), e.get('announced')
        recs = a['recessions']
        if kind == 'peak':
            recs.append(dict(peak=month, peak_announced=ann, source=e.get('source', 'NBER'), trough=None, trough_announced=None, confirmed=datetime.date.today().isoformat())); added.append(e)
        elif kind == 'trough':
            open_ = [r for r in recs if r.get('trough') is None]
            if not open_: print('a trough with no open peak entry:', e); continue
            open_[-1].update(trough=month, trough_announced=ann, confirmed=datetime.date.today().isoformat()); added.append(e)
    a['updated'] = datetime.date.today().isoformat(); json.dump(a, open(F, 'w'), indent=1)
    os.remove(P)
    with open(LEDGER, 'a') as f:
        f.write(json.dumps(dict(confirmed=datetime.datetime.utcnow().isoformat() + 'Z', entries=added, walk='pending: python3 s2/relearn.py rewalk --run', lines_changed=None, note='the lesson enters the file; the walk re-runs from the first cut after the announcement; the port records the new lines as a version')) + '\n')
    print('confirmed %d entr%s into the file; the flag is cleared; the ledger has the entry. Next: python3 s2/relearn.py rewalk' % (len(added), 'y' if len(added) == 1 else 'ies'))
    print('NOTE: e20_knowledge.py keeps the same datings in its dictionaries; add the entry there too (the file and the dictionaries must agree - status shows whether they do).')
    return 0

def rewalk(run=False, memo='relearn'):
    cmds = ['cd "%s"' % SB, ' '.join('%s=%s' % kv for kv in WALK_ENV.items()) + ' BHS_WORKERS=6 BHS_TURNS_SEED=cache/%s_turns.pkl %s walk_fastest.py 1948 2026 %s' % (SHIPPED_MEMO, sys.executable, memo),
            '# the union of the labour walk, walk D, the concurrence branch and the closers (collection 304/310: union_e29.py, make_w7w5.py) with the new memo',
            '# the port: cache/bhs_version.json names the new diary; PREREG, the battery, then the push (only on Anthony\'s word)']
    print('\n'.join(cmds))
    if not run: return 0
    env = dict(os.environ, **WALK_ENV); env['BHS_WORKERS'] = '6'; env.setdefault('OD', _od() or '')
    env.setdefault('BHS_TURNS_SEED', os.path.join(SB, 'cache', '%s_turns.pkl' % SHIPPED_MEMO))   # the shipped walk's record store: a re-walk rebuilds only the records it lacks
    r = subprocess.run([sys.executable, 'walk_fastest.py', '1948', '2026', memo], cwd=SB, env=env, capture_output=True, text=True)   # the runbook's command (310/code/run_e29.sh); the same interpreter as this script
    print(r.stdout[-1500:]); print(r.stderr[-800:])
    return compare(memo)

def compare(memo):
    import pickle
    a = pickle.load(open(os.path.join(SB, 'cache', '%s_chosen_1948.pkl' % SHIPPED_MEMO), 'rb')); b = pickle.load(open(os.path.join(SB, 'cache', '%s_chosen_1948.pkl' % memo), 'rb'))
    cuts = sorted(set(a) | set(b)); diff = []
    for c in cuts:
        if c not in a or c not in b: diff.append((str(c.date()), 'missing in ' + ('shipped' if c not in a else memo))); continue
        d = {k: (a[c].get(k), b[c].get(k)) for k in set(a[c]) | set(b[c]) if a[c].get(k) != b[c].get(k)}
        if d: diff.append((str(c.date()), d))
    print('cuts compared: %d; cuts whose chosen lines differ from the shipped walk: %d' % (len(cuts), len(diff)))
    for x in diff[:20]: print('  ', x)
    return 0 if not diff else 2

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if cmd == 'status': status()
    elif cmd == 'confirm': sys.exit(confirm())
    elif cmd == 'rewalk': sys.exit(rewalk(run='--run' in sys.argv))
    elif cmd == 'replay': sys.exit(rewalk(run=True, memo=(sys.argv[2] if len(sys.argv) > 2 else 'l3replay')))
    elif cmd == 'compare': sys.exit(compare(sys.argv[2]))
    else: print(__doc__)
