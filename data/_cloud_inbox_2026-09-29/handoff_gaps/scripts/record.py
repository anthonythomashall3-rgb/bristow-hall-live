"""Append a found print to found_prints.csv (dedup on series, week, print_kind, source_url)."""
import csv, os
W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps'
F = f'{W}/found_prints.csv'
COLS = ['series', 'week_ended', 'value', 'value_string', 'print_kind', 'pub_date', 'source_url', 'source_name',
        'year_proof', 'raw_file', 'note']
def add(**r):
    rows = list(csv.DictReader(open(F))) if os.path.exists(F) else []
    key = (r['series'], r['week_ended'], r['print_kind'], r['source_url'])
    if any((x['series'], x['week_ended'], x['print_kind'], x['source_url']) == key for x in rows):
        return False
    new = not os.path.exists(F) or os.path.getsize(F) == 0
    with open(F, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if new: w.writeheader()
        w.writerow({k: r.get(k, '') for k in COLS})
    return True
