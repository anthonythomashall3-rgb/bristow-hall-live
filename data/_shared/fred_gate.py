#!/usr/bin/env python3
"""One FRED rate limit for every collector on this Mac (17 September 2026).

Two collectors run here — the standing collector (collection 191) and the queue collector (`_collector`) — and each
throttled itself alone. FRED's edge counts requests per address, not per program, so between them they collected 55
"Access Denied" blocks. This file is the shared gate: every FRED request from either collector passes through it, so
the pair together stay under one limit instead of each staying under it separately.

It is a file lock plus a timestamp, nothing more: standard library, no server, no daemon. If the gate file cannot be
used for any reason the call is let through rather than blocked, because a collector that stops collecting is worse
than one that is impolite.

    import sys; sys.path.insert(0, '<data root>/_shared')
    from fred_gate import fred_wait
    fred_wait()                 # returns when it is this process's turn
    ...request...

Both collectors call it. min_interval is the gap between consecutive FRED requests from the whole machine.
"""
import os, time, errno

GATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fred_gate.state')
MIN_INTERVAL = float(os.environ.get('FRED_MIN_INTERVAL', '0.34'))   # about three a second, machine-wide
BLOCK_PAUSE = float(os.environ.get('FRED_BLOCK_PAUSE', '600'))      # after a 403, nobody asks FRED for this long


def _now():
    return time.time()


def fred_wait(min_interval=None):
    """Block until this process may make one FRED request. Returns the seconds waited."""
    gap = MIN_INTERVAL if min_interval is None else min_interval
    t0 = _now()
    try:
        import fcntl
        fd = os.open(GATE, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                raw = os.read(fd, 128).decode().split()
            except Exception:
                raw = []
            last = float(raw[0]) if raw else 0.0
            blocked_until = float(raw[1]) if len(raw) > 1 else 0.0
            now = _now()
            wait = max(last + gap - now, blocked_until - now, 0.0)
            if wait > 0:
                time.sleep(min(wait, 900))
            os.lseek(fd, 0, 0); os.ftruncate(fd, 0)
            os.write(fd, ('%.3f %.3f' % (_now(), blocked_until)).encode())
        finally:
            try: fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception: pass
            os.close(fd)
    except Exception:
        pass            # the gate must never be the reason collection stops
    return _now() - t0


def fred_blocked(seconds=None):
    """Tell the other collector that FRED has refused this address, so it stops asking too."""
    until = _now() + (BLOCK_PAUSE if seconds is None else seconds)
    try:
        import fcntl
        fd = os.open(GATE, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try: raw = os.read(fd, 128).decode().split()
            except Exception: raw = []
            last = float(raw[0]) if raw else 0.0
            prev = float(raw[1]) if len(raw) > 1 else 0.0
            os.lseek(fd, 0, 0); os.ftruncate(fd, 0)
            os.write(fd, ('%.3f %.3f' % (last, max(prev, until))).encode())
        finally:
            try: fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception: pass
            os.close(fd)
    except Exception:
        pass
    return until


if __name__ == '__main__':
    import sys
    if '--status' in sys.argv:
        try:
            raw = open(GATE).read().split()
            print('last request %.1f s ago; blocked for another %.0f s'
                  % (_now() - float(raw[0]), max(0.0, float(raw[1]) - _now())))
        except Exception as e:
            print('gate not yet used', e)
    else:
        print('waited %.3f s' % fred_wait())
