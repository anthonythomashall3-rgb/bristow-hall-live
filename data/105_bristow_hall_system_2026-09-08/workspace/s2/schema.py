# -*- coding: utf-8 -*-
"""THE STATE'S SCHEMA (plan Step 6 R10; 24 September 2026, collection 372).

bhs_build.py writes out/bhs_state.json; bhs_site.py embeds it in the page and writes it beside the page; the ops readers, the old
Mac's watchdog and the rebuild check read it from the live site. This module is the one place that says which layout that JSON
has. The build stamps `schema_version` and checks the layout before writing; the renderer checks it before rendering and refuses
any other; q41 checks it as a hard gate; the rebuild check compares it live against rebuilt. When the layout changes on purpose,
the port raises SCHEMA_VERSION and lists the new keys in REQUIRED in the same commit - the build and the renderer read the same
constant, so within one version they cannot disagree.

REQUIRED is what the readers hard-read (read 24 September 2026): the template `const S = __STATE__` (built, built_at, notes,
episodes, sahm, sahm_other, nber, through, series, calendar, announcements); bhs_site.py (series.dates, series.values,
standing.state, standing.since, built, near_misses; readings, feeds, next_releases, channels with defaults); the ops readers
(version, built_at, standing, episodes, chronology, walked_record, lines, series)."""
SCHEMA_VERSION = 1
REQUIRED = ('built', 'built_at', 'version', 'walk', 'standing', 'episodes', 'chronology', 'series', 'nber', 'sahm', 'sahm_other', 'notes',
            'through', 'calendar', 'announcements', 'feeds', 'next_releases', 'lines', 'walked_record', 'readings', 'near_misses', 'channels')
NESTED = (('series', 'dates'), ('series', 'values'), ('standing', 'state'), ('standing', 'since'))

def check(state):
    """The problems with a state as this code reads it; an empty list means it is the schema this code renders."""
    problems = []
    v = state.get('schema_version') if isinstance(state, dict) else None
    if v != SCHEMA_VERSION:
        problems.append('schema_version %r; this code reads %d' % (v, SCHEMA_VERSION))
    missing = [k for k in REQUIRED if k not in state] if isinstance(state, dict) else list(REQUIRED)
    if missing:
        problems.append('missing keys: ' + ', '.join(missing))
    for a, b in NESTED:
        d = state.get(a) if isinstance(state, dict) else None
        if not isinstance(d, dict) or b not in d:
            problems.append('missing %s.%s' % (a, b))
    return problems

def stamp(state):
    state['schema_version'] = SCHEMA_VERSION
    return state
