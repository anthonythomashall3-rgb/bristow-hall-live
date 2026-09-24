import json,urllib.request,os,time,sys
KEY=os.environ["FRASER_API_KEY"]
def get(url):
    req=urllib.request.Request(url,headers={"X-API-Key":KEY})
    return json.load(urllib.request.urlopen(req,timeout=45))
def getr(url,tries=6):
    for k in range(tries):
        try: return get(url)
        except Exception as e:
            last=e; time.sleep(1.5*(k+1))
    raise last
titles=[];page=1;total=None
st="research/_staging/fraser/_index_status.txt"
while True:
    d=getr(f"https://fraser.stlouisfed.org/api/title?limit=100&page={page}")
    total=d.get("total"); recs=d.get("records",[])
    if not recs: break
    for r in recs:
        ti=(r.get("titleInfo") or [{}]); title=ti[0].get("title","") if ti else ""
        sub=ti[0].get("subTitle","") if ti else ""
        ri=r.get("recordInfo") or {}; rid=ri.get("recordIdentifier")
        if isinstance(rid,list): rid=rid[0] if rid else None
        oi=r.get("originInfo") or {}; sd=oi.get("sortDate") if isinstance(oi,dict) else None
        titles.append({"id":rid,"title":title,"sub":sub,"sortDate":sd})
    json.dump(titles,open("research/_staging/fraser/_title_index.json","w"))  # checkpoint
    open(st,"w").write(f"page {page} got {len(titles)}/{total}\n")
    if len(titles)>=(total or 0): break
    page+=1; time.sleep(0.1)
open(st,"w").write(f"DONE {len(titles)}/{total}\n")
