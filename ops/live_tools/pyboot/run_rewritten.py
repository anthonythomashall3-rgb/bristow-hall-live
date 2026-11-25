# -*- coding: utf-8 -*-
"""RUN A LIVE-TOOLS SCRIPT WITH ITS parts() ON THE ARRAYS (1167b, 25 Nov 2026). No AI.

    python3 run_rewritten.py <script> [args...]

sitecustomize.py starts this in place of `python3 <script>` when <script> is one of the files below (its SHA-256 exactly; any other version
runs as itself). The script's text is read, its parts() body is replaced by a call to pyboot_fast.parts (same arithmetic, same results;
the replacement keeps the line count, so every later line keeps its number), and the script runs as Python would run it: __main__, its own
__file__, sys.argv and sys.path[0], its exceptions and exit code."""
import os, sys, hashlib

_A198 = ('''def parts(UR, base, Gq, p, m):
    ex = (UR[(UR.index >= p) & (UR.index <= m)] - base).clip(lower=0); L = dd.labour_score(float(ex.max()), float(ex.sum())) if len(ex) else 0.0
    return L, dd.output_dimension(Gq, p, m), (float(ex.max()) if len(ex) else 0.0)
''', '''def parts(UR, base, Gq, p, m):
    return __import__('pyboot_fast').parts(UR, base, Gq, p, m, dd)   # 1167b pyboot: the same arithmetic on the arrays (ops/live_tools/pyboot)
    pass
''')
_NESTED = ('''    def parts(UR, base, Gq, p, m):
        ex = (UR[(UR.index >= p) & (UR.index <= m)] - base).clip(lower=0); L = dd.labour_score(float(ex.max()), float(ex.sum())) if len(ex) else 0.0
        return L, dd.output_dimension(Gq, p, m), (float(ex.max()) if len(ex) else 0.0)
''', '''    def parts(UR, base, Gq, p, m):
        return __import__('pyboot_fast').parts(UR, base, Gq, p, m, dd)   # 1167b pyboot: the same arithmetic on the arrays (ops/live_tools/pyboot)
        pass
''')
# SHA-256 of the file as read on 25 Nov 2026 -> its replacements (each text must occur exactly once)
REWRITES = {
    '8295417d6b2e22c57c22b8a4b6e174b867b62ccf30ef2f84cd4483aca0e57f7f': [_A198],     # 1032 code/state_chronology_v4_growth_cycle_a198_1032.py
    'ae887a2170936346922b973195ce109267c19e82b9a0daa157ed203365f7bf37': [_NESTED],   # 1052 code/stress_map_v3_1_1052.py (the stress map's State layer)
}


def sha_of(path):
    with open(path, 'rb') as f: return hashlib.sha256(f.read()).hexdigest()


def main():
    target = sys.argv[1]
    path = os.path.abspath(target)
    raw = open(path, 'rb').read()
    src = raw.decode('utf-8')
    for old, new in REWRITES.get(hashlib.sha256(raw).hexdigest(), ()):
        if src.count(old) != 1 or old.count('\n') != new.count('\n'):
            raise SystemExit('pyboot run_rewritten: %s does not carry the text it rewrites' % target)
        src = src.replace(old, new)
    code = compile(src, path, 'exec')
    sys.argv = sys.argv[1:]
    sys.path[0] = os.path.dirname(path)
    import __main__, builtins, importlib.machinery
    g = __main__.__dict__
    g.clear()
    g.update(__name__='__main__', __doc__=None, __package__=None, __spec__=None, __file__=path, __cached__=None, __builtins__=builtins,
             __loader__=importlib.machinery.SourceFileLoader('__main__', path))
    exec(code, g)


if __name__ == '__main__':
    main()
