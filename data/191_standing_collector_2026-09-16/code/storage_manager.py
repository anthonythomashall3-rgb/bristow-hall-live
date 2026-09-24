#!/usr/bin/env python3
"""Keeping the archive inside the disk it lives on (collection 191), 18 September 2026.

The warehouse grew from three gigabytes to fourteen in a day, and the print archive is thirty-two. At that rate the
disk is the binding constraint within a fortnight, so this reports where the space goes and thins the one thing that
can be thinned without losing information the programme relies on.

What it does NOT touch: any raw file the collector maintains, any parsed output, any first print, any archive capture.
Those are the record.

What it thins: the dated vintage copies, and only by age. A vintage exists to answer "what did this source show on
that day". For the last ninety days that question is asked at daily resolution; before that, weekly; before a year,
monthly. Copies dropped are always copies whose neighbours are kept, and a file with only one vintage is never
touched. The default is a dry run: it prints what it would remove and removes nothing unless --apply is given.

Run:  python3 code/storage_manager.py            report and dry run
      python3 code/storage_manager.py --apply    actually thin
"""
import os, re, sys, time, shutil, collections, datetime

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
WH = os.path.join(HERE, 'warehouse')
DATED = re.compile(r'^(\d{4})-(\d{2})-(\d{2})__(.+)$')


def gib(b):
    return '%.1f GiB' % (b / 2 ** 30) if b >= 2 ** 30 else '%.0f MiB' % (b / 2 ** 20)


def report():
    du = shutil.disk_usage(ROOT)
    print('disk: %s free of %s (%.0f%% used)' % (gib(du.free), gib(du.total), 100 * du.used / du.total))
    sizes = []
    for name in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, name)
        if not os.path.isdir(p) or name.startswith('.') or name.startswith('_'):
            continue
        if os.path.islink(p):
            continue                      # several entries are aliases to folders already counted: following them
                                          # made the archive look thirty-four gigabytes larger than it is
        n = b = 0
        for dp, dn, fn in os.walk(p, followlinks=False):
            for f in fn:
                try:
                    b += os.path.getsize(os.path.join(dp, f)); n += 1
                except OSError:
                    pass
        if b > 100 * 2 ** 20:
            sizes.append((b, n, name))
    sizes.sort(reverse=True)
    print('\ncollections over 100 MiB:')
    for b, n, name in sizes[:14]:
        print('  %-52s %10s  %7d files' % (name[:52], gib(b), n))
    return sum(b for b, _, _ in sizes)


def vintages():
    """Every vintage folder, grouped by the file it is a copy of."""
    groups = collections.defaultdict(list)
    total = 0
    for dp, dn, fn in os.walk(WH):
        if os.path.basename(dp) != 'vintages':
            continue
        for f in fn:
            m = DATED.match(f)
            if not m:
                continue
            p = os.path.join(dp, f)
            try:
                b = os.path.getsize(p)
            except OSError:
                continue
            total += b
            groups[(dp, m.group(4))].append((m.group(1) + '-' + m.group(2) + '-' + m.group(3), p, b))
    return groups, total


def thin(apply=False):
    groups, total = vintages()
    print('\nvintage copies: %s in %d families' % (gib(total), len(groups)))
    today = datetime.date.today()
    drop, kept_bytes, drop_bytes = [], 0, 0
    for (_, base), items in groups.items():
        items.sort()
        if len(items) < 3:
            kept_bytes += sum(b for _, _, b in items); continue
        keep = {items[0][0], items[-1][0]}          # the first and the newest are always kept
        seen_week, seen_month = set(), set()
        for d, p, b in items:
            age = (today - datetime.date.fromisoformat(d)).days
            if age <= 90:
                keep.add(d)                          # daily resolution for three months
            elif age <= 365:
                wk = datetime.date.fromisoformat(d).isocalendar()[:2]
                if wk not in seen_week:
                    seen_week.add(wk); keep.add(d)   # weekly for the rest of the year
            else:
                mo = d[:7]
                if mo not in seen_month:
                    seen_month.add(mo); keep.add(d)  # monthly beyond that
        for d, p, b in items:
            if d in keep:
                kept_bytes += b
            else:
                drop.append(p); drop_bytes += b
    print('would keep %s, remove %s in %d copies' % (gib(kept_bytes), gib(drop_bytes), len(drop)))
    if not apply:
        for p in drop[:8]:
            print('   would remove', os.path.relpath(p, WH))
        if drop:
            print('   (dry run: pass --apply to remove)')
        return 0
    n = 0
    for p in drop:
        try:
            os.remove(p); n += 1
        except OSError:
            pass
    print('removed %d copies, %s reclaimed' % (n, gib(drop_bytes)))
    return drop_bytes


def main():
    report()
    thin(apply='--apply' in sys.argv)
    print('\nWhat cannot be thinned, and why: raw files the collector maintains are the current record; parsed panels '
          'and first prints are the research output; archive captures are the only copy that exists anywhere of what '
          'a page said on a day. Only dated duplicates of unchanged-then-changed files are candidates, and only by '
          'age.')


if __name__ == '__main__':
    main()
