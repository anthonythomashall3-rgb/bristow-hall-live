#!/usr/bin/env python3
"""Where does the screen's time actually go? Measured, not assumed.

The equality check reported the fast engine and the original agreeing exactly while running at the
same speed, which means the rewritten functions are not where the screen spends its time on those
channels. Guessing a second time would be the same mistake, so this profiles a named channel under
both engines and prints the callees by cumulative time.
"""
import os, sys, time, cProfile, pstats, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screen_1969 as S
import screen_1969_fast as F

sid = sys.argv[1] if len(sys.argv) > 1 else 'TOTBORR'
slow_funcs = (S.daily, S.hold, S.episodes)

S.daily, S.hold, S.episodes = slow_funcs
S.init()
t0 = time.time(); a = S.one(sid); t_slow = time.time() - t0
pr = cProfile.Profile(); pr.enable(); S.one(sid); pr.disable()
b_ = io.StringIO(); pstats.Stats(pr, stream=b_).sort_stats('cumulative').print_stats(12)
print('=== SLOW  %s  %.2f s, %d rows ===' % (sid, t_slow, len(a)))
print('\n'.join(b_.getvalue().splitlines()[4:20]))

F._patch(); S.init()
t0 = time.time(); c = S.one(sid); t_fast = time.time() - t0
pr = cProfile.Profile(); pr.enable(); S.one(sid); pr.disable()
b_ = io.StringIO(); pstats.Stats(pr, stream=b_).sort_stats('cumulative').print_stats(12)
print('\n=== FAST  %s  %.2f s, %d rows ===' % (sid, t_fast, len(c)))
print('\n'.join(b_.getvalue().splitlines()[4:20]))
print('\nidentical rows: %s   speedup %.1fx' % (a == c, t_slow / max(t_fast, 1e-9)))
