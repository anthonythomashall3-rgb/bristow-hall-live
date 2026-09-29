import re, sys
sys.path.insert(0, '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps/scripts')
from fetch import get
W='/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps'
idx=open(f'{W}/raw/deseret_sitemap_index_year.xml').read()
locs=re.findall(r'<loc>([^<]+)</loc>', idx)
want=[l for l in locs if re.search(r'/(19(7[5-9]|8\d|9[0-6])|2003)[-/]', l)]
out=open(f'{W}/deseret_candidates.txt','w')
for l in want:
    tag=re.search(r'sitemap2?/([^/]+)/', l).group(1)
    p,s,b=get(l.replace('&amp;','&'), f'deseret_sitemap_{tag}.xml')
    us=re.findall(r'<loc>([^<]+)</loc>', b.decode('utf-8','replace'))
    hits=[u for u in us if re.search(r'jobless|unemploy|claims', u, re.I)]
    print(tag, s, len(us), len(hits), flush=True)
    for h in hits: out.write(h+'\n')
