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
    import pickle, hashlib, subprocess
    for c in (['lscpu'], ['cat', '/sys/fs/cgroup/cpu.max'], ['cat', '/proc/pressure/cpu']):
        try: print('probe: %s: %s' % (c[-1], ' | '.join(l.strip() for l in subprocess.run(c, capture_output=True, text=True).stdout.splitlines() if any(w in l for w in ('Thread', 'Core', 'Socket', 'Model name', 'CPU(s)', 'max', 'some', 'full')) or c[0] == 'cat')[:400]), flush=True)
        except Exception as e: print('probe:', c, e)
    A = ARGS[:96]
    t = time.perf_counter(); c = time.process_time(); r = [timed(a) for a in A[:24]]
    print('probe: serial (this process, fast path %s) 24 counties: wall %.2f s, cpu %.2f s, %.3f s a county' % (getattr(sm, '_bhs_sm2', False), time.perf_counter() - t, time.process_time() - c, (time.perf_counter() - t) / 24), flush=True)
    for name, procs, n, env in (('1 proc', 1, 24, {}), ('2 procs', 2, 48, {}), ('4 procs', 4, 96, {}), ('4 procs, BLAS 2 threads', 4, 96, {'OPENBLAS_NUM_THREADS': '2'}),
                                ('4 procs, BLAS 1 thread (timing only)', 4, 96, {'OPENBLAS_NUM_THREADS': '1'}), ('4 procs again', 4, 96, {})):
        old = {k: os.environ.get(k) for k in env}; os.environ.update(env)
        try:
            t = time.perf_counter()
            with cf.ProcessPoolExecutor(procs, mp_context=mp.get_context('spawn')) as ex: R = list(ex.map(timed, A[:n], chunksize=8))
            w = time.perf_counter() - t
            with cf.ProcessPoolExecutor(procs, mp_context=mp.get_context('spawn')) as ex: RR = list(ex.map(sm.c0_county_v3, A[:24], chunksize=6))
            print('probe: %-38s %d counties wall %.1f s (%.3f s a county), per county in a worker: wall %.3f s cpu %.3f s; fast path %s; sha(24) %s'
                  % (name, n, w, w / n, sum(x[0] for x in R) / n, sum(x[1] for x in R) / n, sorted({x[2] for x in R}), hashlib.sha256(pickle.dumps(RR, protocol=5)).hexdigest()[:16]), flush=True)
        except Exception as e:
            print('probe: %s failed: %s: %s' % (name, type(e).__name__, e), flush=True)
        finally:
            for k, v in old.items():
                if v is None: os.environ.pop(k, None)
                else: os.environ[k] = v
    import pyboot_fast as pf
    print('probe: pyboot_fast STATS in this process', dict(pf.STATS), flush=True)

if __name__ == '__main__':
    main()
