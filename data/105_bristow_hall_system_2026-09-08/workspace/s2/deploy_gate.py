# -*- coding: utf-8 -*-
"""THE DEPLOY GATE (17 September 2026; collection 201; register items 62 and 63).

Until today bhs_run.sh logged a failed data check and deployed anyway. This script decides, after every build, whether
the build may be published. It reads what s2/q41_data_check.py wrote (out/q41_data_check.json: one row per check with
its gate class), the state just built (out/bhs_state.json) and the state last published (cache/last_deployed_state.json).

  gate 'hard'  a corrupt state or a garbage input (a unit check outside any physically possible range, dates out of
               order, a negative reading, the public copies not this build): HOLD, always - a wrong input must never
               become a published call.
  gate 'soft'  the page disagrees with its own sources (a tile's arithmetic, a feed against the readings table, the
               standing against the episodes, the record table): HOLD - unless the rule's standing has changed since
               the last published state, in which case PUBLISH and alert: a call is never held back by a page check.
  no gate      freshness and presentation (a stale channel, a next-published day in the past, a missing unit): PUBLISH
               and note it.
  the check did not complete (crashed, or wrote nothing): treated as one 'soft' failure.

Prints one line: "DEPLOY ..." or "HOLD ...". Exit 0 = deploy, 10 = hold. Never raises: a gate that crashes says HOLD
unless the standing changed. Run from the workspace: python3 s2/deploy_gate.py
"""
import json, os, sys

def _load(p):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return None

def _standing_key(s):
    if not s: return None
    ep = s.get('episodes') or []
    return (json.dumps(s.get('standing'), sort_keys=True), len(ep), json.dumps([e.get('open_pub') for e in ep][-3:]),
            json.dumps(sorted((p.get('leg'), p.get('published')) for p in (s.get('pending_proposals') or []))))

def decide(checks, new, last):
    changed = (last is not None) and (_standing_key(new) != _standing_key(last))
    if checks is None: hard, soft, note = [], ['the data check did not complete'], []
    else:
        bad = [r for r in checks if r.get('status') != 'PASS']
        hard = [r['name'] for r in bad if r.get('gate') == 'hard']; soft = [r['name'] for r in bad if r.get('gate') == 'soft']
        note = [r['name'] for r in bad if r.get('gate') not in ('hard', 'soft')]
    if new is None: return 10, 'HOLD the built state cannot be read', changed
    if hard: return 10, 'HOLD %d hard failure(s): %s%s' % (len(hard), '; '.join(hard)[:400], ' | THE STANDING CHANGED IN THIS BUILD - A PERSON MUST LOOK NOW' if changed else ''), changed
    if soft and not changed: return 10, 'HOLD %d failure(s): %s' % (len(soft), '; '.join(soft)[:400]), changed
    if soft and changed: return 0, 'DEPLOY although %d check(s) failed, because the standing changed (a call is never held back by a page check): %s' % (len(soft), '; '.join(soft)[:400]), changed
    return 0, 'DEPLOY' + (' with %d advisory failure(s): %s' % (len(note), '; '.join(note)[:300]) if note else ' all checks passed') + (' | standing changed' if changed else ''), changed

if __name__ == '__main__':
    try:
        rc, line, changed = decide(_load('out/q41_data_check.json'), _load('out/bhs_state.json'), _load('cache/last_deployed_state.json'))
    except Exception as e:                       # the gate itself failed: hold, unless the standing moved
        new, last = _load('out/bhs_state.json'), _load('cache/last_deployed_state.json')
        ch = new is not None and last is not None and _standing_key(new) != _standing_key(last)
        rc, line = (0, 'DEPLOY the gate failed (%r) and the standing changed' % (e,)) if ch else (10, 'HOLD the gate failed: %r' % (e,))
    print(line); sys.exit(rc)
