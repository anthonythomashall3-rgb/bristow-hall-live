#!/usr/bin/env python3
"""RAW_FILES.csv: every file under raw/ with bytes, sha256 and a content check (the first bytes must be the
format the name claims -- guards against soft-404 HTML saved under a data name)."""
import os, hashlib, csv

W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/new_candidates'
SIG = {'.pdf': [b'%PDF'], '.xlsx': [b'PK'], '.zip': [b'PK'], '.xls': [bytes.fromhex('d0cf11e0a1b11ae1')]}
rows = []
for root, _, files in os.walk(os.path.join(W, 'raw')):
    for fn in sorted(files):
        p = os.path.join(root, fn)
        b = open(p, 'rb').read()
        ext = os.path.splitext(fn)[1].lower()
        head = b[:8]
        if ext in SIG:
            ok = any(head.startswith(s) for s in SIG[ext])
        elif ext in ('.csv', '.txt', '.jsonl'):
            ok = not head.lstrip().lower().startswith((b'<!doctype', b'<html'))
        else:
            ok = ''
        rows.append(dict(path=os.path.relpath(p, W), bytes=len(b), sha256=hashlib.sha256(b).hexdigest(),
                         content_matches_extension=ok))
with open(os.path.join(W, 'RAW_FILES.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
bad = [r['path'] for r in rows if r['content_matches_extension'] is False]
print(len(rows), 'files;', len(bad), 'content mismatches', bad[:10])
