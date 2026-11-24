# -*- coding: utf-8 -*-
"""ONE PANDAS 3.0.5 SLOWDOWN REMOVED, WITH THE SAME RESULTS (1167, 24 Nov 2026; Anthony: "under 3 minutes of data releases"). No AI.

pandas 3.0.5's DatetimeLikeArrayMixin.__getitem__ (pandas/core/arrays/datetimelike.py) begins
    result = cast(Union[Self, DTScalarOrNaT], super().__getitem__(key))
typing.cast returns its second argument unchanged, but Python evaluates the first one on every call: on Python 3.14 that builds and hashes
Union[Self, DTScalarOrNaT] each time a date array is indexed - 3.2 million times in one build of bhs_build.py from an empty memo store, a
third of its profiled time inside pandas (run 45439849420: typing._type_check 18 s and annotationlib.__hash__ 14 s of 262 s profiled).
apply() puts in the same method without the two casts: the same super() call, the same scalar test, the same frequency, the same object
returned. It is applied only to pandas 3.0.5 and only when the method's source is exactly the one read here (a sha256 of it); any other
pandas keeps its own method untouched. Nothing the walk's memo keys read changes (they hash the closers' code, never pandas')."""
import hashlib, inspect

SOURCE_SHA = None   # filled from the source as read below on the first apply (the check is against this text)
WANT = '''    def __getitem__(self, key: PositionalIndexer2D) -> Self | DTScalarOrNaT:
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


def apply():
    """-> 'applied' | 'already' | the reason it was not applied"""
    try:
        import pandas as pd
        import pandas.core.arrays.datetimelike as m
    except Exception as e:
        return 'pandas not importable (%s)' % type(e).__name__
    if pd.__version__ != '3.0.5':
        return 'pandas %s: its own method kept' % pd.__version__
    C = m.DatetimeLikeArrayMixin
    cur = C.__dict__.get('__getitem__')
    if getattr(cur, '_bhs_fast', False):
        return 'already'
    try:
        src = inspect.getsource(cur)
    except Exception as e:
        return 'source not read (%s): its own method kept' % type(e).__name__
    if src != WANT:
        return 'the method is not the one read on 24 Nov 2026 (sha256 %s): its own method kept' % hashlib.sha256(src.encode()).hexdigest()[:12]
    is_scalar = m.lib.is_scalar

    def __getitem__(self, key):
        result = super(C, self).__getitem__(key)
        if is_scalar(result):
            return result
        result._freq = self._get_getitem_freq(key)
        return result
    __getitem__.__doc__ = cur.__doc__; __getitem__.__qualname__ = cur.__qualname__; __getitem__._bhs_fast = True; __getitem__._bhs_orig = cur
    C.__getitem__ = __getitem__
    return 'applied'


if __name__ == '__main__':
    print(apply())
