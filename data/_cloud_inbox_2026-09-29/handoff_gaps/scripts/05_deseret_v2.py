import re, sys, gzip, os, collections
sys.path.insert(0, '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps/scripts')
from fetch import get
W='/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps'
out=open(f'{W}/deseret_v2_candidates.txt','a')
for i in [int(x) for x in sys.argv[1:]]:
    name=f'deseret_v2_articles-{i}.xml'
    if os.path.exists(f'{W}/raw/{name}.gz'):
        t=gzip.open(f'{W}/raw/{name}.gz','rt').read()
    else:
        p,s,b=get(f'https://uploads.deseret.com/sitemapsV2/deseretnews/sitemap-articles-{i}.xml', name)
        t=b.decode('utf-8','replace')
        os.system(f'gzip -f {W}/raw/{name}')
    u=re.findall(r'<loc>([^<]+)</loc>',t)
    yrs=collections.Counter(m.group(1) for m in (re.search(r'deseret.com/(?:[a-z-]+/)*(\d{4})/\d',x) for x in u) if m)
    hits=[x for x in u if re.search(r'/(19(8[4-9]|9[0-6])|2003)/',x) and re.search(r'jobless|unemploy|claims', x, re.I)]
    for h in hits: out.write(h+'\n')
    print(i, len(u), sorted(yrs.items())[:6], '...', len(hits), flush=True)
