"""Targeted LA Times scan: fetch the archive articles of one day and section(s) (URLs from the monthly sitemap),
keep raw gzipped, and list articles whose body mentions national weekly UI claims."""
import re, sys
sys.path.insert(0, '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps/scripts')
from fetch import get
from latext import la_text
W='/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps'
PAT=re.compile(r'jobless claims|claims for (?:state )?(?:jobless|unemployment)|initial claims|insured unemployment|unemployment (?:insurance|benefit)s?', re.I)
def day(date, sections=('fi',)):
    ym=date[:4]+date[5:7]
    sm=open(f'{W}/raw/latimes_sitemap_{ym}.xml').read()
    urls=sorted(set(re.findall(r'<loc>(https://www.latimes.com/archives/la-xpm-%s-(?:%s)-\d+-story.html)</loc>'%(date,'|'.join(sections)), sm)))
    hits=[]
    for u in urls:
        name='latimes_'+u.rsplit('/',1)[1]
        p,s,b=get(u,name,gz=True)
        ti,pub,body=la_text(b)
        if PAT.search(body) and re.search(r'Labor Department|Department of Labor', body):
            hits.append((u,p.rsplit('/',1)[1],ti))
    return urls,hits
if __name__=='__main__':
    secs=tuple(sys.argv[1].split(','))
    for d in sys.argv[2:]:
        urls,hits=day(d,secs)
        print(d, len(urls), hits, flush=True)
