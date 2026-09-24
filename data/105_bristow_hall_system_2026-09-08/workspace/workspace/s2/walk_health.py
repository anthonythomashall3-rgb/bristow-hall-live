# -*- coding: utf-8 -*-
"""CAN THE WALK STILL BE RUN? (18 September 2026)

On 18 September every walk had been broken for days and nothing noticed. A folder the walk reads had been moved,
so `daily1.py` could not find NFCICREDIT, and the chain died forty files later on a NoneType. The published site
went on working perfectly throughout, because `bhs_build.py` publishes from the walk's CACHED results rather than
re-walking - so the product looked healthy while the laboratory was dead, and no version of the rule could be
rebuilt or any change to it tested.

This loads the live walk's preamble, which is where that failure appeared and where this class of failure appears:
missing data, a moved folder, a renamed series, a library change. It builds nothing and writes nothing.

    python3 s2/walk_health.py        exits 0 if the walk can be run, 1 if it cannot
"""
import sys, os, io, json, contextlib


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(here); sys.path.insert(0, here)
    walk = json.load(open('cache/bhs_version.json'))['walk']
    src = open(walk).read()
    head = src.split("exec(open('walk39.py')")[0]
    sys.argv = [walk, '1962', '1963', 'wHEALTH']
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(head, walk, 'exec'), {'__name__': '__main__'})
    except Exception as e:
        print('THE WALK CANNOT BE RUN: %s: %s' % (type(e).__name__, str(e)[:120]))
        return 1
    print('the walk (%s) loads and can be run' % walk)
    return 0


if __name__ == '__main__':
    sys.exit(main())
