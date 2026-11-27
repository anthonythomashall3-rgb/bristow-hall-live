# -*- coding: utf-8 -*-
"""1167m PROBE (27 Nov 2026), not for main: why the stress map's county layer takes 15-22 minutes on GitHub (4 processes) and about
2 minutes in the cloud session (2 processes). Times the county worker (c0_county_v3) on the first counties of the real inputs under
several pools and prints wall and CPU time per county, the fast path's flag in each worker, and the BLAS threads. Writes nothing."""
import os, sys, time, json, importlib.util, multiprocessing as mp

C = '/Users/anthonyhall/Projects/Onset Detector Data/1052_stress_map_fix_parse_collect_2026-11-12'


def blas_threads():
    try:
        from threadpoolctl import threadpool_info
        return [(i.get('internal_api'), i.get('num_threads')) for i in threadpool_info()]
    except Exception:
        return os.environ.get('OPENBLAS_NUM_THREADS', 'default')


def timed(a):
    import stress_map_v2_1052 as m
    t, c = time.perf_counter(), time.process_time()
    m.c0_county_v3(a)
    return time.perf_counter() - t, time.process_time() - c, bool(getattr(m, '_bhs_sm2', False)), os.getpid()


class Stop(Exception):
    pass


def main():
    sys.argv = [os.path.join(C, 'code', 'stress_map_v2_1052.py'), '--all']
    sys.path.insert(0, os.path.join(C, 'code'))
    spec = importlib.util.spec_from_file_location('stress_map_v2_1052', sys.argv[0])
    sm = importlib.util.module_from_spec(spec); sys.modules['stress_map_v2_1052'] = sm; spec.loader.exec_module(sm)
    sc = sys.modules.get('sitecustomize')
    if sc is not None and hasattr(sc, '_patch_sm2'): sc._patch_sm2(sm)
    import concurrent.futures as cf
    ARGS = []
    class Grab:
        def __init__(self, n, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def map(self, fn, it, chunksize=1): ARGS.extend(it); raise Stop()
    real = cf.ProcessPoolExecutor; cf.ProcessPoolExecutor = Grab
    t = time.perf_counter(); CSH = sm.step_county_shapes(); L = sm.step_fetch_laus()
    try: sm.step_counties(CSH, 4, L)
    except Stop: pass
    cf.ProcessPoolExecutor = real
    print('probe: %s, nproc %s, cpu_count %s, affinity %s, %d counties, inputs %.1f s; parent fast path %s; BLAS %s; default start %s'
          % (sys.version.split()[0], os.cpu_count(), mp.cpu_count(), len(os.sched_getaffinity(0)), len(ARGS), time.perf_counter() - t,
             getattr(sm, '_bhs_sm2', False), blas_threads(), mp.get_start_method()), flush=True)
    try: print('probe: cpu model', [l.split(':', 1)[1].strip() for l in open('/proc/cpuinfo') if l.startswith('model name')][:1], 'load', os.getloadavg(), flush=True)
    except Exception: pass
    A = ARGS[:384]
    t = time.perf_counter(); r = [timed(a) for a in A[:16]]
    print('probe: serial (this process) 16 counties: wall %.2f s, cpu %.2f s, per county %.3f s' % (time.perf_counter() - t, sum(x[1] for x in r), (time.perf_counter() - t) / 16), flush=True)
    import pickle, hashlib
    for name, env in (('BLAS threads spin (as before 1167m)', {'OPENBLAS_THREAD_TIMEOUT': None}), ('OPENBLAS_THREAD_TIMEOUT=4', {'OPENBLAS_THREAD_TIMEOUT': '4'})):
        old = {k: os.environ.get(k) for k in env}
        for k, v in env.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
        try:
            t = time.perf_counter()
            with cf.ProcessPoolExecutor(4, mp_context=mp.get_context('spawn')) as ex: R = list(ex.map(sm.c0_county_v3, A, chunksize=16))
            w = time.perf_counter() - t
            print('probe: %-36s 4 procs (spawn): %d counties wall %.1f s (%.3f s a county), results sha %s'
                  % (name, len(A), w, w / len(A), hashlib.sha256(pickle.dumps(R, protocol=5)).hexdigest()[:16]), flush=True)
        except Exception as e:
            print('probe: %s failed: %s: %s' % (name, type(e).__name__, e), flush=True)
        finally:
            for k, v in old.items():
                if v is None: os.environ.pop(k, None)
                else: os.environ[k] = v

if __name__ == '__main__':
    main()
