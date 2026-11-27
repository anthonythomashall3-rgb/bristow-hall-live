# -*- coding: utf-8 -*-
"""THE LIVE TOOLS' PYTHON, FASTER WITH THE SAME RESULTS (1167, 25 Nov 2026; Anthony: "under 3 minutes of data releases"). No AI.

Python loads this file at the start of every process the live tools run (ops/live_tools/run_live_tools.sh puts this folder first on
PYTHONPATH). The tools' own files are not changed. Each replacement below is made only when the code it replaces is exactly the code read
on 25 Nov 2026 (its sha256 or its text); any other version is left as it is.

1. damage_dimensions_live_v376.pt_and_cum: the fall from a peak to its trough and the cumulative shortfall. The State chronology (a198)
   calls it about 3,800 times a run, each a loop of pandas selections over the window (O(n^2)). Here the same arithmetic runs in one pass
   on the arrays: the trough after each peak is a suffix minimum, and the loop's choice is kept (the first peak with the largest fall above
   0). It is bit-identical on 12,479 windows (random, ties, flat, rising, falling, not_before past the end, and every State's quarterly
   index), and 50 times faster. A window with a repeated or unsorted date, or a missing value, goes to the original.
2. pandas 3.0.5 / 3.0.6 DatetimeLikeArrayMixin.__getitem__ without its runtime Union, as s2/pandas_speed.py does for the update: the same
   super() call, the same scalar test, the same frequency, the same object returned.
3. (1167b) the State chronology's parts() on the arrays: a198 and the stress map's State layer, started by their callers with
   [sys.executable, <script>], are run through run_rewritten.py (pyboot_fast.py), only for the files it knows by SHA-256.
4. (1167b) the same parts() in the stress map's county path (run_v4_main of stress_map_v2_1052)."""
import sys, hashlib, importlib.abc

_DD_SHA = '7b06690898f1d617d9cc2ed81cd2489bd3263e50fed6236eb965dcc2d1f97fe9'
_PD_WANT = '''    def __getitem__(self, key: PositionalIndexer2D) -> Self | DTScalarOrNaT:
        """
        This getitem defers to the underlying array, which by-definition can
        only handle list-likes, slices, and integer scalars
        """
        # Use cast as we know we will get back a DatetimeLikeArray or DTScalar,
        # but skip evaluating the Union at runtime for performance
        # (see https://github.com/pandas-dev/pandas/pull/44624)
        result = cast(Union[Self, DTScalarOrNaT], super().__getitem__(key))
        if lib.is_scalar(result):
            return result
        else:
            # At this point we know the result is an array.
            result = cast(Self, result)
        # error: Incompatible types in assignment (expression has type
        # "BaseOffset | None", variable has type "None")
        result._freq = self._get_getitem_freq(key)  # type: ignore[assignment]
        return result
'''


def _patch_dd(m):
    import inspect
    import numpy as np, pandas as pd
    orig = m.pt_and_cum
    if hashlib.sha256(inspect.getsource(orig).encode()).hexdigest() != _DD_SHA: return

    def pt_and_cum(seg, not_before=None):
        idx = seg.index; vals = seg.to_numpy(dtype=float)
        if len(vals) == 0 or not isinstance(idx, pd.DatetimeIndex) or not (idx.is_monotonic_increasing and idx.is_unique) or np.isnan(vals).any(): return orig(seg, not_before)
        n = len(vals)
        start = np.arange(1, n + 1)                       # a peak's later points start after it ...
        if not_before is not None:                        # ... and not before not_before
            start = np.maximum(start, int(idx.searchsorted(pd.Timestamp(not_before), side='left')))
        sm = np.empty(n + 1); sm[n] = np.inf; sm[:n] = np.minimum.accumulate(vals[::-1])[::-1]
        has = start < n
        if not has.any(): return 0.0, 0.0
        lm = np.where(has, sm[np.minimum(start, n)], np.nan)
        f = np.where(has, (vals - lm) / vals * 100.0, -np.inf)
        i = int(np.argmax(f)); fi = f[i]                  # the first position of the largest fall: the original loop's last update
        if not fi > 0.0: return 0.0, 0.0
        x = (vals[i] - vals[start[i]:]) / vals[i] * 100.0
        return fi, float(np.where(x < 0, 0.0, x).sum())
    pt_and_cum.__doc__ = orig.__doc__; pt_and_cum._bhs_orig = orig
    m.pt_and_cum = pt_and_cum


def _patch_pd(m):
    import inspect
    from importlib.metadata import version
    if version('pandas') not in ('3.0.5', '3.0.6'): return
    C = m.DatetimeLikeArrayMixin; cur = C.__dict__.get('__getitem__')
    if getattr(cur, '_bhs_fast', False) or inspect.getsource(cur) != _PD_WANT: return
    is_scalar = m.lib.is_scalar

    def __getitem__(self, key):
        result = super(C, self).__getitem__(key)
        if is_scalar(result):
            return result
        result._freq = self._get_getitem_freq(key)
        return result
    __getitem__.__doc__ = cur.__doc__; __getitem__.__qualname__ = cur.__qualname__; __getitem__._bhs_fast = True; __getitem__._bhs_orig = cur
    C.__getitem__ = __getitem__


def _patch_subprocess(m):
    """3 (1167b). [sys.executable, <script>] for a script run_rewritten.py knows (its SHA-256) starts run_rewritten.py with it: the
    script's parts() on the arrays (pyboot_fast.py). LT_PYBOOT_REWRITE=0 leaves every command as it is."""
    import os
    if os.environ.get('LT_PYBOOT_REWRITE') == '0': return
    P = m.Popen; cur = P.__init__
    if getattr(cur, '_bhs_fast', False): return
    here = os.path.dirname(os.path.abspath(__file__)); runner = os.path.join(here, 'run_rewritten.py')
    if not os.path.exists(runner): return

    def __init__(self, args, *a, **k):
        try:
            if (type(args) in (list, tuple) and len(args) == 2 and args[0] == sys.executable and isinstance(args[1], str)
                    and args[1].endswith('.py') and not k.get('shell') and not a):
                path = args[1] if os.path.isabs(args[1]) else os.path.join(k.get('cwd') or os.getcwd(), args[1])
                import importlib.util
                spec = importlib.util.spec_from_file_location('_bhs_run_rewritten', runner); rr = importlib.util.module_from_spec(spec); spec.loader.exec_module(rr)
                if rr.sha_of(path) in rr.REWRITES: args = [args[0], runner, args[1]]
        except Exception:
            pass
        cur(self, args, *a, **k)
    __init__.__doc__ = cur.__doc__; __init__._bhs_fast = True; __init__._bhs_orig = cur
    P.__init__ = __init__


_SM2_SHA = '7de81b0575fb412e2fb2b3a6fac0918ffc219d3a820028b09d10cc03401229f5'   # 1052 code/stress_map_v2_1052.py, read on 25 Nov 2026
_V1_SHA = '2b841ee52de7441e97530f670ccfce70b3076b6f26ccf0920109a265e37f5d44'    # 1052 code/stress_map_v1_1052.py
_V1_SHA_Q = '94ec0ac0c619cf5fd25aae6fd66e8968ddbd3e3286717f1c371f79477e04fba5'  # the same since c2f1d5e3 (#147, 26 Nov 2026: parts() with q; 1167m)


def _patch_sm2(m):
    """4 (1167b). The stress map's county layer: stress_map_v2_1052 builds run_v4_main (the county path, c0_county_v3) from the v1
    script's run_v4 by two textual changes; here it is built the same way with the third, the parts() call of run_rewritten.py. Only
    for the two files read on 25 Nov 2026 (SHA-256). stress_map_cached.py calls this for the module it loads; the county workers, which
    import the module by name, get it from the finder below. LT_PYBOOT_REWRITE=0 leaves it as it is. 1167m (27 Nov 2026): also the v1 file of
    c2f1d5e3 (#147: parts() with the production dimension q), with run_rewritten.py's _NESTED_Q."""
    import os, importlib.util
    if os.environ.get('LT_PYBOOT_REWRITE') == '0' or getattr(m, '_bhs_sm2', False): return

    def sha(p):
        with open(p, 'rb') as f: return hashlib.sha256(f.read()).hexdigest()
    v1 = sha(m.V1PY) if sha(m.__file__) == _SM2_SHA else None
    if v1 not in (_V1_SHA, _V1_SHA_Q): return
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location('_bhs_run_rewritten', os.path.join(here, 'run_rewritten.py')); rr = importlib.util.module_from_spec(spec); spec.loader.exec_module(rr)
    old, new = rr._NESTED if v1 == _V1_SHA else rr._NESTED_Q
    src = m._src
    if src.count(old) != 1 or src.count("def run_v4(") != 1 or src.count("w2, _ = dc.windows(dev, 2, 2, 6)") != 1: return
    exec(src.replace(old, new).replace("def run_v4(", "def run_v4_main(").replace("w2, _ = dc.windows(dev, 2, 2, 6)", "w2 = []"), m._G3)
    m.run_v4_main = m._G3['run_v4_main']; m._bhs_sm2 = True


_TARGETS = {'damage_dimensions_live_v376': _patch_dd, 'pandas.core.arrays.datetimelike': _patch_pd, 'subprocess': _patch_subprocess,
            'stress_map_v2_1052': _patch_sm2}


class _Finder(importlib.abc.MetaPathFinder):
    """finds the two modules with the other finders and makes the replacement right after each is first executed"""
    def find_spec(self, name, path, target=None):
        if name not in _TARGETS: return None
        spec = None
        for f in sys.meta_path:
            if f is self or not hasattr(f, 'find_spec'): continue
            spec = f.find_spec(name, path, target)
            if spec is not None: break
        if spec is None or spec.loader is None or not hasattr(spec.loader, 'exec_module'): return spec
        orig = spec.loader.exec_module

        def exec_module(module, _orig=orig, _fix=_TARGETS[name]):
            _orig(module)
            try: _fix(module)
            except Exception as e: print('pyboot (1167): %s left as it is (%s: %s)' % (module.__name__, type(e).__name__, e), file=sys.stderr)
        spec.loader.exec_module = exec_module
        return spec


if not any(type(f).__name__ == '_Finder' and type(f).__module__ == __name__ for f in sys.meta_path):
    sys.meta_path.insert(0, _Finder())
if 'subprocess' in sys.modules:                       # imported before this file ran: replaced at once
    try: _patch_subprocess(sys.modules['subprocess'])
    except Exception as e: print('pyboot (1167b): subprocess left as it is (%s: %s)' % (type(e).__name__, e), file=sys.stderr)
