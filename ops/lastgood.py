#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""THE LAST GOOD CODE (ops/; 22 September 2026, collection 306).

    python3 ops/lastgood.py sha            print the commit of the last run that published (ops/state/last_good.json)
    python3 ops/lastgood.py record         after a full run that published with its own code: remember its commit
    python3 ops/lastgood.py swap-in <sha>  put back that commit's code (*.py, *.sh, requirements.txt) and every other file
                                           a person changed since (a port's version file, template, walked diary), but never
                                           data the runs write, never the published site, never ops/ or the workflow; prints
                                           how many files changed
    python3 ops/lastgood.py swap-out       put the new code back (always run before anything is committed)
The swapped files are listed in ops/out/fallback_files.txt. A swap is only ever for one run: the repository keeps the new
version, and the notification says the new version failed and the last good one published.
The commit this run started from is OPS_BASE (set by the workflow right after the checkout); HEAD otherwise."""
import datetime as dt, json, os, subprocess, sys
OPS = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(OPS)
LG = os.path.join(OPS, 'state', 'last_good.json'); LIST = os.path.join(OPS, 'out', 'fallback_files.txt')
try:
    TOOL = json.load(open(os.path.join(OPS, 'tool.json')))
except Exception:                              # a broken tool.json must never stop the fallback or the swap-out
    TOOL = {}
STATE = TOOL.get('state') or 'data/105_bristow_hall_system_2026-09-08/site/public/bhs_state.json'
SITE_PUBLIC = (TOOL.get('site_public') or 'data/105_bristow_hall_system_2026-09-08/site/public').rstrip('/')
GLOBS = TOOL.get('code_globs') or ['*.py', '*.sh', 'requirements.txt']
# THE FILES THAT MAKE A VERSION WHAT IT IS, BESIDES ITS CODE (22 September 2026, collection 306). A port changes its version
# file (cache/bhs_version.json: the walk, the diary, the version) and the page template in place; the last good code must
# run with its own, or it builds a hybrid under the new version's name. Found from the history (every file a person's
# commit changed since the last good commit, and no run wrote); these are the ones used when the history cannot be read.
VERSION_FILES = TOOL.get('version_files') or ['data/105_bristow_hall_system_2026-09-08/workspace/cache/bhs_version.json',
                                              'data/105_bristow_hall_system_2026-09-08/site/template.html',
                                              'data/105_bristow_hall_system_2026-09-08/site/template_home.html']
RUNNER = 'bristow-hall runner'            # the workflow's own commits (update.yml, "keep the built site in the repository too")


def git(*a, check=True):
    r = subprocess.run(['git'] + list(a), cwd=ROOT, capture_output=True, text=True, timeout=300)
    if check and r.returncode != 0:
        raise RuntimeError('git %s: %s' % (' '.join(a[:3]), r.stderr.strip()[:300]))
    return r


def have(sha):
    return git('cat-file', '-e', sha + '^{commit}', check=False).returncode == 0


def base():
    return os.environ.get('OPS_BASE') or git('rev-parse', 'HEAD').stdout.strip()


def in_commit(sha, f):
    return git('cat-file', '-e', '%s:%s' % (sha, f), check=False).returncode == 0


def person_changed(sha, b):
    """files changed since the last good commit `sha` (up to `b`) by commits that are not the runner's - a port, a fix -
    and never written by the runner in the same span; None when that history cannot be read"""
    try:
        return _person_changed(sha, b)
    except Exception as e:                   # a fetch that hangs or fails: the named version files are used instead
        print('ops: the history could not be read (%s)' % type(e).__name__, file=sys.stderr)
        return None


def _person_changed(sha, b):
    br = os.environ.get('GITHUB_REF_NAME') or git('rev-parse', '--abbrev-ref', 'HEAD', check=False).stdout.strip() or 'main'
    since = None
    try:
        t = dt.datetime.strptime(json.load(open(LG)).get('recorded_utc', ''), '%Y-%m-%dT%H:%M:%SZ') - dt.timedelta(days=2)
        since = t.strftime('%Y-%m-%dT%H:%M:%SZ')
    except Exception:
        pass
    if git('rev-parse', '--is-shallow-repository', check=False).stdout.strip() == 'true':
        git('fetch', '-q', ('--shallow-since=' + since) if since else '--deepen=300', 'origin', br, check=False)
    if git('merge-base', '--is-ancestor', sha, b, check=False).returncode != 0:
        return None
    r = git('log', '--format=%x00%an', '--name-only', '%s..%s' % (sha, b), check=False)
    if r.returncode != 0:
        return None
    person, runner = set(), set()
    for block in r.stdout.split('\x00')[1:]:
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        (runner if lines[0] == RUNNER else person).update(lines[1:])
    return person - runner


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'sha':
        try:
            print(json.load(open(LG)).get('sha', ''))
        except Exception:
            print('')
        return
    if cmd == 'record':
        if os.environ.get('OPS_TEST') == '1':
            print('last good: not recorded (a test run)'); return
        if (os.environ.get('BHS_MODE') or 'full') != 'full':
            print('last good: not recorded (a %s run does not run the update)' % os.environ.get('BHS_MODE')); return
        try:
            res = json.load(open(os.path.join(OPS, 'out', 'run_result.json')))
        except Exception:
            res = {}
        if (res.get('fallback') or {}).get('used'):
            print('last good: unchanged (this run published with the fallback code)'); return
        st = {}
        try:
            st = json.load(open(os.path.join(ROOT, STATE)))
        except Exception:
            pass
        doc = {'sha': base(), 'version': st.get('version'), 'built_at': st.get('built_at'),
               'run_id': os.environ.get('GITHUB_RUN_ID'), 'recorded_utc': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
               'what': 'the commit whose code last updated the site by itself; ops/run.sh falls back to it if a new version fails'}
        os.makedirs(os.path.dirname(LG), exist_ok=True)
        json.dump(doc, open(LG, 'w'), indent=1)
        print('last good: %s (%s, built %s)' % (doc['sha'][:7], doc['version'], doc['built_at']))
        return
    if cmd == 'swap-in':
        sha = sys.argv[2]
        if not have(sha):
            git('fetch', '-q', '--depth=1', 'origin', sha, check=False)
        if not have(sha):
            print('ops: the last good commit %s cannot be fetched' % sha[:7], file=sys.stderr); print(0); return
        specs = [':(glob)**/%s' % g if '/' not in g else g for g in GLOBS]
        specs += [':(exclude)ops/**', ':(exclude).github/**']
        changed = [f for f in git('diff', '--name-only', sha, 'HEAD', '--', *specs).stdout.splitlines() if f.strip()]
        # and what a person changed besides code (the version file, the template, a diary rewritten in place) - never the
        # published site, the state, the ledger, or a file a run also wrote (data)
        every = [f for f in git('diff', '--name-only', sha, 'HEAD', '--', '.', ':(exclude)ops/**', ':(exclude).github/**').stdout.splitlines() if f.strip()]
        pc = person_changed(sha, base())
        if pc is None:
            print('ops: the history since %s cannot be read: the version files named in ops/tool.json are put back with the code' % sha[:7], file=sys.stderr)
            extra = [f for f in every if f in VERSION_FILES]
        else:
            extra = [f for f in every if f in pc]
        extra = [f for f in extra if not f.startswith(SITE_PUBLIC + '/') and f != STATE and '/live/' not in '/' + f]
        changed = sorted(set(changed) | set(extra))
        swapped = []
        for f in changed:
            if in_commit(sha, f):
                git('checkout', sha, '--', f)
                swapped.append(f)
        os.makedirs(os.path.dirname(LIST), exist_ok=True)
        open(LIST, 'w').write('\n'.join(swapped) + ('\n' if swapped else ''))
        print('ops: put back %d file(s) from %s: %s' % (len(swapped), sha[:7], ', '.join(swapped[:12])), file=sys.stderr)
        print(len(swapped))
        return
    if cmd == 'swap-out':
        try:
            files = [l.strip() for l in open(LIST) if l.strip()]
        except OSError:
            files = []
        if not files:
            print('swap-out: nothing to put back'); return
        b = base()
        back, gone = [], []
        for f in files:                          # file by file: a file the new version deleted is removed again, not restored
            if in_commit(b, f):
                git('checkout', b, '--', f)
                back.append(f)
            else:
                git('rm', '-q', '--cached', '--ignore-unmatch', '--', f, check=False)
                try:
                    os.remove(os.path.join(ROOT, f))
                except OSError:
                    pass
                gone.append(f)
        left = git('diff', '--name-only', b, '--', *back).stdout.split() if back else []
        left += [f for f in gone if os.path.exists(os.path.join(ROOT, f))]
        print('swap-out: the new code is back in %d file(s)%s%s' % (len(back), ('; %d file(s) the new version removed are removed again' % len(gone)) if gone else '',
                                                                   ('; STILL DIFFERENT: ' + ', '.join(left)) if left else ''))
        if left:
            sys.exit(1)
        os.remove(LIST)
        return
    print(__doc__)


if __name__ == '__main__':
    main()
