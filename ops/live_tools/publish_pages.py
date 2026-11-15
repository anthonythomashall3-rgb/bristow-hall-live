#!/usr/bin/env python3
"""LIVE TOOLS ON GITHUB (1052, 15 Nov 2026; no AI): put the pages the run built into this checkout, the way the Mac job's publish step
did (1052 code/publish_live_pages_1052.py, imported, its own put() and norm() used unchanged), without the pull request: the workflow
commits to main itself and starts the site deploy.
  - /state-onset/: 1032 web/state-onset/index.html -> s2/state_onset/page.html
  - /stress-map/ : 1052 web/stress-map/index.html  -> s2/stress_map/page.html (+ s2/stress_map/stress_map_site.py)
  - the data page's Mac-built rows: s2/tool_inputs_mac.py run in this checkout (its json compared with time stamps ignored, as the Mac did)
  - when anything changed, the runner's two site steps once, so site/public/{state-onset,stress-map}/ are committed as the runner writes them.
Writes $LT_OUT/publish_pages.json: {changed: [...]} and exits 0 (1 only on an error)."""
import os, re, sys, json, time, subprocess
ROOT = os.path.expanduser('~/Projects/Onset Detector Data'); C52 = os.path.join(ROOT, '1052_stress_map_fix_parse_collect_2026-11-12')
sys.path.insert(0, os.path.join(C52, 'code')); import publish_live_pages_1052 as P
WT = os.environ.get('GITHUB_WORKSPACE') or os.getcwd(); P.WT = WT
OUTD = os.environ.get('LT_OUT') or '/tmp'
def main():
    R = dict(run=time.strftime('%Y-%m-%dT%H:%M:%S%z'), changed=[])
    try:
        ch = R['changed']
        if P.put(P.STATE_PAGE, f'{P.WS}/s2/state_onset/page.html'): ch.append('state-onset')
        if P.put(P.STRESS_PAGE, f'{P.WS}/s2/stress_map/page.html'): ch.append('stress-map')
        if P.put(P.SM_SITE, f'{P.WS}/s2/stress_map/stress_map_site.py'): ch.append('stress_map_site.py')
        assert P.RUNLINE in open(os.path.join(WT, 'run_cloud.sh')).read(), 'run_cloud.sh has no stress map line'
        tj = os.path.join(WT, P.WS, 's2', 'tool_inputs_mac.json'); old_tj = open(tj).read() if os.path.exists(tj) else ''
        r = subprocess.run([sys.executable, 's2/tool_inputs_mac.py'], cwd=os.path.join(WT, P.WS), capture_output=True, text=True, timeout=600)
        R['tool_inputs_mac'] = dict(rc=r.returncode, tail=(r.stdout[-300:] + r.stderr[-300:]))
        if not os.path.exists(tj): raise RuntimeError('s2/tool_inputs_mac.py wrote no json: ' + R['tool_inputs_mac']['tail'])
        strip = lambda t: re.sub(r'"(built|generated|at|run|written)"\s*:\s*"[^"]*"', '', re.sub(r'\d{4}-\d\d-\d\d[T ]\d\d:\d\d(:\d\d)?(Z|[+-]\d\d:?\d\d)?', 'T', t))
        if strip(open(tj).read()) != strip(old_tj): ch.append('tool_inputs_mac.json')
        else: subprocess.run(['git', 'checkout', '--', os.path.join(P.WS, 's2', 'tool_inputs_mac.json')], cwd=WT)   # only time stamps moved: keep the committed file
        if ch:
            wsd = os.path.join(WT, P.WS)
            R['state_site'] = subprocess.run([sys.executable, 's2/state_onset/state_onset_site.py'], cwd=wsd, capture_output=True, text=True).stdout[-300:]
            R['stress_site'] = subprocess.run([sys.executable, 's2/stress_map/stress_map_site.py'], cwd=wsd, capture_output=True, text=True).stdout[-300:]
            if 'page NOT written' in R['stress_site']: raise RuntimeError('stress_map_site.py did not write the page: ' + R['stress_site'])
        R['ok'] = True
    except Exception as e:
        R['ok'] = False; R['error'] = f'{type(e).__name__}: {e}'[:1000]
    json.dump(R, open(os.path.join(OUTD, 'publish_pages.json'), 'w'), indent=1); print(json.dumps(R)[:2000])
    return 0 if R['ok'] else 1
if __name__ == '__main__': sys.exit(main())
