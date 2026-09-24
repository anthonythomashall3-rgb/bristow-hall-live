"""B-PROBE-2 §2 wayback CDX density probe. Read-only GETs to web.archive.org CDX.
Serial, one request at a time (archive.org politeness). Writes cdx_density.json.
URL set = 3 registered CDX lanes (planned_sources) + curated publisher release pages
for the 13 blocking headline members. Curation is EXPLICIT (no silent cap)."""
import json, time, urllib.request, urllib.error, urllib.parse
from pathlib import Path

H = Path("research/probe2_scratch")

# url : (basis members, family, note). 3 registered lanes flagged registered=True.
URLS = [
  ("bls.gov/news.release/empsit.nr0.htm", "PAYEMS,UNRATE", "bls_empsit", True,  "Employment Situation"),
  ("dol.gov/ui/data.pdf",                 "ICSA,IURSA",    "dol_ui",     True,  "DOL weekly UI claims"),
  ("bls.gov/news.release/jolts.nr0.htm",  "(JOLTS)",       "bls_jolts",  True,  "JOLTS (registered, non-blocking)"),
  ("census.gov/construction/nrc/index.html","HOUST,PERMIT","census_nrc", False, "New Residential Construction"),
  ("federalreserve.gov/releases/g17/current/","INDPRO,TCU","fed_g17",    False, "Industrial Production G.17"),
  ("philadelphiafed.org/research-and-data/regional-economy/business-outlook-survey","GACDFSA066","philly_bos",False,"Philly Business Outlook Survey"),
  ("chicagofed.org/publications/nfci/index","NFCI",        "chicago_nfci",False,"Chicago Fed NFCI"),
  ("census.gov/mtis/index.html",          "CMRMTSPL",      "census_mtis",False, "Manufacturing & Trade Inv & Sales"),
  ("sca.isr.umich.edu/",                  "UMCSENT",       "umich_sca",  False, "U.Mich Surveys of Consumers (proprietary)"),
]

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent":"rmv2-probe/1.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.status, r.read()

out = {}
for target, members, fam, registered, note in URLS:
    q = ("http://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(target,safe='') +
         "&output=json&from=19960101&to=20191231&fl=timestamp,statuscode,digest"
         "&collapse=timestamp:6&limit=5000")
    rec = {"url": target, "members": members, "family": fam, "registered": registered, "note": note}
    try:
        status, body = get(q)
        rows = json.loads(body) if body.strip() else []
        data = rows[1:] if rows and rows[0][0]=="timestamp" else rows
        peryear = {}
        for ts, sc, dg in data:
            y = ts[:4]; peryear[y] = peryear.get(y,0)+1
        rec.update({"http_status": status, "total_monthly_captures": len(data),
                    "captures_per_year": dict(sorted(peryear.items())),
                    "first_capture": (data[0][0] if data else None),
                    "last_capture": (data[-1][0] if data else None),
                    "status_codes": sorted({r[1] for r in data})})
    except urllib.error.HTTPError as e:
        rec.update({"http_status": e.code, "error": e.read().decode("utf-8","replace")[:200]})
    except Exception as e:
        rec.update({"http_status": None, "error": repr(e)[:200]})
    out[fam] = rec
    print(fam, rec.get("http_status"), "monthly_caps=", rec.get("total_monthly_captures"),
          "yrs=", len(rec.get("captures_per_year",{})), rec.get("first_capture"))
    time.sleep(2.0)  # archive.org politeness

(H/"cdx_density.json").write_text(json.dumps(out, indent=1)+"\n")
print("WROTE cdx_density.json")
