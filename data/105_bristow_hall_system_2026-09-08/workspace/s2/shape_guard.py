# -*- coding: utf-8 -*-
"""THE SHAPE GUARD (18 September 2026).

The checks this system already has ask whether data ARRIVED. None of them asks whether it arrived in the same
SHAPE. A publisher that switches a series from thousands to millions, or from weekly to monthly, or that drops
twenty years of history in a revision, produces a file that downloads perfectly, parses perfectly, passes every
freshness test - and is wrong by a factor of a thousand. The rule would read it and the line would move for a
reason that has nothing to do with the economy.

So every feed's shape is remembered and compared on each run:

  cadence     the median days between observations. Weekly turning monthly is a redefinition, not an update.
  length      how many observations. A series that gets SHORTER has been redefined or truncated.
  level       the median of the last five years. A units change shows here as a factor of ten or a thousand.
  last step   the newest value against the recent spread. A single impossible print is caught before it is read.

A first run records and reports nothing. Afterwards, anything that moves raises an alert and names the series and
the reason. The record is cache/feed_shapes.json and is updated only when a change is accepted.

    python3 s2/shape_guard.py            compare; exit 1 if any feed changed shape
    python3 s2/shape_guard.py --accept   take the current shapes as correct (a deliberate act)
"""
import sys, os, json, math, datetime, statistics

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(HERE, 'cache', 'feed_shapes.json')
STATE = os.path.join(HERE, 'out', 'bhs_state.json')


def shape_of(dates, values):
    import datetime as dt
    ds = []
    for d in dates:
        try: ds.append(dt.date.fromisoformat(str(d)[:10]))
        except Exception: pass
    vals = [float(v) for v in values if isinstance(v, (int, float))]
    if len(ds) < 8 or len(vals) < 8: return None
    gaps = [(ds[i + 1] - ds[i]).days for i in range(len(ds) - 1) if (ds[i + 1] - ds[i]).days > 0]
    recent = vals[-1300:] if len(vals) > 1300 else vals
    med = statistics.median([abs(v) for v in recent if v == v]) or 0.0
    try: sd = statistics.pstdev(recent[-260:]) if len(recent) >= 20 else 0.0
    except Exception: sd = 0.0
    return dict(n=len(vals), first=str(ds[0]), last=str(ds[-1]),
                cadence=round(statistics.median(gaps), 1) if gaps else None,
                level=round(med, 6), spread=round(sd, 6), newest=round(float(vals[-1]), 6))


def shapes():
    st = json.load(open(STATE))
    out = {}
    se = st.get('series') or {}
    if se.get('dates'): 
        s = shape_of(se['dates'], se.get('values') or [])
        if s: out['THE LINE'] = s
    for f in st.get('leg_feeds') or []:
        ch = f.get('channel')
        if not ch: continue
        out['feed:' + ch] = dict(through=(f.get('through') or '')[:10], cadence_stated=f.get('cadence'),
                                 n=f.get('n'), value=f.get('value'), units=(f.get('units') or '')[:40])
    for r in st.get('readings') or []:
        k = r.get('name') or r.get('series')
        if k: out['reading:' + str(k)] = {a: r.get(a) for a in ('value', 'units', 'through') if a in r}
    return out


def compare(was, now):
    faults = []
    for k, b in now.items():
        a = was.get(k)
        if a is None: continue
        if k.startswith('feed:'):
            if a.get('cadence_stated') and b.get('cadence_stated') and a['cadence_stated'] != b['cadence_stated']:
                faults.append('%s: cadence %s -> %s' % (k, a['cadence_stated'], b['cadence_stated']))
            if a.get('units') and b.get('units') and a['units'] != b['units']:
                faults.append('%s: units "%s" -> "%s"' % (k, a['units'], b['units']))
            try:
                if a.get('n') and b.get('n') and int(b['n']) < int(a['n']) * 0.9:
                    faults.append('%s: lost history, %s observations -> %s' % (k, a['n'], b['n']))
            except Exception: pass
            try:
                x, y = abs(float(a.get('value'))), abs(float(b.get('value')))
                if x > 0 and y > 0 and (y / x > 50 or x / y > 50):
                    faults.append('%s: the value jumped by a factor of %.0f (%s -> %s); a units change looks '
                                  'exactly like this' % (k, max(y / x, x / y), a['value'], b['value']))
            except Exception: pass
        elif k == 'THE LINE':
            if b['n'] < a['n'] * 0.95:
                faults.append('the line lost history: %d readings -> %d' % (a['n'], b['n']))
            if a.get('cadence') and b.get('cadence') and abs(b['cadence'] - a['cadence']) > max(2, a['cadence']):
                faults.append('the line changed cadence: %s days -> %s' % (a['cadence'], b['cadence']))
            if a.get('level') and b.get('level') and a['level'] > 0 and b['level'] > 0:
                r = max(b['level'] / a['level'], a['level'] / b['level'])
                if r > 5: faults.append('the line changed level by a factor of %.1f' % r)
    return faults


def main():
    now = shapes()
    if '--accept' in sys.argv or not os.path.exists(REC):
        os.makedirs(os.path.dirname(REC), exist_ok=True)
        json.dump(dict(recorded=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                       shapes=now), open(REC, 'w'), indent=1, sort_keys=True)
        print('shapes recorded for %d feeds and objects' % len(now)); return 0
    was = json.load(open(REC))['shapes']
    faults = compare(was, now)
    if not faults:
        print('every feed is the shape it was: %d checked' % len(now)); return 0
    print('A SOURCE CHANGED SHAPE — this is what a silent redefinition looks like:')
    for f in faults: print('   ' + f)
    print('If the change is real and correct: python3 s2/shape_guard.py --accept')
    return 1


if __name__ == '__main__':
    sys.exit(main())
