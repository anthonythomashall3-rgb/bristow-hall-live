import re, sys
sys.path.insert(0, '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps/scripts')
from fetch import get
W='/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps'
idx=open(f'{W}/raw/probe_latimes_sitemap.xml').read()
months=[m for m in re.findall(r'sitemap-(\d{6})\.xml', idx) if '198401'<=m<='199612' or m in ('200305','200306')]
out=open(f'{W}/latimes_candidates.txt','w')
for m in months:
    p,s,b=get(f'https://www.latimes.com/sitemaps/sitemap-{m}.xml', f'latimes_sitemap_{m}.xml')
    locs=re.findall(r'<loc>([^<]+)</loc>', b.decode('utf-8','replace'))
    hits=[l for l in locs if re.search(r'jobless|unemploy|claims|layoff|benefit', l, re.I)]
    print(m, s, len(locs), len(hits), flush=True)
    for h in hits: out.write(h+'\n')
