"""B-RESV-PARSER-1 probe (§5.1 read-only). Fetch 7 reservation routes, measure
from bytes, cache payloads. NO store write, NO config write, NO parser authored."""
import json, hashlib, urllib.request, urllib.error, os, sys
from pathlib import Path
CACHE=Path("research/prefetch/bresv1"); CACHE.mkdir(parents=True, exist_ok=True)
UA={"User-Agent":"Mozilla/5.0 rmv2-probe"}
TARGETS={
 "fema_disasters":"https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries?$top=5",
 "nyfed_business_leaders":"https://www.newyorkfed.org/medialibrary/media/survey/business_leaders/data/bls_notseasonallyadjusted_allseries.csv",
 "bls_empsit_cdx_wayback_snapshots":"http://web.archive.org/cdx/search/cdx?url=bls.gov/news.release/empsit.nr0.htm&output=json&fl=timestamp,statuscode,digest&limit=2000&collapse=digest",
 "dol_ui_cdx_wayback_snapshots":"http://web.archive.org/cdx/search/cdx?url=dol.gov/ui/data.pdf&output=json&fl=timestamp,statuscode,digest&limit=2000&collapse=digest",
 "bls_jolts_cdx_wayback_snapshots":"http://web.archive.org/cdx/search/cdx?url=bls.gov/news.release/jolts.nr0.htm&output=json&fl=timestamp,statuscode,digest&limit=2000&collapse=digest",
 "oecd_revision_us_sdmx_dataflow":"https://sdmx.oecd.org/public/rest/dataflow/all/all/latest",
 "cdc_provisional_deaths":"https://wonder.cdc.gov/controller/datarequest/D176",
}
out={}
for sid,url in TARGETS.items():
    rec={"url":url}
    try:
        req=urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=40) as r:
            body=r.read(); ct=r.headers.get("Content-Type","")
        p=CACHE/(sid+".body"); p.write_bytes(body)
        rec.update(http=200, bytes=len(body), content_type=ct,
                   sha256=hashlib.sha256(body).hexdigest())
        head=body[:220].decode("utf-8","replace").replace("\n","\\n")
        rec["head"]=head
    except urllib.error.HTTPError as e:
        rec.update(http=e.code, err=str(e), body_head=e.read()[:200].decode("utf-8","replace"))
    except Exception as e:
        rec.update(http=0, err=repr(e))
    out[sid]=rec
    print(sid, rec.get("http"), rec.get("bytes"), rec.get("content_type",""))
json.dump(out, open("research/bresv1/probe_measure.json","w"), indent=1)
print("WROTE research/bresv1/probe_measure.json")
