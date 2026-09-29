"""Scan the UPI Archives year text index (reverse chronological, pagination capped near page 100-120) down to a stop date;
keep raw pages gzipped; list items whose title/snippet is about weekly UI claims."""
import re, sys, html, json
sys.path.insert(0, '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps/scripts')
from fetch import get
W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps'
PAT = re.compile(r'jobless|unemployment (?:claims|benefits|insurance|compensation)|claims for (?:unemployment|jobless)|initial claims|insured unemployment|economy at a glance|news at a glance|business (?:briefs|digest)|economic indicators', re.I)
def group(y):
    return '1980-1989' if y < 1990 else ('1990-1999' if y < 2000 else '2000-2004')
def scan(y, stop, maxp=130):
    out = []
    for p in range(1, maxp + 1):
        url = f'https://www.upi.com/Archives/{group(y)}/text/{y}/' + (f'p{p}/' if p > 1 else '')
        path, s, b = get(url, f'upi_idx_{y}_p{p}.html', gz=True)
        t = b.decode('utf-8', 'replace')
        pg = re.search(r'Page (\d+) of (\d+)', t)
        if not pg or int(pg.group(1)) != p:
            print(y, 'page', p, 'not served (cap)', flush=True); break
        items = re.findall(r'<a href="(https://www\.upi\.com/Archives/(\d{4})/(\d\d)/(\d\d)/[^"]+)" title="([^"]*)" class="row">.*?<div class="content">(.*?)</div>', t, re.S)
        dates = [f'{a}-{b_}-{c}' for _, a, b_, c, _, _ in items]
        for u, a, b_, c, ti, sn in items:
            txt = html.unescape(ti + ' || ' + re.sub(r'<[^>]+>', '', sn))
            if PAT.search(txt):
                out.append((f'{a}-{b_}-{c}', u, txt[:300]))
        if dates and min(dates) < stop:
            print(y, 'reached', min(dates), 'at page', p, flush=True); break
    return out
if __name__ == '__main__':
    y, stop = int(sys.argv[1]), sys.argv[2]
    res = scan(y, stop)
    with open(f'{W}/upi_index_hits.tsv', 'a') as f:
        for r in res:
            f.write('\t'.join(r) + '\n')
    for r in res: print(r)
