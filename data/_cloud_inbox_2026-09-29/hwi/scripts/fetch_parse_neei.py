#!/usr/bin/env python3
"""Federal Reserve Bank of Boston, New England Economic Indicators (monthly PDF reports, 2002+ online at
https://www.bostonfed.org/-/media/Documents/neei/reports/<mon><yy>.pdf). Each report prints a table
"Help-Wanted Advertising Index (index, 1987 = 100, seasonally adjusted)" with a United States column
(source: The Conference Board). Fetch, save raw PDF + layout text, parse the US column.
Publication date proxy: PDF CreationDate (production date) -- recorded with date_basis='pdf_creation_date'.
"""
import os, re, sys, time, subprocess, urllib.request, json
import pandas as pd

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(W, 'raw', 'neei')
os.makedirs(D, exist_ok=True)
MONS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
FULL = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
        'November', 'December']
last = [0.0]


def get(url, dest):
    if os.path.exists(dest):
        return True
    dt = time.time() - last[0]
    if dt < 1.3:
        time.sleep(1.3 - dt)
    last[0] = time.time()
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            data = r.read(); ctype = r.headers.get('Content-Type', '')
    except Exception as e:
        print('ERR', url, e, file=sys.stderr); return False
    if 'pdf' not in ctype and not data[:4] == b'%PDF':
        open(os.path.join(D, 'missing.txt'), 'a').write(url + '\n')
        return False
    open(dest, 'wb').write(data)
    return True


def parse(pdf):
    txt = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True).stdout
    info = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
    m = re.search(r'CreationDate:\s+(.*)', info)
    cdate = m.group(1).strip() if m else ''
    rows = []
    pages = txt.split('\f')
    for pno, pg in enumerate(pages, 1):
        lines = pg.split('\n')
        for i, ln in enumerate(lines):
            if re.search(r'Help[- ]Wanted Advertising( Index)? \(index', ln, re.I):
                base = re.search(r'(19\d\d)\s*=\s*100', ln)
                for ln2 in lines[i + 1:i + 30]:
                    mm = re.match(r'^\s*(\d{4})\s+(Annual|' + '|'.join(FULL) + r')\s+(\S+)', ln2)
                    if not mm:
                        if rows and re.search(r'Source', ln2):
                            break
                        continue
                    yr, per, tok = mm.groups()
                    if per == 'Annual':
                        continue
                    try:
                        v = float(tok)
                    except ValueError:
                        v = None
                    rows.append(dict(month=f'{int(yr):04d}-{FULL.index(per) + 1:02d}', value=v, raw_token=tok,
                                     page=pno, base=(base.group(1) + '=100') if base else '', line=ln2.strip()))
                break
    return rows, cdate, txt


def main():
    y0, y1 = int(sys.argv[1]), int(sys.argv[2])
    out = []
    for y in range(y0, y1 + 1):
        for k, mo in enumerate(MONS):
            stem = f'{mo}{y % 100:02d}'
            url = f'https://www.bostonfed.org/-/media/Documents/neei/reports/{stem}.pdf'
            pdf = os.path.join(D, f'neei_{y}-{k + 1:02d}.pdf')
            if not get(url, pdf):
                continue
            rows, cdate, txt = parse(pdf)
            open(pdf[:-4] + '.txt', 'w').write(txt)
            m = re.search(r'D:(\d{4})(\d{2})(\d{2})', cdate) or None
            # pdfinfo prints e.g. 'Wed Apr 13 13:43:49 2005 UTC'
            try:
                pdate = pd.to_datetime(cdate.replace(' UTC', ''), format='%a %b %d %H:%M:%S %Y').strftime('%Y-%m-%d')
            except Exception:
                pdate = ''
            for r in rows:
                out.append(dict(publication='New England Economic Indicators (FRB Boston)', issue=f'{y}-{k + 1:02d}',
                                publication_date=pdate, date_basis='pdf_creation_date', month=r['month'],
                                value=r['value'], base=r['base'] or '1987=100', sa_flag='SA', series='46',
                                table='US column', mark='', ocr_doubtful=False, raw_token=r['raw_token'],
                                source_url=url, page=r['page'], note=''))
            print(stem, pdate, len(rows), flush=True)
    df = pd.DataFrame(out)
    os.makedirs(os.path.join(W, 'work'), exist_ok=True)
    df.to_csv(os.path.join(W, 'work', 'neei_long.csv'), index=False)


if __name__ == '__main__':
    main()
