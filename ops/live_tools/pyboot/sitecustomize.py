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
   super() call, the same scalar test, the same frequency, the same object returned."""
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


_TARGETS = {'damage_dimensions_live_v376': _patch_dd, 'pandas.core.arrays.datetimelike': _patch_pd}


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
