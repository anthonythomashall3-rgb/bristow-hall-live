import urllib.request,json,hashlib,os,datetime,ssl
BASE="research/_staging/aggregators"
def now(): return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
def raw(url,timeout=45):
    req=urllib.request.Request(url,headers={"User-Agent":"RMV2-prefetch/1.0"})
    r=urllib.request.urlopen(req,timeout=timeout)
    return r.getcode(), dict(r.headers), r.read()

# TARGET LIST = proprietary composites FRED+publisher-direct could NOT reach
# (CH-R118 permanent_gaps + B-ACQ-LEI-CEI licensed-skips: NAPMNOI=ISM New Orders, ISM PMI, CB LCI)
targets=[
 {"key":"ISM_neword_in","provider":"DBnomics","dataset":"ISM/neword","series":"ISM/neword/in",
  "url":"https://api.db.nomics.world/v22/series/ISM/neword/in?observations=true",
  "upstream_publisher":"Institute for Supply Management (ISM)","fills":"NAPMNOI (ISM Manufacturing New Orders diffusion index) — FRED 400 / LEI component"},
 {"key":"ISM_pmi_pm","provider":"DBnomics","dataset":"ISM/pmi","series":"ISM/pmi/pm",
  "url":"https://api.db.nomics.world/v22/series/ISM/pmi/pm?observations=true",
  "upstream_publisher":"Institute for Supply Management (ISM)","fills":"ISM Manufacturing PMI headline"},
 {"key":"ISM_nm-neword_in","provider":"DBnomics","dataset":"ISM/nm-neword","series":"ISM/nm-neword/in",
  "url":"https://api.db.nomics.world/v22/series/ISM/nm-neword/in?observations=true",
  "upstream_publisher":"Institute for Supply Management (ISM)","fills":"ISM Non-manufacturing New Orders diffusion index"},
 {"key":"ISM_nm-pmi_pm","provider":"DBnomics","dataset":"ISM/nm-pmi","series":"ISM/nm-pmi/pm",
  "url":"https://api.db.nomics.world/v22/series/ISM/nm-pmi/pm?observations=true",
  "upstream_publisher":"Institute for Supply Management (ISM)","fills":"ISM Non-manufacturing PMI headline"},
 # Nasdaq Data Link free tier — probe, expect key-gate
 {"key":"NASDAQ_probe","provider":"NasdaqDataLink","dataset":"free-tier","series":"probe",
  "url":"https://data.nasdaq.com/api/v3/datasets/ISM/MAN_PMI.json?rows=1",
  "upstream_publisher":"(probe)","fills":"aggregator alt-route probe"},
]
objects=[]; failures=[]
for t in targets:
    prov_dir=os.path.join(BASE, t["provider"].lower())
    os.makedirs(prov_dir,exist_ok=True)
    try:
        code,hdr,body=raw(t["url"])
        if code!=200:
            failures.append({**{k:t[k] for k in('key','provider','series','url','upstream_publisher')},"http_status":code,"reason":"non-200","fetch_utc":now()})
            continue
        fn=os.path.join(prov_dir, t["key"]+".json")
        open(fn,"wb").write(body)
        sha=hashlib.sha256(body).hexdigest()
        side={"path":os.path.relpath(fn),"url":t["url"],"http_status":code,
              "last_modified":hdr.get("Last-Modified"),"bytes":len(body),"sha256":sha,
              "fetch_utc":now(),"tier":"aggregator","provider":t["provider"],
              "upstream_publisher":t["upstream_publisher"],"dataset":t["dataset"],
              "series":t["series"],"fills":t["fills"],
              "normalisation":"none (verbatim API bytes, B-FIX-1)"}
        open(fn+".sidecar.json","w").write(json.dumps(side,indent=1))
        objects.append(side)
    except urllib.error.HTTPError as e:
        failures.append({**{k:t[k] for k in('key','provider','series','url','upstream_publisher')},"http_status":e.code,"reason":"HTTPError %s"%e.reason,"fetch_utc":now()})
    except Exception as e:
        failures.append({**{k:t[k] for k in('key','provider','series','url','upstream_publisher')},"http_status":None,"reason":"%s: %s"%(type(e).__name__,str(e)[:120]),"fetch_utc":now()})

open(os.path.join(BASE,"_result.json"),"w").write(json.dumps({"objects":objects,"failures":failures},indent=1))
print("fetched",len(objects),"failed",len(failures))
for o in objects: print("  OK ",o["series"],o["bytes"],"B",o["upstream_publisher"])
for f in failures: print("  FAIL",f["series"],f.get("http_status"),f["reason"])
