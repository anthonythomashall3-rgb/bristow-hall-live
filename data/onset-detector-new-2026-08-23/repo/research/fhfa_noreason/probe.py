import json,re,random,time,urllib.request,urllib.parse,collections,os
key=None
for line in open('live_data/config/local.env'):
    line=line.strip()
    if line.startswith('FRED_API_KEY') and '=' in line:
        key=line.split('=',1)[1].strip().strip('"').strip("'")
assert key, 'no key'
ids=json.load(open('research/fhfa_noreason/_noreason_ids.json'))
def state_of(sid):
    m=re.match(r'ATNHPIUS(\d{2})\d{3}A$',sid)
    if m: return m.group(1)
    m=re.match(r'(?:PCPI|REALGDPALL)(\d{2})\d{3}$',sid)
    if m: return m.group(1)
    return 'XX'
by=collections.defaultdict(list)
for s in ids: by[state_of(s)].append(s)
rng=random.Random(789)
sample=[]
PER=3
for st in sorted(by):
    pool=sorted(by[st]); rng.shuffle(pool)
    sample+= [(st,s) for s in pool[:PER]]
print('strata:',len(by),'sample size:',len(sample))
def probe(sid):
    url='https://api.stlouisfed.org/fred/series/observations?'+urllib.parse.urlencode(
        {'series_id':sid,'api_key':key,'file_type':'json'})
    try:
        r=urllib.request.urlopen(url,timeout=30)
        j=json.loads(r.read())
        obs=j.get('observations',[])
        real=[o for o in obs if o.get('value','.') not in ('.','')]
        return 200,len(obs),len(real)
    except urllib.error.HTTPError as e:
        return e.code,0,0
    except Exception as e:
        return -1,0,0
out=[]
for st,sid in sample:
    code,nobs,nreal=probe(sid)
    if code==200 and nreal>0: cls='PROVEN_FABRICATED'
    elif code==200 and nobs>=0 and nreal==0: cls='STILL_UNKNOWN'  # series exists but empty
    elif code in (400,404): cls='PROVEN_ABSENT'
    else: cls='STILL_UNKNOWN'
    out.append({'state':st,'series':sid,'http':code,'n_obs':nobs,'n_real':nreal,'class':cls})
    time.sleep(0.4)
    if cls=='PROVEN_FABRICATED':
        print('!! FABRICATED',sid,code,nobs,nreal); break
json.dump(out,open('research/fhfa_noreason/probe_results.json','w'),indent=1)
c=collections.Counter(o['class'] for o in out)
print('CLASS COUNTS:',dict(c))
print('sample probed:',len(out))
