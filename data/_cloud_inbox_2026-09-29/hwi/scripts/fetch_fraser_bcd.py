#!/usr/bin/env python3
"""Fetch FRASER title 43 (Business Cycle Developments / Business Conditions Digest)
item metadata + FRASER OCR text for every issue. Plain urllib (default UA), >=1.1 s between requests.
Usage: fetch_fraser_bcd.py [--pdf]   (--pdf also downloads the PDFs)
"""
import json, os, re, sys, time, urllib.request

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(W, 'raw', 'fraser')
os.makedirs(os.path.join(RAW, 'meta'), exist_ok=True)
os.makedirs(os.path.join(RAW, 'txt'), exist_ok=True)
os.makedirs(os.path.join(RAW, 'pdf'), exist_ok=True)
BASE = 'https://fraser.stlouisfed.org'
last = [0.0]

def get(url, dest=None, tries=4):
    for k in range(tries):
        dt = time.time() - last[0]
        if dt < 1.1:
            time.sleep(1.1 - dt)
        last[0] = time.time()
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                data = r.read()
            if dest:
                with open(dest, 'wb') as f:
                    f.write(data)
            return data
        except Exception as e:
            print('ERR', url, e, file=sys.stderr)
            time.sleep(3 * (k + 1))
    return None

def main():
    want_pdf = '--pdf' in sys.argv
    title_id = os.environ.get('TITLE_ID', '43')
    items = [l.strip() for l in open(os.path.join(RAW, 'items.txt')) if l.strip()]
    ids = sorted({int(re.search(r'-(\d+)$', l).group(1)) for l in items})
    index = []
    for iid in ids:
        mp = os.path.join(RAW, 'meta', f'{iid}.json')
        if not os.path.exists(mp):
            get(f'{BASE}/metadata.php?type=item&id={iid}&json=1', mp)
        try:
            m = json.load(open(mp))
        except Exception:
            print('bad meta', iid, file=sys.stderr); continue
        loc = m.get('location', {})
        pdf = (loc.get('pdfUrl') or [''])[0]
        txt = (loc.get('textUrl') or [''])[0]
        sd = m.get('originInfo', {}).get('sortDate', '')
        title = m.get('titleInfo', [{}])[0].get('title', '')
        index.append(dict(item_id=iid, sortDate=sd, title=title, pdfUrl=pdf, textUrl=txt,
                          url=(loc.get('url') or [''])[0]))
        if txt:
            tp = os.path.join(RAW, 'txt', f'{sd}_{iid}.txt')
            if not os.path.exists(tp):
                get(txt, tp)
        if want_pdf and pdf:
            pp = os.path.join(RAW, 'pdf', f'{sd}_{iid}.pdf')
            if not os.path.exists(pp):
                get(pdf, pp)
        print(iid, sd, title, flush=True)
    json.dump(index, open(os.path.join(RAW, 'index.json'), 'w'), indent=1)

if __name__ == '__main__':
    main()
