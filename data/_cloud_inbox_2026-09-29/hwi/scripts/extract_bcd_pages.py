#!/usr/bin/env python3
"""Compact raw store for BCD issues (disk budget): for each issue keep
  raw/fraser/text/<stem>.txt.gz        layout text of every page (form-feed separated)
  raw/fraser/cand/<stem>_pNNN.words.json.gz   pdfplumber word boxes for candidate pages (series 46/60 tables)
  raw/fraser/cand/<stem>_pNNN.png      1-bit page image of candidate pages (for tesseract re-OCR)
then delete the full PDF (and any earlier single-page PDFs).
Candidates: pages mentioning help-wanted (any OCR variant) with >=6 month names, or employment/unemployment/basic-data
pages with >=12 month names.
"""
import os, re, glob, subprocess, json, sys, gzip
import pdfplumber

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(W, 'raw', 'fraser', 'pdf')
OLD = os.path.join(W, 'raw', 'fraser', 'pages')
TXT = os.path.join(W, 'raw', 'fraser', 'text')
CAND = os.path.join(W, 'raw', 'fraser', 'cand')
os.makedirs(TXT, exist_ok=True); os.makedirs(CAND, exist_ok=True)
MON = re.compile(r'\b(January|February|March|April|May|June|July|August|September|October|November|December|'
                 r'Jan\.|Feb\.|Mar\.|Apr\.|Aug\.|Sept\.|Oct\.|Nov\.|Dec\.)', re.I)
HELP = re.compile(r'h[ae]l[pn][- ]?w|help|wanted|wonted|w[ai]nte[dt]|vacanc', re.I)
EMP = re.compile(r'EMPLOYMENT AND UNEMPLOYMENT|UNEMPLOYMENT|BASIC DATA|Basic Data|Job Vacanc', re.I)


def is_cand(pg):
    nm = len(MON.findall(pg))
    return (HELP.search(pg) and nm >= 6) or (EMP.search(pg) and nm >= 12)


def save_page(pdf_path, page_index, stem, pno):
    with pdfplumber.open(pdf_path) as pdf:
        p = pdf.pages[page_index]
        words = p.extract_words(keep_blank_chars=False, x_tolerance=1.5, y_tolerance=2)
        rec = dict(width=float(p.width), height=float(p.height),
                   words=[dict(t=w['text'], x0=round(w['x0'], 2), x1=round(w['x1'], 2), top=round(w['top'], 2),
                               bottom=round(w['bottom'], 2)) for w in words])
    with gzip.open(os.path.join(CAND, f'{stem}_p{pno:03d}.words.json.gz'), 'wt') as f:
        json.dump(rec, f)
    # page image (1-bit PNG at 300 dpi)
    subprocess.run(['pdftoppm', '-r', '300', '-mono', '-png', '-f', str(pno), '-l', str(pno), '-singlefile',
                    pdf_path, os.path.join(CAND, f'{stem}_p{pno:03d}')], check=False)


def process_full(f):
    stem = os.path.basename(f)[:-4]
    r = subprocess.run(['pdftotext', '-layout', f, '-'], capture_output=True, text=True)
    pages = r.stdout.split('\f')
    with gzip.open(os.path.join(TXT, stem + '.txt.gz'), 'wt') as g:
        g.write(r.stdout)
    keep = [i for i, pg in enumerate(pages, 1) if is_cand(pg)]
    for i in keep:
        save_page(f, i - 1, stem, i)
    return len(pages), keep


def process_old(stem):
    """issue whose full PDF was already deleted: use single-page PDFs + their texts."""
    txts = sorted(glob.glob(os.path.join(OLD, stem + '_p*.txt')))
    keep = []
    for t in txts:
        pno = int(re.search(r'_p(\d+)\.txt$', t).group(1))
        pg = open(t).read()
        sp = t[:-4] + '.pdf'
        if is_cand(pg) and os.path.exists(sp):
            save_page(sp, 0, stem, pno)
            # pdftoppm page numbering inside the single-page PDF is 1
            src = os.path.join(CAND, f'{stem}_p{pno:03d}')
            subprocess.run(['pdftoppm', '-r', '300', '-mono', '-png', '-singlefile', sp, src], check=False)
            keep.append(pno)
    with gzip.open(os.path.join(TXT, stem + '.partial_pages.txt.gz'), 'wt') as g:
        for t in txts:
            g.write(f'=== {os.path.basename(t)}\n' + open(t).read() + '\f')
    return None, keep


SHARED = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/claims_pre1975/pdf/bcd'


def main():
    """Process every issue in raw/fraser/index.json. Source PDF: own copy (1977+) or the shared read-only
    copy (1961-10..1976-12, collected by the claims agent). PNG page images kept only for 1977+ strict
    candidates (older ones can be re-rendered from the shared copy)."""
    idx = json.load(open(os.path.join(W, 'raw', 'fraser', 'index.json')))
    log = open(os.path.join(W, 'raw', 'fraser', 'cand_index.jsonl'), 'a')
    for it in sorted(idx, key=lambda d: d['sortDate']):
        stem = f"{it['sortDate']}_{it['item_id']}"
        if os.path.exists(os.path.join(CAND, stem + '.done')):
            continue
        own = os.path.join(PDF, stem + '.pdf')
        y, m = it['sortDate'][:4], it['sortDate'][5:7]
        shared = os.path.join(SHARED, f'bcd_{y}_{m}.pdf')
        src = own if os.path.exists(own) else (shared if os.path.exists(shared) else None)
        if not src:
            log.write(json.dumps(dict(stem=stem, error='no pdf')) + '\n'); continue
        r = subprocess.run(['pdftotext', '-layout', src, '-'], capture_output=True, text=True)
        pages = r.stdout.split('\f')
        with gzip.open(os.path.join(TXT, stem + '.txt.gz'), 'wt') as g:
            g.write(r.stdout)
        keep = [i for i, pg in enumerate(pages, 1) if is_cand(pg)]
        strict = [i for i in keep if HELP.search(pages[i - 1]) and len(MON.findall(pages[i - 1])) >= 12]
        try:
            with pdfplumber.open(src) as pdf:
                for i in keep:
                    p = pdf.pages[i - 1]
                    words = p.extract_words(keep_blank_chars=False, x_tolerance=1.5, y_tolerance=2)
                    rec = dict(width=float(p.width), height=float(p.height), source_pdf=os.path.basename(src),
                               words=[dict(t=w['text'], x0=round(w['x0'], 2), x1=round(w['x1'], 2),
                                           top=round(w['top'], 2), bottom=round(w['bottom'], 2)) for w in words])
                    with gzip.open(os.path.join(CAND, f'{stem}_p{i:03d}.words.json.gz'), 'wt') as f:
                        json.dump(rec, f)
        except Exception as e:
            log.write(json.dumps(dict(stem=stem, error=repr(e))) + '\n')
        if src == own:
            for i in strict:
                subprocess.run(['pdftoppm', '-r', '300', '-mono', '-png', '-f', str(i), '-l', str(i), '-singlefile',
                                src, os.path.join(CAND, f'{stem}_p{i:03d}')], check=False)
        open(os.path.join(CAND, stem + '.done'), 'w').write(json.dumps(dict(keep=keep, strict=strict, src=src)))
        log.write(json.dumps(dict(stem=stem, src=src, npages=len(pages), kept=keep, strict=strict)) + '\n'); log.flush()
        if src == own and '--delete' in sys.argv:
            os.remove(own)
        print(stem, len(pages), keep, strict, flush=True)


if __name__ == '__main__':
    main()
