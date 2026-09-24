"""The revision drill on a schedule (24 September 2026, collection 371; plan Step 5 item 13, Step 6 R3 and R10).

The workflow revision-drill.yml builds the state from the committed data (BHS_MODE=build): once plain (the base), once for each
of the four draws of collection 334 (BHS_REVISION_SEED = 1:typical, 2:typical, 3:typical, 1:all - the pre-first-print claims
histories re-drawn from the Department's real revisions), and once more plain (the base again). Each build's out/bhs_state.json
and out/frozen_record.json are kept under ops/out/drill/<label>_state.json and <label>_frozen.json. This script compares.

The pass line (written in 371's PREREG before the first run): for every draw the walked diary (episodes: open day, close day,
branches) is identical to the base's, the standing is identical, the frozen replay's PEAKS are identical, and the drill was
applied (state['revision_drill']['active'] with every series perturbed) - a draw whose drill did not run equals the base
trivially and is a FAIL, not a pass; and the second base equals the first in every key but the build stamps. The frozen
replay's TROUGH moves are reported, never a failure (334: they move in 4-5 of 9 pre-2002 episodes per draw).

Usage: python3 ops/drill_check.py <dir> [label ...]      (labels default to the four draws). Prints one line; exits 0 always."""
import json, os, sys

def load(d, label):
    s = json.load(open(os.path.join(d, label + '_state.json')))
    f = json.load(open(os.path.join(d, label + '_frozen.json')))
    return s, f

def diary(s): return [(e.get('open_pub'), e.get('close_pub'), e.get('open_branch'), e.get('close_branch')) for e in s.get('episodes') or []]
def peaks(f): return [x.get('published') for x in f if x.get('kind') == 'peak']
def troughs(f): return [x.get('published') for x in f if x.get('kind') == 'trough']

def main():
    d = sys.argv[1]; labels = sys.argv[2:] or ['1_typical', '2_typical', '3_typical', '1_all']
    base_s, base_f = load(d, 'base')
    out = {'version': base_s.get('version'), 'base_built_at': base_s.get('built_at'), 'draws': {}, 'base_again': None}
    ok = True; rows = []
    for lab in labels:
        try: s, f = load(d, lab)
        except Exception as e:
            out['draws'][lab] = {'error': repr(e)}; ok = False; rows.append('%s | MISSING (%r)' % (lab, e)); continue
        rd = s.get('revision_drill') or {}
        applied = bool(rd.get('active')) and all((v or {}).get('weeks_perturbed', 0) > 0 for v in (rd.get('series') or {}).values()) and len(rd.get('series') or {}) == 3
        c = {'walked_diary_identical': diary(s) == diary(base_s),
             'standing_identical': (s.get('standing') or {}) == (base_s.get('standing') or {}),
             'frozen_peaks_identical': peaks(f) == peaks(base_f),
             'drill_applied': applied}
        bt, dt = troughs(base_f), troughs(f)
        moved = [(a, b) for a, b in zip(bt, dt) if a != b] if len(bt) == len(dt) else [('count', '%d vs %d' % (len(bt), len(dt)))]
        c_ok = all(c.values()); ok = ok and c_ok
        out['draws'][lab] = {'checks': c, 'troughs_moved': moved, 'pass': c_ok}
        rows.append('%s | diary %s | standing %s | peaks %s | drill applied %s | troughs moved %d %s' % (lab, c['walked_diary_identical'], c['standing_identical'], c['frozen_peaks_identical'], applied, len(moved), moved))
    # the base again: the drill leaves nothing behind
    try:
        s2, f2 = load(d, 'base_again')
        diff = [k for k in set(base_s) | set(s2) if k not in ('built', 'built_at') and json.dumps(base_s.get(k), sort_keys=True, default=str) != json.dumps(s2.get(k), sort_keys=True, default=str)]
        same_frozen = json.dumps(base_f, sort_keys=True) == json.dumps(f2, sort_keys=True)
        out['base_again'] = {'keys_differing': sorted(diff), 'frozen_identical': same_frozen, 'pass': not diff and same_frozen}
        ok = ok and not diff and same_frozen
        rows.append('base again | keys differing %s | frozen identical %s' % (sorted(diff), same_frozen))
    except Exception as e:
        out['base_again'] = {'error': repr(e)}; ok = False; rows.append('base again | MISSING (%r)' % (e,))
    out['verdict'] = 'PASS' if ok else 'FAIL'
    n_draw = sum(1 for v in out['draws'].values() if v.get('pass'))
    moved = ['%s:%d' % (k, len(v.get('troughs_moved') or [])) for k, v in out['draws'].items() if 'checks' in v]
    print('Revision drill: %s (%s; %d of %d draws clean: peaks, diary and standing unmoved; frozen troughs moved %s)' % (out['verdict'], base_s.get('version'), n_draw, len(labels), ' '.join(moved)))
    for r in rows: print('  ' + r)
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out'), exist_ok=True)
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'drill_check.json'), 'w'), indent=1)

if __name__ == '__main__':
    main()
