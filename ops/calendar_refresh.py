#!/usr/bin/env python3
"""FRED'S RELEASE CALENDAR, ASKED BEFORE THE SITE IS BUILT (17 November 2026, record 1116g; Anthony: "Check ntfy and fix the issue").

The data page's "next published" days are written by the site build (bhs_site.py -> s2/next_published.py, s2/tool_inputs.py) from
ops/cache/fred_release_dates.json, which ops/calendar_build.py refreshed only AFTER the build, and only once a day. On 17 Nov FRED
listed the G.17 annual revision (24 Nov) in the afternoon: the pages still said 16 Dec, the source gate reads FRED live, and the
4:20 PM update was held twice. A held run commits nothing, so the stale calendar would have held every run until the next day.

run_cloud.sh runs this before bhs_site.py: every release already in the cache is asked again (calendar_build.release_dates: the
same request, the same guard against a short answer; an answer under 15 minutes old stands). If FRED cannot be read the cached
days stand. Never fails the run. No AI. Usage: python3 ops/calendar_refresh.py"""
import datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    import calendar_build as cb
    rc = cb.jload(cb.REL_CACHE, {}) or {}
    today = cb.now_et().date()
    rids = [k for k in rc if k.isdigit()]
    before = {k: list((rc.get(k) or {}).get('dates', [])) for k in rids}
    for k in rids:
        cb.release_dates(int(k), rc, True, today)
    cb.jsave(cb.REL_CACHE, rc)
    moved = [k for k in rids if (rc.get(k) or {}).get('dates', []) != before[k]]
    print('release calendar asked before the site build: %d releases%s' % (len(rids), ('; changed: ' + ', '.join(
        '%s (+%s)' % (k, ' '.join(sorted(set(rc[k]['dates']) - set(before[k]))[-3:]) or 'days dropped') for k in moved)) if moved else '; none changed'))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('release calendar not asked before the site build (%s: %s); the cached days stand' % (type(e).__name__, e))
