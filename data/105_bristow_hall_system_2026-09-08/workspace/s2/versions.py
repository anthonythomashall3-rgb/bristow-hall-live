# -*- coding: utf-8 -*-
"""THE VERSION GUARD (18 September 2026).

The rule's arithmetic is pandas' and numpy's arithmetic. On 18 September the cloud runner had pandas 2.3 while
this Mac had 3.0.5, and it died on a date calculation - which was lucky, because the failure was loud. The
dangerous version of that is quiet: a `brew upgrade` one morning, no error, and the tool computing something
slightly different from the tool that was tested.

So the versions are recorded, and every run checks them. A change halts the run before anything is published and
says what moved. Changing them is then a decision someone makes, with the walk re-run to prove the record is
unmoved - not something that happens to us.

    python3 s2/versions.py            check against the record; exit 1 if anything moved
    python3 s2/versions.py --record   write the record from what is installed now (a deliberate act)
"""
import sys, os, json, datetime

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(HERE, 'cache', 'versions.json')
WATCH = ('pandas', 'numpy', 'scipy', 'lxml', 'xlrd', 'openpyxl', 'requests')


def installed():
    out = {'python': '%d.%d.%d' % sys.version_info[:3]}
    for m in WATCH:
        try:
            out[m] = __import__(m).__version__
        except Exception:
            out[m] = None
    return out


def on_owner_host():
    """the record belongs to the machine that publishes. Read from anywhere else - the Linux side of the bridge
    has a different python and a different pandas - a mismatch is expected and is not a fault."""
    import platform, socket
    owner = os.path.join(HERE, 'cache', 'watchdog_owner')
    if platform.system() != 'Darwin': return False
    try: return open(owner).read().strip() == socket.gethostname()
    except OSError: return True


def main():
    now = installed()
    if '--record' in sys.argv:
        os.makedirs(os.path.dirname(REC), exist_ok=True)
        json.dump(dict(recorded=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                       versions=now), open(REC, 'w'), indent=1)
        print('recorded:', json.dumps(now))
        return 0
    if not os.path.exists(REC):
        print('no version record; run python3 s2/versions.py --record once'); return 0
    was = json.load(open(REC))['versions']
    moved = [(k, was.get(k), now.get(k)) for k in sorted(set(was) | set(now)) if was.get(k) != now.get(k)]
    # the python minor line matters; the patch does not
    moved = [m for m in moved if not (m[0] == 'python' and (m[1] or '').rsplit('.', 1)[0] == (m[2] or '').rsplit('.', 1)[0])]
    if not moved:
        print('versions unchanged: ' + ', '.join('%s %s' % (k, now[k]) for k in WATCH if now.get(k)))
        return 0
    if not on_owner_host():
        print('versions differ from the record, but this is not the machine that publishes; not a fault:')
        for k, a, b in moved: print('   %-10s record %s, here %s' % (k, a, b))
        return 0
    print('THE ARITHMETIC MOVED UNDER US:')
    for k, a, b in moved: print('   %-10s %s -> %s' % (k, a, b))
    print('Nothing has been published. Either put the old versions back, or accept the new ones deliberately:')
    print('   python3 s2/versions.py --record     then re-run the walk and check the record is unmoved')
    return 1


if __name__ == '__main__':
    sys.exit(main())
