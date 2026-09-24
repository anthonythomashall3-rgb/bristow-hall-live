#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ONE PHONE NOTIFICATION FOR EVERY UPDATE (ops/; 22 September 2026, collection 306).

Anthony, 22 September 2026: "I want nefy to send me a notification for each update, including successful ones, and what
it updated ... I need to know exactly what updated on the ntfy alerts, for example S&P 500 close: updated from x -> y ...
I dont want the updates being too lengthy".

The last step of every update run that did work (never a GitHub firing that found the site current). Short, one fact a line:
  Updated · indicator 0.433 -> 0.441
  5:07 PM ET · for the S&P 500 close · no recession called · v3.70
  S&P 500 close: 7,764.70 -> 7,801.23 (Sep 22)            every series the data page shows that moved, old -> new
  Not posted yet: weekly claims (due 8:30 AM ET); looking again at 9:20 AM ET      (only when something is late)
  Next data: weekly claims Thu Sep 24 8:30 AM ET · next update tomorrow 8:50 AM ET
A failure or a hold says where, the error, that the site still shows the last good build, and when it tries again; it is
also a GitHub issue (email), closed by the next good run. A recession called or closed goes at the highest priority. Reads
only what any version publishes (ops/tool.json; ops/README.md, "The contract"): what a version lacks is left out, never a
reason not to send.

    python3 ops/notify.py            (from the repository root; the workflow sets the environment)
    python3 ops/notify.py --dry      print the message instead of sending it
"""
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')
UTC = dt.timezone.utc
OPS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(OPS)
DEFAULT_TOOL = {'workspace': 'data/105_bristow_hall_system_2026-09-08/workspace',
                'site_public': 'data/105_bristow_hall_system_2026-09-08/site/public',
                'state': 'data/105_bristow_hall_system_2026-09-08/site/public/bhs_state.json',
                'data_page': 'data/105_bristow_hall_system_2026-09-08/site/public/data/index.html',
                'run_slots': 'data/105_bristow_hall_system_2026-09-08/site/public/run_slots.json',
                'run_log': 'run.log', 'site_url': 'https://bhrrealtime.pages.dev',
                'indicator_url': 'https://bhrrealtime.pages.dev/detector/'}
try:
    TOOL = dict(DEFAULT_TOOL, **json.load(open(os.path.join(OPS, 'tool.json'))))
except Exception:                              # a broken tool.json must never silence the message
    TOOL = dict(DEFAULT_TOOL)
E = os.environ.get
DRY = '--dry' in sys.argv


def jload(p, default=None):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default


def git_json(sha, rel):
    try:
        out = subprocess.run(['git', 'show', '%s:%s' % (sha, rel)], cwd=ROOT, capture_output=True, timeout=60)
        return json.loads(out.stdout.decode('utf-8')) if out.returncode == 0 else None
    except Exception:
        return None


def ny(s):
    """'YYYY-MM-DD HH:MM' (New York) -> aware datetime"""
    try:
        return dt.datetime.strptime(s[:16], '%Y-%m-%d %H:%M').replace(tzinfo=ET)
    except Exception:
        return None


def when(t, now):
    if t is None:
        return '?'
    d = t.date()
    day = 'today' if d == now.date() else ('tomorrow' if d == now.date() + dt.timedelta(days=1) else t.strftime('%a %b ') + str(t.day))
    return '%s %s ET' % (day, t.strftime('%I:%M %p').lstrip('0'))


def day_label(s, monthly=False):
    try:
        d = dt.date.fromisoformat(s[:10]) if len(s) >= 10 else dt.date.fromisoformat(s[:7] + '-01')
    except Exception:
        return s
    if monthly or len(s) == 7:
        return d.strftime('%b %Y')
    return d.strftime('%b ') + str(d.day)


def short_name(n):
    n = re.sub(r'\s*\(.*$', '', n or '').strip()
    return n[:60]


def norm(s):
    return re.sub(r'\s+', ' ', (s or '').strip().lower())


def indicator(st):
    """(value, date) of the headline reading, from what the tool publishes"""
    if not st:
        return None, None
    s = st.get('series') or {}
    ds, vs = s.get('dates') or [], s.get('values') or s.get('reading') or []
    for d, v in zip(reversed(ds), reversed(vs)):
        if isinstance(v, (int, float)):
            return float(v), d
    h = st.get('headline') or {}
    if isinstance(h.get('value'), (int, float)):
        return float(h['value']), h.get('date')
    return None, None


def standing_short(sd):
    s = ((sd or {}).get('state') or '').lower()
    if s == 'open':
        return 'RECESSION CALLED (open since %s)' % day_label((sd or {}).get('since') or '')
    if s == 'closed':
        return 'no recession called'
    return None


# ---- what changed on the site: the data page, before and after, series by series --------------------------------
TR_RE = re.compile(r'<tr\b([^>]*\bdata-ids=[^>]*)>(.*?)</tr>', re.S | re.I)
ATTR_RE = re.compile(r'data-([a-z]+)="([^"]*)"', re.I)
LABELS = {'ICSA': 'Initial claims', 'CCSA': 'Continued claims', 'IURSA': 'Insured unemployment rate',
          'UNRATE': 'Unemployment rate', 'AWHMAN': 'Factory hours', 'NDMANEMP': 'Nondurable jobs (thousands)',
          'PAYEMS': 'Payrolls', 'JTSJOL': 'Job openings (thousands)', 'CLF16OV': 'Labor force (thousands)',
          'JTSQUR': 'Quits rate', 'HOUST': 'Housing starts (thousands, annual rate)', 'PERMIT': 'Building permits (thousands)',
          'INDPRO': 'Industrial production', 'CPIAUCSL': 'CPI inflation (a year)', 'CFNAIMA3': 'Chicago Fed index (3-month)',
          'SAHMREALTIME': 'Sahm rule (real time)', 'DFEDTARU': 'Fed funds target (upper)', '^GSPC': 'S&P 500 close',
          'DCPF1M': 'AA financial paper, 1 month', 'DCPN30': 'AA nonfinancial paper, 30 days', 'WTB3MS': '3-month bill (week)'}
PCT = {'UNRATE', 'IURSA', 'JTSQUR', 'CPIAUCSL', 'DFEDTARU', 'DCPF1M', 'DCPN30', 'WTB3MS'}


def page_items(text):
    """{key: (label, value, through, attr-ids)} for every series the data page shows"""
    out = {}
    for m in TR_RE.finditer(text or ''):
        a = {k.lower(): html.unescape(v) for k, v in ATTR_RE.findall(m.group(1))}
        body = m.group(2)
        idc = re.search(r'<td class="id">(.*?)</td>', body, re.S)
        ids = html.unescape(re.sub('<[^>]+>', '', idc.group(1))).strip() if idc else a.get('ids', '')
        nm = re.search(r'<a [^>]*>(.*?)</a>', body, re.S)
        name = html.unescape(re.sub('<[^>]+>', '', nm.group(1))).replace('↗', '').strip() if nm else a.get('name', '')
        toks = [t.strip() for t in re.split(r',|/', ids) if t.strip()]
        vals = [v.strip() for v in a.get('value', '').split(';')]
        thr, aid = a.get('through', ''), norm(a.get('ids', ''))
        if len(toks) > 1 and len(toks) == len(vals):
            for t, v in zip(toks, vals):
                k = t.upper()
                out.setdefault(k, (LABELS.get(k, t), v + ('%' if k in PCT and v and not v.endswith('%') else ''), thr, aid))
        else:
            k = (toks[0].upper() if len(toks) == 1 else name.lower()) or name.lower()
            if k.startswith('GOOGLE TRENDS'):
                label = 'Searches ' + ids.split(' ', 2)[-1]
            else:
                label = LABELS.get(k) or short_name(name)
            v = a.get('value', '')
            out.setdefault(k, (label, v + ('%' if k in PCT and v and not v.endswith('%') else ''), thr, aid))
    return out


def period(thr, freq):
    if not thr:
        return ''
    if freq == 'monthly' or len(thr) == 7:
        return day_label(thr, monthly=True)
    if freq == 'weekly':
        return 'week to ' + day_label(thr)
    return day_label(thr)


def changes(new_text, old_text, cal):
    freq = {r['ids']: r.get('freq') for r in (cal or {}).get('rows') or []}
    new, old = page_items(new_text), page_items(old_text)
    out = []
    for k, (label, v, thr, aid) in new.items():
        o = old.get(k)
        p = period(thr, freq.get(aid))
        if o is None:
            out.append('%s: %s (%s), new on the site' % (label, v, p))
        elif v != o[1]:
            out.append('%s: %s → %s%s' % (label, o[1] or '?', v, (' (%s)' % p) if p else ''))
        elif thr != o[2] and freq.get(aid) in ('weekly', 'monthly'):
            # a new week or month is news even at the same value; a daily series whose value did not move is not
            out.append('%s: %s, %s (unchanged)' % (label, v, p))
    return out


def next_slot(slots, now, containing=None):
    for s in (slots or {}).get('slots') or []:
        t = ny(s.get('ny') or '')
        if t and t > now and (containing is None or any(containing in w for w in s.get('why') or [])):
            return t, re.sub(r'\s*\(.*$', '', (s.get('why') or [''])[0])
    return None, None


def slot_reason(slots_old, slot, now):
    """why the run happened: the reasons the schedule gave for the slot it was started for"""
    for s in (slots_old or {}).get('slots') or []:
        if s.get('ny') == slot:
            return '; '.join(re.sub(r'\s*\(.*$', '', w) for w in (s.get('why') or [])[:2])
    return ''


def due_slot(slots_old, now):
    """the last slot of the published schedule that has passed (what a GitHub firing was started for)"""
    past = [s.get('ny') for s in (slots_old or {}).get('slots') or [] if ny(s.get('ny') or '') and ny(s.get('ny')) <= now]
    return max(past) if past else ''


def tries_for(slot_ny):
    """how many runs on main have tried this slot, this one included (the Cloudflare starter makes up to three, and does
    not count a GitHub firing that found nothing to do), or None when GitHub cannot be asked"""
    t = ny(slot_ny or '')
    if not t or not E('GH_TOKEN') or not E('GITHUB_REPOSITORY'):
        return None
    try:
        since = t.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
        req = urllib.request.Request('https://api.github.com/repos/%s/actions/workflows/update.yml/runs?branch=main&per_page=30&created=%%3E%%3D%s'
                                     % (E('GITHUB_REPOSITORY'), since),
                                     headers={'Authorization': 'Bearer ' + E('GH_TOKEN'), 'Accept': 'application/vnd.github+json',
                                              'User-Agent': 'bhr-ops-notify'})
        with urllib.request.urlopen(req, timeout=20) as r:
            runs = json.load(r).get('workflow_runs', [])
        return max(1, len([x for x in runs if not (x.get('event') == 'schedule' and x.get('conclusion') == 'success')]))
    except Exception:
        return None


def next_data(cal, now, k=1):
    best = []
    for r in (cal or {}).get('rows') or []:
        src = r.get('source') or ''
        if 'nyse_close' in src or 'daily_next' in src:
            continue
        t = next((x for x in r.get('times') or [] if ny(x['ny']) and ny(x['ny']) > now), None)
        if t:
            best.append((ny(t['ny']), r.get('short') or short_name(r.get('name')), r.get('time_known'), t.get('expected'), r.get('time_note')))
    best.sort(key=lambda x: x[0])
    out, seen = [], set()
    for t, name, known, exp, note in best:
        if name in seen:
            continue
        seen.add(name)
        out.append((t, '%s %s%s%s' % (name, when(t, now) if known else t.strftime('%a %b ') + str(t.day),
                                      (' (%s)' % note) if note else '', ' (expected)' if exp else '')))
        if len(out) >= k:
            break
    return out


def log_tail(n=4):
    try:
        lines = [l.rstrip() for l in open(os.path.join(ROOT, TOOL.get('run_log', 'run.log')), errors='replace') if l.strip()]
    except OSError:
        return ''
    keep = [l for l in lines if not l.startswith(('  warnings.warn', 'DeprecationWarning'))][-n:]
    return ' | '.join(x[-220:] for x in keep)


def gate_line():
    try:
        for l in reversed(open(os.path.join(ROOT, TOOL.get('run_log', 'run.log')), errors='replace').read().splitlines()):
            if l.startswith(('DEPLOY', 'HOLD')):
                return l.strip()
    except OSError:
        pass
    return ''


def send(topic, title, body, prio, tags, click):
    if DRY or not topic:
        print('--- %s [prio %s, tags %s]\n%s\n---' % (title, prio, tags, body))
        return True
    doc = {'topic': topic, 'title': title, 'message': body[:3900], 'priority': prio, 'tags': tags, 'click': click}
    runurl = run_url()
    if runurl:
        doc['actions'] = [{'action': 'view', 'label': 'Run log', 'url': runurl}, {'action': 'view', 'label': 'Site', 'url': click}]
    for i in range(4):
        try:
            req = urllib.request.Request('https://ntfy.sh/', data=json.dumps(doc).encode('utf-8'),
                                         headers={'Content-Type': 'application/json', 'User-Agent': 'bhr-ops-notify'})
            with urllib.request.urlopen(req, timeout=20) as r:
                r.read()
            return True
        except Exception as e:
            print('ntfy send failed (%s), try %d' % (type(e).__name__, i + 1))
            time.sleep(3 + 5 * i)
    return False


def run_url():
    if E('GITHUB_RUN_ID'):
        return '%s/%s/actions/runs/%s' % (E('GITHUB_SERVER_URL', 'https://github.com'), E('GITHUB_REPOSITORY', ''), E('GITHUB_RUN_ID'))
    return ''


def gh_issue(kind, title, body, close_on_ok=False):
    """the second channel: a GitHub issue (GitHub emails it). One a day per kind; on success, the day's are closed."""
    if DRY or E('OPS_TEST') == '1' or not E('GH_TOKEN'):
        return
    repo = E('GITHUB_REPOSITORY', '')
    try:
        found = json.loads(subprocess.run(['gh', 'issue', 'list', '-R', repo, '--state', 'open', '--search', 'UPDATE in:title',
                                           '--json', 'number,title', '-L', '50'], capture_output=True, timeout=60).stdout or b'[]')
    except Exception:
        found = []
    ours = [i for i in found if i.get('title', '').startswith(('[UPDATE FAILED]', '[UPDATE HELD]'))]
    if close_on_ok:
        for i in ours:
            subprocess.run(['gh', 'issue', 'close', str(i['number']), '-R', repo, '-c', body], capture_output=True, timeout=60)
        return
    today = dt.datetime.now(ET).strftime('%Y-%m-%d')
    same = [i for i in ours if i['title'].startswith('[UPDATE %s] %s' % (kind, today))]
    if same:
        subprocess.run(['gh', 'issue', 'comment', str(same[0]['number']), '-R', repo, '-b', body], capture_output=True, timeout=60)
    else:
        subprocess.run(['gh', 'issue', 'create', '-R', repo, '-t', '[UPDATE %s] %s %s' % (kind, today, title), '-b', body],
                       capture_output=True, timeout=60)


def git_text(sha, rel):
    try:
        out = subprocess.run(['git', 'show', '%s:%s' % (sha, rel)], cwd=ROOT, capture_output=True, timeout=60)
        return out.stdout.decode('utf-8', 'replace') if out.returncode == 0 else ''
    except Exception:
        return ''


def live_check(built_at):
    """the live site carries this build (Cloudflare can take a few seconds)"""
    for i in range(4):
        try:
            req = urllib.request.Request('%s/run_slots.json?t=%d' % (TOOL.get('site_url'), time.time()), headers={'User-Agent': 'bhr-ops-notify'})
            with urllib.request.urlopen(req, timeout=20) as r:
                if json.loads(r.read().decode('utf-8')).get('built_at') == built_at:
                    return True
        except Exception:
            pass
        time.sleep(10)
    return False


def main():
    now = dt.datetime.now(ET)
    sha = E('OPS_BASE') or E('GITHUB_SHA') or 'HEAD'
    new = jload(os.path.join(ROOT, TOOL['state']))
    old = git_json(sha, TOOL['state']) or jload(os.path.join(ROOT, TOOL['workspace'], 'cache', 'last_deployed_state.json'))
    cal = jload(os.path.join(ROOT, TOOL['site_public'], 'ops', 'release_calendar.json'))
    slots = jload(os.path.join(ROOT, TOOL['run_slots']))
    slots_old = git_json(sha, TOOL['run_slots'])
    pdoc = jload(os.path.join(OPS, 'state', 'pending.json'), {}) or {}
    pend = pdoc.get('pending', [])
    expired = [x for x in pdoc.get('expired', []) if (x.get('expired_ny') or '')[:10] == now.strftime('%Y-%m-%d')]
    res = jload(os.path.join(OPS, 'out', 'run_result.json'), {}) or {}
    o_main, o_gate, o_pub, o_push = E('OUT_MAIN', ''), E('OUT_GATE', ''), E('OUT_PUBLISH', ''), E('OUT_PUSH', '')
    o_setup = E('OUT_SETUP', 'success')
    job = E('JOB_STATUS', '')
    origin, slot, event = E('OPS_ORIGIN', ''), E('OPS_SLOT', ''), E('GITHUB_EVENT_NAME', '')
    test = E('OPS_TEST') == '1'
    site = TOOL.get('indicator_url') or TOOL.get('site_url')
    fb = res.get('fallback') or {}

    if o_main == 'success' and o_gate in ('success', 'skipped') and o_pub == 'success':
        status = 'OK_FALLBACK' if fb.get('used') and fb.get('rc') == 0 else 'OK'
    elif o_main == 'success' and o_gate == 'failure':
        status = 'HELD' if gate_line().startswith('HOLD') else 'FAILED'
    else:
        status = 'FAILED'
    if job == 'cancelled' and status != 'OK':
        status = 'FAILED'

    if event == 'push':
        why = 'new code pushed (%s)' % (E('OPS_COMMIT_MSG', '').splitlines() or [''])[0][:60]
    elif origin == 'push-recovery':
        why = "new code (its first run was dropped from GitHub's queue)"
    elif origin == 'slot' and slot:
        why = 'for ' + (slot_reason(slots_old, slot, now) or ('the %s slot' % slot[11:]))
    elif event == 'schedule':
        why = "GitHub's backup start (the starter missed a slot)"
    else:
        why = 'started by hand'

    def stamp(t):
        return (t.strftime('%I:%M %p').lstrip('0') + ' ET') if t else '?'

    lines, prio, tags = [], 3, []
    retrying = False
    lv, _ = indicator(new)
    olv, _ = indicator(old)
    ver, over = (new or {}).get('version'), (old or {}).get('version')
    built = ny((new or {}).get('built_at') or '')
    sd_new, sd_old = (new or {}).get('standing') or {}, (old or {}).get('standing') or {}
    standing_changed = bool(sd_new and sd_old and (sd_new.get('state'), sd_new.get('since')) != (sd_old.get('state'), sd_old.get('since')))

    if status in ('OK', 'OK_FALLBACK'):
        if lv is not None and olv is not None and abs(lv - olv) >= 0.0005:
            ind = 'indicator %.3f → %.3f' % (olv, lv)
        elif lv is not None:
            ind = 'indicator %.3f, no change' % lv
        else:
            ind = 'indicator n/a'
        title = 'Updated · ' + ind
        tags = ['white_check_mark']
        if status == 'OK_FALLBACK':
            title = 'Updated with the previous version · ' + ind
            tags, prio = ['warning'], 4
            lines.append('The new code (commit %s) failed, so %s ran instead and the data are current. Needs fixing: %s'
                         % (fb.get('failed_version') or '?', fb.get('version') or 'the last good version', (fb.get('primary_error') or '?')[:160]))
        head = [stamp(built or now), why]
        stx = standing_short(sd_new)
        if stx:
            head.append(stx)
        head.append(ver or '?')
        lines.insert(0, ' · '.join(head))
        if ver and over and ver != over:
            lines.append('NEW VERSION LIVE: %s → %s' % (over, ver))
        if res.get('attempts', 1) > 1 and not fb.get('used'):
            lines.append('(needed a second try; the first failed: %s)' % (res.get('first_error') or 'see the run log')[:120])
        ch = changes(open(os.path.join(ROOT, TOOL['data_page']), encoding='utf-8').read() if os.path.exists(os.path.join(ROOT, TOOL['data_page'])) else '',
                     git_text(sha, TOOL['data_page']), cal)
        if ch:
            lines += ch[:7]
            if len(ch) > 7:
                lines.append('+%d more on the data page' % (len(ch) - 7))
        else:
            lines.append('No new data this run.')
        for p in pend[:3]:
            t_look, _ = next_slot(slots, now, 'look again: ' + p['short'])
            lines.append('Not posted yet: %s (due %s)%s' % (p['short'], when(ny(p['due_ny']), now),
                                                          ('; looking again %s' % when(t_look, now)) if t_look else '; looked for at every update'))
        for p in expired[:2]:
            lines.append('Still not published a week after its day: %s (due %s). The agency may have cancelled or moved it; it is no longer waited for.' % (p['short'], p['due_ny']))
        exp = sorted({r.get('short') for r in (cal or {}).get('rows') or [] if r.get('next_expected')})
        if exp:
            lines.append('Projected, not yet official: the next %s (the agency has not published it; checked daily)' % ', '.join(exp[:3]))
        nd = next_data(cal, now)
        t_next, _ = next_slot(slots, now)
        if nd:
            lines.append('Next data: %s%s' % (nd[0][1], (' · next update %s' % when(t_next, now)) if t_next else ''))
        elif t_next:
            lines.append('Next update: %s' % when(t_next, now))
        if standing_changed:
            prio, tags = 5, ['rotating_light']
            title = ('RECESSION CALLED by the Bristow-Hall Rule' if sd_new.get('state') == 'open' else 'The Bristow-Hall Rule closed the recession') + ' · ' + ind
    else:
        prio = 4
        tags = ['x'] if status == 'FAILED' else ['warning']
        shown = ny((old or {}).get('built_at') or '')
        where = 'the checks (deploy gate)' if status == 'HELD' else (
            'setting up the runner' if o_main in ('', 'skipped') and o_setup != 'success' else
            'update, build, site' if o_main != 'success' else
            'the checks (the data check crashed)' if o_gate == 'failure' else
            'publishing to Cloudflare' if o_pub != 'success' else 'a later step')
        if job == 'cancelled':
            where += ' (stopped: time limit or cancelled)'
        # A SLOT'S RUN THAT FAILS IS STARTED AGAIN BY ITSELF (the Cloudflare starter: up to three runs for one release, about
        # ten minutes apart), so the first and second say so plainly; only a failure nothing will retry is "FAILED"
        # (22 September 2026, collection 306; Anthony: "I SHOULD NEVER GET A NOTIFICATION THAT THE AUTOMATIC UPDATING
        # FEATURE HAS FAILED" - a failure that is being handled is not a failure of the updating)
        t_next, _ = next_slot(slots_old or slots, now)
        tries = None
        if status == 'FAILED' and not test and (origin == 'slot' or event == 'schedule'):
            tries = tries_for(slot if (origin == 'slot' and slot) else due_slot(slots_old or slots, now))
        retrying = tries is not None and tries < 3
        if status == 'HELD':
            title = 'Update HELD by the checks · site unchanged'
        elif retrying:
            title = 'Update did not go through · retrying by itself · site unchanged'
            prio, tags = 3, ['hourglass']
        else:
            title = 'Update FAILED · site unchanged'
        lines.append('%s · %s · failed at: %s%s' % (stamp(now), why, where, (' (%d tries)' % res['attempts']) if res.get('attempts', 1) > 1 else ''))
        if status == 'HELD':
            lines.append('The checks said: ' + (gate_line() or '?')[:220])
        else:
            err = res.get('error') or log_tail(2)
            if err:
                lines.append('Error: ' + err[:260])
        if fb.get('tried'):
            lines.append('The last good version (%s) failed too.' % (fb.get('version') or (fb.get('sha') or '')[:7]))
        lines.append('The site still shows the %s build (indicator %s). Nothing wrong was published.' % (
            stamp(shown) if shown else 'last', ('%.3f' % olv) if olv is not None else 'n/a'))
        nxt = when(t_next, now) if t_next else 'the next scheduled update'
        if status == 'HELD':
            lines.append('Next try: %s, automatically (a held build is not retried for the same release: the same data would be held again).' % nxt)
        elif retrying:
            lines.append('Next try: automatically in about 10 minutes (try %d of 3 for this release). Nothing for you to do.' % tries)
        elif tries is not None:
            lines.append('That was the last of 3 tries for this release. Next update: %s, automatically.' % nxt)
        elif origin == 'slot' or event == 'schedule':
            lines.append('Next try: automatically within about 10 minutes (up to 3 tries per release), then %s.' % nxt)
        else:
            lines.append('Next try: %s, automatically.' % nxt)
    # THE NEXT NBER DATING (23 September 2026, collection 356; plan L2-L3: "the next NBER dating is the one true new lesson").
    # The committee watch (s2/chronology_watch.py, once a day) raises chronology/lesson_pending.json when the committee's pages carry
    # a turning point or an announcement the chronology file lacks; the state carries it (chronology_watch.lesson_pending). Until now
    # only the site showed it. It goes first in every run's message until Anthony confirms it (L3), at the highest priority once a
    # day; and a day the watch could not read the committee's pages is a CHECK, so a blocked page is never taken for "nothing new".
    cw = (new or {}).get('chronology_watch') or {}
    if cw.get('lesson_pending'):
        pend_l = ((cw.get('pending') or {}).get('pending') or []) if isinstance(cw.get('pending'), dict) else []
        what = '; '.join('%s %s%s' % (x.get('kind', '?'), x.get('month', '?'), (' (announced %s)' % x['announced']) if x.get('announced') else '') for x in pend_l[:3]) or 'see the site'
        lines.insert(0, 'NBER: a dating lesson is pending your confirmation - %s. Nothing in the rule changes until you confirm it (plan L3: the entry joins the chronology file with its announcement day and the walk re-runs from that cut).' % what)
        title = 'NBER DATING PENDING · ' + title
        tags = ['bangbang'] + [t for t in tags if t != 'white_check_mark']
        seen_n = jload(os.path.join(OPS, 'state', 'nber_seen.json'), {}) or {}
        if seen_n.get('day') != now.strftime('%Y-%m-%d'):
            prio = 5
            if not DRY:
                try:
                    os.makedirs(os.path.join(OPS, 'state'), exist_ok=True)
                    json.dump({'day': now.strftime('%Y-%m-%d'), 'what': what}, open(os.path.join(OPS, 'state', 'nber_seen.json'), 'w'))
                except Exception:
                    pass
    try:
        for l_ in open(os.path.join(ROOT, TOOL.get('run_log', 'run.log')), errors='replace'):
            if l_.startswith('chronology watch:') and '(errors:' in l_:
                lines.append('CHECK: the NBER dating pages could not be read today (%s); the watch tries again tomorrow.' % l_.split('(errors:', 1)[1].strip().rstrip(')')[:160])
                prio = max(prio, 4)
                break
    except Exception:
        pass
    # THE FRED KEY (23 September 2026, collection 356; risks register R6): the workflow asks FRED on every run whether it accepts
    # the key (ops/out/key_check.json). A refused or missing key goes first, in the title and at the highest priority, on a
    # success as on a failure: the run can end "Updated" while every FRED series silently stops (the files in hand are kept).
    kc = jload(os.path.join(OPS, 'out', 'key_check.json'), {}) or {}
    if kc.get('fred') in ('refused', 'missing'):
        lines.insert(0, 'KEY: FRED %s the API key%s. Every series the tool reads from FRED stops updating until the repository '
                     'secret FRED_API_KEY holds a working key (fred.stlouisfed.org > My Account > API Keys)%s.' % (
                         'refuses' if kc['fred'] == 'refused' else 'has no',
                         (' (HTTP %s: %s)' % (kc.get('http'), (kc.get('why') or '').split(' Read http')[0][:140])) if kc['fred'] == 'refused' else '',
                         '; the rest of the tool runs on' if status in ('OK', 'OK_FALLBACK') else ''))
        title = 'FRED KEY REFUSED · ' + title if kc['fred'] == 'refused' else 'FRED KEY MISSING · ' + title
        prio, tags = 5, ['key'] + [t for t in tags if t != 'white_check_mark']
    elif kc.get('fred') == 'unreachable':
        lines.append('Note: FRED could not be reached to check the key (%s); the next run checks again.' % ', '.join(str(kc[x]) for x in ('http', 'why') if x in kc)[:120])
    # THE REAL-TIME PARITY CHECK (23 September 2026, collection 362; handoff B item 14): ops/parity_check.py keeps the ledger of
    # every read of a new print against the publisher's post. A release posted more than six hours ago that no run has read is an
    # open miss; it goes in as a CHECK once a day until it clears (ops/state/parity_seen.json).
    pj = jload(os.path.join(OPS, 'state', 'parity.json'), {}) or {}
    if status in ('OK', 'OK_FALLBACK') and pj.get('open_misses'):
        pseen = jload(os.path.join(OPS, 'state', 'parity_seen.json'), {}) or {}
        today_p = now.strftime('%Y-%m-%d')
        if pseen.get('day') != today_p:
            for m in pj['open_misses'][:3]:
                lines.append('CHECK (parity): %s was posted %s and no run has read it (%s h). The walk assumes it is known on its publication day.' % (m.get('name'), m.get('posted'), m.get('hours')))
            prio = max(prio, 4)
            if not DRY:
                try:
                    json.dump({'day': today_p, 'misses': [m.get('name') for m in pj['open_misses']]}, open(os.path.join(OPS, 'state', 'parity_seen.json'), 'w'))
                except Exception:
                    pass
    # THE YEARLY DRIFT REPORT (23 September 2026, collection 356; risks register R4): ops/drift_report.py measures, each run, what the
    # tool's objects measure (claims coverage of the unemployed, claims per job loser, the insured rate against the unemployment rate,
    # the states' first-print noise). Its summary goes into the first message of each January; a flag - a registered line crossed -
    # goes in as a CHECK once a day until it clears. ops/state/drift_seen.json remembers what was said.
    dr = jload(os.path.join(OPS, 'out', 'drift_report.json'), {}) or {}
    if status in ('OK', 'OK_FALLBACK') and dr and not dr.get('failed'):
        seen = jload(os.path.join(OPS, 'state', 'drift_seen.json'), {}) or {}
        today = now.strftime('%Y-%m-%d'); said = False
        if now.month == 1 and seen.get('yearly') != now.year:
            lines.append('Yearly drift report: ' + (dr.get('summary') or '')[:300]); seen['yearly'] = now.year; said = True
        if dr.get('flags') and seen.get('flags_day') != today:
            for f in dr['flags'][:3]:
                lines.append('CHECK (drift): ' + f[:260])
            seen['flags_day'] = today; prio = max(prio, 4); said = True
        if said and not DRY:
            try:
                os.makedirs(os.path.join(OPS, 'state'), exist_ok=True)
                json.dump(seen, open(os.path.join(OPS, 'state', 'drift_seen.json'), 'w'), indent=1)
            except Exception:
                pass
    cs = jload(os.path.join(OPS, 'out', 'calendar_status.json'), {}) or {}
    if status in ('OK', 'OK_FALLBACK') and cs and not cs.get('ok', True):
        lines.append('WARNING: the release calendar could not be rebuilt (%s); the schedule stands as it was.' % cs.get('why', '?')[:120])
        prio = max(prio, 4)
    if status in ('OK', 'OK_FALLBACK') and cs.get('disagree'):
        lines.append('CHECK: next release days disagree (%s); the page keeps the tool\'s day until they agree.' % '; '.join(cs['disagree'][:2])[:200])
    if status in ('OK', 'OK_FALLBACK') and cs.get('glitch'):
        lines.append('Calendar note: ' + '; '.join(str(x) for x in cs['glitch'][:2])[:200])
    # nothing the site shows may be without a release day, a time or a working link (22 September 2026, collection 306)
    # a run that published a new version says what was re-checked for it (22 September 2026, collection 306)
    if status in ('OK', 'OK_FALLBACK') and cs.get('version_change'):
        lines.append('New version: every release calendar and link re-checked - %s rows, %s with a day and a time, %s with a link.'
                     % (cs.get('rows', '?'), cs.get('timed', '?'), cs.get('linked', '?')))
    if status in ('OK', 'OK_FALLBACK') and cs.get('gaps'):
        lines.append('CHECK: ' + '; '.join(cs['gaps'][:2])[:220])
        prio = max(prio, 4)
    if status in ('OK', 'OK_FALLBACK') and cs.get('links'):
        lines.append('CHECK the data page links: ' + '; '.join(cs['links'][:2])[:220])
        prio = max(prio, 4)
    if o_push != 'success' and status in ('OK', 'OK_FALLBACK'):
        lines.append('WARNING: the site is updated but the run could not save its data to the repository (%s); the next run retries.' % (o_push or 'not run'))
        prio = max(prio, 4)
    if status in ('OK', 'OK_FALLBACK') and not test and (new or {}).get('built_at') and not live_check(new['built_at']):
        lines.append('WARNING: the live site does not show this build yet (Cloudflare); the next update republishes it.')
        prio = max(prio, 4)
    if test:
        title = '[TEST] ' + title
    body = '\n'.join(lines)
    topic = E('NTFY_TOPIC', '')
    ok = send(topic, 'Bristow-Hall: ' + title, body, prio, tags, site) if (topic or DRY) else False
    print('notification %s: %s' % ('sent' if ok else 'NOT SENT (no topic)' if not topic else 'NOT SENT', title))
    print(body)
    if status in ('FAILED', 'HELD') and not retrying:       # a failure that is retried by itself is not an email
        gh_issue(status, title, body + '\n\n' + run_url())
    elif not ok and not DRY:
        gh_issue('FAILED', 'the phone message could not be sent', title + '\n' + body + '\n\n' + run_url())
    elif status == 'OK' and not test:
        gh_issue('OK', title, 'Recovered: %s published the build of %s (%s).' % (run_url(), (new or {}).get('built_at'), ver), close_on_ok=True)
    os.makedirs(os.path.join(OPS, 'out'), exist_ok=True)
    json.dump({'status': status, 'title': title, 'body': body, 'sent': ok}, open(os.path.join(OPS, 'out', 'notify.json'), 'w'), indent=1)
    if not ok and not DRY:
        sys.exit(1)       # the step fails, so the Cloudflare starter sees a run that could not report and says so itself


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:                     # the last resort: a plain message, so a crash here is never silent
        import traceback
        traceback.print_exc()
        sent = False
        try:
            sent = bool(E('NTFY_TOPIC', '')) and send(E('NTFY_TOPIC', ''), 'Bristow-Hall: update run finished (the summary could not be written)',
                 'Run %s ended; the notifier itself failed (%s: %s). Check the run log.' % (run_url(), type(e).__name__, e), 4, ['warning'],
                 TOOL.get('site_url', ''))
        except Exception:
            pass
        sys.exit(0 if sent else 1)
    sys.exit(0)
