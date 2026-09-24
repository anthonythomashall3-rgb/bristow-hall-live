import json,urllib.request,os,time
KEY=os.environ["FRASER_API_KEY"]
def get(url):
    req=urllib.request.Request(url,headers={"X-API-Key":KEY})
    return json.load(urllib.request.urlopen(req,timeout=45))
def getr(url,tries=5):
    last=None
    for k in range(tries):
        try: return get(url)
        except Exception as e: last=e; time.sleep(1.2*(k+1))
    raise last
TARGETS=[(144,"employment_situation"),(60,"employment_earnings"),(189,"employment_earnings_us"),
         (77,"g17_industrial_production"),(55,"g123_industrial_production"),(46,"survey_current_business")]
st="research/_staging/fraser/_enum_status.txt"
summary={}
for tid,slug in TARGETS:
    items=[]; page=1; total=None; gaps=[]
    while True:
        try:
            d=getr(f"https://fraser.stlouisfed.org/api/title/{tid}/items?limit=100&page={page}")
        except Exception as e:
            gaps.append({"page":page,"error":str(e)}); page+=1
            if page>60: break
            continue
        total=d.get("total"); recs=d.get("records",[])
        if not recs: break
        for r in recs:
            oi=r.get("originInfo") or {}
            loc=r.get("location") or {}
            ri=r.get("recordInfo") or {}
            rid=ri.get("recordIdentifier"); rid=rid[0] if isinstance(rid,list) and rid else rid
            ti=(r.get("titleInfo") or [{}]); itl=ti[0].get("title","") if ti else ""
            pdf=loc.get("pdfUrl"); pdf=pdf[0] if isinstance(pdf,list) and pdf else pdf
            txt=loc.get("textUrl"); txt=txt[0] if isinstance(txt,list) and txt else txt
            pg=loc.get("url"); pg=pg[0] if isinstance(pg,list) and pg else pg
            pd=r.get("physicalDescription") or {}
            items.append({"rid":rid,"item_title":itl,"sortDate":oi.get("sortDate"),
                "dateIssued":oi.get("dateIssued"),"frequency":oi.get("frequency"),
                "pdfUrl":pdf,"textUrl":txt,"pageUrl":pg,"extent":pd.get("extent")})
        open(st,"w").write(f"{slug} page {page} items {len(items)}/{total} gaps={len(gaps)}\n")
        if len(items)>=(total or 0): break
        page+=1; time.sleep(0.08)
    json.dump({"title_id":tid,"slug":slug,"total_declared":total,"items_enumerated":len(items),
               "gaps":gaps,"items":items}, open(f"research/_staging/fraser/{slug}_items.json","w"))
    # date reach
    dates=sorted([i["sortDate"] for i in items if i.get("sortDate")])
    summary[slug]={"title_id":tid,"n_items":len(items),"n_with_date":len(dates),
        "earliest":dates[0] if dates else None,"latest":dates[-1] if dates else None,
        "n_with_pdf":sum(1 for i in items if i.get("pdfUrl")),"gaps":len(gaps)}
    open(st,"w").write(f"{slug} DONE items {len(items)} earliest {summary[slug]['earliest']}\n")
json.dump(summary,open("research/_staging/fraser/_enum_summary.json","w"),indent=1)
open(st,"w").write("ALL_DONE\n")
