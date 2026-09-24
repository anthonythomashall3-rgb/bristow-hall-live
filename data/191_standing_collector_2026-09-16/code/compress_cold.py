#!/usr/bin/env python3
"""Compressing the cold collections in place, reversibly (18 September 2026).

The disk is the binding constraint within about a fortnight at the present rate of collection. Two collections hold
most of the compressible weight: 112 (state high frequency, 47.5 GiB, mostly comma-separated text) and 110 (the state
recession panel, 5.1 GiB in a hundred and twelve thousand small files). Text of that kind compresses by roughly three
quarters, so this is the cheapest space there is.

Rules it keeps to, because these collections belong to another line of work as well as this one:
  * only files that have not been modified for `--older-than` days (14 by default), so nothing in flight is touched;
  * only text formats - csv, txt, tsv, htm, html, json, xml - above 100 kB, where compression actually pays;
  * never anything under code/, .git/ or a folder named vintages (already compressed), and never a file already
    compressed;
  * every file keeps its name with .gz added, which pandas, the collector's own reader and gzip all open directly;
  * an index is written listing every file compressed, its old and new size, so the change is auditable;
  * a RESTORE.sh is written beside it that puts everything back with one command.

Default is a dry run. `--apply` does the work.

  python3 code/compress_cold.py                             report only
  python3 code/compress_cold.py --apply                     compress collections 112 and 110
  python3 code/compress_cold.py --apply --only 112_state    a single collection
"""
import os, sys, csv, gzip, time, shutil, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TARGETS = ['112_state_high_frequency_2026-09-12', '110_state_recession_panel_2026-09-12']
EXT = ('.csv', '.txt', '.tsv', '.htm', '.html', '.json', '.xml', '.tab', '.dat')
SKIP_DIRS = {'code', '.git', 'vintages', '__pycache__', 'venv', '.venv'}
MIN_BYTES = 100 * 1024


def gib(b):
    return '%.2f GiB' % (b / 2 ** 30) if b >= 2 ** 30 else '%.0f MiB' % (b / 2 ** 20)


def candidates(base, older_than_days):
    cutoff = time.time() - older_than_days * 86400
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if not f.lower().endswith(EXT):
                continue
            p = os.path.join(dp, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size < MIN_BYTES or st.st_mtime > cutoff:
                continue
            if os.path.exists(p + '.gz'):
                continue
            yield p, st.st_size, st.st_mtime


def compress(p, size, mtime, index_writer):
    tmp = p + '.gz.tmp'
    try:
        with open(p, 'rb') as a, gzip.open(tmp, 'wb', compresslevel=6) as b:
            shutil.copyfileobj(a, b, 1 << 20)
        new = os.path.getsize(tmp)
        if new >= size:                       # already dense: leave the original alone
            os.remove(tmp); return 0
        os.replace(tmp, p + '.gz')
        os.utime(p + '.gz', (mtime, mtime))   # the copy keeps the original's date, so freshness rules still hold
        os.remove(p)
        index_writer.writerow([os.path.relpath(p, ROOT), size, new, round(100 * (1 - new / size))])
        return size - new
    except Exception:
        for q in (tmp,):
            try: os.remove(q)
            except OSError: pass
        return 0


RESTORE = '''#!/bin/sh
# Undoes code/compress_cold.py for this collection. Every file listed in COMPRESSED.csv is unzipped back to its
# original name and date. Safe to run twice.
set -e
cd "$(dirname "$0")"
tail -n +2 COMPRESSED.csv | cut -d, -f1 | while IFS= read -r rel; do
  f="../$rel"
  if [ -f "$f.gz" ]; then gunzip -k -f "$f.gz" && rm -f "$f.gz"; fi
done
echo "restored"
'''


def main():
    apply = '--apply' in sys.argv
    only = None
    if '--only' in sys.argv:
        only = sys.argv[sys.argv.index('--only') + 1]
    days = 14
    if '--older-than' in sys.argv:
        days = int(sys.argv[sys.argv.index('--older-than') + 1])
    du = shutil.disk_usage(ROOT)
    print('disk before: %s free of %s' % (gib(du.free), gib(du.total)))
    grand = 0
    for name in TARGETS:
        if only and only not in name:
            continue
        base = os.path.join(ROOT, name)
        if not os.path.isdir(base):
            print('  missing', name); continue
        items = list(candidates(base, days))
        total = sum(s for _, s, _ in items)
        print('\n%s\n  %d files eligible, %s, untouched for %d days or more' % (name, len(items), gib(total), days))
        if not items:
            continue
        if not apply:
            for p, s, _ in sorted(items, key=lambda x: -x[1])[:5]:
                print('    %-70s %s' % (os.path.relpath(p, base)[:70], gib(s)))
            print('    estimated saving at three quarters: %s  (dry run)' % gib(total * 0.75))
            continue
        ipath = os.path.join(base, 'COMPRESSED.csv')
        new_index = not os.path.exists(ipath)
        saved = 0
        with open(ipath, 'a', newline='') as f:
            w = csv.writer(f)
            if new_index:
                w.writerow(['file', 'bytes_before', 'bytes_after', 'percent_saved'])
            for i, (p, s, m) in enumerate(items, 1):
                saved += compress(p, s, m, w)
                if i % 500 == 0:
                    f.flush(); print('    %d of %d, %s saved' % (i, len(items), gib(saved)), flush=True)
        rp = os.path.join(base, 'RESTORE.sh')
        if not os.path.exists(rp):
            open(rp, 'w').write(RESTORE); os.chmod(rp, 0o755)
        print('  compressed %d files, %s reclaimed; index COMPRESSED.csv, undo with RESTORE.sh' % (len(items), gib(saved)))
        grand += saved
    du = shutil.disk_usage(ROOT)
    print('\ndisk after: %s free%s' % (gib(du.free), ('  (+%s)' % gib(grand)) if grand else ''))


if __name__ == '__main__':
    main()
