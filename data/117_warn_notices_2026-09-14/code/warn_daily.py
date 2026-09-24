#!/usr/bin/env python3
"""THE WARN NOTICES, REFRESHED DAILY (16 September 2026). For every state in data/warn_notices/_INDEX.json, runs the
biglocalnews warn-scraper (venv at ../.venv) and replaces data/warn_notices/<st>.csv when the new file parses and is
not shorter than the old one by more than 5 per cent (a state site that answers with a stub must not erase a record);
the old file is kept in data/backup_<date>/. Then rebuilds the leg's proposals (121/code/warn_proposals.py) with a
python that has pandas ($WARN_PROPOSALS_PY, else /opt/homebrew/bin/python3, else this one). Skips the scrape when it
ran within the last 20 hours unless --force, and when another copy is running (scratch/running, under 3 hours old).
A state's scraper that overruns its time is killed with its whole process group (17 September 2026: Texas left a
child running for half an hour after the timeout). Run:  .venv/bin/python code/warn_daily.py [--force]
From 17 September 2026 the live update (105/workspace/bhs_update.py) starts this detached once a day."""
import os, sys, json, time, shutil, subprocess, datetime, csv, signal
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
W = os.path.join(HERE, 'data', 'warn_notices'); SCR = os.path.join(HERE, 'scratch'); os.makedirs(os.path.join(SCR, 'data'), exist_ok=True); os.makedirs(os.path.join(SCR, 'cache'), exist_ok=True)
STAMP = os.path.join(SCR, 'last_scrape'); today = datetime.date.today().isoformat()
BK = os.path.join(HERE, 'data', 'backup_' + today)
VENV = os.path.join(HERE, '.venv', 'bin', 'warn-scraper')
def say(*a): print(' '.join(str(x) for x in a), flush=True)
RUN = os.path.join(SCR, 'running')
if '--force' not in sys.argv and os.path.exists(STAMP) and time.time() - os.path.getmtime(STAMP) < 20 * 3600:
    say('warn: scraped within 20 h; skipping'); sys.exit(0)
if os.path.exists(RUN) and time.time() - os.path.getmtime(RUN) < 3 * 3600:
    say('warn: another copy is running (scratch/running); skipping'); sys.exit(0)
open(RUN, 'w').write(str(os.getpid()))
say('warn: scrape started', datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
SLOW = {'tx': 900, 'ca': 900, 'il': 900}   # seconds a state may take; the rest get 420
def run_killable(cmd, timeout):
    """like subprocess.run(capture_output=True, timeout=...) but the whole process group dies on timeout"""
    pr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try: out, err = pr.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try: os.killpg(os.getpgid(pr.pid), signal.SIGKILL)
        except Exception: pr.kill()
        try: pr.communicate(timeout=30)
        except Exception: pass
        raise
    return subprocess.CompletedProcess(cmd, pr.returncode, out, err)
IDX = json.load(open(os.path.join(W, '_INDEX.json')))
ok = fail = kept = 0
for rec in IDX:
    st = rec['state'].lower(); old = os.path.join(W, st + '.csv'); new = os.path.join(SCR, 'data', st + '.csv')
    try:
        if os.path.exists(new): os.remove(new)
        r = run_killable([VENV, '--data-dir', os.path.join(SCR, 'data'), '--cache-dir', os.path.join(SCR, 'cache'), '-l', 'error', st], SLOW.get(st, 420))
        if not os.path.exists(new): say(f'warn {st.upper()}: no file ({r.stderr.strip()[-100:]})'); fail += 1; continue
        n_new = sum(1 for _ in open(new, encoding='utf-8', errors='ignore')) - 1
        n_old = (sum(1 for _ in open(old, encoding='utf-8', errors='ignore')) - 1) if os.path.exists(old) else 0
        if n_new < 0.95 * n_old: say(f'warn {st.upper()}: new file {n_new} rows < 95% of old {n_old}; kept old'); kept += 1; continue
        with open(new, encoding='utf-8', errors='ignore') as fh: hdr = next(csv.reader(fh))
        if not any(h.strip().lower() == rec['col'].strip().lower() for h in hdr): say(f'warn {st.upper()}: column {rec["col"]!r} missing in new file; kept old'); kept += 1; continue
        if os.path.exists(old): os.makedirs(BK, exist_ok=True); shutil.copy2(old, os.path.join(BK, st + '.csv'))
        shutil.copy2(new, old); rec['to'] = today; rec['n'] = n_new; ok += 1
        say(f'warn {st.upper()}: {n_old} -> {n_new} rows')
    except subprocess.TimeoutExpired: say(f'warn {st.upper()}: timeout'); fail += 1
    except Exception as e: say(f'warn {st.upper()}: {type(e).__name__} {str(e)[:100]}'); fail += 1
json.dump(IDX, open(os.path.join(W, '_INDEX.json'), 'w'), indent=1)
open(STAMP, 'w').write(today)
say(f'warn: {ok} states refreshed, {kept} kept old, {fail} failed')
def py_with_pandas():
    for c in [os.environ.get('WARN_PROPOSALS_PY'), '/opt/homebrew/bin/python3', '/usr/local/bin/python3', shutil.which('python3'), sys.executable]:
        if c and os.path.exists(c) and subprocess.run([c, '-c', 'import numpy, pandas'], capture_output=True).returncode == 0: return c
    return sys.executable
try:
    r = subprocess.run([py_with_pandas(), os.path.join(ROOT, '121_warn_causal_breadth_2026-09-14', 'code', 'warn_proposals.py')], capture_output=True, text=True, timeout=1800)
    say('warn proposals:', (r.stdout.strip().splitlines() or [r.stderr.strip()[-160:]])[-1] if r.returncode == 0 else 'FAILED ' + r.stderr.strip()[-200:])
except Exception as e: say(f'warn proposals: FAILED ({type(e).__name__} {str(e)[:120]})')
finally:
    try: os.remove(RUN)
    except Exception: pass
say('warn: done', datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
