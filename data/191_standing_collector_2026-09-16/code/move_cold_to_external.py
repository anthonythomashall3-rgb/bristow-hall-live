#!/usr/bin/env python3
"""Moving the cold collections to an external drive, verifiably (prepared 18 September 2026).

Run this once the external drive is mounted. It moves the two write-once collections that hold most of the weight —
198, the scanned print archive, and 112, the state high-frequency panel — to the drive, and leaves a symbolic link in
their place so every existing path keeps working. What stays local: the text extracted from the archive, which is what
anything actually reads.

It never deletes anything it has not first copied and verified. The order is copy, checksum every file, and only then
remove the original. If any file's checksum differs the move is abandoned with the original untouched.

  python3 code/move_cold_to_external.py --drive "/Volumes/YourDrive"           report what would move
  python3 code/move_cold_to_external.py --drive "/Volumes/YourDrive" --apply   do it
"""
import os, sys, shutil, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COLD = ['198_realtime_print_archives_2026-09-17', '112_state_high_frequency_2026-09-12']
KEEP_LOCAL = {'198_realtime_print_archives_2026-09-17': ['text_pages', 'index', 'logs', 'code', 'MANIFEST.csv']}


def gib(b):
    return '%.2f GiB' % (b / 2 ** 30)


def tree_size(p):
    n = b = 0
    for dp, dn, fn in os.walk(p):
        for f in fn:
            try:
                b += os.path.getsize(os.path.join(dp, f)); n += 1
            except OSError:
                pass
    return n, b


def sha(p, buf=1 << 20):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for ch in iter(lambda: f.read(buf), b''):
            h.update(ch)
    return h.hexdigest()


def move(name, drive, apply):
    src = os.path.join(ROOT, name)
    if not os.path.isdir(src) or os.path.islink(src):
        print('  %s: not a directory here (already moved?)' % name); return 0
    dst = os.path.join(drive, 'Onset Detector Data', name)
    n, b = tree_size(src)
    print('\n%s\n  %d files, %s  ->  %s' % (name, n, gib(b), dst))
    keep = KEEP_LOCAL.get(name, [])
    if keep:
        print('  staying on the internal disk: ' + ', '.join(keep))
    if not apply:
        print('  (report only; pass --apply)'); return 0
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    print('  copying...', flush=True)
    shutil.copytree(src, dst, dirs_exist_ok=True, symlinks=True)
    print('  verifying every file by checksum...', flush=True)
    bad = 0
    checked = 0
    for dp, dn, fn in os.walk(src):
        for f in fn:
            a = os.path.join(dp, f)
            c = os.path.join(dst, os.path.relpath(a, src))
            try:
                if not os.path.exists(c) or os.path.getsize(a) != os.path.getsize(c) or sha(a) != sha(c):
                    bad += 1
                    if bad < 6: print('    MISMATCH', os.path.relpath(a, src))
            except OSError:
                bad += 1
            checked += 1
            if checked % 2000 == 0: print('    checked', checked, flush=True)
    if bad:
        print('  %d files did not verify: NOTHING removed, the originals are untouched' % bad); return 0
    print('  all %d files verified' % checked)
    hold = os.path.join(ROOT, name + '.local')
    if keep:
        os.makedirs(hold, exist_ok=True)
        for k in keep:
            p = os.path.join(src, k)
            if os.path.exists(p): shutil.move(p, os.path.join(hold, k))
    shutil.rmtree(src)
    os.symlink(dst, src)
    if keep:
        for k in keep:
            p = os.path.join(hold, k)
            if os.path.exists(p): shutil.move(p, os.path.join(ROOT, name + '_local_' + k))
        try: os.rmdir(hold)
        except OSError: pass
    print('  moved; %s is now a link to the drive' % name)
    return b


def main():
    if '--drive' not in sys.argv:
        print(__doc__); return
    drive = sys.argv[sys.argv.index('--drive') + 1]
    apply = '--apply' in sys.argv
    if not os.path.isdir(drive):
        print('drive not mounted:', drive); return
    du = shutil.disk_usage(ROOT); dd = shutil.disk_usage(drive)
    print('internal: %s free of %s' % (gib(du.free), gib(du.total)))
    print('drive:    %s free of %s' % (gib(dd.free), gib(dd.total)))
    freed = sum(move(n, drive, apply) for n in COLD)
    if apply:
        du = shutil.disk_usage(ROOT)
        print('\ninternal now: %s free  (+%s)' % (gib(du.free), gib(freed)))
    print('\nAfterwards: in Time Machine, add the external drive itself and the two moved folders to the exclusion '
          'list, or the backup will copy the archive straight back onto the machine it came from.')


if __name__ == '__main__':
    main()
