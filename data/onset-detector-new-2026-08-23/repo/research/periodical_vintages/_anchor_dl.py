import os,json,urllib.request,time,hashlib,datetime
OUT="research/periodical_vintages";ST=OUT+"/staging"
K=os.environ["FRASER_API_KEY"];GK=os.environ.get("GOVINFO_API_KEY","DEMO_KEY")
UTC=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
os.makedirs(ST,exist_ok=True)
def fetch(url,headers,timeout=120):
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=timeout) as r:
        return r.getcode(),r.read()
import datetime as _dt
def d2(s):
    try:return _dt.date.fromisoformat(s[:10])
    except:return None
man=[]
# FRASER anchors: pick issue nearest 1948-01 + latest, per family
for slug in ["survey_current_business","federal_reserve_bulletin"]:
    D=json.load(open(f"{OUT}/{slug}_issues.json"))
    its=[i for i in D["items"] if i.get("pdfUrl") and i.get("sortDate")]
    its.sort(key=lambda i:i["sortDate"])
    a=_dt.date(1948,1,1)
    near48=min(its,key=lambda i:abs((d2(i["sortDate"])-a).days))
    picks=[("anchor_1948",near48),("latest",its[-1])]
    for tag,it in picks:
        url=it["pdfUrl"];dest=f"{ST}/{slug}__{tag}__{it['rid']}.pdf"
        rec={"family":slug,"source":"FRASER","tag":tag,"rid":it["rid"],"sortDate":it["sortDate"],
             "item_title":it.get("item_title"),"pdfUrl":url,"pageUrl":it.get("pageUrl"),"fetch_utc":UTC()}
        try:
            code,body=fetch(url,{"X-API-Key":K,"User-Agent":"RMV2-PERIODICAL-VINTAGES"})
            open(dest,"wb").write(body)
            rec.update({"http_status":code,"bytes":len(body),"sha256":hashlib.sha256(body).hexdigest(),"local_path":dest})
        except Exception as e:
            rec.update({"http_status":None,"bytes":0,"error":str(e)})
        man.append(rec);print(f"{slug} {tag} {rec.get('http_status')} {rec.get('bytes')}B {rec.get('sha256','')[:12]}")
        time.sleep(0.2)
# ERP anchor: earliest (1948) + latest package -> govinfo pdf
E=json.load(open(f"{OUT}/erp_issues.json"))
pk=[p for p in E["packages"] if p.get("dateIssued")]
pk.sort(key=lambda p:p["dateIssued"])
for tag,p in [("anchor_1948",pk[0]),("latest",pk[-1])]:
    pid=p["packageId"];url=f"https://api.govinfo.gov/packages/{pid}/pdf?api_key={GK}"
    dest=f"{ST}/erp__{tag}__{pid}.pdf"
    rec={"family":"economic_report_president","source":"GovInfo","tag":tag,"packageId":pid,
         "dateIssued":p["dateIssued"],"title":(p.get('title') or '')[:80],"pdfUrl":f"https://api.govinfo.gov/packages/{pid}/pdf","fetch_utc":UTC()}
    try:
        code,body=fetch(url,{"User-Agent":"RMV2-PERIODICAL-VINTAGES"})
        open(dest,"wb").write(body)
        rec.update({"http_status":code,"bytes":len(body),"sha256":hashlib.sha256(body).hexdigest(),"local_path":dest})
    except Exception as e:
        rec.update({"http_status":None,"bytes":0,"error":str(e)})
    man.append(rec);print(f"erp {tag} {rec.get('http_status')} {rec.get('bytes')}B {rec.get('sha256','')[:12]}")
    time.sleep(0.3)
json.dump({"generated_utc":UTC(),"anchors":man},open(f"{OUT}/_anchor_download_manifest.json","w"),indent=1)
ok=sum(1 for m in man if m.get("bytes",0)>0)
print(f"ANCHOR_DONE ok={ok}/{len(man)} bytes={sum(m.get('bytes',0) for m in man)}")
