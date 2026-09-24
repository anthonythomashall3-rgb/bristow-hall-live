# -*- coding: utf-8 -*-
"""THE FORWARD LEDGER (18 September 2026; collection 202; open-register item 24, work order 0.1).

Every test of the rule that can be run on the past can also be fitted to the past. The forward record cannot. This
appends one line per run to an append-only file, so that what the rule said on a day is fixed on that day and can be
shown later to have been said then:

    live/FORWARD-LEDGER.jsonl     one JSON object per line, never rewritten:
      at              the moment this line was written (UTC)
      built_at        the build's own stamp
      version, walk   the rule of record
      freeze_id       the freeze the running files match (or 'DRIFTED' with the count, from s2/freeze.py --check)
      standing        state, since, dated, leg
      reading         the day's reading and the branch carrying it
      through         the last observation of each object the rule reads
      pending         every leg proposal outstanding, with its lapse date
      state_sha256    the sha256 of out/bhs_state.json, which fixes every number in the build
      archive         the Internet Archive capture asked for, and what it answered

No AI, standard library only. Idempotent within a build: a second run on the same built_at appends nothing.

Run from the workspace (bhs_run.sh calls it after a successful deploy):
    python3 s2/ledger.py                 append the day's line and ask for a capture
    python3 s2/ledger.py --no-archive    append only
    python3 s2/ledger.py --tail 5        print the last five lines
"""
import os, sys, json, hashlib, datetime, subprocess

W = os.getcwd()
COL = os.path.dirname(W)
LEDGER = os.path.join(COL, 'live', 'FORWARD-LEDGER.jsonl')
STATE = os.path.join('out', 'bhs_state.json')
SITE = 'https://bhrrealtime.pages.dev'
CAPTURE = [SITE + '/bhs_state.json', SITE + '/detector/']


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def archive(url, timeout=90):
    """ask the Internet Archive to capture the page; return the capture's URL or the reason it did not.

    Save Page Now stopped answering anonymous callers (HTTP 500) in 2026; with an archive.org S3 key in local.env
    (ARCHIVE_S3_ACCESS and ARCHIVE_S3_SECRET, free from https://archive.org/account/s3.php) it answers again. The
    timestamp the record actually rests on is the OpenTimestamps receipt below, which needs no account and no trust."""
    hdr = ['-A', 'bristow-hall-rule forward ledger (research; one capture a day)']
    env = os.path.join(os.path.expanduser('~/mnt/Onset Detector Data'), 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env')
    try:
        if os.path.exists(env):
            kv = dict(l.strip().split('=', 1) for l in open(env) if '=' in l and not l.startswith('#'))
            a, s = kv.get('ARCHIVE_S3_ACCESS', '').strip('"\''), kv.get('ARCHIVE_S3_SECRET', '').strip('"\'')
            if a and s: hdr += ['-H', 'Authorization: LOW %s:%s' % (a, s)]
    except Exception: pass
    try:
        r = subprocess.run(['curl', '-sS', '-m', str(timeout), '-o', '/dev/null', '-D', '-'] + hdr +
                           ['https://web.archive.org/save/' + url], capture_output=True, text=True)
        if r.returncode != 0: return {'url': url, 'ok': False, 'why': (r.stderr or 'curl failed').strip()[:120]}
        loc = ''
        for ln in r.stdout.splitlines():
            k = ln.split(':', 1)
            if len(k) == 2 and k[0].strip().lower() in ('content-location', 'location'): loc = k[1].strip()
        code = next((ln.split()[1] for ln in r.stdout.splitlines() if ln.startswith('HTTP/')), '?')
        return {'url': url, 'ok': code in ('200', '302'), 'http': code,
                'capture': ('https://web.archive.org' + loc) if loc.startswith('/web/') else loc}
    except Exception as e:
        return {'url': url, 'ok': False, 'why': type(e).__name__}


def timestamp(line, at, state_sha):
    """A third-party timestamp on the day's record that needs no account and no one's good faith: the receipt is
    written to live/ots/ and stamped with OpenTimestamps, which anchors its hash in the Bitcoin chain. Afterwards
    `ots verify live/ots/<file>.ots` shows the block, and so the day the rule said this, to anyone, for ever.
    Upgrade the receipts when the block has settled (a few hours):  ots upgrade live/ots/*.ots"""
    d = os.path.join(COL, 'live', 'ots'); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, '%s-%s.json' % (at.replace(':', '').replace('-', ''), state_sha[:8]))
    open(p, 'w').write(line + '\n')
    try:
        r = subprocess.run(['ots', 'stamp', p], capture_output=True, text=True, timeout=180)
        ok = os.path.exists(p + '.ots')
        return {'receipt': os.path.relpath(p, COL), 'ots': ok,
                'calendars': [l.split()[-1] for l in (r.stderr + r.stdout).splitlines() if 'Submitting to remote calendar' in l],
                'why': '' if ok else ((r.stderr or r.stdout).strip()[-120:] or 'ots produced no receipt')}
    except FileNotFoundError:
        return {'receipt': os.path.relpath(p, COL), 'ots': False, 'why': 'the ots client is not installed (pip3 install opentimestamps-client)'}
    except Exception as e:
        return {'receipt': os.path.relpath(p, COL), 'ots': False, 'why': type(e).__name__}


def freeze_state():
    try:
        r = subprocess.run([sys.executable, os.path.join('s2', 'freeze.py'), '--check'], capture_output=True, text=True, timeout=300)
        last = [l for l in r.stdout.strip().splitlines() if l.startswith('freeze ')]
        if not last: return 'NO FREEZE ON FILE'
        if ': 0 file(s) differ' in last[-1]:
            fs = sorted(__import__('glob').glob(os.path.join(COL, 'freeze', 'FREEZE-*.json')))
            return json.load(open(fs[-1]))['freeze_id'] if fs else 'UNKNOWN'
        return 'DRIFTED: ' + last[-1].split(': ', 1)[1]
    except Exception as e:
        return 'CHECK FAILED: ' + type(e).__name__


def main():
    if '--tail' in sys.argv:
        n = int(sys.argv[sys.argv.index('--tail') + 1])
        for ln in (open(LEDGER).read().strip().splitlines() if os.path.exists(LEDGER) else [])[-n:]:
            r = json.loads(ln)
            print('%s  %-6s  %-7s %-10s  reading %-6s  %s' % (r['at'], r.get('version'), (r.get('standing') or {}).get('state'),
                  (r.get('standing') or {}).get('since'), r.get('reading'), r.get('state_sha256', '')[:12]))
        return 0

    s = json.load(open(STATE))
    built_at = s.get('built_at')
    if os.path.exists(LEDGER):
        for ln in open(LEDGER).read().strip().splitlines()[-5:]:
            try:
                if json.loads(ln).get('built_at') == built_at:
                    print('forward ledger: this build (%s) is already on file' % built_at); return 0
            except Exception: pass

    se = s.get('series') or {}
    vals = se.get('values') or []
    rec = {
        'at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'built_at': built_at, 'built': s.get('built'), 'version': s.get('version'), 'walk': s.get('walk'),
        'freeze_id': freeze_state(),
        'standing': s.get('standing'),
        'reading': (round(float(vals[-1]), 4) if vals else None),
        'reading_day': (se.get('dates') or [None])[-1],
        'branch': (se.get('branch') or [None])[-1],
        'phase': (se.get('phase') or [None])[-1],
        # the old guard was d[-1] == d[-1], the NaN test. Once bhs_build writes non-finite values as null (18 Sep)
        # that test passes for None and float(None) raises, so the guard is on the type instead.
        'damage': (lambda d: (round(float(d[-1]), 4) if d and isinstance(d[-1], (int, float)) else None))(se.get('damage') or []),
        'through': s.get('through'),
        'pending': s.get('pending_proposals') or [],
        'episodes': len(s.get('episodes') or []),
        'state_sha256': sha(STATE),
    }
    if '--no-archive' not in sys.argv:
        rec['archive'] = [archive(u) for u in CAPTURE]
        rec['timestamp'] = timestamp(json.dumps(dict(rec, timestamp=None), sort_keys=True), rec['at'], rec['state_sha256'])

    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    try:                              # the file is left read-only between runs, so that nothing edits it by accident
        if os.path.exists(LEDGER): os.chmod(LEDGER, 0o644)
    except Exception: pass
    with open(LEDGER, 'a') as f:
        f.write(json.dumps(rec, sort_keys=True) + '\n')
    try: os.chmod(LEDGER, 0o444)      # append-only by convention; a line already written is never rewritten
    except Exception: pass
    caps = [a.get('capture') for a in rec.get('archive', []) if a.get('ok') and a.get('capture')]
    ts = rec.get('timestamp') or {}
    print('forward ledger: %s | %s %s | reading %s | state %s | timestamped %s | captures %d' % (
        rec['at'], (rec['standing'] or {}).get('state'), (rec['standing'] or {}).get('since'),
        rec['reading'], rec['state_sha256'][:12], ('yes, %d calendars' % len(ts.get('calendars') or [])) if ts.get('ots') else 'NO', len(caps)))
    for c in caps: print('  ', c)
    if ts and not ts.get('ots'): print('   no timestamp:', ts.get('why'))
    elif ts.get('ots'): print('  ', ts['receipt'] + '.ots')
    if isinstance(rec['freeze_id'], str) and rec['freeze_id'].startswith(('DRIFTED', 'NO FREEZE', 'CHECK FAILED')):
        print('  freeze:', rec['freeze_id'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
