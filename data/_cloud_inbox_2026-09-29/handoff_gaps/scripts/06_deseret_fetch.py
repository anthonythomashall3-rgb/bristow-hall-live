import re, sys, html, json
sys.path.insert(0, '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps/scripts')
from fetch import get
W='/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps'
def ds_text(b):
    t=b.decode('utf-8','replace')
    title=re.search(r'<title>(.*?)</title>',t,re.S); title=html.unescape(title.group(1)).strip() if title else ''
    pub=re.search(r'"datePublished"\s*:\s*"([^"]+)"',t); pub=pub.group(1) if pub else ''
    # Arc fusion: article body in <p> elements with class containing 'paragraph' or in Fusion.globalContent JSON
    m=re.search(r'Fusion\.globalContent\s*=\s*(\{.*?\});\s*Fusion\.',t,re.S)
    body=''
    if m:
        try:
            gc=json.loads(m.group(1))
            els=gc.get('content_elements',[])
            body='\n'.join(html.unescape(re.sub(r'<[^>]+>','',e.get('content',''))) for e in els if e.get('type') in ('text','header'))
            pub=gc.get('display_date') or gc.get('first_publish_date') or pub
        except Exception as e:
            body=''
    if not body:
        body='\n'.join(html.unescape(re.sub(r'<[^>]+>','',p)).strip() for p in re.findall(r'<p[^>]*>(.*?)</p>',t,re.S))
    return title,pub,body
if __name__=='__main__':
    for u in open(f'{W}/deseret_fetch_list.txt').read().split():
        m=re.search(r'deseret.com/(\d{4})/(\d+)/(\d+)/(\d+)/',u)
        name=f'deseret_{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}_{m.group(4)}.html'
        p,s,b=get(u,name,gz=True)
        ti,pub,body=ds_text(b)
        print(s, name, pub[:10], len(body), ti[:60], flush=True)
