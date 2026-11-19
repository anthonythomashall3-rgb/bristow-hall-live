# -*- coding: utf-8 -*-
"""THE RULE'S IDENTITY (19 November 2026). No AI, standard library only.

The forward ledger's freeze_id has read 'NO FREEZE ON FILE' since 21 September 2026: s2/freeze.py hashes the data with the
code, and the data change at every release, so no freeze could stand for more than a day. A line of the ledger therefore named
the commit that made it but not the rule, and two lines could not be seen to come from the same rule without comparing commits.

This gives each line two short identities that change only when a person changes the tool:
    rule_id    sha256 over the files that decide a call: the starter (s2/c1021.py, its real-time seasonal adjustment, its
               record of calls and of readings to the record cut), the ender (s2/e22.py and its two frozen histories) and the
               version file
    build_id   sha256 over the files that turn the calls into the published state (bhs_build.py, the damage grade, the scale)
and keeps live/RULE-IDS.jsonl, one line the first time an identity is seen, with every file's own sha256, so the ledger shows
on its face the day the rule changed and which file changed it.

    python3 s2/rule_id.py            print both identities
"""
import os, sys, json, hashlib, datetime

W = os.getcwd()
COL = os.path.dirname(W)
REG = os.path.join(COL, 'live', 'RULE-IDS.jsonl')
RULE = ['s2/c1021.py', 's2/c1021_rtsa.py', 's2/c1021_record.json', 's2/c1021_reading_record.csv',
        's2/e22.py', 's2/e22_history.csv', 's2/e22_rate_history.csv', 'cache/bhs_version.json']
BUILD = ['bhs_build.py', 's2/damage_dimensions.py', 's2/one_scale.py']


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def _id(files):
    per = {f: (sha(f) if os.path.exists(f) else 'ABSENT') for f in files}
    return hashlib.sha256(json.dumps(per, sort_keys=True).encode()).hexdigest(), per


def ids(register=True):
    """{'rule_id', 'build_id'}; with register, a first sighting of either is appended to live/RULE-IDS.jsonl"""
    rid, rper = _id(RULE); bid, bper = _id(BUILD)
    if register:
        seen = set()
        if os.path.exists(REG):
            for ln in open(REG).read().strip().splitlines():
                try: r = json.loads(ln); seen.add((r.get('rule_id'), r.get('build_id')))
                except Exception: pass
        if (rid, bid) not in seen:
            try: version = json.load(open('cache/bhs_version.json')).get('version')
            except Exception: version = None
            os.makedirs(os.path.dirname(REG), exist_ok=True)
            with open(REG, 'a') as f:
                f.write(json.dumps(dict(first_seen=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), version=version,
                                        rule_id=rid, build_id=bid, rule_files=rper, build_files=bper,
                                        commit=os.environ.get('GITHUB_SHA') or None), sort_keys=True) + '\n')
    return dict(rule_id=rid, build_id=bid)


if __name__ == '__main__':
    r = ids(register='--register' in sys.argv)
    print('rule %s  build %s' % (r['rule_id'][:16], r['build_id'][:16]))
