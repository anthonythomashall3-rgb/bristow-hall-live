"""B-ACQ-RESIDUAL-11 fetch — prefetch FRED bytes for the 8 truly-actionable absent
series (the 2026-08-08 census residual). All PROVEN fred_json_api shape (JSON series
+ observations). ZERO new parser shapes (section 6.2). ADSINDEX excluded (parser job,
B-UNBLOCK-3). Two OECD/World Bank international series excluded (owner deferral).

BUSLOANS fetched for identity comparison ONLY (already in store; TOTCI vs BUSLOANS is
the section 3.5 identity question) — it is NOT landed.

Key read via engine (never shell env, never disk). fetch_manifest.jsonl matches the
lander's reader: fields fred_id, sha256, fetch_utc, status; url stores <KEY> redaction.
"""
import hashlib
import json
import sys
import time

sys.path.insert(0, ".")
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from tools.rmv2_data_cloudflare.rmv2_connectors import engine

KEY = engine._read_credential("FRED_API_KEY")
if not KEY:
    raise SystemExit("FRED_API_KEY did not resolve")

OUT = Path("research/prefetch/bacq_residual11")
OUT.mkdir(parents=True, exist_ok=True)

# series_id -> (land?, reason)
CANDS = [
    ("GAMFSA066MSFRBNY", True,  "Empire State mfg general business conditions (2 of 5 regional Feds absent)"),
    ("RCPHBS",           True,  "Richmond Fed mfg composite (regional Fed set)"),
    ("JTSQUL",           True,  "JOLTS quits — leading labor flow; hires+layoffs enabled, quits absent"),
    ("DRALACBN",         True,  "Delinquency rate all loans all commercial banks"),
    ("CORCACBS",         True,  "Charge-off rate all loans all commercial banks (realized loss)"),
    ("TOTCI",            True,  "C&I loans alt series — IDENTITY vs BUSLOANS must be NON-IDENTITY before land (3.5)"),
    ("BAAFFM",           True,  "Moody's Baa less fed funds — policy-stance credit spread"),
    ("USPHCI",           True,  "US coincident index (Phil Fed) — IDENTITY vs state coincidents check (3.5)"),
    ("BUSLOANS",         False, "IDENTITY COMPARATOR ONLY for TOTCI — already in store, NOT landed"),
]


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "rmv2-bacq-residual11/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.getcode(), r.read()


def _redact(url):
    return url.replace(KEY, "<KEY>")


def main():
    man = open(OUT / "fetch_manifest.jsonl", "w")
    ok, skipped = 0, []
    for sid, land, reason in CANDS:
        meta_url = ("https://api.stlouisfed.org/fred/series?series_id=%s"
                    "&api_key=%s&file_type=json" % (sid, KEY))
        obs_url = ("https://api.stlouisfed.org/fred/series/observations?"
                   "series_id=%s&api_key=%s&file_type=json" % (sid, KEY))
        rec = {"candidate": reason, "fred_id": sid, "land": land,
               "kind": "fred_current_obs", "url": _redact(obs_url),
               "fetch_utc": _now()}
        try:
            mc, mb = _get(meta_url)
            if mc != 200:
                raise RuntimeError("meta http %d" % mc)
            mj = json.loads(mb)
            if not mj.get("seriess"):
                raise RuntimeError("no seriess in meta")
            oc, ob = _get(obs_url)
            if oc != 200:
                raise RuntimeError("obs http %d" % oc)
            oj = json.loads(ob)
            if "observations" not in oj:
                raise RuntimeError("no observations in obs")
        except (urllib.error.HTTPError, urllib.error.URLError,
                RuntimeError, ValueError) as exc:
            rec.update({"status": "skip", "error": str(exc)})
            man.write(json.dumps(rec, sort_keys=True) + "\n")
            skipped.append((sid, str(exc)))
            print("SKIP", sid, exc)
            time.sleep(0.4)
            continue
        (OUT / ("%s.meta.json" % sid)).write_bytes(mb)
        (OUT / ("%s.obs.json" % sid)).write_bytes(ob)
        sha = hashlib.sha256(ob).hexdigest()
        s = mj["seriess"][0]
        rec.update({"status": "ok", "http": 200, "bytes": len(ob),
                    "sha256": sha, "title": s.get("title"),
                    "frequency": s.get("frequency"),
                    "seasonal_adjustment": s.get("seasonal_adjustment_short"),
                    "units": s.get("units"),
                    "observation_start": s.get("observation_start"),
                    "observation_end": s.get("observation_end"),
                    "last_updated": s.get("last_updated")})
        man.write(json.dumps(rec, sort_keys=True) + "\n")
        ok += 1
        print("OK  ", sid, len(ob), "B", s.get("frequency"),
              s.get("observation_start"), "->", s.get("observation_end"))
        time.sleep(0.4)
    man.close()
    print("\nFETCH DONE ok=%d skip=%d" % (ok, len(skipped)))
    if skipped:
        print("SKIPPED:", skipped)


main()
