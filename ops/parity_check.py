"""The real-time parity check (23 September 2026, collection 362; handoff B item 14): the live tool must carry each new print no
later than the walk assumes it is known - its publication day. Every run, after the build:

  1. the reads ledger - every data-page row whose `through` advanced against the state the repository already carried
     (git show HEAD:<state>) is written to ops/state/parity.json with the run's time; for a row that is one of FRED's releases
     (calendar_build.FRED_SERIES) the matching post from ops/state/fred_posted.json (the latest post at or before the read,
     within 14 days) and the lag in minutes; for the claims row the reference is the Department's Thursday 8:30 ET release
     (Wednesday before a holiday), not FRED's post;
  2. open misses - a release whose latest post is older than PARITY_HOURS and has no read after it: the publisher posted and
     the tool has not read it. ops/notify.py says so on the phone (CHECK (parity)) once a day until it clears.

Usage:  python3 ops/parity_check.py                 in a run (ledger + misses; never fails the run)
        python3 ops/parity_check.py --report        the lags per release from the ledger
        python3 ops/parity_check.py --history [N]   on a clone with history: rebuild the ledger from the last N committed states
"""
import datetime as dt, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calendar_build as cb

OPS = cb.OPS; ROOT = cb.ROOT; ET = cb.ET; UTC = dt.timezone.utc
TOOL = cb.jload(os.path.join(OPS, 'tool.json'), {}) or {}
STATE_REL = TOOL.get('state', 'data/105_bristow_hall_system_2026-09-08/site/public/bhs_state.json')
PARITY = os.path.join(OPS, 'state', 'parity.json')
PARITY_HOURS = 6
# the backstop tier's rows (workspace/out/backstop_state.json), read like data-page rows (seagate-0924, 24 Sep 2026)
BACKSTOP_REL = os.path.join(os.path.dirname(STATE_REL).replace('site/public', 'workspace/out'), 'backstop_state.json')
BACKSTOP_IDS = {'WEI': 'WEI (backstop shadow reading)', 'CFNAI': 'CFNAIMA3 (backstop CFNAI)'}
NAMES = {10: 'CPI', 13: 'G.17 industrial production', 18: 'H.15 rates', 27: 'housing starts', 50: 'the jobs report', 53: 'GDP',
         101: 'the fed funds target', 112: 'state unemployment rates', 180: 'weekly claims', 189: 'the S&P 500 close',
         192: 'JOLTS', 219: 'CFNAI', 386: 'GDPNow', 456: 'the Sahm rule (FRED)', 465: 'the Weekly Economic Index'}
# which data-page row (by its ids text) carries each release's print
ROW_OF = {10: 'CPIAUCSL', 13: 'INDPRO', 18: 'DCPN30', 27: 'HOUST', 50: 'UNRATE', 53: 'GDPC1', 101: 'DFEDTARU', 112: 'LAUS state rates',
          180: 'ICSA', 189: '^GSPC', 192: 'JTSJOL', 219: 'CFNAIMA3', 386: 'GDPNOW', 456: 'SAHMREALTIME', 465: 'WEI'}


def sh(*a):
    return subprocess.run(list(a), capture_output=True, text=True, cwd=ROOT).stdout


def feeds_of(text):
    try:
        st = json.loads(text)
    except Exception:
        return {}
    return {(f.get('ids') or f.get('name') or ''): str(f.get('through') or '') for f in st.get('feeds') or []}


def backstop_rows(text):
    """{row ids: data_through} for the backstop rules that are FRED releases (WEI 465, CFNAI 219)"""
    try:
        rules = (json.loads(text) or {}).get('rules') or {}
    except Exception:
        return {}
    return {BACKSTOP_IDS[k]: str(v.get('data_through') or '') for k, v in rules.items()
            if k in BACKSTOP_IDS and isinstance(v, dict)}


def rid_of(ids):
    for rid, key in ROW_OF.items():
        if key.lower() in (ids or '').lower():
            return rid
    return None


def claims_release(read_at):
    """the Department's release before read_at: Thursday 8:30 ET, Wednesday when the Thursday is a federal holiday"""
    d = read_at.astimezone(ET).date()
    for k in range(0, 14):
        day = d - dt.timedelta(days=k)
        thu = day.weekday() == 3 and day not in cb.federal_holidays(day.year)
        wed = day.weekday() == 2 and (day + dt.timedelta(days=1)) in cb.federal_holidays(day.year)
        if thu or wed:
            t = dt.datetime(day.year, day.month, day.day, 8, 30, tzinfo=ET)
            if t <= read_at.astimezone(ET):
                return t
    return None


def post_before(rid, read_at, posted):
    """FRED's latest post for the release at or before read_at (New York stamps in fred_posted.json), within 14 days"""
    posts = ((posted.get(str(rid)) or {}).get('posts') or [])
    best = None
    for p in posts:
        try:
            t = dt.datetime.strptime(p, '%Y-%m-%d %H:%M').replace(tzinfo=ET)
        except Exception:
            continue
        if t <= read_at and (read_at - t).days < 14 and (best is None or t > best):
            best = t
    return best


def norm(thr):
    """a through as a comparable day: '2026-08' (a month) counts as its first day, so a format change is not an advance"""
    t = (thr or '')[:10]
    return t + '-01' if len(t) == 7 else t


def reference(rid, read_at, posted, to=None):
    """the publication the read followed: the Department's Thursday 8:30 for claims; the 4:00 PM close of the through day for the
    S&P 500 (the tool reads Yahoo's close at 5:05 PM, before FRED's 8 PM post); FRED's latest post at or before the read otherwise"""
    if rid == 180:
        return claims_release(read_at)
    if rid == 189 and to:
        try:
            d = dt.date.fromisoformat(norm(to)); t = dt.datetime(d.year, d.month, d.day, 16, 0, tzinfo=ET)
            return t if t <= read_at else None
        except Exception:
            return None
    return post_before(rid, read_at, posted)


def advances(old_text, new_text, read_at, posted, old_extra=None, new_extra=None):
    old, new = feeds_of(old_text), feeds_of(new_text)
    old.update(old_extra or {})
    new.update(new_extra or {})
    out = []
    for ids, thr in new.items():
        o = old.get(ids, '')
        if thr and norm(thr) > norm(o):
            rid = rid_of(ids) if o else None           # a row that first appears (a port added it) is not a read of a print
            ref = reference(rid, read_at, posted, thr) if rid else None
            out.append({'ids': ids, 'from': o, 'to': thr, 'read_at': read_at.astimezone(UTC).strftime('%Y-%m-%dT%H:%MZ'),
                        'release': rid, 'name': NAMES.get(rid), 'posted': ref.strftime('%Y-%m-%d %H:%M ET') if ref else None,
                        'lag_min': int((read_at - ref).total_seconds() // 60) if ref else None,
                        **({'note': 'row first appeared'} if not o else {})})
    return out


def latest_post(rid, posted, now):
    if rid == 180:
        return claims_release(now)
    return post_before(rid, now, posted)


def misses(doc, posted, now, present=None):
    """releases whose latest post is older than PARITY_HOURS with no read of their row after it; only posts since the ledger
    began count (a post the ledger never saw read is not a miss)"""
    out = []
    reads = doc.get('reads') or []
    try:
        since = dt.datetime.strptime(doc.get('since') or '', '%Y-%m-%dT%H:%MZ').replace(tzinfo=UTC)
    except Exception:
        since = now
    for rid in sorted(ROW_OF):
        if rid == 189:
            continue                                   # the S&P close is read at 5:05 PM by the tool's own slot; not a FRED post to miss
        if present is not None and not any(ROW_OF[rid].lower() in (i or '').lower() for i in present):
            continue                                   # no row of the state carries this release: it cannot be read or missed
        lp = latest_post(rid, posted, now)
        if not lp or lp < since:
            continue
        hours = (now - lp).total_seconds() / 3600
        if hours < PARITY_HOURS:
            continue
        after = [r for r in reads if r.get('release') == rid and r.get('read_at') and
                 dt.datetime.strptime(r['read_at'], '%Y-%m-%dT%H:%MZ').replace(tzinfo=UTC) >= lp]
        if not after:
            out.append({'release': rid, 'name': NAMES.get(rid), 'posted': lp.strftime('%Y-%m-%d %H:%M ET'), 'hours': round(hours, 1)})
    return out


def save(doc):
    doc['_what'] = ('the real-time parity ledger (collection 362): every advance of a data-page row\'s through, when the run read it '
                    'and the publisher\'s post it followed (fred_posted.json; the Department\'s Thursday 8:30 for claims); '
                    'open_misses = posts older than %d h with no read' % PARITY_HOURS)
    doc['reads'] = (doc.get('reads') or [])[-600:]
    cb.jsave(PARITY, doc)


def run_once(now=None):
    now = now or dt.datetime.now(UTC)
    posted = cb.jload(cb.FRED_POSTED, {}) or {}
    doc = cb.jload(PARITY, {}) or {}
    new_text = open(os.path.join(ROOT, STATE_REL), encoding='utf-8').read()
    old_text = sh('git', 'show', 'HEAD:' + STATE_REL)
    try:
        new_bs = backstop_rows(open(os.path.join(ROOT, BACKSTOP_REL), encoding='utf-8').read())
    except Exception:
        new_bs = {}
    old_bs = backstop_rows(sh('git', 'show', 'HEAD:' + BACKSTOP_REL))
    adv = advances(old_text, new_text, now, posted, old_bs, new_bs) if old_text else []
    known = {(r['ids'], r['to']) for r in doc.get('reads') or []}
    adv = [a for a in adv if (a['ids'], a['to']) not in known]
    doc['reads'] = (doc.get('reads') or []) + adv
    doc.setdefault('since', now.strftime('%Y-%m-%dT%H:%MZ'))
    present = set(feeds_of(new_text)) | set(new_bs)
    doc['open_misses'] = misses(doc, posted, now, present)
    doc['checked_at'] = now.strftime('%Y-%m-%dT%H:%MZ')
    save(doc)
    print('parity: %d new read(s) this run%s; open misses: %s' % (
        len(adv), (' - ' + '; '.join('%s through %s, lag %s min' % (a['name'] or a['ids'], a['to'], a['lag_min']) for a in adv)) if adv else '',
        '; '.join('%s posted %s, unread for %s h' % (m['name'], m['posted'], m['hours']) for m in doc['open_misses']) or 'none'))


def history(n=80):
    """rebuild the ledger from the last n committed states (a clone with history); prints the parity table"""
    posted = cb.jload(cb.FRED_POSTED, {}) or {}
    log = [l.split('|') for l in sh('git', 'log', '-n', str(n), '--format=%H|%cI', '--', STATE_REL).splitlines() if '|' in l]
    log.reverse()
    reads = []
    for (h0, _), (h1, t1) in zip(log, log[1:]):
        read_at = dt.datetime.fromisoformat(t1).astimezone(UTC)
        reads += advances(sh('git', 'show', '%s:%s' % (h0, STATE_REL)), sh('git', 'show', '%s:%s' % (h1, STATE_REL)), read_at, posted)
    since = dt.datetime.fromisoformat(log[0][1]).astimezone(UTC).strftime('%Y-%m-%dT%H:%MZ') if log else None
    doc = {'reads': reads, 'since': since, 'checked_at': dt.datetime.now(UTC).strftime('%Y-%m-%dT%H:%MZ'), 'history_commits': len(log)}
    doc['open_misses'] = misses(doc, posted, dt.datetime.now(UTC))
    return doc


def report(doc):
    by = {}
    for r in doc.get('reads') or []:
        if r.get('release') and r.get('lag_min') is not None:
            by.setdefault(r['release'], []).append(r)
    print('%-28s %5s %8s %8s  %s' % ('release', 'reads', 'median', 'max', 'last read (through, posted -> read, lag)'))
    for rid in sorted(by):
        L = sorted(x['lag_min'] for x in by[rid]); last = by[rid][-1]
        print('%-28s %5d %6d m %6d m  %s: posted %s -> %s, %d min' % (NAMES[rid], len(L), L[len(L) // 2], L[-1], last['to'], last['posted'], last['read_at'], last['lag_min']))
    other = [r for r in doc.get('reads') or [] if not r.get('release')]
    if other:
        print('rows with no publisher clock (%d reads): %s' % (len(other), ', '.join(sorted({r['ids'] for r in other}))))
    print('open misses: %s' % ('; '.join('%s posted %s, unread %s h' % (m['name'], m['posted'], m['hours']) for m in doc.get('open_misses') or []) or 'none'))


def backfill_backstop(n=80):
    """one-off (seagate-0924, 24 Sep 2026): write into the ledger the backstop reads made before the ledger counted them"""
    posted = cb.jload(cb.FRED_POSTED, {}) or {}
    doc = cb.jload(PARITY, {}) or {}
    log = [l.split('|') for l in sh('git', 'log', '-n', str(n), '--format=%H|%cI', '--', BACKSTOP_REL).splitlines() if '|' in l]
    log.reverse()
    known = {(r['ids'], r['to']) for r in doc.get('reads') or []}
    new = []
    for (h0, _), (h1, t1) in zip(log, log[1:]):
        read_at = dt.datetime.fromisoformat(t1).astimezone(UTC)
        o = backstop_rows(sh('git', 'show', '%s:%s' % (h0, BACKSTOP_REL)))
        w = backstop_rows(sh('git', 'show', '%s:%s' % (h1, BACKSTOP_REL)))
        for a in advances('{}', '{}', read_at, posted, o, w):
            if (a['ids'], a['to']) not in known and a.get('from'):
                new.append(a); known.add((a['ids'], a['to']))
    doc['reads'] = sorted((doc.get('reads') or []) + new, key=lambda r: r.get('read_at') or '')
    now = dt.datetime.now(UTC)
    try:
        cur = open(os.path.join(ROOT, STATE_REL), encoding='utf-8').read()
        bs = backstop_rows(open(os.path.join(ROOT, BACKSTOP_REL), encoding='utf-8').read())
        doc['open_misses'] = misses(doc, posted, now, set(feeds_of(cur)) | set(bs))
    except Exception:
        pass
    save(doc)
    print('backfilled %d backstop read(s): %s; open misses: %s' % (len(new), '; '.join('%s %s -> %s at %s' % (a['ids'], a['from'], a['to'], a['read_at']) for a in new),
          '; '.join(m['name'] for m in doc.get('open_misses') or []) or 'none'))


if __name__ == '__main__':
    if '--backfill-backstop' in sys.argv:
        backfill_backstop()
    elif '--history' in sys.argv:
        n = int(sys.argv[sys.argv.index('--history') + 1]) if len(sys.argv) > sys.argv.index('--history') + 1 and sys.argv[-1].isdigit() else 80
        d = history(n); report(d)
        if '--save' in sys.argv:
            save(d); print('saved', PARITY)
    elif '--report' in sys.argv:
        report(cb.jload(PARITY, {}) or {})
    else:
        try:
            run_once()
        except Exception as e:
            print('parity: check failed (%s: %s); the run continues' % (type(e).__name__, str(e)[:160]))
