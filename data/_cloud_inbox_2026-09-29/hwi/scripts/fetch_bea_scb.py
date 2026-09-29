#!/usr/bin/env python3
"""Fetch Survey of Current Business issues from BEA's SCB archive (apps.bea.gov/scb/issues/YYYY/scb-YYYY-month.pdf),
keep only the pages that mention help-wanted advertising (layout text + single-page PDF), delete the full PDF.
Plain urllib default UA, >=1.2 s between requests.
Usage: fetch_bea_scb.py START_YYYY END_YYYY
"""
import os, re, sys, time, subprocess, urllib.request, json

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(W, 'raw', 'bea')
PAGES = os.path.join(RAW, 'pages')
os.makedirs(PAGES, exist_ok=True)
MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september',
          'october', 'november', 'december']
last = [0.0]

def get(url, dest, tries=4):
    for k in range(tries):
        dt = time.time() - last[0]
        if dt < 1.2:
            time.sleep(1.2 - dt)
        last[0] = time.time()
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                data = r.read()
            open(dest, 'wb').write(data)
            return True
        except Exception as e:
            print('ERR', url, e, file=sys.stderr)
            if '404' in str(e):
                return False
            time.sleep(4 * (k + 1))
    return False

def main():
    y0, y1 = int(sys.argv[1]), int(sys.argv[2])
    html = open(os.path.join(RAW, 'scb_issues.html')).read()
    links = sorted(set(re.findall(r'href="(/scb/issues/(\d{4})/scb-\d{4}-[a-z-]+\.pdf)"', html)))
    log = open(os.path.join(RAW, 'scb_fetch_log.jsonl'), 'a')
    for path, yr in links:
        yr = int(yr)
        if not (y0 <= yr <= y1):
            continue
        stem = os.path.basename(path)[:-4]
        done = os.path.join(PAGES, stem + '.done')
        if os.path.exists(done):
            continue
        url = 'https://apps.bea.gov' + path
        tmp = os.path.join(RAW, stem + '.pdf')
        if not os.path.exists(tmp) and not get(url, tmp):
            log.write(json.dumps(dict(stem=stem, url=url, status='fetch_failed')) + '\n'); continue
        try:
            npages = int(re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', tmp], capture_output=True, text=True).stdout).group(1))
        except Exception:
            log.write(json.dumps(dict(stem=stem, url=url, status='bad_pdf')) + '\n'); os.remove(tmp); continue
        full = subprocess.run(['pdftotext', '-layout', tmp, '-'], capture_output=True, text=True).stdout
        pages = full.split('\f')
        hits = []
        for i, pg in enumerate(pages, start=1):
            if re.search(r'help.{0,3}wanted|help.{0,3}wonted|helpwanted', pg, re.I):
                hits.append(i)
                open(os.path.join(PAGES, f'{stem}_p{i:03d}.txt'), 'w').write(pg)
                subprocess.run(['pdfseparate', '-f', str(i), '-l', str(i), tmp,
                                os.path.join(PAGES, f'{stem}_p{i:03d}.pdf')])
        log.write(json.dumps(dict(stem=stem, url=url, status='ok', npages=npages, hit_pages=hits)) + '\n')
        log.flush()
        open(done, 'w').write(json.dumps(hits))
        os.remove(tmp)
        print(stem, npages, hits, flush=True)

if __name__ == '__main__':
    main()
